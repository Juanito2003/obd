import pytest

from escaner_obd import DetectorFallas, crear_parser


def lectura(rpm=800, throttle=0.0, presion=35.0, temp=90.0):
    return {"rpm": rpm, "throttle": throttle, "presion": presion, "temp_refrigerante": temp}


def test_lectura_normal_al_ralenti_sin_fallas():
    assert DetectorFallas().analizar(lectura()) == []


def test_motor_apagado_normal_sin_fallas():
    assert DetectorFallas().analizar(lectura(rpm=0, throttle=0.0, presion=100.0)) == []


def test_tps_abierto_con_motor_apagado():
    fallas = DetectorFallas().analizar(lectura(rpm=0, throttle=12.0, presion=100.0))
    assert len(fallas) == 1 and fallas[0].startswith("FALLA TPS")


def test_map_bajo_con_motor_apagado():
    fallas = DetectorFallas().analizar(lectura(rpm=0, throttle=0.0, presion=80.0))
    assert len(fallas) == 1 and fallas[0].startswith("FALLA MAP")


def test_map_alto_al_ralenti():
    fallas = DetectorFallas().analizar(lectura(rpm=800, throttle=0.0, presion=70.0))
    assert len(fallas) == 1 and "ralentí" in fallas[0]


@pytest.mark.parametrize("rpm, throttle", [(3000, 60.0), (900, 40.0)])
def test_map_alto_acelerando_no_es_falla(rpm, throttle):
    # Al pisar el acelerador la presión del colector sube con normalidad
    assert DetectorFallas().analizar(lectura(rpm=rpm, throttle=throttle, presion=90.0)) == []


def test_tps_al_100_puntual_no_es_falla():
    detector = DetectorFallas(lecturas_tps_100=3)
    assert detector.analizar(lectura(rpm=4000, throttle=100.0, presion=95.0)) == []
    assert detector.analizar(lectura(rpm=4500, throttle=100.0, presion=95.0)) == []


def test_tps_al_100_constante_es_falla():
    detector = DetectorFallas(lecturas_tps_100=3)
    for _ in range(2):
        detector.analizar(lectura(rpm=4000, throttle=100.0, presion=95.0))
    fallas = detector.analizar(lectura(rpm=4000, throttle=100.0, presion=95.0))
    assert any("100% constante" in f for f in fallas)


def test_soltar_acelerador_reinicia_el_contador():
    detector = DetectorFallas(lecturas_tps_100=3)
    detector.analizar(lectura(rpm=4000, throttle=100.0, presion=95.0))
    detector.analizar(lectura(rpm=4000, throttle=100.0, presion=95.0))
    detector.analizar(lectura(rpm=2000, throttle=20.0, presion=60.0))
    assert detector.analizar(lectura(rpm=4000, throttle=100.0, presion=95.0)) == []


def test_sin_rpm_no_se_evalua():
    valores = {"rpm": None, "throttle": 30.0, "presion": 20.0, "temp_refrigerante": None}
    assert DetectorFallas().analizar(valores) == []


def test_parser_valores_por_defecto():
    args = crear_parser().parse_args([])
    assert args.puerto is None and args.intervalo == 2.0 and not args.una_vez


def test_parser_con_opciones():
    args = crear_parser().parse_args(["--puerto", "COM3", "--intervalo", "0.5", "--una-vez"])
    assert args.puerto == "COM3" and args.intervalo == 0.5 and args.una_vez


def test_temperatura_normal_sin_aviso():
    assert DetectorFallas().analizar(lectura(temp=90.0)) == []


def test_temperatura_en_el_limite_sin_aviso():
    assert DetectorFallas().analizar(lectura(temp=105.0)) == []


def test_sobrecalentamiento_avisa():
    fallas = DetectorFallas().analizar(lectura(temp=110.0))
    assert fallas == ["AVISO TEMPERATURA: refrigerante a 110.0 °C"]


def test_sobrecalentamiento_avisa_aunque_falte_rpm():
    valores = {"rpm": None, "throttle": None, "presion": None, "temp_refrigerante": 112.0}
    fallas = DetectorFallas().analizar(valores)
    assert len(fallas) == 1 and fallas[0].startswith("AVISO TEMPERATURA")
