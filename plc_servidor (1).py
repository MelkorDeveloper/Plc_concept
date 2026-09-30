#!/usr/bin/env python3
"""
plc_servidor.py (v3 - planta completa + VDF + secuenciador de formula)
------------------------------------------------------------------------
Simula el controlador (equivalente a un SNAP PAC) de la planta completa
de referencia: Granos, Harinas, Pre Mix, Acido Graso, Enteros, Mezcladora
y Salida. Habla Modbus TCP real, sin librerias externas.

Comportamiento fisico simulado (no solo numeros al azar):
  - Cada motor tiene un retardo de arranque real (contactor + termico)
    antes de que su discrete input de "corriendo" se active. Las
    valvulas responden mas rapido (accionamiento neumatico).
  - Mientras el motor de un silo esta "corriendo" de verdad (discreta=1),
    el nivel del silo baja y el peso de la bascula sube, simulando el
    flujo real de material.
  - Las basculas se pueden "tarar" (poner a cero) via un coil dedicado.
  - Los VDF (variador de frecuencia, tipo ABB) rampean su frecuencia real
    hacia la consigna, exponen una palabra de estado On/Run/Ref/Trip, y
    se les puede forzar una falla (para practicar el reset de un drive).
  - El secuenciador de formula dosifica ingrediente por ingrediente en
    la Bascula General, luego mezcla y descarga, incrementando el
    contador de Batch, igual que el panel "Formula/Batchs" real. Mientras
    la secuencia esta activa, el HMI no puede tocar manualmente los
    motores que estan bajo control automatico (interlock Auto/Manual).

Uso:
    python3 plc_servidor.py [puerto]   (por defecto 5020)
"""

import socket
import struct
import sys
import threading
import time

import mapa_senales as mapa

HOST = "0.0.0.0"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5020

lock = threading.Lock()

coils = [0] * mapa.N_COILS
discretas = [0] * mapa.N_DISCRETAS
holding_regs = [0] * mapa.N_HOLDING_REGS
input_regs = [0] * mapa.N_INPUT_REGS

# Consignas iniciales de los VDF: 50.0 Hz
for _v in mapa.VDFS:
    holding_regs[mapa.HOLDING_REG_DE_VDF_CONSIGNA[_v["tag"]]] = 500

# Estado interno de simulacion (no expuesto directo por Modbus)
tiempo_comandado = [0.0] * mapa.N_DISPOSITIVOS   # segundos que lleva el coil en ON
niveles_silo_kg = {s["nombre"]: float(s["nivel_inicial_kg"]) for s in mapa.SILOS}
peso_bascula_kg = {b["nombre"]: 0.0 for b in mapa.BASCULAS}
frecuencia_actual_hz = {v["tag"]: 0.0 for v in mapa.VDFS}
vdf_en_falla = {v["tag"]: False for v in mapa.VDFS}

# Estado del secuenciador de formula
estado_secuencia = 0     # 0 DETENIDO, 1 DOSIFICANDO, 2 MEZCLANDO, 3 DESCARGANDO
batch_actual = 0
ingrediente_idx = -1
peso_acumulado_previo_kg = 0.0
tiempo_mezclado_restante = 0
tiempo_descarga_restante = 0
destino_override = {}   # nombre de silo -> nombre de bascula (mientras dosifica el secuenciador)

RETARDO_ARRANQUE_MOTOR = 2.0     # segundos hasta que el contactor confirma marcha
RETARDO_ARRANQUE_VALVULA = 0.5   # segundos hasta que el limit switch confirma
TASA_DESCARGA_KG_S = 6.0         # velocidad de dosificacion simulada
RAMPA_VDF_HZ_S = 5.0             # aceleracion/frenado del variador
TOLERANCIA_REF_HZ = 1.0          # ventana para considerar "en referencia"
TIEMPO_MEZCLADO_S = 20           # duracion de la mezcla, para no esperar tanto en pruebas
TIEMPO_DESCARGA_S = 5
NOMBRE_BASCULA_FORMULA = "Bascula General (Formula)"


def _volcar_niveles_a_registros():
    for silo in mapa.SILOS:
        direccion = mapa.INPUT_REG_DE_SILO[silo["nombre"]]
        input_regs[direccion] = min(65535, max(0, int(niveles_silo_kg[silo["nombre"]])))
    for bas in mapa.BASCULAS:
        direccion = mapa.INPUT_REG_DE_BASCULA[bas["nombre"]]
        input_regs[direccion] = min(65535, max(0, int(peso_bascula_kg[bas["nombre"]] * 10)))


def _actualizar_confirmacion_dispositivos():
    """Cada motor/valvula tarda un tiempo real en confirmar que arranco."""
    for i, disp in enumerate(mapa.DISPOSITIVOS):
        comandado = coils[i]
        if comandado:
            tiempo_comandado[i] += 1.0
            retardo = (RETARDO_ARRANQUE_VALVULA if disp["tipo"] == "valvula"
                       else RETARDO_ARRANQUE_MOTOR)
            discretas[i] = 1 if tiempo_comandado[i] >= retardo else 0
        else:
            tiempo_comandado[i] = 0.0
            discretas[i] = 0


def _actualizar_flujo_material():
    """Silo -> bascula, solo si el motor esta REALMENTE corriendo."""
    for silo in mapa.SILOS:
        idx = mapa.COIL_DE[silo["motor"]]
        corriendo_de_verdad = discretas[idx]
        if corriendo_de_verdad and niveles_silo_kg[silo["nombre"]] > 0:
            destino = destino_override.get(silo["nombre"], silo["alimenta_a"])
            flujo = min(TASA_DESCARGA_KG_S, niveles_silo_kg[silo["nombre"]])
            niveles_silo_kg[silo["nombre"]] -= flujo
            peso_bascula_kg[destino] += flujo


def _procesar_tara():
    for bas in mapa.BASCULAS:
        direccion_tara = mapa.COIL_TARA_DE[bas["nombre"]]
        if coils[direccion_tara]:
            peso_bascula_kg[bas["nombre"]] = 0.0
            coils[direccion_tara] = 0


def _actualizar_vdfs():
    """Rampa de frecuencia real y palabra de estado On/Run/Ref/Trip, tipo ABB."""
    for v in mapa.VDFS:
        idx_motor = mapa.COIL_DE[v["motor"]]
        direccion_forzar = mapa.COIL_VDF_FORZAR_FALLA[v["tag"]]
        direccion_reset = mapa.COIL_VDF_RESET_FALLA[v["tag"]]

        if coils[direccion_forzar]:
            vdf_en_falla[v["tag"]] = True
            coils[direccion_forzar] = 0
        if coils[direccion_reset]:
            vdf_en_falla[v["tag"]] = False
            coils[direccion_reset] = 0

        estado_bits = 0
        if vdf_en_falla[v["tag"]]:
            # Un drive en falla corta el motor y decelera bruscamente
            coils[idx_motor] = 0
            tiempo_comandado[idx_motor] = 0.0
            discretas[idx_motor] = 0
            frecuencia_actual_hz[v["tag"]] = max(0.0, frecuencia_actual_hz[v["tag"]] - RAMPA_VDF_HZ_S * 2)
            estado_bits |= mapa.VDF_BIT_TRIP
        else:
            comandado = coils[idx_motor]
            corriendo = discretas[idx_motor]
            if comandado:
                estado_bits |= mapa.VDF_BIT_ON
            if corriendo:
                estado_bits |= mapa.VDF_BIT_RUN
                consigna = holding_regs[mapa.HOLDING_REG_DE_VDF_CONSIGNA[v["tag"]]] / 10.0
                actual = frecuencia_actual_hz[v["tag"]]
                if actual < consigna:
                    actual = min(consigna, actual + RAMPA_VDF_HZ_S)
                elif actual > consigna:
                    actual = max(consigna, actual - RAMPA_VDF_HZ_S)
                frecuencia_actual_hz[v["tag"]] = actual
                if abs(actual - consigna) < TOLERANCIA_REF_HZ:
                    estado_bits |= mapa.VDF_BIT_REF
            else:
                frecuencia_actual_hz[v["tag"]] = max(0.0, frecuencia_actual_hz[v["tag"]] - RAMPA_VDF_HZ_S)

        input_regs[mapa.INPUT_REG_DE_VDF_FRECUENCIA[v["tag"]]] = int(frecuencia_actual_hz[v["tag"]] * 10)
        input_regs[mapa.INPUT_REG_DE_VDF_ESTADO[v["tag"]]] = estado_bits


def _procesar_secuencia_formula():
    """Maquina de estados del batch: Dosificando -> Mezclando -> Descargando."""
    global estado_secuencia, batch_actual, ingrediente_idx
    global peso_acumulado_previo_kg, tiempo_mezclado_restante, tiempo_descarga_restante

    idx_formula = holding_regs[mapa.HOLDING_REG_FORMULA_SELECCIONADA]
    idx_formula = max(0, min(idx_formula, len(mapa.FORMULAS) - 1))
    formula = mapa.FORMULAS[idx_formula]

    # --- comandos de inicio/paro (pulsos autoreseteables) ---
    if coils[mapa.COIL_SECUENCIA_INICIAR]:
        if estado_secuencia == 0:
            estado_secuencia = 1
            ingrediente_idx = 0
            peso_acumulado_previo_kg = 0.0
            peso_bascula_kg[NOMBRE_BASCULA_FORMULA] = 0.0
        coils[mapa.COIL_SECUENCIA_INICIAR] = 0

    if coils[mapa.COIL_SECUENCIA_DETENER]:
        if ingrediente_idx >= 0:
            silo_actual = mapa.silo_por_nombre(formula["ingredientes"][ingrediente_idx]["silo"])
            if silo_actual:
                coils[mapa.COIL_DE[silo_actual["motor"]]] = 0
        coils[mapa.COIL_DE["M-441"]] = 0
        coils[mapa.COIL_DE["M-442"]] = 0
        destino_override.clear()
        estado_secuencia = 0
        ingrediente_idx = -1
        coils[mapa.COIL_SECUENCIA_DETENER] = 0

    # --- maquina de estados ---
    if estado_secuencia == 1:  # DOSIFICANDO
        ingrediente = formula["ingredientes"][ingrediente_idx]
        silo = mapa.silo_por_nombre(ingrediente["silo"])
        idx_motor = mapa.COIL_DE[silo["motor"]]
        objetivo_total = peso_acumulado_previo_kg + ingrediente["objetivo_kg"]
        peso_actual = peso_bascula_kg[NOMBRE_BASCULA_FORMULA]

        destino_override[silo["nombre"]] = NOMBRE_BASCULA_FORMULA

        if peso_actual < objetivo_total and niveles_silo_kg[silo["nombre"]] > 0:
            coils[idx_motor] = 1
        else:
            coils[idx_motor] = 0
            del destino_override[silo["nombre"]]
            if peso_actual >= objetivo_total:
                peso_acumulado_previo_kg = objetivo_total
                ingrediente_idx += 1
                if ingrediente_idx >= len(formula["ingredientes"]):
                    estado_secuencia = 2
                    tiempo_mezclado_restante = TIEMPO_MEZCLADO_S
                    ingrediente_idx = -1

    elif estado_secuencia == 2:  # MEZCLANDO
        coils[mapa.COIL_DE["M-441"]] = 1
        tiempo_mezclado_restante -= 1
        if tiempo_mezclado_restante <= 0:
            coils[mapa.COIL_DE["M-441"]] = 0
            estado_secuencia = 3
            tiempo_descarga_restante = TIEMPO_DESCARGA_S

    elif estado_secuencia == 3:  # DESCARGANDO
        coils[mapa.COIL_DE["M-442"]] = 1
        tiempo_descarga_restante -= 1
        if tiempo_descarga_restante <= 0:
            coils[mapa.COIL_DE["M-442"]] = 0
            batch_actual += 1
            peso_bascula_kg[NOMBRE_BASCULA_FORMULA] = 0.0
            estado_secuencia = 0

    # --- volcar estado a los input registers de solo lectura ---
    input_regs[mapa.INPUT_REG_ESTADO_SECUENCIA] = estado_secuencia
    input_regs[mapa.INPUT_REG_BATCH_ACTUAL] = batch_actual
    input_regs[mapa.INPUT_REG_FORMULA_ACTUAL] = idx_formula
    input_regs[mapa.INPUT_REG_INGREDIENTE_IDX] = ingrediente_idx if ingrediente_idx >= 0 else 0xFFFF
    if estado_secuencia == 1 and ingrediente_idx >= 0:
        ingrediente = formula["ingredientes"][ingrediente_idx]
        avance = peso_bascula_kg[NOMBRE_BASCULA_FORMULA] - peso_acumulado_previo_kg
        input_regs[mapa.INPUT_REG_OBJETIVO_INGREDIENTE] = int(ingrediente["objetivo_kg"] * 10)
        input_regs[mapa.INPUT_REG_AVANCE_INGREDIENTE] = max(0, int(avance * 10))
    else:
        input_regs[mapa.INPUT_REG_OBJETIVO_INGREDIENTE] = 0
        input_regs[mapa.INPUT_REG_AVANCE_INGREDIENTE] = 0
    input_regs[mapa.INPUT_REG_TIEMPO_MEZCLADO] = max(0, tiempo_mezclado_restante)


def motor_de_planta():
    """Hilo que simula fisicamente motores, valvulas, silos, basculas, VDFs y la formula."""
    while True:
        with lock:
            _procesar_secuencia_formula()
            _actualizar_confirmacion_dispositivos()
            _actualizar_flujo_material()
            _procesar_tara()
            _actualizar_vdfs()
            _volcar_niveles_a_registros()
        time.sleep(1)


# ---------------------------------------------------------------
# Implementacion minima del protocolo Modbus TCP (MBAP + PDU)
# ---------------------------------------------------------------
def construir_respuesta(transaccion_id, unit_id, pdu):
    longitud = len(pdu) + 1
    mbap = struct.pack(">HHHB", transaccion_id, 0, longitud, unit_id)
    return mbap + pdu


def leer_bits(tabla, direccion, cantidad):
    return [tabla[direccion + i] for i in range(cantidad)]


def empaquetar_bits(bits):
    n_bytes = (len(bits) + 7) // 8
    datos = bytearray(n_bytes)
    for i, b in enumerate(bits):
        if b:
            datos[i // 8] |= (1 << (i % 8))
    return bytes(datos)


def manejar_pdu(pdu):
    fc = pdu[0]
    with lock:
        if fc == 0x01:  # Read Coils
            direccion, cantidad = struct.unpack(">HH", pdu[1:5])
            datos = empaquetar_bits(leer_bits(coils, direccion, cantidad))
            return bytes([fc, len(datos)]) + datos

        elif fc == 0x02:  # Read Discrete Inputs
            direccion, cantidad = struct.unpack(">HH", pdu[1:5])
            datos = empaquetar_bits(leer_bits(discretas, direccion, cantidad))
            return bytes([fc, len(datos)]) + datos

        elif fc == 0x03:  # Read Holding Registers
            direccion, cantidad = struct.unpack(">HH", pdu[1:5])
            valores = holding_regs[direccion:direccion + cantidad]
            datos = struct.pack(f">{cantidad}H", *valores)
            return bytes([fc, len(datos)]) + datos

        elif fc == 0x04:  # Read Input Registers
            direccion, cantidad = struct.unpack(">HH", pdu[1:5])
            valores = input_regs[direccion:direccion + cantidad]
            datos = struct.pack(f">{cantidad}H", *valores)
            return bytes([fc, len(datos)]) + datos

        elif fc == 0x05:  # Write Single Coil
            direccion, valor = struct.unpack(">HH", pdu[1:5])
            # Interlock Auto/Manual: mientras la secuencia de formula esta
            # activa, el HMI no puede forzar manualmente los motores/valvulas
            # de planta (el PLC los controla el solo). Los coils de tara,
            # de VDF y de la propia secuencia siguen siempre disponibles.
            if estado_secuencia != 0 and direccion < mapa.N_DISPOSITIVOS:
                return pdu  # se ignora el intento, pero se responde igual
            coils[direccion] = 1 if valor == 0xFF00 else 0
            return pdu

        elif fc == 0x06:  # Write Single Register
            direccion, valor = struct.unpack(">HH", pdu[1:5])
            if 0 <= direccion < len(holding_regs):
                holding_regs[direccion] = valor
            return pdu

        else:
            return bytes([fc | 0x80, 0x01])  # excepcion: funcion no soportada


def atender_cliente(conn, addr):
    print(f"[PLC] Cliente HMI conectado desde {addr}")
    with conn:
        while True:
            cabecera = conn.recv(7)
            if not cabecera or len(cabecera) < 7:
                break
            transaccion_id, protocolo, longitud, unit_id = struct.unpack(">HHHB", cabecera)
            pdu = conn.recv(longitud - 1)
            respuesta_pdu = manejar_pdu(pdu)
            conn.sendall(construir_respuesta(transaccion_id, unit_id, respuesta_pdu))
    print(f"[PLC] Cliente {addr} desconectado")


def main():
    threading.Thread(target=motor_de_planta, daemon=True).start()

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen(5)
    print(f"[PLC] Controlador simulado (planta completa + VDF + formula) en {HOST}:{PORT}")
    print(f"[PLC] {mapa.N_DISPOSITIVOS} dispositivos, {len(mapa.SILOS)} silos, "
          f"{len(mapa.BASCULAS)} basculas, {len(mapa.VDFS)} VDF, {len(mapa.FORMULAS)} formula(s)")
    print(f"[PLC] Coils: 0-{mapa.N_COILS - 1}  Discretas: 0-{mapa.N_DISCRETAS - 1}  "
          f"Holding Regs: 0-{mapa.N_HOLDING_REGS - 1}  Input Regs: 0-{mapa.N_INPUT_REGS - 1}")

    try:
        while True:
            conn, addr = servidor.accept()
            threading.Thread(target=atender_cliente, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[PLC] Apagando controlador simulado")
        servidor.close()


if __name__ == "__main__":
    main()
