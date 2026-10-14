import csv
from datetime import datetime

from escaner_obd import COLUMNAS_CSV, crear_parser, guardar_csv


def leer(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_crea_el_archivo_con_cabecera_y_una_fila(tmp_path):
    ruta = tmp_path / "viaje.csv"
    valores = {"rpm": 812.0, "throttle": 14.1, "presion": 33, "temp_refrigerante": 88}
    guardar_csv(ruta, valores, [], ahora=datetime(2026, 10, 15, 8, 30, 2))
    filas = leer(ruta)
    assert filas[0] == COLUMNAS_CSV
    assert filas[1] == ["2026-10-15T08:30:02", "812.0", "14.1", "33", "88", ""]


def test_dos_lecturas_una_sola_cabecera(tmp_path):
    ruta = tmp_path / "viaje.csv"
    valores = {"rpm": 800.0, "throttle": 0.0, "presion": 35, "temp_refrigerante": 90}
    guardar_csv(ruta, valores, [])
    guardar_csv(ruta, valores, [])
    filas = leer(ruta)
    assert len(filas) == 3
    assert filas.count(COLUMNAS_CSV) == 1


def test_valores_que_faltan_quedan_vacios_y_fallas_juntas(tmp_path):
    ruta = tmp_path / "viaje.csv"
    valores = {"rpm": None, "throttle": 30.0, "presion": None, "temp_refrigerante": 112.0}
    fallas = ["AVISO TEMPERATURA: refrigerante a 112.0 °C", "FALLA TPS: prueba"]
    guardar_csv(ruta, valores, fallas)
    fila = leer(ruta)[1]
    assert fila[1] == "" and fila[3] == ""
    assert fila[5] == "AVISO TEMPERATURA: refrigerante a 112.0 °C | FALLA TPS: prueba"


def test_parser_opcion_csv():
    assert crear_parser().parse_args([]).csv is None
    assert crear_parser().parse_args(["--csv", "viaje.csv"]).csv == "viaje.csv"


def test_main_guarda_la_lectura_en_el_csv(tmp_path, monkeypatch):
    import escaner_obd

    class ConexionFalsa:
        def close(self):
            pass

    valores = {"rpm": 800.0, "throttle": 0.0, "presion": 35, "temp_refrigerante": 90}
    monkeypatch.setattr(escaner_obd, "conectar_obd", lambda puerto: ConexionFalsa())
    monkeypatch.setattr(escaner_obd, "leer_parametros", lambda conexion: valores)
    ruta = tmp_path / "viaje.csv"

    assert escaner_obd.main(["--una-vez", "--csv", str(ruta)]) == 0
    filas = leer(ruta)
    assert len(filas) == 2 and filas[1][1] == "800.0"
