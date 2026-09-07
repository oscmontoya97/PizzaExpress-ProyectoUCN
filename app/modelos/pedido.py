"""Modelos del pedido y de sus lineas."""

from dataclasses import dataclass, field

from app.configuracion import ESTADOS, MODALIDADES, TAMANOS, TRANSICIONES_PERMITIDAS


@dataclass
class LineaDePedido:
    """Una linea del pedido: tantas pizzas de un tipo y un tamano."""

    id: int
    pizza_id: int
    pizza_nombre: str
    tamano: str
    cantidad: int
    precio_unitario: float      # precio congelado en el momento de la venta

    @property
    def tamano_legible(self) -> str:
        return TAMANOS[self.tamano]["etiqueta"]

    @property
    def subtotal(self) -> float:
        return self.cantidad * self.precio_unitario

    @classmethod
    def desde_fila(cls, fila) -> "LineaDePedido":
        return cls(
            id=fila["id"],
            pizza_id=fila["pizza_id"],
            pizza_nombre=fila["pizza_nombre"],
            tamano=fila["tamano"],
            cantidad=fila["cantidad"],
            precio_unitario=fila["precio_unitario"],
        )


@dataclass
class Pedido:
    """Pedido completo: cabecera mas sus lineas."""

    id: int
    codigo: str                 # PED-0001, PED-0002...
    modalidad: str              # mesa, llevar o domicilio
    cliente: str
    referencia: str             # numero de mesa, telefono o direccion
    estado: str
    total: float
    notas: str
    usuario_nombre: str         # quien tomo el pedido
    creado_en: str
    lineas: list = field(default_factory=list)

    @property
    def modalidad_legible(self) -> str:
        return MODALIDADES[self.modalidad]["etiqueta"]

    @property
    def estado_legible(self) -> str:
        return ESTADOS[self.estado]["etiqueta"]

    @property
    def color_estado(self) -> str:
        """Nombre de la clase CSS que pinta la etiqueta de estado."""
        return ESTADOS[self.estado]["color"]

    @property
    def siguientes_estados(self) -> list:
        """Estados a los que se puede mover el pedido desde el actual."""
        return TRANSICIONES_PERMITIDAS[self.estado]

    @property
    def total_pizzas(self) -> int:
        return sum(linea.cantidad for linea in self.lineas)

    @classmethod
    def desde_fila(cls, fila) -> "Pedido":
        return cls(
            id=fila["id"],
            codigo=fila["codigo"],
            modalidad=fila["modalidad"],
            cliente=fila["cliente"],
            referencia=fila["referencia"] or "",
            estado=fila["estado"],
            total=fila["total"],
            notas=fila["notas"] or "",
            usuario_nombre=fila["usuario_nombre"] if "usuario_nombre" in fila.keys() else "",
            creado_en=fila["creado_en"],
        )
