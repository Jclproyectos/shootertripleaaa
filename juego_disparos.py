"""Lanzador del juego de disparos 2D.

La implementación vive en el paquete `shooter/`. Este script sólo
delega en el punto de entrada para mantener el comando documentado:

    python juego_disparos.py

También se puede ejecutar con:

    python -m shooter
"""

from shooter.app import main

if __name__ == "__main__":
    main()
