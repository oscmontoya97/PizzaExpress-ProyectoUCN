"""Autenticacion de los empleados de la pizzeria."""

from app.basedatos import cifrar_clave
from app.modelos import Usuario


def validar_credenciales(conexion, usuario: str, clave: str):
    """Devuelve el Usuario si el nombre y la clave son correctos, si no None."""
    fila = conexion.execute(
        "SELECT * FROM usuario WHERE usuario = ? AND clave_hash = ?",
        (usuario.strip().lower(), cifrar_clave(clave)),
    ).fetchone()
    return Usuario.desde_fila(fila) if fila else None


def listar_usuarios(conexion) -> list:
    """Todos los empleados registrados (se muestran en la pantalla de acceso)."""
    return [Usuario.desde_fila(fila)
            for fila in conexion.execute("SELECT * FROM usuario ORDER BY rol, nombre")]
