"""Configuracion general de la aplicacion Pizza Express.

Aqui viven las constantes que se usan en toda la aplicacion (nombre comercial,
rutas de archivos, tamanos de pizza, estados de los pedidos...). Tenerlas en un
solo modulo evita repetir "numeros magicos" por el codigo.
"""

from pathlib import Path

# --- Marca comercial (requisito: debe aparecer en todas las pantallas) ---
NOMBRE_APP = "Pizza Express"
LEMA = "Sistema de Gestión de Pedidos e Inventario"

# --- Rutas del proyecto ---
RUTA_RAIZ = Path(__file__).resolve().parent.parent
RUTA_ASSETS = RUTA_RAIZ / "assets"          # logo.png y estilos.css
RUTA_DATOS = RUTA_RAIZ / "datos"            # base de datos SQLite
RUTA_BD = RUTA_DATOS / "pizzaexpress.db"
NOMBRE_LOGO = "logo.png"                    # extraido de la presentacion del proyecto

# Clave usada por Flask para firmar la cookie de sesion.
# En un proyecto real vendria de una variable de entorno; para el prototipo
# academico se deja fija para que la aplicacion funcione sin configuracion extra.
CLAVE_SECRETA = "pizza-express-proyecto-ing-software"

# --- Reglas de negocio ---
# Cada tamano multiplica a la vez el precio de venta y las cantidades de la
# receta que se descuentan del inventario.
TAMANOS = {
    "personal": {"etiqueta": "Personal", "factor": 0.6},
    "mediana": {"etiqueta": "Mediana", "factor": 1.0},
    "familiar": {"etiqueta": "Familiar", "factor": 1.6},
}
TAMANO_POR_DEFECTO = "mediana"

# Modalidades de pedido exigidas por los requerimientos (mesa, llevar, domicilio).
MODALIDADES = {
    "mesa": {"etiqueta": "En mesa", "etiqueta_referencia": "Número de mesa", "referencia_obligatoria": True},
    "llevar": {"etiqueta": "Para llevar", "etiqueta_referencia": "Teléfono de contacto", "referencia_obligatoria": False},
    "domicilio": {"etiqueta": "A domicilio", "etiqueta_referencia": "Dirección de entrega", "referencia_obligatoria": True},
}

# Ciclo de vida del pedido. La clave es el estado actual y el valor la lista de
# estados a los que se puede pasar desde el.
ESTADOS = {
    "pendiente": {"etiqueta": "Pendiente", "color": "gris"},
    "en_preparacion": {"etiqueta": "En preparación", "color": "azul"},
    "lista": {"etiqueta": "Lista", "color": "morado"},
    "entregado": {"etiqueta": "Entregado", "color": "verde"},
    "cancelado": {"etiqueta": "Cancelado", "color": "rojo"},
}
TRANSICIONES_PERMITIDAS = {
    "pendiente": ["en_preparacion", "cancelado"],
    "en_preparacion": ["lista", "cancelado"],
    "lista": ["entregado", "cancelado"],
    "entregado": [],
    "cancelado": [],
}

# --- Roles de usuario (stakeholders del proyecto) ---
ROLES = {
    "administrador": "Administrador / dueño",
    "cajero": "Cajero / mesero",
    "pizzero": "Pizzero / cocina",
}

# Moneda usada en la interfaz (el proyecto es colombiano).
SIMBOLO_MONEDA = "$"
