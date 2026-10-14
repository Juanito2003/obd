from escaner_obd import crear_parser, formatear_dtc


def test_sin_codigos():
    assert formatear_dtc([]) == "✅ Sin códigos de avería"


def test_varios_codigos():
    texto = formatear_dtc([
        ("P0401", "Exhaust Gas Recirculation Flow Insufficient Detected"),
        ("P0300", "Random Misfire Detected"),
    ])
    assert texto.splitlines() == [
        "⚠️ 2 código(s) de avería:",
        "- P0401: Exhaust Gas Recirculation Flow Insufficient Detected",
        "- P0300: Random Misfire Detected",
    ]


def test_codigo_sin_descripcion():
    assert "- P1234: (sin descripción)" in formatear_dtc([("P1234", "")])


def test_parser_opcion_dtc():
    assert crear_parser().parse_args([]).dtc is False
    assert crear_parser().parse_args(["--dtc"]).dtc is True


def test_main_con_dtc_muestra_los_codigos_y_termina(monkeypatch, capsys):
    import escaner_obd

    cerrada = []

    class ConexionFalsa:
        def close(self):
            cerrada.append(True)

    monkeypatch.setattr(escaner_obd, "conectar_obd", lambda puerto: ConexionFalsa())
    monkeypatch.setattr(escaner_obd, "leer_dtc", lambda conexion: [("P0401", "EGR")])
    monkeypatch.setattr(escaner_obd, "leer_parametros",
                        lambda conexion: (_ for _ in ()).throw(AssertionError("no debe leer parámetros")))

    assert escaner_obd.main(["--dtc"]) == 0
    salida = capsys.readouterr().out
    assert "- P0401: EGR" in salida
    assert cerrada == [True]
