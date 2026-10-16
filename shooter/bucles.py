"""Bucles de juego: un jugador, anfitrión y cliente.

Cada bucle coordina la simulación (Mundo), la red (cuando corresponde)
y el dibujado (interfaz). Aquí no hay lógica de reglas ni de red pura.
"""

import socket

import pygame

from .config import (
    ALTO,
    ANCHO,
    COLOR_AVISO,
    COLOR_FONDO,
    COLOR_JUGADOR_2,
    COLOR_ROJO,
    COLOR_TEXTO,
    FPS,
    INTERVALO_SONIDO_DISPARO,
    PUERTO,
    TAM_JUGADOR,
    UMBRAL_DESINCRONIA,
    VEL_JUGADOR,
)
from .interfaz import (
    crear_texto,
    dibujar_estado,
    dibujar_marcador,
    esperar_tecla,
    pantalla_game_over,
    puntuaciones,
)
from .mundo import Mundo
from .red import ServidorAnfitrion, conectar_a, ip_local
from .sonidos import reproducir


def leer_entradas():
    """Lee el teclado y devuelve la entrada del jugador local."""
    teclas = pygame.key.get_pressed()
    return {
        "izq": teclas[pygame.K_LEFT] or teclas[pygame.K_a],
        "der": teclas[pygame.K_RIGHT] or teclas[pygame.K_d],
        "disparar": teclas[pygame.K_SPACE],
    }


# --- Modo un jugador ---
def bucle_un_jugador(pantalla, fuentes, sonidos):
    """Ejecuta la partida completa en local."""
    fuente, fuente_grande = fuentes
    sonido_disparo, sonido_explosion = sonidos
    reloj = pygame.time.Clock()
    mundo = Mundo(1)

    while True:
        dt = reloj.tick(FPS) / 1000.0
        ahora = pygame.time.get_ticks()
        reiniciar = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
                if ev.key == pygame.K_r and mundo.perdido:
                    reiniciar = True

        if reiniciar:
            mundo = Mundo(1)
        elif not mundo.perdido:
            entradas = [leer_entradas()]
            mundo.paso(dt, entradas, ahora, pantalla, sonido_disparo, sonido_explosion)

        pantalla.fill(COLOR_FONDO)
        mundo.dibujar(pantalla)
        dibujar_marcador(pantalla, fuente, [mundo.jugadores[0].puntos, 0], False)
        if mundo.perdido:
            pantalla_game_over(pantalla, fuente, fuente_grande, [mundo.jugadores[0].puntos, 0], False, True)
        pygame.display.flip()


# --- Modo anfitrión ---
def bucle_anfitrin(pantalla, fuentes, sonidos):
    """Crea la partida, espera al jugador 2 y ejecuta la simulación autoritativa."""
    fuente, fuente_grande = fuentes
    sonido_disparo, sonido_explosion = sonidos
    reloj = pygame.time.Clock()
    servidor = ServidorAnfitrion(PUERTO)
    ip = ip_local()
    mundo = None
    cliente = None

    try:
        # Pantalla de espera
        while cliente is None:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return
            cliente = servidor.comprobar_cliente()
            pantalla.fill(COLOR_FONDO)
            crear_texto(pantalla, fuente_grande, "ANFITRIÓN", COLOR_AVISO, ANCHO // 2, 120, centrado=True)
            crear_texto(pantalla, fuente, "Esperando al jugador 2...", COLOR_TEXTO, ANCHO // 2, 240, centrado=True)
            crear_texto(pantalla, fuente, "Comparte esta IP:", COLOR_TEXTO, ANCHO // 2, 330, centrado=True)
            crear_texto(pantalla, fuente_grande, ip, COLOR_JUGADOR_2, ANCHO // 2, 390, centrado=True)
            crear_texto(pantalla, fuente, f"(puerto {PUERTO})  Esc para cancelar", COLOR_AVISO, ANCHO // 2, 450, centrado=True)
            pygame.display.flip()
            reloj.tick(FPS)

        mundo = Mundo(2)
        cliente.enviar({"tipo": "bienvenida", "indice": 1})
        entrada_cliente = {"izq": False, "der": False, "disparar": False}

        while True:
            dt = reloj.tick(FPS) / 1000.0
            ahora = pygame.time.get_ticks()
            reiniciar = False
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r and mundo.perdido:
                    reiniciar = True

            if cliente.cerrada:
                pantalla.fill(COLOR_FONDO)
                crear_texto(pantalla, fuente_grande, "CONECTADO CORTADO", COLOR_ROJO, ANCHO // 2, ALTO // 2 - 30, centrado=True)
                crear_texto(pantalla, fuente, "El jugador 2 se desconectó. Esc para salir.", COLOR_TEXTO, ANCHO // 2, ALTO // 2 + 30, centrado=True)
                pygame.display.flip()
                continue

            # Recoger las entradas del cliente
            while True:
                msg = cliente.recibir()
                if msg is None:
                    break
                if msg.get("tipo") == "entrada":
                    entrada_cliente = {"izq": msg["izq"], "der": msg["der"], "disparar": msg["disparar"]}

            if not mundo.perdido:
                entradas = [leer_entradas(), entrada_cliente]
                mundo.paso(dt, entradas, ahora, pantalla, sonido_disparo, sonido_explosion)
            if reiniciar:
                mundo = Mundo(2)

            # Enviar el estado al cliente
            cliente.enviar({"tipo": "estado", **mundo.a_estado()})

            pantalla.fill(COLOR_FONDO)
            mundo.dibujar(pantalla)
            dibujar_marcador(pantalla, fuente, [j.puntos for j in mundo.jugadores], True)
            if mundo.perdido:
                pantalla_game_over(pantalla, fuente, fuente_grande, [j.puntos for j in mundo.jugadores], True, True)
            pygame.display.flip()
    finally:
        servidor.cerrar()


# --- Modo cliente ---
def bucle_cliente(pantalla, fuentes, sonidos, host):
    """Se conecta al anfitrión y dibuja el estado recibido."""
    fuente, fuente_grande = fuentes
    sonido_disparo, sonido_explosion = sonidos
    reloj = pygame.time.Clock()

    pantalla.fill(COLOR_FONDO)
    crear_texto(pantalla, fuente, f"Conectando a {host}:{PUERTO}...", COLOR_TEXTO, ANCHO // 2, ALTO // 2, centrado=True)
    pygame.display.flip()

    try:
        conexion = conectar_a(host, PUERTO)
    except (socket.timeout, OSError) as error:
        pantalla.fill(COLOR_FONDO)
        crear_texto(pantalla, fuente_grande, "SIN CONEXIÓN", COLOR_ROJO, ANCHO // 2, ALTO // 2 - 30, centrado=True)
        crear_texto(pantalla, fuente, f"No se pudo conectar: {error}", COLOR_TEXTO, ANCHO // 2, ALTO // 2 + 30, centrado=True)
        crear_texto(pantalla, fuente, "Pulsa cualquier tecla para volver", COLOR_AVISO, ANCHO // 2, ALTO // 2 + 80, centrado=True)
        pygame.display.flip()
        esperar_tecla()
        return

    indice_propio = 1
    estado = {"jugadores": [], "disparos": [], "enemigos": [], "perdido": False}
    puntos_previos = [0, 0]
    mi_x = None
    ultimo_envio = 0
    ultimo_sonido_disparo = 0

    try:
        while True:
            dt = reloj.tick(FPS) / 1000.0
            ahora = pygame.time.get_ticks()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return

            if conexion.cerrada:
                pantalla.fill(COLOR_FONDO)
                crear_texto(pantalla, fuente_grande, "CONECTADO CORTADO", COLOR_ROJO, ANCHO // 2, ALTO // 2 - 30, centrado=True)
                crear_texto(pantalla, fuente, "El anfitrión cerró la partida.", COLOR_TEXTO, ANCHO // 2, ALTO // 2 + 30, centrado=True)
                crear_texto(pantalla, fuente, "Pulsa cualquier tecla para volver", COLOR_AVISO, ANCHO // 2, ALTO // 2 + 80, centrado=True)
                pygame.display.flip()
                esperar_tecla()
                return

            # Procesar mensajes entrantes
            while True:
                msg = conexion.recibir()
                if msg is None:
                    break
                if msg.get("tipo") == "bienvenida":
                    indice_propio = msg.get("indice", 1)
                elif msg.get("tipo") == "estado":
                    estado = msg
                    # El anfitrión nos da la posición autoritativa de nuestro jugador
                    for j in estado.get("jugadores", []):
                        if j["indice"] == indice_propio:
                            if mi_x is None:
                                mi_x = j["x"]
                            elif abs(j["x"] - mi_x) > UMBRAL_DESINCRONIA:
                                mi_x = j["x"]  # reajuste si nos desincronizamos

            # Enviar nuestras entradas al anfitrión
            if ahora - ultimo_envio >= 33:   # ~30 envíos por segundo
                ultimo_envio = ahora
                entradas = leer_entradas()
                conexion.enviar({"tipo": "entrada", **entradas})
                # Sonido local de disparo para respuesta inmediata
                if entradas["disparar"] and ahora - ultimo_sonido_disparo >= INTERVALO_SONIDO_DISPARO:
                    ultimo_sonido_disparo = ahora
                    reproducir(sonido_disparo)

            # Predicción local de nuestro jugador (movimiento fluido)
            entradas = leer_entradas()
            if mi_x is not None and not estado.get("perdido", False):
                if entradas["izq"]:
                    mi_x -= int(VEL_JUGADOR * dt)
                if entradas["der"]:
                    mi_x += int(VEL_JUGADOR * dt)
                mi_x = max(0, min(ANCHO - TAM_JUGADOR, mi_x))

            # Explosiones cuando sube la puntuación de cualquiera
            puntos = puntuaciones(estado)
            if puntos != puntos_previos:
                reproducir(sonido_explosion)
                puntos_previos = puntos[:]

            pantalla.fill(COLOR_FONDO)
            dibujar_estado(pantalla, estado, indice_propio, mi_x)
            dibujar_marcador(pantalla, fuente, puntos, True)
            if estado.get("perdido", False):
                pantalla_game_over(pantalla, fuente, fuente_grande, puntos, True, False)
            pygame.display.flip()
    finally:
        conexion.cerrar()
