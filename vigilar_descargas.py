"""Vigila la carpeta de Descargas y organiza los archivos apenas terminan de bajar."""
import logging
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import main

SEGUNDOS_DEBOUNCE = 5
SEGUNDOS_RASTREO_PERIODICO = 60


class ManejadorDescargas(FileSystemEventHandler):
    def __init__(self, carpeta_descargas):
        self.carpeta_descargas = carpeta_descargas
        self._temporizador = None
        self._lock = threading.Lock()

    def on_created(self, event):
        self._programar_organizacion()

    def on_moved(self, event):
        self._programar_organizacion()

    def _programar_organizacion(self):
        with self._lock:
            if self._temporizador is not None:
                self._temporizador.cancel()
            self._temporizador = threading.Timer(SEGUNDOS_DEBOUNCE, self._organizar)
            self._temporizador.daemon = True
            self._temporizador.start()

    def _organizar(self):
        try:
            reglas = main.cargar_reglas(main.CONFIG_PATH)
            main.organizar_carpeta(self.carpeta_descargas, reglas)
        except Exception as e:
            logging.error(f"Error organizando: {e}")


def main_vigilancia() -> None:
    main.configurar_logging()
    carpeta_descargas = main.obtener_carpeta_descargas()

    if not carpeta_descargas.is_dir():
        logging.error(f"No se encontró la carpeta de Descargas: {carpeta_descargas}")
        return

    logging.info(f"Vigilando: {carpeta_descargas}")
    logging.info("Los archivos nuevos se van a organizar solos unos segundos después de terminar de descargarse.")

    manejador = ManejadorDescargas(carpeta_descargas)
    observador = Observer()
    observador.schedule(manejador, str(carpeta_descargas), recursive=False)
    observador.start()

    try:
        while True:
            time.sleep(SEGUNDOS_RASTREO_PERIODICO)
            # Rastreo de respaldo: por si algún evento se perdió o el archivo
            # todavía no cumplía la antigüedad mínima cuando disparó el debounce.
            manejador._organizar()
    except KeyboardInterrupt:
        observador.stop()
    observador.join()


if __name__ == "__main__":
    main_vigilancia()
