#!/usr/bin/env python3
"""
modbus_sniffer.py
------------------
Lee un stream pcap (el que produce tcpdump con -w -) desde stdin y
decodifica en tiempo real las tramas Modbus TCP (Ethernet/IP/TCP + MBAP),
mostrando peticion/respuesta, funcion, direccion y valores en lugar
de hexadecimal crudo.

USO EN VIVO (necesita permisos de captura, por eso el sudo):
    sudo tcpdump -i lo -w - 'tcp port 5020' 2>/dev/null | python3 modbus_sniffer.py 5020

USO SOBRE UN ARCHIVO YA CAPTURADO:
    tcpdump -i lo -w captura.pcap 'tcp port 5020'
    python3 modbus_sniffer.py 5020 < captura.pcap

Si tu red de pruebas usa otra interfaz (ej. eth0, wlan0) o el puerto
502 en vez de 5020, ajusta ambos comandos.
"""

import struct
import sys
import time

PUERTO_PLC = int(sys.argv[1]) if len(sys.argv) > 1 else 5020

# Traduccion opcional de direcciones a nombres de tag, si mapa_senales.py
# esta en el mismo directorio (mismo mapa que usan plc_servidor y hmi_cliente)
try:
    import mapa_senales as mapa
    TIENE_MAPA = True
except ImportError:
    TIENE_MAPA = False

FUNCIONES = {
    0x01: "Leer Coils",
    0x02: "Leer Discrete Inputs",
    0x03: "Leer Holding Registers",
    0x04: "Leer Input Registers",
    0x05: "Escribir Coil",
    0x06: "Escribir Registro",
}

# Buffers de reensamblado TCP, uno por conexion (4-tupla), por direccion
buffers = {}

# Contexto peticion->respuesta: recuerda que direccion/cantidad se pidio
# en cada transaccion, para poder anotar tambien la respuesta con nombres de tag
contexto_transacciones = {}


def resolver_nombre(fc, direccion):
    """Traduce direccion Modbus a nombre de tag, si hay mapa_senales disponible."""
    if not TIENE_MAPA:
        return None
    if fc in (0x01, 0x05):
        return mapa.nombre_por_direccion_coil(direccion)
    if fc == 0x02:
        return mapa.nombre_por_direccion_discreta(direccion)
    if fc == 0x04:
        return mapa.nombre_por_direccion_input_reg(direccion)
    if fc in (0x03, 0x06):
        return mapa.nombre_por_direccion_holding(direccion)
    return None


def etiquetas_de_rango(fc, direccion_base, cantidad):
    """Lista de 'direccion: nombre' para cada punto de un rango leido."""
    etiquetas = []
    for i in range(cantidad):
        nombre = resolver_nombre(fc, direccion_base + i)
        if nombre:
            etiquetas.append(f"{direccion_base + i}:{nombre}")
        else:
            etiquetas.append(str(direccion_base + i))
    return etiquetas


# --- Utilidad para leer exactamente N bytes de stdin (stream, no archivo) ---
def leer_exacto(stream, n):
    datos = b""
    while len(datos) < n:
        trozo = stream.read(n - len(datos))
        if not trozo:
            return None  # EOF
        datos += trozo
    return datos


def formato_hora(ts_sec, ts_usec):
    t = time.localtime(ts_sec)
    return f"{time.strftime('%H:%M:%S', t)}.{ts_usec // 1000:03d}"


def procesar_pdu(pdu, es_peticion, transaccion_id):
    if len(pdu) < 2:
        return "  (PDU incompleta)"

    fc = pdu[0]

    if fc & 0x80:  # excepcion Modbus
        codigo_excepcion = pdu[1]
        return f"  !! EXCEPCION funcion=0x{fc & 0x7F:02X} codigo={codigo_excepcion}"

    nombre = FUNCIONES.get(fc, f"funcion desconocida 0x{fc:02X}")

    if fc in (0x01, 0x02, 0x03, 0x04):
        if es_peticion:
            if len(pdu) < 5:
                return f"  {nombre}: PDU incompleta"
            direccion, cantidad = struct.unpack(">HH", pdu[1:5])
            contexto_transacciones[transaccion_id] = (fc, direccion, cantidad)
            etiquetas = etiquetas_de_rango(fc, direccion, cantidad)
            return f"  {nombre}: {', '.join(etiquetas)}"
        else:
            contexto = contexto_transacciones.get(transaccion_id)
            direccion_base = contexto[1] if contexto else None
            n_bytes = pdu[1]
            datos = pdu[2:2 + n_bytes]
            if fc in (0x03, 0x04):  # registros de 16 bits
                cantidad = n_bytes // 2
                valores = struct.unpack(f">{cantidad}H", datos) if cantidad else ()
                if direccion_base is not None:
                    partes = []
                    for i, v in enumerate(valores):
                        nombre_tag = resolver_nombre(fc, direccion_base + i)
                        partes.append(f"{nombre_tag or direccion_base + i}={v}")
                    return f"  {nombre} -> {', '.join(partes)}"
                return f"  {nombre} -> valores={list(valores)}"
            else:  # bits empaquetados
                bits = []
                for byte in datos:
                    for i in range(8):
                        bits.append((byte >> i) & 1)
                cantidad_real = contexto[2] if contexto else n_bytes * 8
                bits = bits[:cantidad_real]
                if direccion_base is not None:
                    partes = []
                    for i, b in enumerate(bits):
                        nombre_tag = resolver_nombre(fc, direccion_base + i)
                        partes.append(f"{nombre_tag or direccion_base + i}={b}")
                    return f"  {nombre} -> {', '.join(partes)}"
                return f"  {nombre} -> bits={bits}"

    elif fc in (0x05, 0x06):
        if len(pdu) < 5:
            return f"  {nombre}: PDU incompleta"
        direccion, valor = struct.unpack(">HH", pdu[1:5])
        nombre_tag = resolver_nombre(fc, direccion)
        etiqueta_direccion = nombre_tag or f"direccion={direccion}"
        if fc == 0x05:
            valor_legible = "ON" if valor == 0xFF00 else "OFF"
        else:
            valor_legible = valor
        etiqueta = "peticion" if es_peticion else "confirmacion del PLC"
        return f"  {nombre} ({etiqueta}): {etiqueta_direccion} valor={valor_legible}"

    return f"  {nombre}: datos crudos={pdu[1:].hex(' ')}"


def extraer_frames_modbus(buf):
    """Extrae del buffer todas las tramas MBAP completas que se puedan, devuelve (frames, resto)."""
    frames = []
    while len(buf) >= 7:
        transaccion_id, protocolo, longitud, unit_id = struct.unpack(">HHHB", buf[:7])
        total = 6 + longitud  # cabecera fija (6) + lo que indica "longitud" (unit_id + pdu)
        if len(buf) < total:
            break  # aun no llego completa, esperar mas datos
        pdu = buf[7:total]
        frames.append((transaccion_id, unit_id, pdu))
        buf = buf[total:]
    return frames, buf


def procesar_paquete(paquete, linktype, ts_sec, ts_usec):
    # --- Quitar cabecera de enlace segun linktype ---
    if linktype == 1:  # Ethernet (incluye loopback con cabecera falsa)
        if len(paquete) < 14:
            return
        eth_tipo = struct.unpack(">H", paquete[12:14])[0]
        if eth_tipo != 0x0800:  # no es IPv4
            return
        ip_paquete = paquete[14:]
    elif linktype == 113:  # Linux cooked capture (SLL)
        if len(paquete) < 16:
            return
        proto = struct.unpack(">H", paquete[14:16])[0]
        if proto != 0x0800:
            return
        ip_paquete = paquete[16:]
    elif linktype == 101:  # RAW IP
        ip_paquete = paquete
    else:
        return  # tipo de enlace no soportado por este script

    if len(ip_paquete) < 20:
        return
    version_ihl = ip_paquete[0]
    ihl = (version_ihl & 0x0F) * 4
    protocolo_ip = ip_paquete[9]
    if protocolo_ip != 6:  # no es TCP
        return
    ip_origen = ".".join(str(b) for b in ip_paquete[12:16])
    ip_destino = ".".join(str(b) for b in ip_paquete[16:20])

    tcp_paquete = ip_paquete[ihl:]
    if len(tcp_paquete) < 20:
        return
    puerto_origen, puerto_destino = struct.unpack(">HH", tcp_paquete[0:4])
    offset_datos = (tcp_paquete[12] >> 4) * 4
    payload = tcp_paquete[offset_datos:]

    if not payload:
        return  # ACK puro, sin datos Modbus

    if PUERTO_PLC not in (puerto_origen, puerto_destino):
        return

    es_peticion = (puerto_destino == PUERTO_PLC)
    clave = (ip_origen, puerto_origen, ip_destino, puerto_destino)

    buf = buffers.get(clave, b"") + payload
    frames, resto = extraer_frames_modbus(buf)
    buffers[clave] = resto

    for transaccion_id, unit_id, pdu in frames:
        hora = formato_hora(ts_sec, ts_usec)
        direccion_txt = f"{ip_origen}:{puerto_origen} -> {ip_destino}:{puerto_destino}"
        etiqueta = "PETICION " if es_peticion else "RESPUESTA"
        print(f"[{hora}] {etiqueta}  {direccion_txt}  (tid={transaccion_id} unit={unit_id})")
        print(procesar_pdu(pdu, es_peticion, transaccion_id))


def main():
    entrada = sys.stdin.buffer

    cabecera_global = leer_exacto(entrada, 24)
    if cabecera_global is None:
        print("No se pudo leer la cabecera pcap (stream vacio).", file=sys.stderr)
        return

    magic = struct.unpack("<I", cabecera_global[:4])[0]
    if magic == 0xa1b2c3d4:
        endian = "<"
    elif magic == 0xd4c3b2a1:
        endian = ">"
    else:
        print("Formato pcap no reconocido (usa 'tcpdump -w -').", file=sys.stderr)
        return

    linktype = struct.unpack(endian + "I", cabecera_global[20:24])[0]
    print(f"[sniffer] Escuchando Modbus TCP en el puerto {PUERTO_PLC} "
          f"(link-type={linktype})", file=sys.stderr)

    while True:
        cab_paquete = leer_exacto(entrada, 16)
        if cab_paquete is None:
            break
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack(endian + "IIII", cab_paquete)
        paquete = leer_exacto(entrada, incl_len)
        if paquete is None:
            break
        try:
            procesar_paquete(paquete, linktype, ts_sec, ts_usec)
        except Exception as e:
            print(f"[sniffer] error decodificando paquete: {e}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
