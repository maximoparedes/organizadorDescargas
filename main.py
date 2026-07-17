"""Organizador automático de archivos para la carpeta de Descargas."""
import json
import os
import shutil
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"
CATEGORIA_OTROS = "Otros"


def cargar_reglas(config_path: Path) -> dict[str, list[str]]:
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


def organizar_carpeta(carpeta: Path, reglas: dict[str, list[str]]) -> None:
    mapa_extensiones = construir_mapa_extensiones(reglas)

    archivos = [f for f in carpeta.iterdir() if f.is_file()]

    for archivo in archivos:
        categoria = categoria_para_archivo(archivo, mapa_extensiones)
        carpeta_destino = carpeta / categoria
        carpeta_destino.mkdir(exist_ok=True)

        destino = destino_sin_colision(carpeta_destino, archivo.name)
        shutil.move(str(archivo), str(destino))
        print(f"Movido: {archivo.name} -> {categoria}/{destino.name}")


def main() -> None:
    carpeta_descargas = obtener_carpeta_descargas()

    if not carpeta_descargas.is_dir():
        print(f"No se encontró la carpeta de Descargas: {carpeta_descargas}")
        return

    reglas = cargar_reglas(CONFIG_PATH)
    print(f"Organizando: {carpeta_descargas}")
    organizar_carpeta(carpeta_descargas, reglas)
    print("Listo.")


if __name__ == "__main__":
    main()
