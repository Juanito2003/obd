# Escáner OBD-II en Python

[![Tests](https://github.com/Juanito2003/obd/actions/workflows/tests.yml/badge.svg)](https://github.com/Juanito2003/obd/actions/workflows/tests.yml)

Lee en tiempo real los datos del coche a través de un adaptador **ELM327** (USB o Bluetooth) y avisa cuando las lecturas apuntan a un sensor **TPS** (posición del acelerador) o **MAP** (presión del colector) defectuoso.

```
✅ Conectado al adaptador OBD2 en /dev/ttyUSB0
Protocolo: ISO 15765-4 (CAN 11/500)

=== Parámetros en tiempo real ===
RPM: 812.0
THROTTLE: 14.1
PRESION: 33
TEMP_REFRIGERANTE: 88

✅ Todos los parámetros son normales
```

## Qué lee

| Parámetro | Comando OBD-II | Unidad |
|---|---|---|
| Revoluciones | `RPM` | rpm |
| Posición del acelerador | `THROTTLE_POS` | % |
| Presión del colector de admisión | `INTAKE_PRESSURE` | kPa |
| Temperatura del refrigerante | `COOLANT_TEMP` | °C |

## Qué detecta

| Falla | Condición |
|---|---|
| TPS con motor apagado | Acelerador por encima del 5 % con el motor parado |
| TPS al 100 % constante | Acelerador al 100 % durante 3 lecturas seguidas con el motor en marcha (un acelerón puntual no cuenta) |
| MAP con motor apagado | Presión por debajo de 95 kPa con el motor parado (debería estar cerca de la atmosférica, ~100 kPa) |
| MAP alto al ralentí | Presión por encima de 50 kPa al ralentí y sin pisar el acelerador |

Los umbrales están al principio de `escaner_obd.py` y se pueden ajustar. Están pensados para motores atmosféricos: en un turbo la presión del colector se comporta distinto. Los avisos son orientativos y no sustituyen a una diagnosis en el taller.

## Requisitos

- Python 3.9 o superior
- Un adaptador ELM327 conectado al puerto OBD-II del coche
- La librería [python-OBD](https://github.com/brendan-w/python-OBD)

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Detecta el adaptador automáticamente
python escaner_obd.py

# Indicando el puerto (Windows / Linux)
python escaner_obd.py --puerto COM3
python escaner_obd.py --puerto /dev/ttyUSB0

# Una lectura por segundo, o una sola lectura y salir
python escaner_obd.py --intervalo 1
python escaner_obd.py --una-vez

# Guardar cada lectura en un CSV (por ejemplo, para grabar un trayecto)
python escaner_obd.py --csv viaje.csv
```

Para pararlo, pulsa `Ctrl+C`.

### Grabar un trayecto en CSV

Con `--csv RUTA`, cada lectura se añade como una fila al archivo; si no existe, se crea con la cabecera:

```
fecha_hora,rpm,throttle,presion,temp_refrigerante,fallas
2026-10-15T08:30:02,812.0,14.1,33,88,
2026-10-15T08:30:04,2450.0,38.0,71,90,
```

La columna `fallas` junta los avisos de esa lectura separados por ` | `. Se abre en LibreOffice Calc o en Excel (*Datos → Desde texto/CSV*, separador coma).

## Tests

La lógica de detección está separada de la lectura del adaptador, así que se puede probar sin coche:

```bash
pip install pytest
pytest
```

Los tests se ejecutan automáticamente en cada push y pull request con GitHub Actions.
