#!/usr/bin/env python3
"""
plc_servidor.py (v2 - planta completa)
----------------------------------------
Simula el controlador (equivalente a un SNAP PAC) de la planta completa
de referencia: Granos, Harinas, Pre Mix, Acido Graso, Enteros, Mezcladora
y Salida. Habla Modbus TCP real, sin librerias externas.

Comportamiento fisico simulado (no solo numeros al azar):
  - Cada motor tiene un retardo de arranque real (contactor + termico)
    antes de que su discrete input de "corriendo" se active. Las
    valvulas responden mas rapido (accionamiento neumatico).
  - Mientras el motor de un silo esta "corriendo" de verdad (discreta=1),
    el nivel del silo baja y el peso de la bascula de su sector sube,
    simulando el flujo real de material.
  - Las basculas se pueden "tarar" (poner a cero) via un coil dedicado,
    igual que el boton de tara de una bascula real.

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
input_regs = [0] * mapa.N_INPUT_REGS

# Estado interno de simulacion (no expuesto directo por Modbus)
tiempo_comandado = [0.0] * mapa.N_DISPOSITIVOS   # segundos que lleva el coil en ON
niveles_silo_kg = {s["nombre"]: float(s["nivel_inicial_kg"]) for s in mapa.SILOS}
peso_bascula_kg = {b["nombre"]: 0.0 for b in mapa.BASCULAS}

RETARDO_ARRANQUE_MOTOR = 2.0   # segundos hasta que el contactor confirma marcha
RETARDO_ARRANQUE_VALVULA = 0.5  # segundos hasta que el limit switch confirma
TASA_DESCARGA_KG_S = 6.0        # velocidad de dosificacion simulada


def _volcar_niveles_a_registros():
    # Los silos guardan Kg enteros (sin decimal): sus valores pueden llegar
    # a varias toneladas y un registro de 16 bits solo llega a 65535.
    for silo in mapa.SILOS:
        direccion = mapa.INPUT_REG_DE_SILO[silo["nombre"]]
        input_regs[direccion] = min(65535, max(0, int(niveles_silo_kg[silo["nombre"]])))
    # Las basculas si guardan un decimal (x10): sus valores tipicos (decenas
    # a pocos miles de Kg por lote) entran de sobra en 65535/10 = 6553.5 Kg.
    for bas in mapa.BASCULAS:
        direccion = mapa.INPUT_REG_DE_BASCULA[bas["nombre"]]
        input_regs[direccion] = min(65535, max(0, int(peso_bascula_kg[bas["nombre"]] * 10)))


def motor_de_planta():
    """Hilo que simula fisicamente motores, valvulas, silos y basculas."""
    while True:
        with lock:
            # 1) actualizar confirmacion real (discreta) de cada dispositivo
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

            # 2) flujo de material: silo -> bascula, solo si el motor esta
            #    REALMENTE corriendo (discreta=1), no solo comandado
            for silo in mapa.SILOS:
                idx = mapa.COIL_DE[silo["motor"]]  # coils y discretas comparten indice
                corriendo_de_verdad = discretas[idx]
                if corriendo_de_verdad and niveles_silo_kg[silo["nombre"]] > 0:
                    flujo = min(TASA_DESCARGA_KG_S, niveles_silo_kg[silo["nombre"]])
                    niveles_silo_kg[silo["nombre"]] -= flujo
                    peso_bascula_kg[silo["alimenta_a"]] += flujo

            # 3) procesar comandos de tara (pulso: se auto-resetea el coil)
            for bas in mapa.BASCULAS:
                direccion_tara = mapa.COIL_TARA_DE[bas["nombre"]]
                if coils[direccion_tara]:
                    peso_bascula_kg[bas["nombre"]] = 0.0
                    coils[direccion_tara] = 0  # el PLC confirma la tara y limpia el pulso

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

        elif fc == 0x03:  # Read Holding Registers (no usados en esta version)
            direccion, cantidad = struct.unpack(">HH", pdu[1:5])
            valores = [0] * cantidad
            datos = struct.pack(f">{cantidad}H", *valores)
            return bytes([fc, len(datos)]) + datos

        elif fc == 0x04:  # Read Input Registers
            direccion, cantidad = struct.unpack(">HH", pdu[1:5])
            valores = input_regs[direccion:direccion + cantidad]
            datos = struct.pack(f">{cantidad}H", *valores)
            return bytes([fc, len(datos)]) + datos

        elif fc == 0x05:  # Write Single Coil
            direccion, valor = struct.unpack(">HH", pdu[1:5])
            coils[direccion] = 1 if valor == 0xFF00 else 0
            return pdu

        elif fc == 0x06:  # Write Single Register (no usado en esta version)
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
    print(f"[PLC] Controlador simulado (planta completa) escuchando en {HOST}:{PORT}")
    print(f"[PLC] {mapa.N_DISPOSITIVOS} dispositivos, {len(mapa.SILOS)} silos, "
          f"{len(mapa.BASCULAS)} basculas")
    print(f"[PLC] Coils: 0-{mapa.N_COILS - 1}  Discretas: 0-{mapa.N_DISCRETAS - 1}  "
          f"Input Regs: 0-{mapa.N_INPUT_REGS - 1}")

    try:
        while True:
            conn, addr = servidor.accept()
            threading.Thread(target=atender_cliente, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[PLC] Apagando controlador simulado")
        servidor.close()


if __name__ == "__main__":
    main()
