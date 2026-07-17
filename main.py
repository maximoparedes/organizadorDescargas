"""Organizador automático de archivos para la carpeta de Descargas."""
import json
import logging
import os
import shutil
import time
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_PATH = Path(__file__).parent / "organizador.log"
CATEGORIA_OTROS = "Otros"
CATEGORIA_DOCUMENTOS = "Documentos"
CATEGORIA_SIN_CLASIFICAR = "Sin_Clasificar"
MODELO_CLAUDE = "claude-haiku-4-5"
MAX_PAGINAS_PDF = 3
MAX_PARRAFOS_DOCX = 50
MAX_FILAS_EXCEL = 30
MAX_HOJAS_EXCEL = 3
MAX_CARACTERES_TEXTO = 3000
MAX_LARGO_NOMBRE_CATEGORIA = 40
CARACTERES_INVALIDOS_CARPETA = '<>:"/\\|?*'
EXTENSIONES_DESCARGA_EN_CURSO = {"crdownload", "tmp", "part", "partial", "download"}
SEGUNDOS_MINIMOS_DESDE_MODIFICACION = 3


def configurar_logging() -> None:
    if logging.getLogger().handlers:
        return  # ya configurado (evita duplicar handlers si se llama más de una vez)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def cargar_reglas(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_carpeta_descargas() -> Path:
    return Path(os.path.expanduser("~")) / "Downloads"


def construir_mapa_extensiones(reglas: dict[str, list[str]]) -> dict[str, str]:
    mapa = {}
    for categoria, extensiones in reglas.items():
        for ext in extensiones:
            mapa[ext.lower()] = categoria
    return mapa


def categoria_para_archivo(archivo: Path, mapa_extensiones: dict[str, str]) -> str:
    ext = archivo.suffix.lower().lstrip(".")
    return mapa_extensiones.get(ext, CATEGORIA_OTROS)


def destino_sin_colision(carpeta_destino: Path, nombre_archivo: str) -> Path:
    destino = carpeta_destino / nombre_archivo
    if not destino.exists():
        return destino

    base = Path(nombre_archivo).stem
    ext = Path(nombre_archivo).suffix
    contador = 1
    while True:
        candidato = carpeta_destino / f"{base} ({contador}){ext}"
        if not candidato.exists():
            return candidato
        contador += 1


def extraer_texto_pdf(archivo: Path) -> str | None:
    try:
        from pypdf import PdfReader

        lector = PdfReader(str(archivo))
        paginas = lector.pages[:MAX_PAGINAS_PDF]
        texto = "\n".join(pagina.extract_text() or "" for pagina in paginas)
        return texto.strip() or None
    except Exception:
        return None


def extraer_texto_docx(archivo: Path) -> str | None:
    try:
        from docx import Document

        documento = Document(str(archivo))
        parrafos = [
            p.text for p in documento.paragraphs[:MAX_PARRAFOS_DOCX] if p.text.strip()
        ]
        return "\n".join(parrafos).strip() or None
    except Exception:
        return None


def extraer_texto_xlsx(archivo: Path) -> str | None:
    libro = None
    try:
        from openpyxl import load_workbook

        libro = load_workbook(str(archivo), read_only=True, data_only=True)
        partes = []
        for hoja in libro.worksheets[:MAX_HOJAS_EXCEL]:
            partes.append(f"[Hoja: {hoja.title}]")
            for fila in hoja.iter_rows(max_row=MAX_FILAS_EXCEL, values_only=True):
                valores = [str(v) for v in fila if v is not None and str(v).strip()]
                if valores:
                    partes.append(" | ".join(valores))
        return "\n".join(partes).strip() or None
    except Exception:
        return None
    finally:
        if libro is not None:
            libro.close()


def extraer_texto_xls(archivo: Path) -> str | None:
    try:
        import xlrd

        libro = xlrd.open_workbook(str(archivo))
        partes = []
        for hoja in libro.sheets()[:MAX_HOJAS_EXCEL]:
            partes.append(f"[Hoja: {hoja.name}]")
            for fila_idx in range(min(hoja.nrows, MAX_FILAS_EXCEL)):
                valores = [
                    str(v) for v in hoja.row_values(fila_idx) if str(v).strip()
                ]
                if valores:
                    partes.append(" | ".join(valores))
        return "\n".join(partes).strip() or None
    except Exception:
        return None


def extraer_texto(archivo: Path) -> str | None:
    ext = archivo.suffix.lower().lstrip(".")
    if ext == "pdf":
        return extraer_texto_pdf(archivo)
    if ext == "docx":
        return extraer_texto_docx(archivo)
    if ext == "xlsx":
        return extraer_texto_xlsx(archivo)
    if ext == "xls":
        return extraer_texto_xls(archivo)
    return None


def listar_categorias_existentes(carpeta_documentos: Path) -> list[str]:
    if not carpeta_documentos.is_dir():
        return []
    return sorted(
        p.name
        for p in carpeta_documentos.iterdir()
        if p.is_dir() and p.name != CATEGORIA_SIN_CLASIFICAR
    )


def sanitizar_nombre_categoria(nombre: str) -> str:
    limpio = nombre.strip()
    for caracter in CARACTERES_INVALIDOS_CARPETA:
        limpio = limpio.replace(caracter, "_")
    limpio = limpio.strip(" .")[:MAX_LARGO_NOMBRE_CATEGORIA].strip()
    return limpio


def clasificar_categoria(
    nombre_archivo: str, texto: str | None, categorias_existentes: list[str]
) -> str | None:
    try:
        import anthropic

        cliente = anthropic.Anthropic()
        categorias_texto = ", ".join(categorias_existentes) if categorias_existentes else "(ninguna todavía)"

        if texto:
            seccion_contenido = f"Contenido (primeras páginas):\n{texto[:MAX_CARACTERES_TEXTO]}"
        else:
            seccion_contenido = (
                "No se pudo extraer el contenido de este archivo (por ejemplo, es un "
                ".pptx u otro formato no soportado para lectura, o la extracción "
                "falló). Guiate ÚNICAMENTE por el nombre del archivo para inferir el "
                "tema — muchas veces el nombre ya lo indica (ej: 'Clase 6 - Algebra.pptx' "
                "es de la materia Algebra)."
            )

        prompt = (
            f"Nombre del archivo: {nombre_archivo}\n\n"
            f"{seccion_contenido}\n\n"
            f"Carpetas que ya existen dentro de Documentos: {categorias_texto}\n\n"
            "Estás organizando la carpeta Documentos de un usuario que mezcla archivos "
            "académicos (de la facultad) y personales (trámites, certificados, CV, etc). "
            "Elegí la carpeta que mejor represente el TEMA o TIPO de este documento. "
            "Puede ser una materia universitaria (ej: 'Calculo I', 'Bases de Datos'), "
            "un tipo de documento personal (ej: 'CV', 'CUIL', 'Certificados', "
            "'Constancias'), o cualquier otra categoría clara y específica que "
            "corresponda.\n\n"
            "Si el documento corresponde EXACTAMENTE al mismo tema o tipo de "
            "documento que una de las carpetas que ya existen, respondé ese mismo "
            "nombre (para no crear una carpeta duplicada). No reutilices una carpeta "
            "solo porque el tema es parecido: una constancia de CUIL y una constancia "
            "de alumno, por ejemplo, son tipos de documento distintos aunque ambas "
            "sean 'constancias' — no las mezcles en la misma carpeta. Si no hay una "
            "carpeta que coincida exactamente pero podés identificar "
            "claramente de qué se trata (por contenido o por el nombre del archivo), "
            "inventá un nombre corto y específico (2 a 4 palabras, en español, sin "
            "caracteres especiales, apto para nombre de carpeta, máximo "
            f"{MAX_LARGO_NOMBRE_CATEGORIA} caracteres). Si es genérico o ambiguo pero "
            "reconocible respondé exactamente "
            f"'{CATEGORIA_OTROS}'. Si ni el contenido ni el nombre del archivo dan "
            "ninguna pista de qué se trata, respondé exactamente "
            f"'{CATEGORIA_SIN_CLASIFICAR}'.\n\n"
            "Respondé ÚNICAMENTE con el nombre de la carpeta: una etiqueta corta, "
            "nunca una oración ni una explicación."
        )
        respuesta = cliente.messages.create(
            model=MODELO_CLAUDE,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        texto_respuesta = next(
            (b.text for b in respuesta.content if b.type == "text"), ""
        ).strip()
    except Exception as e:
        logging.warning(f"Fallo la clasificación por IA de '{nombre_archivo}': {e}")
        return None

    for categoria in categorias_existentes:
        if categoria.lower() == texto_respuesta.lower():
            return categoria

    return sanitizar_nombre_categoria(texto_respuesta) or None


def clasificar_documento(archivo: Path, carpeta_documentos: Path) -> str:
    texto = extraer_texto(archivo)
    categorias_existentes = listar_categorias_existentes(carpeta_documentos)
    categoria = clasificar_categoria(archivo.name, texto, categorias_existentes)
    return categoria or CATEGORIA_SIN_CLASIFICAR


def archivo_listo_para_mover(archivo: Path) -> bool:
    ext = archivo.suffix.lower().lstrip(".")
    if ext in EXTENSIONES_DESCARGA_EN_CURSO:
        return False

    try:
        segundos_desde_modificacion = time.time() - archivo.stat().st_mtime
    except FileNotFoundError:
        return False

    return segundos_desde_modificacion >= SEGUNDOS_MINIMOS_DESDE_MODIFICACION


def organizar_carpeta(carpeta: Path, reglas: dict) -> None:
    mapa_extensiones = construir_mapa_extensiones(reglas)

    archivos = [
        f for f in carpeta.iterdir() if f.is_file() and archivo_listo_para_mover(f)
    ]

    for archivo in archivos:
        categoria = categoria_para_archivo(archivo, mapa_extensiones)

        if categoria == CATEGORIA_DOCUMENTOS:
            carpeta_documentos = carpeta / CATEGORIA_DOCUMENTOS
            subcarpeta = clasificar_documento(archivo, carpeta_documentos)
            carpeta_destino = carpeta_documentos / subcarpeta
        else:
            carpeta_destino = carpeta / categoria

        carpeta_destino.mkdir(parents=True, exist_ok=True)
        destino = destino_sin_colision(carpeta_destino, archivo.name)
        shutil.move(str(archivo), str(destino))
        logging.info(f"Movido: {archivo.name} -> {carpeta_destino.relative_to(carpeta)}/{destino.name}")


def main() -> None:
    configurar_logging()
    carpeta_descargas = obtener_carpeta_descargas()

    if not carpeta_descargas.is_dir():
        logging.error(f"No se encontró la carpeta de Descargas: {carpeta_descargas}")
        return

    reglas = cargar_reglas(CONFIG_PATH)
    logging.info(f"Organizando: {carpeta_descargas}")
    organizar_carpeta(carpeta_descargas, reglas)
    logging.info("Listo.")


if __name__ == "__main__":
    main()
