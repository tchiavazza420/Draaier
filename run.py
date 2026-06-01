"""
run.py
------
Punto de entrada de la aplicación.

Crea la app con el factory y expone el objeto `app` para:
  - `flask run`  (Flask detecta automáticamente esta variable),
  - `python run.py`  (ejecución directa para desarrollo).
"""

from app import create_app

app = create_app()


if __name__ == "__main__":
    # host=127.0.0.1 para desarrollo local. El puerto 5000 es el default de Flask.
    app.run(host="127.0.0.1", port=5000, debug=True)
