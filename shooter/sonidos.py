"""Generación y reproducción de sonidos (sin archivos externos).

Los sonidos se sintetizan en memoria al arrancar como buffers PCM,
evitando así depender de archivos .wav ni de numpy.
"""

import math
import random
import struct

import pygame


def generar_sonido_disparo():
    """Crea un 'pew' con un barrido de tono descendente."""
    frecuencia, _, _ = pygame.mixer.get_init()
    duracion = 0.12
    muestras = int(frecuencia * duracion)
    datos = []
    fase = 0.0
    for i in range(muestras):
        t = i / muestras
        tono = 880 - 660 * t          # de 880 Hz a 220 Hz
        fase += 2 * math.pi * tono / frecuencia
        envolvente = (1 - t) ** 2     # decaimiento suave
        valor = int(0.35 * envolvente * 32767 * math.sin(fase))
        datos.append(valor)
    return pygame.mixer.Sound(buffer=struct.pack(f"<{muestras}h", *datos))


def generar_sonido_explosion():
    """Crea una explosión con ruido y un tono grave que cae."""
    frecuencia, _, _ = pygame.mixer.get_init()
    duracion = 0.45
    muestras = int(frecuencia * duracion)
    azar = random.Random(1234)        # sonido reproducible
    datos = []
    fase = 0.0
    for i in range(muestras):
        t = i / muestras
        envolvente = math.exp(-6 * t)
        tono = 150 * (1 - 0.8 * t)
        fase += 2 * math.pi * tono / frecuencia
        ruido = azar.uniform(-1, 1)
        valor = 0.6 * ruido + 0.4 * math.sin(fase)
        datos.append(int(0.55 * envolvente * 32767 * valor))
    return pygame.mixer.Sound(buffer=struct.pack(f"<{muestras}h", *datos))


def preparar_audio():
    """Inicializa el audio si es posible; devuelve los sonidos (o None si falla)."""
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        return generar_sonido_disparo(), generar_sonido_explosion()
    except pygame.error:
        print("Aviso: no se pudo inicializar el audio, el juego continúa sin sonido.")
        return None, None


def reproducir(sonido):
    """Reproduce un sonido si existe (el audio puede fallar en algunos equipos)."""
    if sonido is not None:
        sonido.play()
