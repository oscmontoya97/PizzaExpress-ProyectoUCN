"""Punto de entrada de Pizza Express.

Ejecutar con:  python ejecutar.py
Luego abrir en el navegador:  http://127.0.0.1:5000
"""

from app import crear_app
from app.configuracion import LEMA, NOMBRE_APP

# La aplicacion se crea a nivel de modulo para poder usarla tambien con
# el comando "flask --app ejecutar run".
aplicacion = crear_app()


if __name__ == "__main__":
    print("=" * 60)
    print(f"  {NOMBRE_APP} - {LEMA}")
    print("  Servidor en http://127.0.0.1:5000  (Ctrl+C para detener)")
    print("=" * 60)
    aplicacion.run(host="127.0.0.1", port=5000, debug=True)
