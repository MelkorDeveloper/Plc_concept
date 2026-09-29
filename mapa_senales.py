#!/usr/bin/env python3
"""
mapa_senales.py
----------------
Base de datos de tags de la planta (equivalente a la configuracion de un
"I/O Unit" real de Opto 22, o a una tabla de tags de cualquier SCADA).

Tanto plc_servidor.py como hmi_cliente.py importan este mismo archivo,
para que ambos usen exactamente las mismas direcciones Modbus. Esto es
tal cual como se trabaja en un proyecto real: primero se define la base
de datos de puntos, y despues el programa del controlador y las pantallas
del HMI apuntan a ella.

Basado en el diagrama de referencia (planta de alimentos balanceados):
sectores Granos, Harinas, Pre Mix, Acido Graso, Enteros, Mezcladora y Salida.
"""

# =================================================================
# 1) DISPOSITIVOS DIGITALES (motores y valvulas)
#    tipo "motor"   -> tiene retardo de arranque real (contactor + termico)
#    tipo "valvula" -> accionamiento neumatico, mas rapido
# =================================================================
DISPOSITIVOS = [
    # --- Sector Granos ---
    {"tag": "M-404", "nombre": "Silo 1 Granos",   "tipo": "motor", "sector": "GRANOS"},
    {"tag": "M-405", "nombre": "Silo 2 Granos",   "tipo": "motor", "sector": "GRANOS"},
    {"tag": "M-406", "nombre": "Silo 3 Granos",   "tipo": "motor", "sector": "GRANOS"},
    {"tag": "M-407", "nombre": "Silo 4 Granos",   "tipo": "motor", "sector": "GRANOS"},
    {"tag": "M-408", "nombre": "Silo 5 Granos",   "tipo": "motor", "sector": "GRANOS"},
    {"tag": "M-400", "nombre": "Elevador Granos", "tipo": "motor", "sector": "GRANOS"},

    # --- Sector Harinas ---
    {"tag": "M-419", "nombre": "Silo 7 Harinas",   "tipo": "motor", "sector": "HARINAS"},
    {"tag": "M-420", "nombre": "Silo 8 Harinas",   "tipo": "motor", "sector": "HARINAS"},
    {"tag": "M-421", "nombre": "Silo 9 Harinas",   "tipo": "motor", "sector": "HARINAS"},
    {"tag": "M-422", "nombre": "Silo 10 Harinas",  "tipo": "motor", "sector": "HARINAS"},
    {"tag": "M-423", "nombre": "Silo 11 Harinas",  "tipo": "motor", "sector": "HARINAS"},
    {"tag": "M-425", "nombre": "Silo 12 Harinas",  "tipo": "motor", "sector": "HARINAS"},
    {"tag": "M-402", "nombre": "Elevador Harinas", "tipo": "motor", "sector": "HARINAS"},

    # --- Sector Pre Mix ---
    {"tag": "M-410", "nombre": "PMix 1 (S-13)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-411", "nombre": "PMix 2 (S-14)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-412", "nombre": "PMix 3 (S-15)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-413", "nombre": "PMix 4 (S-16)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-414", "nombre": "PMix 5 (S-17)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-415", "nombre": "PMix 6 (S-18)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-416", "nombre": "PMix 7 (S-19)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-417", "nombre": "PMix 8 (S-20)",    "tipo": "motor", "sector": "PREMIX"},
    {"tag": "M-401", "nombre": "Elevador PreMix",  "tipo": "motor", "sector": "PREMIX"},

    # --- Acido graso ---
    {"tag": "M-433", "nombre": "Dosificador Acido Graso", "tipo": "motor",   "sector": "ACIDO_GRASO"},
    {"tag": "M-437", "nombre": "Valvula Silo 30",         "tipo": "valvula", "sector": "ACIDO_GRASO"},

    # --- Enteros ---
    {"tag": "M-409", "nombre": "Transporte Enteros", "tipo": "motor",   "sector": "ENTEROS"},
    {"tag": "M-428", "nombre": "Valvula Vacio",       "tipo": "valvula", "sector": "ENTEROS"},

    # --- Mezcladora ---
    {"tag": "M-441", "nombre": "Motor Mezcladora",            "tipo": "motor",   "sector": "MEZCLADORA"},
    {"tag": "M-442", "nombre": "Valvula Descarga Mezcladora", "tipo": "valvula", "sector": "MEZCLADORA"},

    # --- Salida / Empaque ---
    {"tag": "M-403", "nombre": "Elevador Salida",       "tipo": "motor",   "sector": "SALIDA"},
    {"tag": "M-439", "nombre": "Transportador Salida",  "tipo": "motor",   "sector": "SALIDA"},
    {"tag": "M-418", "nombre": "Valvula Desvio 1",      "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-430", "nombre": "Valvula Desvio 2",      "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-444", "nombre": "Valvula Desvio 3",      "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-445", "nombre": "Valvula Desvio 4",      "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-450", "nombre": "Valvula Silo Prod. 1",  "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-451", "nombre": "Valvula Silo Prod. 2",  "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-452", "nombre": "Valvula Silo Prod. 3",  "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-453", "nombre": "Valvula Silo Prod. 4",  "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-454", "nombre": "Valvula Silo Prod. 5",  "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-455", "nombre": "Valvula Silo Prod. 6",  "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-456", "nombre": "Valvula Silo Prod. 7",  "tipo": "valvula", "sector": "SALIDA"},
    {"tag": "M-457", "nombre": "Valvula Silo Prod. 8",  "tipo": "valvula", "sector": "SALIDA"},
]

# =================================================================
# 2) SILOS DE MATERIA PRIMA (nivel en Kg). Cada uno se descarga con su
#    motor y alimenta a la bascula de su sector, igual que en la planta real.
# =================================================================
SILOS = [
    {"nombre": "Silo 1 Granos",  "sector": "GRANOS", "motor": "M-404", "nivel_inicial_kg": 8000, "alimenta_a": "Bascula Granos"},
    {"nombre": "Silo 2 Granos",  "sector": "GRANOS", "motor": "M-405", "nivel_inicial_kg": 7500, "alimenta_a": "Bascula Granos"},
    {"nombre": "Silo 3 Granos",  "sector": "GRANOS", "motor": "M-406", "nivel_inicial_kg": 9000, "alimenta_a": "Bascula Granos"},
    {"nombre": "Silo 4 Granos",  "sector": "GRANOS", "motor": "M-407", "nivel_inicial_kg": 6000, "alimenta_a": "Bascula Granos"},
    {"nombre": "Silo 5 Granos",  "sector": "GRANOS", "motor": "M-408", "nivel_inicial_kg": 7000, "alimenta_a": "Bascula Granos"},

    {"nombre": "Silo 7 Harinas",  "sector": "HARINAS", "motor": "M-419", "nivel_inicial_kg": 4000, "alimenta_a": "Bascula Harinas"},
    {"nombre": "Silo 8 Harinas",  "sector": "HARINAS", "motor": "M-420", "nivel_inicial_kg": 3500, "alimenta_a": "Bascula Harinas"},
    {"nombre": "Silo 9 Harinas",  "sector": "HARINAS", "motor": "M-421", "nivel_inicial_kg": 4200, "alimenta_a": "Bascula Harinas"},
    {"nombre": "Silo 10 Harinas", "sector": "HARINAS", "motor": "M-422", "nivel_inicial_kg": 3800, "alimenta_a": "Bascula Harinas"},
    {"nombre": "Silo 11 Harinas", "sector": "HARINAS", "motor": "M-423", "nivel_inicial_kg": 4500, "alimenta_a": "Bascula Harinas"},
    {"nombre": "Silo 12 Harinas", "sector": "HARINAS", "motor": "M-425", "nivel_inicial_kg": 3900, "alimenta_a": "Bascula Harinas"},

    {"nombre": "Silo S-13 PreMix", "sector": "PREMIX", "motor": "M-410", "nivel_inicial_kg": 800, "alimenta_a": "Bascula PreMix"},
    {"nombre": "Silo S-14 PreMix", "sector": "PREMIX", "motor": "M-411", "nivel_inicial_kg": 750, "alimenta_a": "Bascula PreMix"},
    {"nombre": "Silo S-15 PreMix", "sector": "PREMIX", "motor": "M-412", "nivel_inicial_kg": 900, "alimenta_a": "Bascula PreMix"},
    {"nombre": "Silo S-16 PreMix", "sector": "PREMIX", "motor": "M-413", "nivel_inicial_kg": 650, "alimenta_a": "Bascula PreMix"},
    {"nombre": "Silo S-17 PreMix", "sector": "PREMIX", "motor": "M-414", "nivel_inicial_kg": 700, "alimenta_a": "Bascula PreMix"},
    {"nombre": "Silo S-18 PreMix", "sector": "PREMIX", "motor": "M-415", "nivel_inicial_kg": 850, "alimenta_a": "Bascula PreMix"},
    {"nombre": "Silo S-19 PreMix", "sector": "PREMIX", "motor": "M-416", "nivel_inicial_kg": 780, "alimenta_a": "Bascula PreMix"},
    {"nombre": "Silo S-20 PreMix", "sector": "PREMIX", "motor": "M-417", "nivel_inicial_kg": 820, "alimenta_a": "Bascula PreMix"},

    {"nombre": "Silo 30 Acido Graso", "sector": "ACIDO_GRASO", "motor": "M-433", "nivel_inicial_kg": 500, "alimenta_a": "Bascula Acido Graso"},
]

# =================================================================
# 3) BASCULAS (una por sector de dosificacion, como los recuadros
#    con "Kg" del diagrama real)
# =================================================================
BASCULAS = [
    {"nombre": "Bascula Granos"},
    {"nombre": "Bascula Harinas"},
    {"nombre": "Bascula PreMix"},
    {"nombre": "Bascula Acido Graso"},
    {"nombre": "Bascula Enteros"},
]

SECTORES = ["GRANOS", "HARINAS", "PREMIX", "ACIDO_GRASO", "ENTEROS", "MEZCLADORA", "SALIDA"]

# =================================================================
# 4) ASIGNACION AUTOMATICA DE DIRECCIONES MODBUS (tag database real)
# =================================================================
COIL_DE = {}       # tag de dispositivo -> direccion de coil (comando)
DISCRETA_DE = {}   # tag de dispositivo -> direccion de discrete input (confirmacion real)
for _i, _disp in enumerate(DISPOSITIVOS):
    COIL_DE[_disp["tag"]] = _i
    DISCRETA_DE[_disp["tag"]] = _i

N_DISPOSITIVOS = len(DISPOSITIVOS)

# Coils de "Tara" (reset de bascula a cero), a continuacion de los de los dispositivos
COIL_TARA_DE = {}
for _i, _bas in enumerate(BASCULAS):
    COIL_TARA_DE[_bas["nombre"]] = N_DISPOSITIVOS + _i

N_COILS = N_DISPOSITIVOS + len(BASCULAS)
N_DISCRETAS = N_DISPOSITIVOS

INPUT_REG_DE_SILO = {}       # nombre de silo -> direccion de input register (nivel Kg x10)
for _i, _silo in enumerate(SILOS):
    INPUT_REG_DE_SILO[_silo["nombre"]] = _i

_OFFSET_BASCULAS = len(SILOS)
INPUT_REG_DE_BASCULA = {}    # nombre de bascula -> direccion de input register (peso Kg x10)
for _i, _bas in enumerate(BASCULAS):
    INPUT_REG_DE_BASCULA[_bas["nombre"]] = _OFFSET_BASCULAS + _i

N_INPUT_REGS = len(SILOS) + len(BASCULAS)


def dispositivo_por_tag(tag):
    for d in DISPOSITIVOS:
        if d["tag"] == tag:
            return d
    return None


def nombre_por_direccion_coil(direccion):
    """Traduce una direccion de coil a nombre legible (para el sniffer)."""
    for tag, addr in COIL_DE.items():
        if addr == direccion:
            return f"{tag} ({dispositivo_por_tag(tag)['nombre']})"
    for nombre, addr in COIL_TARA_DE.items():
        if addr == direccion:
            return f"Tara {nombre}"
    return None


def nombre_por_direccion_discreta(direccion):
    for tag, addr in DISCRETA_DE.items():
        if addr == direccion:
            return f"{tag} ({dispositivo_por_tag(tag)['nombre']}) - confirmacion real"
    return None


def nombre_por_direccion_input_reg(direccion):
    for nombre, addr in INPUT_REG_DE_SILO.items():
        if addr == direccion:
            return f"{nombre} (nivel)"
    for nombre, addr in INPUT_REG_DE_BASCULA.items():
        if addr == direccion:
            return f"{nombre} (peso)"
    return None


if __name__ == "__main__":
    print(f"Dispositivos: {N_DISPOSITIVOS}  Coils totales: {N_COILS}  "
          f"Discretas: {N_DISCRETAS}  Input Registers: {N_INPUT_REGS}  "
          f"Silos: {len(SILOS)}  Basculas: {len(BASCULAS)}")
