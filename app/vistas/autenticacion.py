"""Pantalla de acceso: inicio y cierre de sesion."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.servicios.autenticacion import listar_usuarios, validar_credenciales

bp = Blueprint("autenticacion", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Valida las credenciales y guarda el usuario en la sesion."""
    from app import obtener_bd

    conexion = obtener_bd()

    if request.method == "POST":
        nombre_usuario = request.form.get("usuario", "")
        clave = request.form.get("clave", "")
        usuario = validar_credenciales(conexion, nombre_usuario, clave)

        if usuario is None:
            flash("Usuario o contraseña incorrectos.", "error")
        else:
            session["usuario_id"] = usuario.id
            session["usuario_nombre"] = usuario.nombre
            session["usuario_usuario"] = usuario.usuario
            session["usuario_rol"] = usuario.rol
            session["usuario_rol_legible"] = usuario.rol_legible
            flash(f"Bienvenido, {usuario.nombre}.", "exito")
            return redirect(url_for("panel.inicio"))

    # Los usuarios de prueba se muestran en pantalla porque es un prototipo academico.
    return render_template("login.html", usuarios=listar_usuarios(conexion))


@bp.route("/logout")
def logout():
    """Cierra la sesion actual."""
    session.clear()
    flash("Sesión cerrada.", "aviso")
    return redirect(url_for("autenticacion.login"))
