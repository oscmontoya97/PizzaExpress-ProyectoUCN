"""Genera la version PDF de los documentos de Pizza Express.

Convierte cada archivo .md de esta carpeta en un PDF con portada, encabezado de
marca y las imagenes incrustadas, de modo que el PDF sea autocontenido.

Uso:
    python3 docs/generar_pdf.py

Requisitos (herramientas de documentacion, no de la aplicacion):
  * el modulo "markdown" de Python  ->  pip install markdown
  * Google Chrome instalado (se usa su modo headless para imprimir a PDF)
"""

import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile

import markdown

# Carpeta donde vive este script (docs/) y raiz del proyecto.
RUTA_DOCS = os.path.dirname(os.path.abspath(__file__))
RUTA_RAIZ = os.path.dirname(RUTA_DOCS)
RUTA_LOGO = os.path.join(RUTA_RAIZ, "assets", "logo.png")

# Documentos a convertir: nombre de archivo -> titulo de la portada.
DOCUMENTOS = {
    "plan-de-pruebas.md": "Plan de pruebas del sistema",
    "documentacion-tecnica.md": "Documentación técnica",
    "manual-de-usuario.md": "Manual de usuario",
    "gestion-del-proyecto.md": "Estrategia de gestión del proyecto",
}

# Rutas donde suele estar Chrome segun el sistema operativo.
RUTAS_CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
]

# Hoja de estilos del PDF. Usa los colores de la marca Pizza Express.
ESTILOS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }

body {
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.5;
    color: #2b2b2b;
}

/* --- Portada --- */
.portada {
    text-align: center;
    padding-top: 55mm;
    page-break-after: always;
}
/* El logo es blanco con transparencia, por eso va sobre un circulo rojo:
   sobre el papel blanco no se veria. */
.portada img {
    width: 110px;
    height: 110px;
    background: #8c1414;
    border-radius: 50%;
    padding: 16px;
}
.portada .marca { font-size: 30pt; font-weight: bold; color: #8c1414; margin: 14px 0 2px; }
.portada .lema { font-size: 11pt; color: #6b6b6b; margin: 0 0 30mm; }
.portada .titulo {
    font-size: 20pt;
    font-weight: bold;
    border-top: 3px solid #8c1414;
    border-bottom: 3px solid #8c1414;
    padding: 12px 0;
    margin: 0 18mm;
}
.portada .pie { margin-top: 24mm; font-size: 10pt; color: #6b6b6b; }

/* --- Encabezado de marca repetido al inicio del contenido --- */
.cabecera {
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 2px solid #8c1414;
    padding-bottom: 8px;
    margin-bottom: 18px;
}
.cabecera img { width: 30px; height: 30px; background: #8c1414; border-radius: 50%; padding: 4px; }
.cabecera strong { color: #8c1414; font-size: 13pt; }
.cabecera span { color: #6b6b6b; font-size: 9pt; }

/* --- Contenido --- */
h1 { font-size: 18pt; color: #8c1414; border-bottom: 2px solid #e4d9c7; padding-bottom: 6px; }
h2 { font-size: 14pt; color: #8c1414; margin-top: 22px; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin-top: 16px; page-break-after: avoid; }
h4 { font-size: 10.5pt; margin-top: 12px; page-break-after: avoid; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 16px;
    font-size: 8.8pt;
    page-break-inside: avoid;
}
th, td { border: 1px solid #d9cdb8; padding: 5px 7px; text-align: left; vertical-align: top; }
th { background: #f6efe4; color: #6d0f0f; }
tr:nth-child(even) td { background: #fdfaf5; }

code {
    background: #f6efe4;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: "SF Mono", Consolas, monospace;
    font-size: 8.5pt;
}
pre {
    background: #fbf7f1;
    border-left: 3px solid #8c1414;
    padding: 10px 12px;
    overflow-x: auto;
    font-size: 8pt;
    line-height: 1.35;
    page-break-inside: avoid;
}
pre code { background: none; padding: 0; }

blockquote {
    border-left: 3px solid #b35c00;
    background: #fdf3e3;
    margin: 12px 0;
    padding: 8px 12px;
    color: #6b5636;
}

img {
    max-width: 100%;
    max-height: 200mm;          /* que ninguna captura desborde la pagina */
    border: 1px solid #e4d9c7;
    border-radius: 4px;
    page-break-inside: avoid;
}
a { color: #8c1414; }
hr { border: none; border-top: 1px solid #e4d9c7; margin: 20px 0; }
"""

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{titulo} - Pizza Express</title>
<style>{estilos}</style>
</head>
<body>

<div class="portada">
    <img src="data:image/png;base64,{logo}" alt="Logo de Pizza Express">
    <p class="marca">Pizza Express</p>
    <p class="lema">Sistema de Gestión de Pedidos e Inventario</p>
    <div class="titulo">{titulo}</div>
    <p class="pie">
        Proyecto de Ingeniería de Software<br>
        Católica del Norte Fundación Universitaria
    </p>
</div>

<div class="cabecera">
    <img src="data:image/png;base64,{logo}" alt="Logo de Pizza Express">
    <div>
        <strong>Pizza Express</strong><br>
        <span>Sistema de Gestión de Pedidos e Inventario</span>
    </div>
</div>

{contenido}

</body>
</html>
"""


def buscar_chrome():
    """Devuelve la ruta al ejecutable de Chrome, o None si no se encuentra."""
    for ruta in RUTAS_CHROME:
        if os.path.exists(ruta):
            return ruta
    # Ultimo intento: buscarlo en el PATH del sistema.
    for nombre in ("google-chrome", "chromium", "chromium-browser"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


def leer_base64(ruta):
    """Lee un archivo y lo devuelve codificado en base64."""
    with open(ruta, "rb") as archivo:
        return base64.b64encode(archivo.read()).decode("ascii")


def incrustar_imagenes(html):
    """Sustituye las rutas de imagen por los datos del archivo en base64.

    Asi el PDF no depende de la carpeta imagenes/ y se puede enviar suelto.
    """
    def reemplazo(coincidencia):
        ruta_relativa = coincidencia.group(1)
        ruta = os.path.join(RUTA_DOCS, ruta_relativa)
        if not os.path.exists(ruta):
            print(f"    aviso: no se encontro la imagen {ruta_relativa}")
            return coincidencia.group(0)
        return f'src="data:image/png;base64,{leer_base64(ruta)}"'

    return re.sub(r'src="([^"]+\.png)"', reemplazo, html)


def quitar_enlaces_internos(html):
    """Convierte los enlaces a otros .md en texto plano.

    En un PDF suelto esos enlaces no llevarian a ninguna parte.
    """
    return re.sub(r'<a href="[^"]*\.md">([^<]*)</a>', r"\1", html)


def generar(nombre_archivo, titulo, chrome, logo):
    """Convierte un documento Markdown en PDF."""
    ruta_md = os.path.join(RUTA_DOCS, nombre_archivo)
    ruta_pdf = os.path.join(RUTA_DOCS, nombre_archivo.replace(".md", ".pdf"))

    with open(ruta_md, encoding="utf-8") as archivo:
        texto = archivo.read()

    # El titulo ya lo pone la portada, asi que se quita el primer encabezado.
    texto = re.sub(r"^# .*\n", "", texto, count=1)

    contenido = markdown.markdown(texto, extensions=["tables", "fenced_code", "sane_lists"])
    contenido = incrustar_imagenes(contenido)
    contenido = quitar_enlaces_internos(contenido)

    html = PLANTILLA.format(titulo=titulo, estilos=ESTILOS, logo=logo, contenido=contenido)

    # Chrome necesita un archivo en disco para imprimirlo.
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(html)
        ruta_html = tmp.name

    try:
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={ruta_pdf}", f"file://{ruta_html}"],
            check=True, capture_output=True, timeout=120,
        )
    finally:
        os.unlink(ruta_html)

    tamano = os.path.getsize(ruta_pdf) / 1024
    print(f"  {os.path.basename(ruta_pdf):<32} {tamano:>8.0f} KB")


def main():
    chrome = buscar_chrome()
    if chrome is None:
        print("Error: no se encontró Google Chrome, necesario para generar los PDF.")
        return 1

    logo = leer_base64(RUTA_LOGO)

    print("Generando los PDF de la documentación de Pizza Express...")
    for nombre, titulo in DOCUMENTOS.items():
        if not os.path.exists(os.path.join(RUTA_DOCS, nombre)):
            print(f"  aviso: falta {nombre}, se omite")
            continue
        generar(nombre, titulo, chrome, logo)

    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
