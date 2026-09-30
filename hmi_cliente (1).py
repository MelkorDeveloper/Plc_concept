#!/usr/bin/env python3
"""
hmi_cliente.py (v3 - planta completa, look tipo PAC Display)
----------------------------------------------------------------
Misma logica Modbus que la version anterior (polling en bloque, 
motores/valvulas con confirmacion real, basculas, VDF, secuenciador
de formula), pero con un aspecto visual mas cercano a la pantalla
real de referencia: fondo azul, silos dibujados con su nivel, cajas
blancas de lectura tipo bascula industrial, y el panel de formula en
un tono oscuro como el "Formula/Batchs" del diagrama.

Todo se dibuja con formas vectoriales simples en Canvas y widgets
tk normales -- nada de imagenes ni librerias graficas pesadas, para
que el consumo de RAM siga siendo minimo (pensado para 1GB de RAM).

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

# =================================================================
# Paleta de colores, inspirada en la pantalla PAC Display de referencia
# =================================================================
AZUL_FONDO = "#1c67c7"        # fondo de las pestañas de sector (como la pantalla real)
AZUL_PANEL = "#0b3f7a"        # barra superior y paneles (VDF, etc)
AZUL_OSCURO = "#07203e"       # panel de Formula/Batchs (lado derecho del diagrama)
BLANCO = "#ffffff"
NEGRO = "#000000"
GRIS_SILO = "#cfd8dc"
BORDE_SILO = "#37474f"
MATERIAL_COLOR = "#8d6e63"
VERDE_ACTIVO = "#00e676"
GRIS_INACTIVO = "#78909c"
ROJO_TRIP = "#e53935"
AMARILLO = "#ffd54f"
CIAN_BARRA = "#26c6da"
TEXTO_CLARO = "#e3f2fd"


def caja_titulo(parent, texto, bg_parent):
    """Caja blanca con texto negro, como los rotulos 'SECTOR X' del diagrama real."""
    return tk.Label(parent, text=texto, bg=BLANCO, fg=NEGRO,
                     font=("Sans", 9, "bold"), relief="solid", bd=1, padx=8, pady=3)


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

    def leer_holding_regs(self, direccion, cantidad):
        resp = self._transaccion(struct.pack(">BHH", 0x03, direccion, cantidad))
        n_bytes = resp[1]
        return list(struct.unpack(f">{n_bytes // 2}H", resp[2:2 + n_bytes]))

    def escribir_coil(self, direccion, valor):
        val = 0xFF00 if valor else 0x0000
        self._transaccion(struct.pack(">BHH", 0x05, direccion, val))

    def escribir_registro(self, direccion, valor):
        self._transaccion(struct.pack(">BHH", 0x06, direccion, valor))


class FilaDispositivo:
    """Motor/valvula: icono circular con M/V, indicador real, boton de comando."""

    def __init__(self, parent, disp, cliente, bg=AZUL_FONDO):
        self.disp = disp
        self.cliente = cliente
        self.bg = bg
        self.direccion = mapa.COIL_DE[disp["tag"]]

        self.marco = tk.Frame(parent, bg=bg)
        self.marco.pack(fill="x", pady=2, padx=4)

        letra = "M" if disp["tipo"] == "motor" else "V"
        self.canvas_led = tk.Canvas(self.marco, width=24, height=24, bg=bg,
                                     highlightthickness=0)
        self.led = self.canvas_led.create_oval(2, 2, 22, 22, fill=GRIS_INACTIVO,
                                                outline="black", width=1)
        self.canvas_led.create_text(12, 12, text=letra, fill="white",
                                     font=("Sans", 9, "bold"))
        self.canvas_led.pack(side="left", padx=(0, 8))

        etiqueta = f"{disp['tag']}  {disp['nombre']}"
        tk.Label(self.marco, text=etiqueta, width=30, anchor="w",
                 bg=bg, fg=TEXTO_CLARO, font=("Sans", 9)).pack(side="left")

        self.var_cmd = tk.BooleanVar()
        texto_boton = "Abrir" if disp["tipo"] == "valvula" else "Arrancar"
        self.boton = tk.Checkbutton(self.marco, text=texto_boton, variable=self.var_cmd,
                                     command=self._on_toggle, bg=bg, fg="white",
                                     selectcolor=AZUL_PANEL, activebackground=bg,
                                     activeforeground="white", highlightthickness=0)
        self.boton.pack(side="left")

        self.lbl_estado = tk.Label(self.marco, text="detenido", width=12,
                                    bg=bg, fg="#cfe8ff", font=("Sans", 9))
        self.lbl_estado.pack(side="left", padx=6)

    def _on_toggle(self):
        try:
            self.cliente.escribir_coil(self.direccion, self.var_cmd.get())
        except (ConnectionError, OSError):
            pass

    def actualizar(self, comandado, corriendo_real):
        self.var_cmd.set(bool(comandado))
        if corriendo_real:
            self.canvas_led.itemconfig(self.led, fill=VERDE_ACTIVO)
            self.lbl_estado.config(text="corriendo" if self.disp["tipo"] == "motor" else "abierta")
        else:
            self.canvas_led.itemconfig(self.led, fill=GRIS_INACTIVO)
            self.lbl_estado.config(text="arrancando" if comandado else "detenido")


class FilaSilo:
    """Silo dibujado (cuerpo + cono) con su nivel real relleno, como en el diagrama."""

    def __init__(self, parent, silo, capacidad_kg=10000, bg=AZUL_FONDO):
        self.silo = silo
        self.capacidad_kg = capacidad_kg
        self.bg = bg
        self.direccion = mapa.INPUT_REG_DE_SILO[silo["nombre"]]

        marco = tk.Frame(parent, bg=bg)
        marco.pack(side="left", padx=8, pady=6, anchor="n")

        self.canvas = tk.Canvas(marco, width=46, height=62, bg=bg, highlightthickness=0)
        self.canvas.pack()
        # cuerpo del silo (cilindro visto de frente) y cono de descarga
        self.canvas.create_rectangle(8, 6, 38, 40, fill=GRIS_SILO, outline=BORDE_SILO, width=2)
        self.canvas.create_polygon(8, 40, 38, 40, 23, 56, fill=GRIS_SILO, outline=BORDE_SILO, width=2)
        # rectangulo de nivel (se mueve con canvas.coords, no se recrea)
        self.item_nivel = self.canvas.create_rectangle(10, 38, 36, 38, fill=MATERIAL_COLOR, outline="")
        self.canvas.tag_raise(self.item_nivel)

        nombre_corto = silo["nombre"].replace("Silo ", "").replace(" Granos", "").\
            replace(" Harinas", "").replace(" PreMix", "").replace(" Acido Graso", "")
        tk.Label(marco, text=nombre_corto, bg=bg, fg=TEXTO_CLARO,
                 font=("Sans", 8), wraplength=60, justify="center").pack()
        self.lbl_kg = tk.Label(marco, text="-- Kg", bg=bg, fg=AMARILLO, font=("Sans", 8, "bold"))
        self.lbl_kg.pack()

    def actualizar(self, valor_registro):
        kg = valor_registro
        fraccion = max(0.0, min(1.0, kg / self.capacidad_kg))
        y_top = 40 - fraccion * (40 - 8)
        self.canvas.coords(self.item_nivel, 10, y_top, 36, 39)
        self.lbl_kg.config(text=f"{kg} Kg")


class FilaBascula:
    """Bascula: caja blanca de lectura (como los recuadros de Kg del diagrama) + Tara."""

    def __init__(self, parent, bascula, cliente, bg=AZUL_FONDO):
        self.bascula = bascula
        self.cliente = cliente
        self.direccion_peso = mapa.INPUT_REG_DE_BASCULA[bascula["nombre"]]
        self.direccion_tara = mapa.COIL_TARA_DE[bascula["nombre"]]

        marco = tk.Frame(parent, bg=bg)
        marco.pack(fill="x", pady=6, padx=4)
        tk.Label(marco, text=bascula["nombre"], width=20, anchor="w",
                 bg=bg, fg="white", font=("Sans", 10, "bold")).pack(side="left")
        self.lbl_peso = tk.Label(marco, text="-- Kg", width=11, bg="white", fg="black",
                                  font=("Consolas", 13, "bold"), relief="sunken", bd=3)
        self.lbl_peso.pack(side="left", padx=6)
        tk.Button(marco, text="Tara", command=self._tarar).pack(side="left")

    def _tarar(self):
        try:
            self.cliente.escribir_coil(self.direccion_tara, True)
        except (ConnectionError, OSError):
            pass

    def actualizar(self, valor_registro):
        self.lbl_peso.config(text=f"{valor_registro / 10.0:.1f} Kg")


class FilaVDF:
    """Variador de frecuencia (tipo ABB): consigna, frecuencia real, estado On/Run/Ref/Trip."""

    def __init__(self, parent, vdf, cliente, bg=AZUL_PANEL):
        self.vdf = vdf
        self.cliente = cliente
        self.direccion_consigna = mapa.HOLDING_REG_DE_VDF_CONSIGNA[vdf["tag"]]
        self.direccion_frecuencia = mapa.INPUT_REG_DE_VDF_FRECUENCIA[vdf["tag"]]
        self.direccion_estado = mapa.INPUT_REG_DE_VDF_ESTADO[vdf["tag"]]
        self.direccion_forzar_falla = mapa.COIL_VDF_FORZAR_FALLA[vdf["tag"]]
        self.direccion_reset_falla = mapa.COIL_VDF_RESET_FALLA[vdf["tag"]]

        marco = tk.LabelFrame(parent, text=f"{vdf['tag']}  {vdf['nombre']}",
                               bg=bg, fg="white", font=("Sans", 9, "bold"),
                               labelanchor="nw")
        marco.pack(fill="x", padx=4, pady=(10, 4))

        fila1 = tk.Frame(marco, bg=bg)
        fila1.pack(fill="x", padx=6, pady=4)
        tk.Label(fila1, text="Consigna (Hz):", bg=bg, fg="white").pack(side="left")
        self.entrada_consigna = tk.Entry(fila1, width=6)
        self.entrada_consigna.pack(side="left", padx=4)
        tk.Button(fila1, text="Enviar", command=self._enviar_consigna).pack(side="left")
        self.lbl_frecuencia = tk.Label(fila1, text="Real: -- Hz", width=14, bg=bg, fg=AMARILLO,
                                        font=("Consolas", 10, "bold"))
        self.lbl_frecuencia.pack(side="left", padx=(12, 0))

        fila2 = tk.Frame(marco, bg=bg)
        fila2.pack(fill="x", padx=6, pady=(0, 6))
        self.lbl_estados = tk.Label(fila2, text="On: -  Run: -  Ref: -  Trip: -",
                                     bg=bg, fg="white")
        self.lbl_estados.pack(side="left")
        tk.Button(fila2, text="Forzar Falla", command=self._forzar_falla).pack(side="left", padx=(12, 4))
        tk.Button(fila2, text="Reset Falla", command=self._reset_falla).pack(side="left")

    def _enviar_consigna(self):
        try:
            hz = float(self.entrada_consigna.get())
            self.cliente.escribir_registro(self.direccion_consigna, int(hz * 10))
        except (ValueError, ConnectionError, OSError):
            pass

    def _forzar_falla(self):
        try:
            self.cliente.escribir_coil(self.direccion_forzar_falla, True)
        except (ConnectionError, OSError):
            pass

    def _reset_falla(self):
        try:
            self.cliente.escribir_coil(self.direccion_reset_falla, True)
        except (ConnectionError, OSError):
            pass

    def actualizar(self, frecuencia_reg, estado_bits):
        self.lbl_frecuencia.config(text=f"Real: {frecuencia_reg / 10.0:.1f} Hz")
        on = "SI" if estado_bits & mapa.VDF_BIT_ON else "no"
        run = "SI" if estado_bits & mapa.VDF_BIT_RUN else "no"
        ref = "SI" if estado_bits & mapa.VDF_BIT_REF else "no"
        trip = "SI" if estado_bits & mapa.VDF_BIT_TRIP else "no"
        self.lbl_estados.config(
            text=f"On: {on}  Run: {run}  Ref: {ref}  Trip: {trip}",
            fg=ROJO_TRIP if estado_bits & mapa.VDF_BIT_TRIP else "white")


class FilaIngrediente:
    """Fila de la tabla de formula (panel oscuro), estilo 'Formula/Batchs' del diagrama."""

    def __init__(self, parent, ingrediente, bg=AZUL_OSCURO):
        self.ingrediente = ingrediente
        marco = tk.Frame(parent, bg=bg)
        marco.pack(fill="x", padx=4, pady=2)
        tk.Label(marco, text=ingrediente["nombre"], width=20, anchor="w",
                 bg=bg, fg=AMARILLO, font=("Sans", 9, "bold")).pack(side="left")
        tk.Label(marco, text=f"{ingrediente['objetivo_kg']:.1f} Kg", width=10, anchor="e",
                 bg=bg, fg="white", font=("Consolas", 9)).pack(side="left")
        self.barra = ttk.Progressbar(marco, length=150, maximum=ingrediente["objetivo_kg"],
                                      style="Formula.Horizontal.TProgressbar")
        self.barra.pack(side="left", padx=6)
        self.lbl_estado = tk.Label(marco, text="pendiente", width=12, bg=bg, fg="#90a4ae")
        self.lbl_estado.pack(side="left")

    def actualizar(self, estado_txt, avance_kg=None):
        colores = {"pendiente": "#90a4ae", "dosificando...": CIAN_BARRA, "completado": VERDE_ACTIVO}
        self.lbl_estado.config(text=estado_txt, fg=colores.get(estado_txt, "white"))
        if avance_kg is not None:
            self.barra["value"] = min(avance_kg, self.ingrediente["objetivo_kg"])
        elif estado_txt == "completado":
            self.barra["value"] = self.ingrediente["objetivo_kg"]
        else:
            self.barra["value"] = 0


class PantallaHMI(tk.Tk):
    def __init__(self, cliente):
        super().__init__()
        self.cliente = cliente
        self.title(f"HMI Planta Completa - Modbus TCP {IP_PLC}:{PUERTO_PLC}")
        self.geometry("780x560")
        self.configure(bg=AZUL_PANEL)

        self.filas_dispositivo = {}
        self.filas_silo = {}
        self.filas_bascula = {}
        self.filas_vdf = {}
        self.filas_ingrediente = []
        self._consignas_precargadas = False

        self._configurar_estilo()
        self._construir_ui()
        self._activo = True
        threading.Thread(target=self._bucle_sondeo, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _configurar_estilo(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=AZUL_PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", background=AZUL_PANEL, foreground="white",
                         padding=(6, 3), font=("Sans", 8, "bold"))
        style.map("TNotebook.Tab", background=[("selected", AZUL_FONDO)])
        style.configure("Vertical.TScrollbar", background=AZUL_PANEL)
        style.configure("Formula.Horizontal.TProgressbar", troughcolor=AZUL_PANEL,
                         background=CIAN_BARRA, bordercolor=AZUL_OSCURO)
        style.configure("TCombobox", fieldbackground="white")

    def _construir_ui(self):
        barra_superior = tk.Frame(self, bg=AZUL_PANEL, padx=8, pady=6)
        barra_superior.pack(fill="x")
        tk.Label(barra_superior, text="Estacion HMI - Planta de Alimentos Balanceados",
                  bg=AZUL_PANEL, fg="white", font=("Sans", 12, "bold")).pack(side="left")
        self.lbl_estado_conexion = tk.Label(barra_superior, text="Conectado",
                                             bg=AZUL_PANEL, fg=VERDE_ACTIVO, font=("Sans", 9, "bold"))
        self.lbl_estado_conexion.pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self.notebook = notebook

        for sector in mapa.SECTORES:
            pestana = tk.Frame(notebook, bg=AZUL_FONDO)
            notebook.add(pestana, text=sector.replace("_", " ").title())
            self._construir_pestana_sector(pestana, sector)

        pestana_secuencia = tk.Frame(notebook, bg=AZUL_OSCURO)
        notebook.add(pestana_secuencia, text="Secuencia / Batch")
        self._construir_pestana_secuencia(pestana_secuencia)

    def _construir_pestana_sector(self, contenedor, sector):
        canvas = tk.Canvas(contenedor, bg=AZUL_FONDO, highlightthickness=0)
        scroll = ttk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
        marco_interno = tk.Frame(canvas, bg=AZUL_FONDO)
        marco_interno.bind("<Configure>",
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=marco_interno, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        caja_titulo(marco_interno, f"SECTOR {sector.replace('_', ' ')}", AZUL_FONDO)\
            .pack(anchor="w", padx=6, pady=(8, 6))

        silos_del_sector = [s for s in mapa.SILOS if s["sector"] == sector]
        if silos_del_sector:
            marco_silos = tk.Frame(marco_interno, bg=AZUL_FONDO)
            marco_silos.pack(fill="x", padx=2)
            for silo in silos_del_sector:
                fila = FilaSilo(marco_silos, silo)
                self.filas_silo[silo["nombre"]] = fila

        dispositivos_del_sector = [d for d in mapa.DISPOSITIVOS if d["sector"] == sector]
        if dispositivos_del_sector:
            caja_titulo(marco_interno, "Motores / Valvulas", AZUL_FONDO)\
                .pack(anchor="w", padx=6, pady=(10, 4))
            for disp in dispositivos_del_sector:
                fila = FilaDispositivo(marco_interno, disp, self.cliente)
                self.filas_dispositivo[disp["tag"]] = fila

        basculas_del_sector = [b for b in mapa.BASCULAS
                                if sector.replace("_", " ").lower() in b["nombre"].lower()
                                or (sector == "ACIDO_GRASO" and "acido" in b["nombre"].lower())]
        if basculas_del_sector:
            caja_titulo(marco_interno, "Bascula", AZUL_FONDO).pack(anchor="w", padx=6, pady=(10, 4))
            for bas in basculas_del_sector:
                fila = FilaBascula(marco_interno, bas, self.cliente)
                self.filas_bascula[bas["nombre"]] = fila

        vdfs_del_sector = [v for v in mapa.VDFS
                           if mapa.dispositivo_por_tag(v["motor"])["sector"] == sector]
        if vdfs_del_sector:
            caja_titulo(marco_interno, "Variadores de Frecuencia (VDF)", AZUL_FONDO)\
                .pack(anchor="w", padx=6, pady=(10, 4))
            for vdf in vdfs_del_sector:
                fila = FilaVDF(marco_interno, vdf, self.cliente, bg=AZUL_FONDO)
                self.filas_vdf[vdf["tag"]] = fila

    def _construir_pestana_secuencia(self, contenedor):
        marco = tk.Frame(contenedor, padx=12, pady=10, bg=AZUL_OSCURO)
        marco.pack(fill="both", expand=True)

        caja_titulo(marco, "FORMULA / BATCHS", AZUL_OSCURO).pack(anchor="w", pady=(0, 10))

        fila_control = tk.Frame(marco, bg=AZUL_OSCURO)
        fila_control.pack(fill="x", pady=(0, 10))
        tk.Label(fila_control, text="Formula:", bg=AZUL_OSCURO, fg="white").pack(side="left")
        nombres_formula = [f'{f["id"]} - {f["nombre"]}' for f in mapa.FORMULAS]
        self.combo_formula = ttk.Combobox(fila_control, values=nombres_formula,
                                           state="readonly", width=24)
        self.combo_formula.current(0)
        self.combo_formula.pack(side="left", padx=6)
        self.combo_formula.bind("<<ComboboxSelected>>", self._on_cambio_formula)

        tk.Button(fila_control, text="Iniciar Batch", bg=VERDE_ACTIVO, fg="black",
                   font=("Sans", 9, "bold"),
                   command=self._iniciar_secuencia).pack(side="left", padx=(20, 4))
        tk.Button(fila_control, text="Detener", bg=ROJO_TRIP, fg="white",
                   font=("Sans", 9, "bold"),
                   command=self._detener_secuencia).pack(side="left")

        fila_estado = tk.Frame(marco, bg=AZUL_OSCURO)
        fila_estado.pack(fill="x", pady=(0, 10))
        self.lbl_estado_secuencia = tk.Label(fila_estado, text="Estado: DETENIDO",
                                              bg=AZUL_OSCURO, fg=AMARILLO, font=("Sans", 11, "bold"))
        self.lbl_estado_secuencia.pack(side="left")
        self.lbl_batch = tk.Label(fila_estado, text="Batchs: 0", width=14,
                                   bg=AZUL_OSCURO, fg="white", font=("Consolas", 10, "bold"))
        self.lbl_batch.pack(side="left", padx=20)
        self.lbl_tiempo_mezclado = tk.Label(fila_estado, text="", bg=AZUL_OSCURO, fg=CIAN_BARRA)
        self.lbl_tiempo_mezclado.pack(side="left")

        cabecera = tk.Frame(marco, bg=AZUL_OSCURO)
        cabecera.pack(fill="x", padx=4)
        tk.Label(cabecera, text="Ingrediente", width=20, anchor="w",
                 bg=AZUL_OSCURO, fg="#90a4ae", font=("Sans", 8, "bold")).pack(side="left")
        tk.Label(cabecera, text="Objetivo", width=10, anchor="e",
                 bg=AZUL_OSCURO, fg="#90a4ae", font=("Sans", 8, "bold")).pack(side="left")

        self.marco_ingredientes = tk.Frame(marco, bg=AZUL_OSCURO)
        self.marco_ingredientes.pack(fill="both", expand=True)
        self._reconstruir_ingredientes(0)

    def _reconstruir_ingredientes(self, idx_formula):
        for w in self.marco_ingredientes.winfo_children():
            w.destroy()
        self.filas_ingrediente = []
        formula = mapa.FORMULAS[idx_formula]
        for ingrediente in formula["ingredientes"]:
            fila = FilaIngrediente(self.marco_ingredientes, ingrediente)
            self.filas_ingrediente.append(fila)

    def _on_cambio_formula(self, event=None):
        idx = self.combo_formula.current()
        self._reconstruir_ingredientes(idx)
        try:
            self.cliente.escribir_registro(mapa.HOLDING_REG_FORMULA_SELECCIONADA, idx)
        except (ConnectionError, OSError):
            pass

    def _iniciar_secuencia(self):
        try:
            self.cliente.escribir_coil(mapa.COIL_SECUENCIA_INICIAR, True)
        except (ConnectionError, OSError):
            pass

    def _detener_secuencia(self):
        try:
            self.cliente.escribir_coil(mapa.COIL_SECUENCIA_DETENER, True)
        except (ConnectionError, OSError):
            pass

    def _bucle_sondeo(self):
        """Polling en bloque: 4 lecturas Modbus cubren TODA la planta."""
        while self._activo:
            try:
                coils = self.cliente.leer_coils(0, mapa.N_COILS)
                discretas = self.cliente.leer_discretas(0, mapa.N_DISCRETAS)
                holding_regs = self.cliente.leer_holding_regs(0, mapa.N_HOLDING_REGS)
                input_regs = self.cliente.leer_input_regs(0, mapa.N_INPUT_REGS)
                self.after(0, self._actualizar_ui, coils, discretas, holding_regs, input_regs)
            except (socket.timeout, ConnectionError, OSError):
                self.after(0, self._marcar_desconectado)
                return
            time.sleep(1)

    def _actualizar_ui(self, coils, discretas, holding_regs, input_regs):
        for tag, fila in self.filas_dispositivo.items():
            direccion = mapa.COIL_DE[tag]
            fila.actualizar(coils[direccion], discretas[direccion])

        for nombre, fila in self.filas_silo.items():
            direccion = mapa.INPUT_REG_DE_SILO[nombre]
            fila.actualizar(input_regs[direccion])

        for nombre, fila in self.filas_bascula.items():
            direccion = mapa.INPUT_REG_DE_BASCULA[nombre]
            fila.actualizar(input_regs[direccion])

        for tag, fila in self.filas_vdf.items():
            frecuencia = input_regs[mapa.INPUT_REG_DE_VDF_FRECUENCIA[tag]]
            estado_bits = input_regs[mapa.INPUT_REG_DE_VDF_ESTADO[tag]]
            fila.actualizar(frecuencia, estado_bits)
            if not self._consignas_precargadas:
                consigna = holding_regs[mapa.HOLDING_REG_DE_VDF_CONSIGNA[tag]]
                fila.entrada_consigna.insert(0, f"{consigna / 10.0:.1f}")
        self._consignas_precargadas = True

        self._actualizar_secuencia(input_regs)

    def _actualizar_secuencia(self, input_regs):
        estado = input_regs[mapa.INPUT_REG_ESTADO_SECUENCIA]
        batch = input_regs[mapa.INPUT_REG_BATCH_ACTUAL]
        formula_idx = input_regs[mapa.INPUT_REG_FORMULA_ACTUAL]
        ingrediente_idx = input_regs[mapa.INPUT_REG_INGREDIENTE_IDX]
        objetivo = input_regs[mapa.INPUT_REG_OBJETIVO_INGREDIENTE] / 10.0
        avance = input_regs[mapa.INPUT_REG_AVANCE_INGREDIENTE] / 10.0
        tiempo_mezclado = input_regs[mapa.INPUT_REG_TIEMPO_MEZCLADO]

        self.lbl_estado_secuencia.config(text=f"Estado: {mapa.ESTADOS_SECUENCIA[estado]}")
        self.lbl_batch.config(text=f"Batchs: {batch}")
        self.lbl_tiempo_mezclado.config(
            text=f"Mezclando... {tiempo_mezclado}s restantes" if estado == 2 else "")

        if self.combo_formula.current() != formula_idx:
            self.combo_formula.current(formula_idx)
            self._reconstruir_ingredientes(formula_idx)

        ingrediente_activo = ingrediente_idx if ingrediente_idx != 0xFFFF else -1
        for i, fila in enumerate(self.filas_ingrediente):
            if estado == 0 and ingrediente_activo == -1:
                fila.actualizar("pendiente")
            elif i < ingrediente_activo or (estado in (2, 3) and ingrediente_activo == -1):
                fila.actualizar("completado")
            elif i == ingrediente_activo and estado == 1:
                fila.actualizar("dosificando...", avance)
            else:
                fila.actualizar("pendiente")

    def _marcar_desconectado(self):
        self.lbl_estado_conexion.config(text="Desconectado del PLC", fg=ROJO_TRIP)

    def _cerrar(self):
        self._activo = False
        self.destroy()


def main():
    cliente = ClienteModbus(IP_PLC, PUERTO_PLC)
    app = PantallaHMI(cliente)
    app.mainloop()


if __name__ == "__main__":
    main()
