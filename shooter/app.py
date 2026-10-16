"""Punto de entrada de la aplicación.

Inicializa Pygame y gestiona el bucle de menús que lanza cada modo.
"""

import sys

import pygame

from .bucles import bucle_anfitrin, bucle_cliente, bucle_un_jugador
from .config import ALTO, ANCHO
from .interfaz import menu_principal, pantalla_ip
from .sonidos import preparar_audio


def main():
    """Arranca Pygame y gestiona el bucle principal de menús y partida."""
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Disparos 2D")
    sonidos = preparar_audio()
    fuente = pygame.font.SysFont("consolas", 28, bold=True)
    fuente_grande = pygame.font.SysFont("consolas", 52, bold=True)
    fuentes = (fuente, fuente_grande)

    try:
        while True:
            modo = menu_principal(pantalla, fuente, fuente_grande)
            if modo == "un_jugador":
                bucle_un_jugador(pantalla, fuentes, sonidos)
            elif modo == "anfitrin":
                bucle_anfitrin(pantalla, fuentes, sonidos)
            elif modo == "unirse":
                host = pantalla_ip(pantalla, fuente, fuente_grande)
                if host:
                    bucle_cliente(pantalla, fuentes, sonidos, host)
            else:
                break
    finally:
        pygame.quit()
        sys.exit()
