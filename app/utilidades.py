"""Funciones auxiliares compartidas por las vistas y las plantillas."""

import functools
from datetime import datetime

from flask import flash, redirect, session, url_for

from app.configuracion import SIMBOLO_MONEDA


class ErrorDeNegocio(Exception):
    """Error previsible causado por una regla de negocio.

    Se usa, por ejemplo, cuando no hay inventario suficiente para vender una
    pizza. Las vistas lo capturan y muestran el mensaje al usuario.
    """


def formato_moneda(valor) -> str:
    """Devuelve un numero como precio legible: 28000 -> '$ 28.000'."""
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        numero = 0.0
    # Se formatea con coma como separador de miles y luego se cambia por punto,
    # que es el separador que se usa en Colombia.
    entero = f"{numero:,.0f}".replace(",", ".")
    return f"{SIMBOLO_MONEDA} {entero}"


def formato_cantidad(valor) -> str:
    """Muestra cantidades sin decimales innecesarios: 2.0 -> '2', 0.25 -> '0.25'."""
    numero = float(valor or 0)
    if numero == int(numero):
        return str(int(numero))
    return f"{numero:.2f}".rstrip("0").rstrip(".")


def formato_fecha(texto: str) -> str:
    """Convierte '2026-09-06 18:30:00' en '06/09/2026 18:30'."""
    if not texto:
        return ""
    try:
        momento = datetime.strptime(str(texto)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(texto)
    return momento.strftime("%d/%m/%Y %H:%M")


def usuario_en_sesion():
    """Devuelve un diccionario con el usuario logueado, o None si no hay sesion."""
    if "usuario_id" not in session:
        return None
    return {
        "id": session["usuario_id"],
        "nombre": session.get("usuario_nombre", ""),
        "usuario": session.get("usuario_usuario", ""),
        "rol": session.get("usuario_rol", ""),
        "rol_legible": session.get("usuario_rol_legible", ""),
    }


def requiere_sesion(funcion):
    """Decorador: obliga a iniciar sesion antes de entrar a la vista."""

    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        if usuario_en_sesion() is None:
            flash("Inicia sesión para entrar al sistema.", "aviso")
            return redirect(url_for("autenticacion.login"))
        return funcion(*args, **kwargs)

    return envoltura


def requiere_rol(*roles_permitidos):
    """Decorador: solo deja pasar a los roles indicados.

    Ejemplo de uso:
        @requiere_rol("administrador", "cajero")
        def nuevo_pedido(): ...
    """

    def decorador(funcion):
        @functools.wraps(funcion)
        def envoltura(*args, **kwargs):
            usuario = usuario_en_sesion()
            if usuario is None:
                flash("Inicia sesión para entrar al sistema.", "aviso")
                return redirect(url_for("autenticacion.login"))
            if usuario["rol"] not in roles_permitidos:
                flash(
                    "Tu rol ({}) no tiene permiso para esa sección.".format(usuario["rol_legible"]),
                    "error",
                )
                return redirect(url_for("panel.inicio"))
            return funcion(*args, **kwargs)

        return envoltura

    return decorador
