"""Juego de disparos 2D con Pygame y multijugador cooperativo en línea.

Estructura del paquete:
    - config: constantes y ajustes del juego.
    - sonidos: generación procedural de sonidos (sin archivos externos).
    - red: comunicación TCP + JSON para el multijugador.
    - mundo: simulación (jugadores, disparos, enemigos).
    - interfaz: dibujado, menús y pantallas.
    - bucles: bucles de juego (un jugador, anfitrión, cliente).
    - app: punto de entrada.
"""

__all__ = ["main"]


def main():
    """Arranca el juego (importación perezosa para no cargar Pygame al importar)."""
    from .app import main as _main

    return _main()
