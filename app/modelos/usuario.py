"""Modelo del usuario que opera el sistema."""

from dataclasses import dataclass

from app.configuracion import ROLES


@dataclass
class Usuario:
    """Empleado de la pizzeria con un rol asignado."""

    id: int
    nombre: str
    usuario: str
    rol: str        # administrador, cajero o pizzero

    @property
    def rol_legible(self) -> str:
        """Nombre del rol tal como se muestra en pantalla."""
        return ROLES.get(self.rol, self.rol)

    @classmethod
    def desde_fila(cls, fila) -> "Usuario":
        """Construye el objeto a partir de una fila sqlite3.Row."""
        return cls(
            id=fila["id"],
            nombre=fila["nombre"],
            usuario=fila["usuario"],
            rol=fila["rol"],
        )
