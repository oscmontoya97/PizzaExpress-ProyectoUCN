"""Modelo de un ingrediente del inventario."""

from dataclasses import dataclass


@dataclass
class Ingrediente:
    """Insumo que se consume al preparar una pizza."""

    id: int
    nombre: str
    categoria: str
    unidad: str              # kg, L, unidad...
    stock: float             # cantidad disponible ahora mismo
    stock_minimo: float      # umbral por debajo del cual se genera una alerta
    costo_unitario: float    # costo de compra por unidad, sirve para valorar el inventario

    @property
    def esta_agotado(self) -> bool:
        """True si ya no queda nada de este ingrediente."""
        return self.stock <= 0

    @property
    def esta_bajo(self) -> bool:
        """True si queda algo pero se alcanzo el stock minimo."""
        return 0 < self.stock <= self.stock_minimo

    @property
    def necesita_alerta(self) -> bool:
        """True si el ingrediente debe aparecer en el panel de alertas."""
        return self.stock <= self.stock_minimo

    @property
    def valor_en_inventario(self) -> float:
        """Cuanto dinero representa el stock actual de este ingrediente."""
        return self.stock * self.costo_unitario

    @classmethod
    def desde_fila(cls, fila) -> "Ingrediente":
        """Construye el objeto a partir de una fila sqlite3.Row."""
        return cls(
            id=fila["id"],
            nombre=fila["nombre"],
            categoria=fila["categoria"],
            unidad=fila["unidad"],
            stock=fila["stock"],
            stock_minimo=fila["stock_minimo"],
            costo_unitario=fila["costo_unitario"],
        )
