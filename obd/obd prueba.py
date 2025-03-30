import obd
import time

# Configuración de la conexión OBD2
PUERTO_COM = "COM3"  # Ajusta al puerto correcto
UMBRAL_PRESION_APAGADO = 95  # kPa (valor normal con motor apagado: ~100 kPa)
UMBRAL_TPS_APAGADO = 5       # % (máximo permitido con motor apagado)

def conectar_obd():
    try:
        connection = obd.OBD(PUERTO_COM)
        if not connection.is_connected():
            print(f"Error: No se pudo conectar al adaptador en {PUERTO_COM}")
            return None
        print(f"✅ Conectado al adaptador OBD2 en {PUERTO_COM}")
        print(f"Protocolo: {connection.protocol_name()}")
        return connection
    except Exception as e:
        print(f"Error de conexión: {str(e)}")
        return None

def leer_parametros(connection):
    parametros = {
        "rpm": connection.query(obd.commands.RPM),
        "throttle": connection.query(obd.commands.THROTTLE_POS),
        "presion": connection.query(obd.commands.INTAKE_PRESSURE),
        "temp_refrigerante": connection.query(obd.commands.COOLANT_TEMP)
    }
    
    # Convertir a valores numéricos
    valores = {}
    for key, cmd in parametros.items():
        if not cmd.is_null():
            valores[key] = cmd.value.magnitude
        else:
            valores[key] = None
            
    return valores

def detectar_fallas(valores):
    fallas = []
    
    # Verificar si el motor está apagado (RPM = 0)
    motor_apagado = valores["rpm"] == 0 if valores["rpm"] is not None else False
    
    # Detección de falla en TPS
    if valores["throttle"] is not None:
        if motor_apagado and valores["throttle"] > UMBRAL_TPS_APAGADO:
            fallas.append(f"FALLA TPS: Acelerador al {valores['throttle']}% con motor apagado")
        elif not motor_apagado and valores["throttle"] == 100.0:
            fallas.append("FALLA TPS: Acelerador al 100% constante")
            
    # Detección de falla en MAP
    if valores["presion"] is not None:
        if motor_apagado and valores["presion"] < UMBRAL_PRESION_APAGADO:
            fallas.append(f"FALLA MAP: Presión anormal ({valores['presion']} kPa) con motor apagado")
        elif not motor_apagado and valores["presion"] > 50:  # kPa máximo esperado en ralentí
            fallas.append(f"FALLA MAP: Presión alta ({valores['presion']} kPa) con motor encendido")
    
    return fallas

def main():
    conexion = conectar_obd()
    if not conexion:
        return

    try:
        while True:
            valores = leer_parametros(conexion)
            fallas = detectar_fallas(valores)
            
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
                
            print("\n" + "-"*50)
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nMonitoreo detenido por el usuario.")
    except Exception as e:
        print(f"Error general: {str(e)}")
    finally:
        if conexion:
            conexion.close()
            print("\nConexión cerrada.")

if __name__ == "__main__":
    main()