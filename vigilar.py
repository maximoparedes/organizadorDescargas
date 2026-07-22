"""Vigila las carpetas configuradas y organiza los archivos apenas aparecen."""
import logging
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import main

SEGUNDOS_DEBOUNCE = 5
SEGUNDOS_RASTREO_PERIODICO = 60


class ManejadorCarpeta(FileSystemEventHandler):
    def __init__(self, carpeta, reglas):
        self.carpeta = carpeta
        self.reglas = reglas
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
            main.organizar_carpeta(self.carpeta, self.reglas)
        except Exception as e:
            logging.error(f"Error organizando {self.carpeta}: {e}")


def main_vigilancia() -> None:
    main.configurar_logging()
    reglas = main.cargar_reglas(main.CONFIG_PATH)
    carpetas = [c for c in main.obtener_carpetas_a_organizar(reglas) if c.is_dir()]

    if not carpetas:
        logging.error("No se encontró ninguna de las carpetas configuradas para vigilar.")
        return

    logging.info(f"Vigilando: {', '.join(str(c) for c in carpetas)}")
    logging.info("Los archivos nuevos se van a organizar solos unos segundos después de aparecer.")

    manejadores = []
    observador = Observer()
    for carpeta in carpetas:
        manejador = ManejadorCarpeta(carpeta, reglas)
        observador.schedule(manejador, str(carpeta), recursive=False)
        manejadores.append(manejador)
    observador.start()

    try:
        while True:
            time.sleep(SEGUNDOS_RASTREO_PERIODICO)
            # Rastreo de respaldo: por si algún evento se perdió o el archivo
            # todavía no cumplía la antigüedad mínima cuando disparó el debounce.
            for manejador in manejadores:
                manejador._organizar()
    except KeyboardInterrupt:
        observador.stop()
    observador.join()


if __name__ == "__main__":
    main_vigilancia()
