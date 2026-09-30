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
    {"nombre": "Bascula General (Formula)"},
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

# =================================================================
# 5) VARIADORES DE FRECUENCIA (VDF tipo ABB), como los del diagrama real
#    Cada VDF va asociado a un motor existente y le agrega:
#      - una consigna de frecuencia (holding register, escribible)
#      - la frecuencia real (input register, con rampa de aceleracion)
#      - una palabra de estado con bits On/Run/Ref/Trip (input register)
#      - un coil para forzar una falla (fines de aprendizaje) y otro para
#        reconocer/resetear el drive, igual que el boton "Reset" de un VDF real
# =================================================================
VDFS = [
    {"tag": "VDF-402", "nombre": "VDF Elevador Harinas (ABB)",   "motor": "M-402"},
    {"tag": "VDF-409", "nombre": "VDF Transporte Enteros (ABB)", "motor": "M-409"},
]

VDF_BIT_ON = 0x01
VDF_BIT_RUN = 0x02
VDF_BIT_REF = 0x04
VDF_BIT_TRIP = 0x08

HOLDING_REG_DE_VDF_CONSIGNA = {}   # tag VDF -> holding register (consigna Hz x10)
for _i, _v in enumerate(VDFS):
    HOLDING_REG_DE_VDF_CONSIGNA[_v["tag"]] = _i
N_HOLDING_REGS = len(VDFS)

INPUT_REG_DE_VDF_FRECUENCIA = {}   # tag VDF -> input register (frecuencia real Hz x10)
INPUT_REG_DE_VDF_ESTADO = {}       # tag VDF -> input register (bits On/Run/Ref/Trip)
for _i, _v in enumerate(VDFS):
    INPUT_REG_DE_VDF_FRECUENCIA[_v["tag"]] = N_INPUT_REGS + _i * 2
    INPUT_REG_DE_VDF_ESTADO[_v["tag"]] = N_INPUT_REGS + _i * 2 + 1
N_INPUT_REGS += len(VDFS) * 2

COIL_VDF_FORZAR_FALLA = {}   # tag VDF -> coil (pulso, simula un trip para aprender)
COIL_VDF_RESET_FALLA = {}    # tag VDF -> coil (pulso, reconoce/resetea el drive)
for _i, _v in enumerate(VDFS):
    COIL_VDF_FORZAR_FALLA[_v["tag"]] = N_COILS + _i * 2
    COIL_VDF_RESET_FALLA[_v["tag"]] = N_COILS + _i * 2 + 1
N_COILS += len(VDFS) * 2

# =================================================================
# 6) SECUENCIADOR DE FORMULA / BATCH (equivalente al panel derecho
#    "Formula / Batchs" del diagrama real). Replica la formula 12862
#    tal cual aparece en el diagrama de referencia.
# =================================================================
FORMULAS = [
    {
        "id": 12862,
        "nombre": "Formula 12862",
        "ingredientes": [
            {"nombre": "MAIZ NACIONAL",     "silo": "Silo 1 Granos",       "objetivo_kg": 281.0},
            {"nombre": "AFRECHILLO",        "silo": "Silo 7 Harinas",      "objetivo_kg": 85.0},
            {"nombre": "HARINA DE CARNE",   "silo": "Silo 8 Harinas",      "objetivo_kg": 70.0},
            {"nombre": "HARINA DE SOYA",    "silo": "Silo 9 Harinas",      "objetivo_kg": 104.0},
            {"nombre": "CONCHUELA ENTERA",  "silo": "Silo 2 Granos",       "objetivo_kg": 115.0},
            {"nombre": "ACIDO GRASO",       "silo": "Silo 30 Acido Graso", "objetivo_kg": 32.0},
            {"nombre": "TRITICAL",          "silo": "Silo 3 Granos",       "objetivo_kg": 200.0},
            {"nombre": "POROTO DE SOYA",    "silo": "Silo 4 Granos",       "objetivo_kg": 100.0},
            {"nombre": "PREMIX",            "silo": "Silo S-13 PreMix",    "objetivo_kg": 14.0},
        ],
    },
]

ESTADOS_SECUENCIA = {0: "DETENIDO", 1: "DOSIFICANDO", 2: "MEZCLANDO", 3: "DESCARGANDO"}

COIL_SECUENCIA_INICIAR = N_COILS
COIL_SECUENCIA_DETENER = N_COILS + 1
N_COILS += 2

HOLDING_REG_FORMULA_SELECCIONADA = N_HOLDING_REGS
N_HOLDING_REGS += 1

INPUT_REG_ESTADO_SECUENCIA = N_INPUT_REGS
INPUT_REG_BATCH_ACTUAL = N_INPUT_REGS + 1
INPUT_REG_FORMULA_ACTUAL = N_INPUT_REGS + 2
INPUT_REG_INGREDIENTE_IDX = N_INPUT_REGS + 3
INPUT_REG_OBJETIVO_INGREDIENTE = N_INPUT_REGS + 4   # Kg x10
INPUT_REG_AVANCE_INGREDIENTE = N_INPUT_REGS + 5     # Kg x10
INPUT_REG_TIEMPO_MEZCLADO = N_INPUT_REGS + 6        # segundos
N_INPUT_REGS += 7


def dispositivo_por_tag(tag):
    for d in DISPOSITIVOS:
        if d["tag"] == tag:
            return d
    return None


def silo_por_nombre(nombre):
    for s in SILOS:
        if s["nombre"] == nombre:
            return s
    return None


def nombre_por_direccion_coil(direccion):
    """Traduce una direccion de coil a nombre legible (para el sniffer)."""
    for tag, addr in COIL_DE.items():
        if addr == direccion:
            return f"{tag} ({dispositivo_por_tag(tag)['nombre']})"
    for nombre, addr in COIL_TARA_DE.items():
        if addr == direccion:
            return f"Tara {nombre}"
    for tag, addr in COIL_VDF_FORZAR_FALLA.items():
        if addr == direccion:
            return f"Forzar Falla {tag}"
    for tag, addr in COIL_VDF_RESET_FALLA.items():
        if addr == direccion:
            return f"Reset Falla {tag}"
    if direccion == COIL_SECUENCIA_INICIAR:
        return "Iniciar Secuencia"
    if direccion == COIL_SECUENCIA_DETENER:
        return "Detener Secuencia"
    return None


def nombre_por_direccion_holding(direccion):
    for tag, addr in HOLDING_REG_DE_VDF_CONSIGNA.items():
        if addr == direccion:
            return f"Consigna Hz {tag}"
    if direccion == HOLDING_REG_FORMULA_SELECCIONADA:
        return "Formula Seleccionada"
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
    for tag, addr in INPUT_REG_DE_VDF_FRECUENCIA.items():
        if addr == direccion:
            return f"Frecuencia real {tag}"
    for tag, addr in INPUT_REG_DE_VDF_ESTADO.items():
        if addr == direccion:
            return f"Estado {tag} (On/Run/Ref/Trip)"
    _etiquetas_secuencia = {
        INPUT_REG_ESTADO_SECUENCIA: "Estado Secuencia",
        INPUT_REG_BATCH_ACTUAL: "Batch Actual",
        INPUT_REG_FORMULA_ACTUAL: "Formula Actual",
        INPUT_REG_INGREDIENTE_IDX: "Indice Ingrediente Actual",
        INPUT_REG_OBJETIVO_INGREDIENTE: "Objetivo Ingrediente Actual",
        INPUT_REG_AVANCE_INGREDIENTE: "Avance Ingrediente Actual",
        INPUT_REG_TIEMPO_MEZCLADO: "Tiempo Mezclado Restante",
    }
    return _etiquetas_secuencia.get(direccion)


if __name__ == "__main__":
    print(f"Dispositivos: {N_DISPOSITIVOS}  Coils totales: {N_COILS}  "
          f"Discretas: {N_DISCRETAS}  Holding Regs: {N_HOLDING_REGS}  "
          f"Input Registers: {N_INPUT_REGS}  Silos: {len(SILOS)}  "
          f"Basculas: {len(BASCULAS)}  VDFs: {len(VDFS)}  Formulas: {len(FORMULAS)}")
