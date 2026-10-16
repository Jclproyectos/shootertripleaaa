"""Interfaz: dibujado de textos/estados, menús y pantallas.

Este módulo sólo se ocupa de pintar en pantalla y de capturar la
entrada del usuario en los menús; no contiene lógica de juego.
"""

import pygame

from .config import (
    ALTO,
    ALTO_DISPARO,
    ANCHO,
    ANCHO_DISPARO,
    COLOR_AVISO,
    COLOR_DISPARO_1,
    COLOR_DISPARO_2,
    COLOR_ENEMIGO,
    COLOR_FONDO,
    COLOR_JUGADOR_1,
    COLOR_JUGADOR_2,
    COLOR_ROJO,
    COLOR_TEXTO,
    RADIO_ENEMIGO,
    TAM_JUGADOR,
)


def crear_texto(pantalla, fuente, texto, color, x, y, centrado=False):
    """Dibuja un texto; por defecto con su esquina superior izquierda en (x, y)."""
    superficie = fuente.render(texto, True, color)
    rect = superficie.get_rect()
    if centrado:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    pantalla.blit(superficie, rect)
    return rect


def esperar_tecla():
    """Bloquea hasta que se pulsa cualquier tecla (para las pantallas de aviso)."""
    esperando = True
    while esperando:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                esperando = False
            elif ev.type == pygame.KEYDOWN:
                esperando = False
        pygame.time.wait(30)


# --- Dibujo del estado recibido (usado por el cliente) ---
def dibujar_estado(pantalla, estado, indice_propio, mi_x_predicho):
    """Dibuja el estado recibido del anfitrión en el cliente."""
    for j in estado.get("jugadores", []):
        color = COLOR_JUGADOR_1 if j["indice"] == 0 else COLOR_JUGADOR_2
        x = j["x"]
        if j["indice"] == indice_propio and mi_x_predicho is not None:
            x = mi_x_predicho   # predicción local para que el movimiento sea fluido
        pygame.draw.rect(pantalla, color, pygame.Rect(x, j["y"], TAM_JUGADOR, TAM_JUGADOR))

    for d in estado.get("disparos", []):
        color = COLOR_DISPARO_1 if d["duenio"] == 0 else COLOR_DISPARO_2
        pygame.draw.rect(pantalla, color, pygame.Rect(d["x"], d["y"], ANCHO_DISPARO, ALTO_DISPARO))

    for e in estado.get("enemigos", []):
        pygame.draw.circle(pantalla, COLOR_ENEMIGO, (e["x"], e["y"]), RADIO_ENEMIGO)


def puntuaciones(estado):
    """Extrae [puntos_jugador_0, puntos_jugador_1] del estado recibido."""
    puntos = [0, 0]
    for j in estado.get("jugadores", []):
        puntos[j["indice"]] = j["puntos"]
    return puntos


# --- Marcador y pantallas ---
def dibujar_marcador(pantalla, fuente, puntos, dos_jugadores):
    """Pinta la puntuación (J1 arriba a la izquierda, J2 arriba a la derecha)."""
    crear_texto(pantalla, fuente, f"J1: {puntos[0]}", COLOR_TEXTO, 12, 10)
    if dos_jugadores:
        texto = f"J2: {puntos[1]}"
        superficie = fuente.render(texto, True, COLOR_TEXTO)
        pantalla.blit(superficie, (ANCHO - superficie.get_width() - 12, 10))


def pantalla_game_over(pantalla, fuente, fuente_grande, puntos, dos_jugadores, anfitrin):
    """Capa atenuada con el mensaje de fin de partida."""
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    capa.fill((0, 0, 0, 160))
    pantalla.blit(capa, (0, 0))
    crear_texto(pantalla, fuente_grande, "GAME OVER", COLOR_ROJO, ANCHO // 2, ALTO // 2 - 70, centrado=True)
    if dos_jugadores:
        crear_texto(pantalla, fuente, f"J1: {puntos[0]}   J2: {puntos[1]}", COLOR_TEXTO, ANCHO // 2, ALTO // 2, centrado=True)
        if anfitrin:
            crear_texto(pantalla, fuente, "Pulsa R para reiniciar o Esc para salir", COLOR_TEXTO, ANCHO // 2, ALTO // 2 + 60, centrado=True)
        else:
            crear_texto(pantalla, fuente, "Esperando al anfitrión...", COLOR_AVISO, ANCHO // 2, ALTO // 2 + 60, centrado=True)
    else:
        crear_texto(pantalla, fuente, f"Puntuación final: {puntos[0]}", COLOR_TEXTO, ANCHO // 2, ALTO // 2, centrado=True)
        crear_texto(pantalla, fuente, "Pulsa R para reiniciar o Esc para salir", COLOR_TEXTO, ANCHO // 2, ALTO // 2 + 60, centrado=True)


# --- Menús ---
def menu_principal(pantalla, fuente, fuente_grande):
    """Muestra el menú inicial y devuelve el modo elegido (o None para salir)."""
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key == pygame.K_1:
                    return "un_jugador"
                if ev.key == pygame.K_2:
                    return "anfitrin"
                if ev.key == pygame.K_3:
                    return "unirse"

        pantalla.fill(COLOR_FONDO)
        crear_texto(pantalla, fuente_grande, "DISPAROS 2D", COLOR_AVISO, ANCHO // 2, 140, centrado=True)
        crear_texto(pantalla, fuente, "Cooperativo en línea", COLOR_TEXTO, ANCHO // 2, 200, centrado=True)

        y = 320
        for tecla, texto in [("1", "Un jugador"), ("2", "Anfitrión (crear partida)"), ("3", "Unirse por IP")]:
            crear_texto(pantalla, fuente, f"[{tecla}]  {texto}", COLOR_TEXTO, ANCHO // 2, y, centrado=True)
            y += 60

        crear_texto(pantalla, fuente, "Esc  Salir", COLOR_AVISO, ANCHO // 2, y + 30, centrado=True)
        pygame.display.flip()
        pygame.time.wait(30)


def pantalla_ip(pantalla, fuente, fuente_grande):
    """Pide la IP del anfitrión con un campo de texto; devuelve la IP o None."""
    texto = ""
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key == pygame.K_RETURN and texto.strip():
                    return texto.strip()
                if ev.key == pygame.K_BACKSPACE:
                    texto = texto[:-1]
                elif ev.unicode and ev.unicode.isprintable() and len(texto) < 40:
                    texto += ev.unicode

        pantalla.fill(COLOR_FONDO)
        crear_texto(pantalla, fuente_grande, "UNIRSE A PARTIDA", COLOR_AVISO, ANCHO // 2, 160, centrado=True)
        crear_texto(pantalla, fuente, "IP del anfitrión:", COLOR_TEXTO, ANCHO // 2, 300, centrado=True)
        # Campo de texto
        caja = pygame.Rect(0, 0, 360, 52)
        caja.center = (ANCHO // 2, 370)
        pygame.draw.rect(pantalla, (40, 40, 60), caja)
        pygame.draw.rect(pantalla, COLOR_JUGADOR_2, caja, 2)
        crear_texto(pantalla, fuente, texto + "_", COLOR_TEXTO, caja.x + 14, caja.y + 12)
        crear_texto(pantalla, fuente, "Enter para conectar   Esc para volver", COLOR_AVISO, ANCHO // 2, 470, centrado=True)
        pygame.display.flip()
        pygame.time.wait(30)
