"""Modelos del menu: la pizza y los ingredientes de su receta."""

from dataclasses import dataclass, field

from app.configuracion import TAMANOS


@dataclass
class IngredienteDeReceta:
    """Cantidad de un ingrediente que consume una pizza de tamano mediano."""

    ingrediente_id: int
    nombre: str
    unidad: str
    cantidad: float


@dataclass
class Pizza:
    """Pizza del menu, con su precio base y su receta."""

    id: int
    nombre: str
    descripcion: str
    precio_base: float                 # precio de la pizza mediana
    activa: bool = True
    receta: list = field(default_factory=list)   # lista de IngredienteDeReceta

    def precio_por_tamano(self, tamano: str) -> float:
        """Precio final segun el tamano elegido, redondeado a centenas."""
        factor = TAMANOS[tamano]["factor"]
        return round(self.precio_base * factor / 100) * 100

    @classmethod
    def desde_fila(cls, fila) -> "Pizza":
        """Construye el objeto a partir de una fila sqlite3.Row."""
        return cls(
            id=fila["id"],
            nombre=fila["nombre"],
            descripcion=fila["descripcion"],
            precio_base=fila["precio_base"],
            activa=bool(fila["activa"]),
        )
