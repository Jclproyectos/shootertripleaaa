"""Simulación del juego: jugadores, disparos y enemigos.

La clase Mundo encapsula toda la lógica de la partida y se reutiliza
tanto en el modo un jugador como en el anfitrión del multijugador.
"""

import random

import pygame

from .config import (
    ALTO,
    ALTO_DISPARO,
    ANCHO,
    ANCHO_DISPARO,
    COLOR_DISPARO_1,
    COLOR_DISPARO_2,
    COLOR_ENEMIGO,
    COLOR_JUGADOR_1,
    COLOR_JUGADOR_2,
    INTERVALO_ENEMIGO,
    INTERVALO_SONIDO_DISPARO,
    PUNTOS_POR_ENEMIGO,
    RADIO_ENEMIGO,
    TAM_JUGADOR,
    VEL_DISPARO,
    VEL_ENEMIGO_MAX,
    VEL_ENEMIGO_MIN,
    VEL_JUGADOR,
    Y_JUGADOR,
)
from .sonidos import reproducir


class Jugador:
    """Un cuadrado controlado por un participante, con su puntuación."""

    def __init__(self, indice, x, color, color_disparo):
        self.indice = indice
        self.rect = pygame.Rect(x, Y_JUGADOR, TAM_JUGADOR, TAM_JUGADOR)
        self.color = color
        self.color_disparo = color_disparo
        self.puntos = 0


class Mundo:
    """Contiene jugadores, disparos y enemigos, y los simula."""

    def __init__(self, num_jugadores):
        self.jugadores = []
        if num_jugadores == 1:
            posiciones = [(ANCHO - TAM_JUGADOR) // 2]
        else:
            posiciones = [ANCHO // 4, (ANCHO * 3) // 4 - TAM_JUGADOR]
        colores = [COLOR_JUGADOR_1, COLOR_JUGADOR_2]
        colores_disparo = [COLOR_DISPARO_1, COLOR_DISPARO_2]
        for i in range(num_jugadores):
            self.jugadores.append(Jugador(i, posiciones[i], colores[i], colores_disparo[i]))
        self.disparos = []      # {"rect": Rect, "duenio": int}
        self.enemigos = []      # {"rect": Rect, "vel": float}
        self.perdido = False
        self._ultimo_enemigo = pygame.time.get_ticks()
        self._ultimo_sonido_disparo = 0

    def paso(self, dt, entradas, ahora, pantalla, sonido_disparo, sonido_explosion):
        """Avanza la simulación un frame.

        'entradas' es una lista con una entrada por jugador; cada una es un
        diccionario con las claves 'izq', 'der' y 'disparar' (True/False).
        """
        # Movimiento de los jugadores
        for i, jugador in enumerate(self.jugadores):
            e = entradas[i]
            if e["izq"]:
                jugador.rect.x -= int(VEL_JUGADOR * dt)
            if e["der"]:
                jugador.rect.x += int(VEL_JUGADOR * dt)
            jugador.rect.clamp_ip(pantalla.get_rect())

        # Disparos (sin límite)
        for i, jugador in enumerate(self.jugadores):
            if entradas[i]["disparar"]:
                bala = pygame.Rect(
                    jugador.rect.centerx - ANCHO_DISPARO // 2,
                    jugador.rect.top - ALTO_DISPARO,
                    ANCHO_DISPARO,
                    ALTO_DISPARO,
                )
                self.disparos.append({"rect": bala, "duenio": jugador.indice})
                if ahora - self._ultimo_sonido_disparo >= INTERVALO_SONIDO_DISPARO:
                    self._ultimo_sonido_disparo = ahora
                    reproducir(sonido_disparo)

        # Aparición de enemigos
        if ahora - self._ultimo_enemigo >= INTERVALO_ENEMIGO:
            self._ultimo_enemigo = ahora
            x = random.randint(RADIO_ENEMIGO, ANCHO - RADIO_ENEMIGO)
            rect = pygame.Rect(0, 0, RADIO_ENEMIGO * 2, RADIO_ENEMIGO * 2)
            rect.centerx = x
            rect.centery = -RADIO_ENEMIGO
            vel = random.uniform(VEL_ENEMIGO_MIN, VEL_ENEMIGO_MAX)
            self.enemigos.append({"rect": rect, "vel": vel})

        # Avance de disparos
        for d in self.disparos[:]:
            d["rect"].y -= int(VEL_DISPARO * dt)
            if d["rect"].bottom < 0:
                self.disparos.remove(d)

        # Avance de enemigos
        for e in self.enemigos[:]:
            e["rect"].y += int(e["vel"] * dt)
            if e["rect"].bottom >= ALTO:
                self.perdido = True
                reproducir(sonido_explosion)

        # Colisiones disparo / enemigo
        for d in self.disparos[:]:
            for e in self.enemigos[:]:
                if d["rect"].colliderect(e["rect"]):
                    if d in self.disparos:
                        self.disparos.remove(d)
                    self.enemigos.remove(e)
                    self.jugadores[d["duenio"]].puntos += PUNTOS_POR_ENEMIGO
                    reproducir(sonido_explosion)
                    break

    def a_estado(self):
        """Serializa el mundo para enviarlo por la red."""
        return {
            "jugadores": [
                {"indice": j.indice, "x": j.rect.x, "y": j.rect.y, "puntos": j.puntos}
                for j in self.jugadores
            ],
            "disparos": [
                {"x": d["rect"].x, "y": d["rect"].y, "duenio": d["duenio"]}
                for d in self.disparos
            ],
            "enemigos": [
                {"x": e["rect"].x, "y": e["rect"].y} for e in self.enemigos
            ],
            "perdido": self.perdido,
        }

    def dibujar(self, pantalla):
        """Dibuja el mundo local (jugadores, disparos y enemigos)."""
        for jugador in self.jugadores:
            pygame.draw.rect(pantalla, jugador.color, jugador.rect)
        for d in self.disparos:
            pygame.draw.rect(pantalla, self.jugadores[d["duenio"]].color_disparo, d["rect"])
        for e in self.enemigos:
            pygame.draw.circle(pantalla, COLOR_ENEMIGO, e["rect"].center, RADIO_ENEMIGO)
