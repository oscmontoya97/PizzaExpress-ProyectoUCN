"""Fabrica de la aplicacion Flask de Pizza Express.

Aqui se crea la aplicacion, se abre y cierra la conexion a la base de datos en
cada peticion y se registran los blueprints (un modulo de vistas por seccion).
"""

import sqlite3

from flask import Flask, g

from app.basedatos import inicializar_base_de_datos, obtener_conexion
from app.configuracion import (
    CLAVE_SECRETA,
    ESTADOS,
    LEMA,
    MODALIDADES,
    NOMBRE_APP,
    NOMBRE_LOGO,
    RUTA_ASSETS,
    TAMANOS,
)
from app.utilidades import formato_cantidad, formato_fecha, formato_moneda, usuario_en_sesion


def obtener_bd() -> sqlite3.Connection:
    """Conexion a la base de datos reutilizada durante toda la peticion."""
    if "bd" not in g:
        g.bd = obtener_conexion()
    return g.bd


def crear_app() -> Flask:
    """Construye y configura la aplicacion web."""
    aplicacion = Flask(
        __name__,
        template_folder="plantillas",
        # La carpeta assets del proyecto es la carpeta estatica de Flask, asi el
        # logo extraido de la presentacion se sirve en /assets/logo.png.
        static_folder=str(RUTA_ASSETS),
        static_url_path="/assets",
    )
    aplicacion.config["SECRET_KEY"] = CLAVE_SECRETA

    # La base de datos se crea (y se puebla) la primera vez que se ejecuta.
    inicializar_base_de_datos()

    @aplicacion.teardown_appcontext
    def cerrar_bd(excepcion):
        """Cierra la conexion cuando termina la peticion."""
        conexion = g.pop("bd", None)
        if conexion is not None:
            conexion.close()

    # --- Datos disponibles en todas las plantillas ---
    # Gracias a esto el nombre y el logo de Pizza Express estan al alcance de
    # cualquier pantalla sin tener que pasarlos vista por vista.
    @aplicacion.context_processor
    def variables_globales():
        from app.servicios.inventario import contar_alertas

        try:
            total_alertas = contar_alertas(obtener_bd())
        except sqlite3.Error:
            total_alertas = 0

        return {
            "NOMBRE_APP": NOMBRE_APP,
            "LEMA": LEMA,
            "NOMBRE_LOGO": NOMBRE_LOGO,
            "ESTADOS": ESTADOS,
            "MODALIDADES": MODALIDADES,
            "TAMANOS": TAMANOS,
            "usuario_actual": usuario_en_sesion(),
            "total_alertas": total_alertas,
        }

    # --- Filtros de plantilla para dar formato a precios, cantidades y fechas ---
    aplicacion.jinja_env.filters["moneda"] = formato_moneda
    aplicacion.jinja_env.filters["cantidad"] = formato_cantidad
    aplicacion.jinja_env.filters["fecha"] = formato_fecha

    # --- Registro de las secciones de la aplicacion ---
    from app.vistas import autenticacion, cocina, inventario, menu, panel, pedidos, reportes

    aplicacion.register_blueprint(autenticacion.bp)
    aplicacion.register_blueprint(panel.bp)
    aplicacion.register_blueprint(pedidos.bp)
    aplicacion.register_blueprint(cocina.bp)
    aplicacion.register_blueprint(inventario.bp)
    aplicacion.register_blueprint(menu.bp)
    aplicacion.register_blueprint(reportes.bp)

    return aplicacion
