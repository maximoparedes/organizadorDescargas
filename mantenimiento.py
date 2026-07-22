"""
mantenimiento.py
=================
Limpieza y mantenimiento de la PC: temporales, duplicados y programas
instalados. Los módulos "a demanda" del organizador — no se disparan solos,
se corren cuando vos querés.

(El módulo "organizar" por tipo de archivo NO está acá: eso lo hace
main.py / el vigilante en tiempo real automáticamente.)

SEGURIDAD:
  - Por defecto corre en modo DRY RUN (simulación): no borra ni mueve nada,
    solo te muestra qué haría.
  - Para que actúe de verdad, corré con --ejecutar
  - Los duplicados nunca se borran automáticamente: se mueven a
    Desktop/revision_duplicados para que vos decidas.

USO:
  python mantenimiento.py                              -> simulación de todo
  python mantenimiento.py --ejecutar                   -> ejecuta todo de verdad
  python mantenimiento.py --modulos temporales         -> solo un módulo (simulación)
  python mantenimiento.py --modulos temporales duplicados --ejecutar
"""
import argparse
import logging

import main

CARPETAS_DUPLICADOS = [
    main.Path.home() / "Downloads",
    main.Path.home() / "Documents",
    main.Path.home() / "Desktop",
]


def ejecutar_mantenimiento() -> None:
    parser = argparse.ArgumentParser(description="Mantenimiento de PC")
    parser.add_argument(
        "--modulos",
        nargs="+",
        choices=["temporales", "duplicados", "programas"],
        default=["temporales", "duplicados", "programas"],
        help="Qué módulos correr (por defecto: todos)",
    )
    parser.add_argument(
        "--ejecutar",
        action="store_true",
        help="Ejecuta los cambios de verdad. Sin esto, corre en modo simulación.",
    )
    args = parser.parse_args()

    main.configurar_logging()
    modo = "EJECUCIÓN REAL" if args.ejecutar else "SIMULACIÓN (no se borra/mueve nada)"
    logging.info(f"Mantenimiento - Modo: {modo}")
    logging.info(f"Módulos a correr: {', '.join(args.modulos)}")

    if "temporales" in args.modulos:
        main.limpiar_temporales(args.ejecutar)
    if "duplicados" in args.modulos:
        main.buscar_duplicados(args.ejecutar, CARPETAS_DUPLICADOS)
    if "programas" in args.modulos:
        main.listar_programas()

    if not args.ejecutar:
        logging.info("Esto fue una simulación. Para aplicar los cambios de verdad, corré con --ejecutar")


if __name__ == "__main__":
    ejecutar_mantenimiento()
