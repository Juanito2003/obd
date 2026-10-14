"""Escáner OBD-II en tiempo real con un adaptador ELM327.

Lee RPM, posición del acelerador (TPS), presión del colector (MAP) y
temperatura del refrigerante, y avisa de lecturas que apuntan a un
sensor TPS o MAP defectuoso o a un motor que se calienta de más.

Uso:
    python escaner_obd.py                  # detecta el puerto automáticamente
    python escaner_obd.py --puerto COM3    # Windows
    python escaner_obd.py --puerto /dev/ttyUSB0 --intervalo 1
    python escaner_obd.py --csv viaje.csv  # guarda cada lectura en un CSV
    python escaner_obd.py --dtc            # lee los códigos de avería y sale
"""

import argparse
import csv
import os
import time
from datetime import datetime

# Umbrales de detección
UMBRAL_PRESION_APAGADO = 95   # kPa (valor normal con motor apagado: ~100 kPa)
UMBRAL_TPS_APAGADO = 5        # % (máximo permitido con motor apagado)
UMBRAL_PRESION_RALENTI = 50   # kPa (máximo esperado al ralentí en un motor atmosférico)
RPM_RALENTI_MAX = 1100        # rpm por debajo de las cuales se considera ralentí
TPS_RALENTI_MAX = 20          # % de acelerador para considerar el pedal suelto (muchos
                              # coches marcan 10-20 % con la mariposa cerrada)
LECTURAS_TPS_100_PARA_FALLA = 3  # lecturas seguidas al 100 % para considerarlo constante
UMBRAL_TEMP_REFRIGERANTE = 105  # °C (lo normal en marcha es 85-100 °C)


class DetectorFallas:
    """Analiza lecturas sucesivas y devuelve las fallas detectadas.

    Guarda estado entre lecturas para distinguir un acelerador pisado a
    fondo un momento de un TPS que marca 100 % de forma constante.
    """

    def __init__(self, lecturas_tps_100=LECTURAS_TPS_100_PARA_FALLA):
        self.lecturas_tps_100 = lecturas_tps_100
        self._seguidas_tps_100 = 0

    def analizar(self, valores):
        fallas = []
        rpm = valores.get("rpm")
        tps = valores.get("throttle")
        presion = valores.get("presion")
        temp = valores.get("temp_refrigerante")

        # Temperatura: el sobrecalentamiento se avisa aunque falte la lectura
        # de RPM, porque no depende de si el motor está encendido.
        if temp is not None and temp > UMBRAL_TEMP_REFRIGERANTE:
            fallas.append(f"AVISO TEMPERATURA: refrigerante a {temp} °C")

        # Sin RPM no sabemos si el motor está encendido: no se evalúa nada
        # que dependa de ello, para no dar falsos positivos.
        if rpm is None:
            self._seguidas_tps_100 = 0
            return fallas

        motor_apagado = rpm == 0
        al_ralenti = not motor_apagado and rpm < RPM_RALENTI_MAX

        # TPS
        if tps is not None:
            if motor_apagado and tps > UMBRAL_TPS_APAGADO:
                fallas.append(f"FALLA TPS: Acelerador al {tps}% con motor apagado")

            if not motor_apagado and tps >= 100.0:
                self._seguidas_tps_100 += 1
            else:
                self._seguidas_tps_100 = 0

            if self._seguidas_tps_100 >= self.lecturas_tps_100:
                fallas.append(
                    f"FALLA TPS: Acelerador al 100% constante "
                    f"({self._seguidas_tps_100} lecturas seguidas)"
                )
        else:
            self._seguidas_tps_100 = 0

        # MAP
        if presion is not None:
            if motor_apagado and presion < UMBRAL_PRESION_APAGADO:
                fallas.append(
                    f"FALLA MAP: Presión anormal ({presion} kPa) con motor apagado"
                )
            # Al acelerar, la presión del colector sube de forma normal, así
            # que el límite de ralentí solo se aplica con el pie fuera del pedal.
            elif (
                al_ralenti
                and tps is not None
                and tps < TPS_RALENTI_MAX
                and presion > UMBRAL_PRESION_RALENTI
            ):
                fallas.append(
                    f"FALLA MAP: Presión alta ({presion} kPa) al ralentí"
                )

        return fallas


def conectar_obd(puerto=None):
    import obd

    destino = puerto or "detección automática"
    try:
        connection = obd.OBD(puerto)
        if not connection.is_connected():
            print(f"Error: No se pudo conectar al adaptador ({destino})")
            return None
        print(f"✅ Conectado al adaptador OBD2 en {connection.port_name()}")
        print(f"Protocolo: {connection.protocol_name()}")
        return connection
    except Exception as e:
        print(f"Error de conexión ({destino}): {e}")
        return None


def leer_parametros(connection):
    import obd

    parametros = {
        "rpm": connection.query(obd.commands.RPM),
        "throttle": connection.query(obd.commands.THROTTLE_POS),
        "presion": connection.query(obd.commands.INTAKE_PRESSURE),
        "temp_refrigerante": connection.query(obd.commands.COOLANT_TEMP),
    }

    # Convertir a valores numéricos
    valores = {}
    for key, respuesta in parametros.items():
        if not respuesta.is_null():
            valores[key] = respuesta.value.magnitude
        else:
            valores[key] = None

    return valores


def mostrar(valores, fallas):
    print("\n=== Parámetros en tiempo real ===")
    for key, value in valores.items():
        if value is not None:
            print(f"{key.upper()}: {value}")

    if fallas:
        print("\n⚠️ Fallas detectadas:")
        for falla in fallas:
            print(f"- {falla}")
    else:
        print("\n✅ Todos los parámetros son normales")

    print("\n" + "-" * 50)


def leer_dtc(connection):
    """Devuelve la lista de códigos de avería (codigo, descripcion) guardados en la centralita."""
    import obd

    respuesta = connection.query(obd.commands.GET_DTC)
    if respuesta.is_null():
        return []
    return list(respuesta.value)


def formatear_dtc(codigos):
    """Texto a mostrar para una lista de códigos de avería (separado para poder probarlo sin coche)."""
    if not codigos:
        return "✅ Sin códigos de avería"
    lineas = [f"⚠️ {len(codigos)} código(s) de avería:"]
    for codigo, descripcion in codigos:
        lineas.append(f"- {codigo}: {descripcion or '(sin descripción)'}")
    return "\n".join(lineas)


COLUMNAS_CSV = ["fecha_hora", "rpm", "throttle", "presion", "temp_refrigerante", "fallas"]


def guardar_csv(ruta, valores, fallas, ahora=None):
    """Añade una lectura al final del CSV; escribe la cabecera si el archivo es nuevo."""
    nuevo = not os.path.exists(ruta) or os.path.getsize(ruta) == 0
    ahora = ahora or datetime.now()
    fila = [ahora.isoformat(timespec="seconds")]
    fila += ["" if valores.get(c) is None else valores[c] for c in COLUMNAS_CSV[1:5]]
    fila.append(" | ".join(fallas))
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if nuevo:
            escritor.writerow(COLUMNAS_CSV)
        escritor.writerow(fila)


def crear_parser():
    parser = argparse.ArgumentParser(
        description="Escáner OBD-II en tiempo real con un adaptador ELM327."
    )
    parser.add_argument(
        "--puerto",
        help="puerto del adaptador (COM3, /dev/ttyUSB0...). "
        "Si no se indica, se detecta automáticamente.",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=2.0,
        help="segundos entre lecturas (por defecto: 2)",
    )
    parser.add_argument(
        "--una-vez",
        action="store_true",
        help="hace una sola lectura y termina",
    )
    parser.add_argument(
        "--csv",
        metavar="RUTA",
        help="guarda cada lectura en un archivo CSV (se añade al final si ya existe)",
    )
    parser.add_argument(
        "--dtc",
        action="store_true",
        help="lee los códigos de avería guardados en la centralita y termina",
    )
    return parser


def main(argv=None):
    args = crear_parser().parse_args(argv)

    conexion = conectar_obd(args.puerto)
    if not conexion:
        return 1

    detector = DetectorFallas()
    try:
        if args.dtc:
            print(formatear_dtc(leer_dtc(conexion)))
            return 0

        while True:
            valores = leer_parametros(conexion)
            fallas = detector.analizar(valores)
            mostrar(valores, fallas)
            if args.csv:
                guardar_csv(args.csv, valores, fallas)
            if args.una_vez:
                break
            time.sleep(args.intervalo)

    except KeyboardInterrupt:
        print("\nMonitoreo detenido por el usuario.")
    except Exception as e:
        print(f"Error general: {e}")
        return 1
    finally:
        conexion.close()
        print("\nConexión cerrada.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
