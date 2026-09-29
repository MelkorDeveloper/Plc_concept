#!/usr/bin/env python3
"""
hmi_cliente.py (v2 - planta completa)
---------------------------------------
Simula la estacion HMI (equivalente a PAC Display) para la planta
completa: pestañas por sector, motores/valvulas con indicador de
confirmacion real (no solo el comando), niveles de silo y basculas.

El polling se hace en BLOQUE (todos los coils en una sola lectura,
todas las discretas en otra, todos los input registers en otra),
igual que lo hace un SCADA de verdad -- no una peticion por cada tag.

Requiere: python3-tk
    sudo apt install python3-tk

Uso:
    python3 hmi_cliente.py [ip_plc] [puerto]
"""

import socket
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

import mapa_senales as mapa

IP_PLC = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PUERTO_PLC = int(sys.argv[2]) if len(sys.argv) > 2 else 5020

COLOR_ACTIVO = "#2ecc71"
COLOR_INACTIVO = "#7f8c8d"
COLOR_FONDO_SECTOR = "#eef2f5"


class ClienteModbus:
    """Cliente Modbus TCP minimo, con lectura/escritura en bloque."""

    def __init__(self, ip, puerto):
        self.ip = ip
        self.puerto = puerto
        self.sock = None
        self.transaccion_id = 0
        self.lock = threading.Lock()
        self.conectar()

    def conectar(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect((self.ip, self.puerto))

    def _transaccion(self, pdu):
        with self.lock:
            self.transaccion_id = (self.transaccion_id + 1) % 0xFFFF
            mbap = struct.pack(">HHHB", self.transaccion_id, 0, len(pdu) + 1, 1)
            self.sock.sendall(mbap + pdu)
            cabecera = self.sock.recv(7)
            if len(cabecera) < 7:
                raise ConnectionError("PLC cerro la conexion")
            _, _, longitud, _ = struct.unpack(">HHHB", cabecera)
            return self.sock.recv(longitud - 1)

    def leer_coils(self, direccion, cantidad):
        resp = self._transaccion(struct.pack(">BHH", 0x01, direccion, cantidad))
        n_bytes = resp[1]
        datos = resp[2:2 + n_bytes]
        return [(datos[i // 8] >> (i % 8)) & 1 for i in range(cantidad)]

    def leer_discretas(self, direccion, cantidad):
        resp = self._transaccion(struct.pack(">BHH", 0x02, direccion, cantidad))
        n_bytes = resp[1]
        datos = resp[2:2 + n_bytes]
        return [(datos[i // 8] >> (i % 8)) & 1 for i in range(cantidad)]

    def leer_input_regs(self, direccion, cantidad):
        resp = self._transaccion(struct.pack(">BHH", 0x04, direccion, cantidad))
        n_bytes = resp[1]
        return list(struct.unpack(f">{n_bytes // 2}H", resp[2:2 + n_bytes]))

    def escribir_coil(self, direccion, valor):
        val = 0xFF00 if valor else 0x0000
        self._transaccion(struct.pack(">BHH", 0x05, direccion, val))


class FilaDispositivo:
    """Una fila de motor/valvula: nombre, indicador real, boton de comando."""

    def __init__(self, parent, disp, cliente):
        self.disp = disp
        self.cliente = cliente
        self.direccion = mapa.COIL_DE[disp["tag"]]

        self.marco = ttk.Frame(parent)
        self.marco.pack(fill="x", pady=2, padx=4)

        self.canvas_led = tk.Canvas(self.marco, width=16, height=16,
                                     highlightthickness=0)
        self.led = self.canvas_led.create_oval(2, 2, 14, 14, fill=COLOR_INACTIVO)
        self.canvas_led.pack(side="left", padx=(0, 8))

        etiqueta = f"{disp['tag']}  {disp['nombre']}"
        ttk.Label(self.marco, text=etiqueta, width=32, anchor="w").pack(side="left")

        self.var_cmd = tk.BooleanVar()
        texto_boton = "Abrir" if disp["tipo"] == "valvula" else "Arrancar"
        self.boton = ttk.Checkbutton(self.marco, text=texto_boton,
                                      variable=self.var_cmd, command=self._on_toggle)
        self.boton.pack(side="left")

        self.lbl_estado = ttk.Label(self.marco, text="detenido", width=12)
        self.lbl_estado.pack(side="left", padx=6)

    def _on_toggle(self):
        try:
            self.cliente.escribir_coil(self.direccion, self.var_cmd.get())
        except (ConnectionError, OSError):
            pass

    def actualizar(self, comandado, corriendo_real):
        self.var_cmd.set(bool(comandado))
        if corriendo_real:
            self.canvas_led.itemconfig(self.led, fill=COLOR_ACTIVO)
            self.lbl_estado.config(text="corriendo" if self.disp["tipo"] == "motor" else "abierta")
        else:
            self.canvas_led.itemconfig(self.led, fill=COLOR_INACTIVO)
            self.lbl_estado.config(text="arrancando" if comandado else "detenido")


class FilaSilo:
    """Barra de nivel de un silo (Kg), calculada a partir del input register."""

    def __init__(self, parent, silo, capacidad_kg=10000):
        self.silo = silo
        self.capacidad_kg = capacidad_kg
        self.direccion = mapa.INPUT_REG_DE_SILO[silo["nombre"]]

        marco = ttk.Frame(parent)
        marco.pack(fill="x", pady=2, padx=4)
        ttk.Label(marco, text=silo["nombre"], width=22, anchor="w").pack(side="left")
        self.barra = ttk.Progressbar(marco, length=140, maximum=capacidad_kg)
        self.barra.pack(side="left", padx=6)
        self.lbl_kg = ttk.Label(marco, text="-- Kg", width=12)
        self.lbl_kg.pack(side="left")

    def actualizar(self, valor_registro):
        kg = valor_registro  # los silos se transmiten en Kg enteros, sin decimal
        self.barra["value"] = min(kg, self.capacidad_kg)
        self.lbl_kg.config(text=f"{kg} Kg")


class FilaBascula:
    """Peso acumulado de una bascula, con boton de Tara."""

    def __init__(self, parent, bascula, cliente):
        self.bascula = bascula
        self.cliente = cliente
        self.direccion_peso = mapa.INPUT_REG_DE_BASCULA[bascula["nombre"]]
        self.direccion_tara = mapa.COIL_TARA_DE[bascula["nombre"]]

        marco = ttk.Frame(parent)
        marco.pack(fill="x", pady=4, padx=4)
        ttk.Label(marco, text=bascula["nombre"], width=22,
                  anchor="w", font=("Sans", 10, "bold")).pack(side="left")
        self.lbl_peso = tk.Label(marco, text="-- Kg", width=12, bg="black",
                                  fg="#00ff88", font=("Consolas", 12, "bold"))
        self.lbl_peso.pack(side="left", padx=6)
        ttk.Button(marco, text="Tara", command=self._tarar).pack(side="left")

    def _tarar(self):
        try:
            self.cliente.escribir_coil(self.direccion_tara, True)
        except (ConnectionError, OSError):
            pass

    def actualizar(self, valor_registro):
        self.lbl_peso.config(text=f"{valor_registro / 10.0:.1f} Kg")


class PantallaHMI(tk.Tk):
    def __init__(self, cliente):
        super().__init__()
        self.cliente = cliente
        self.title(f"HMI Planta Completa - Modbus TCP {IP_PLC}:{PUERTO_PLC}")
        self.geometry("640x520")

        self.filas_dispositivo = {}   # tag -> FilaDispositivo
        self.filas_silo = {}          # nombre -> FilaSilo
        self.filas_bascula = {}       # nombre -> FilaBascula

        self._construir_ui()
        self._activo = True
        threading.Thread(target=self._bucle_sondeo, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _construir_ui(self):
        barra_superior = ttk.Frame(self, padding=6)
        barra_superior.pack(fill="x")
        ttk.Label(barra_superior, text="Estacion HMI - Planta de Alimentos Balanceados",
                  font=("Sans", 12, "bold")).pack(side="left")
        self.lbl_estado_conexion = ttk.Label(barra_superior, text="Conectado", foreground="green")
        self.lbl_estado_conexion.pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        for sector in mapa.SECTORES:
            pestana = ttk.Frame(notebook)
            notebook.add(pestana, text=sector.replace("_", " ").title())
            self._construir_pestana_sector(pestana, sector)

    def _construir_pestana_sector(self, contenedor, sector):
        canvas = tk.Canvas(contenedor, highlightthickness=0)
        scroll = ttk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
        marco_interno = ttk.Frame(canvas)
        marco_interno.bind("<Configure>",
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=marco_interno, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        silos_del_sector = [s for s in mapa.SILOS if s["sector"] == sector]
        if silos_del_sector:
            ttk.Label(marco_interno, text="Silos de materia prima",
                      font=("Sans", 10, "bold")).pack(anchor="w", padx=4, pady=(6, 2))
            for silo in silos_del_sector:
                fila = FilaSilo(marco_interno, silo)
                self.filas_silo[silo["nombre"]] = fila

        dispositivos_del_sector = [d for d in mapa.DISPOSITIVOS if d["sector"] == sector]
        if dispositivos_del_sector:
            ttk.Label(marco_interno, text="Motores / Valvulas",
                      font=("Sans", 10, "bold")).pack(anchor="w", padx=4, pady=(10, 2))
            for disp in dispositivos_del_sector:
                fila = FilaDispositivo(marco_interno, disp, self.cliente)
                self.filas_dispositivo[disp["tag"]] = fila

        basculas_del_sector = [b for b in mapa.BASCULAS
                                if sector.replace("_", " ").lower() in b["nombre"].lower()
                                or (sector == "ACIDO_GRASO" and "acido" in b["nombre"].lower())]
        if basculas_del_sector:
            ttk.Label(marco_interno, text="Bascula",
                      font=("Sans", 10, "bold")).pack(anchor="w", padx=4, pady=(10, 2))
            for bas in basculas_del_sector:
                fila = FilaBascula(marco_interno, bas, self.cliente)
                self.filas_bascula[bas["nombre"]] = fila

    def _bucle_sondeo(self):
        """Polling en bloque: 3 lecturas Modbus cubren TODA la planta."""
        while self._activo:
            try:
                coils = self.cliente.leer_coils(0, mapa.N_COILS)
                discretas = self.cliente.leer_discretas(0, mapa.N_DISCRETAS)
                input_regs = self.cliente.leer_input_regs(0, mapa.N_INPUT_REGS)
                self.after(0, self._actualizar_ui, coils, discretas, input_regs)
            except (socket.timeout, ConnectionError, OSError):
                self.after(0, self._marcar_desconectado)
                return
            time.sleep(1)

    def _actualizar_ui(self, coils, discretas, input_regs):
        for tag, fila in self.filas_dispositivo.items():
            direccion = mapa.COIL_DE[tag]
            fila.actualizar(coils[direccion], discretas[direccion])

        for nombre, fila in self.filas_silo.items():
            direccion = mapa.INPUT_REG_DE_SILO[nombre]
            fila.actualizar(input_regs[direccion])

        for nombre, fila in self.filas_bascula.items():
            direccion = mapa.INPUT_REG_DE_BASCULA[nombre]
            fila.actualizar(input_regs[direccion])

    def _marcar_desconectado(self):
        self.lbl_estado_conexion.config(text="Desconectado del PLC", foreground="red")

    def _cerrar(self):
        self._activo = False
        self.destroy()


def main():
    cliente = ClienteModbus(IP_PLC, PUERTO_PLC)
    app = PantallaHMI(cliente)
    app.mainloop()


if __name__ == "__main__":
    main()
