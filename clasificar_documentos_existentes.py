"""Reclasifica por materia los archivos que ya están sueltos dentro de Documentos/."""
import sys
from pathlib import Path

import main


def clasificar_documentos_sueltos(carpeta_documentos: Path) -> None:
    archivos = [f for f in carpeta_documentos.iterdir() if f.is_file()]
    print(f"Encontrados {len(archivos)} archivos sueltos en {carpeta_documentos}")

    for i, archivo in enumerate(archivos, 1):
        subcarpeta = main.clasificar_documento(archivo, carpeta_documentos)
        carpeta_destino = carpeta_documentos / subcarpeta
        carpeta_destino.mkdir(parents=True, exist_ok=True)

        destino = main.destino_sin_colision(carpeta_destino, archivo.name)
        archivo.rename(destino)
        print(f"[{i}/{len(archivos)}] {archivo.name} -> {subcarpeta}/{destino.name}")


if __name__ == "__main__":
    carpeta_descargas = main.obtener_carpeta_descargas()
    carpeta_documentos = carpeta_descargas / main.CATEGORIA_DOCUMENTOS

    if not carpeta_documentos.is_dir():
        print(f"No existe la carpeta: {carpeta_documentos}")
        sys.exit(1)

    clasificar_documentos_sueltos(carpeta_documentos)
    print("Listo.")
