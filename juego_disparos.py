"""Juego de disparos 2D con Pygame.

Controles:
    - Flechas izquierda / derecha (o A / D): mover el jugador.
    - Barra espaciadora: disparar (sin límite: mantén pulsado para spammear).
    - R: reiniciar tras el game over.
    - Esc: salir.

Reglas:
    - Los círculos enemigos caen desde la parte superior.
    - Cada disparo que acierta a un enemigo suma 10 puntos.
    - Si un enemigo toca el fondo, pierdes la partida.
"""

import math
import random
import struct
import sys

import pygame

# --- Configuración general ---
ANCHO, ALTO = 600, 800
FPS = 60

COLOR_FONDO = (18, 18, 30)
COLOR_JUGADOR = (80, 200, 120)
COLOR_DISPARO = (240, 230, 80)
COLOR_ENEMIGO = (220, 70, 70)
COLOR_TEXTO = (240, 240, 240)
COLOR_ROJO = (235, 80, 80)

VEL_JUGADOR = 320          # píxeles por segundo
VEL_DISPARO = 520          # píxeles por segundo
VEL_ENEMIGO_MIN = 80       # píxeles por segundo
VEL_ENEMIGO_MAX = 200      # píxeles por segundo
INTERVALO_ENEMIGO = 700    # ms entre apariciones de enemigos

TAM_JUGADOR = 48
ANCHO_DISPARO, ALTO_DISPARO = 6, 18
RADIO_ENEMIGO = 18

PUNTOS_POR_ENEMIGO = 10

# El disparo no tiene límite, pero el sonido se limita un poco
# para no saturar la tarjeta de audio al spammear.
INTERVALO_SONIDO_DISPARO = 70  # ms


# --- Generación de sonidos (sin archivos externos) ---
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


def reproducir(sonido):
    """Reproduce un sonido si existe (el audio puede fallar en algunos equipos)."""
    if sonido is not None:
        sonido.play()


def crear_texto(fuente, texto, color, x, y, centrado=False):
    """Dibuja un texto; por defecto con su esquina superior izquierda en (x, y)."""
    superficie = fuente.render(texto, True, color)
    rect = superficie.get_rect()
    if centrado:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    pantalla.blit(superficie, rect)


def main():
    global pantalla

    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Disparos 2D")

    # El audio puede no estar disponible; en ese caso el juego sigue sin sonido.
    sonido_disparo = None
    sonido_explosion = None
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        sonido_disparo = generar_sonido_disparo()
        sonido_explosion = generar_sonido_explosion()
    except pygame.error:
        print("Aviso: no se pudo inicializar el audio, el juego continúa sin sonido.")

    reloj = pygame.time.Clock()
    fuente = pygame.font.SysFont("consolas", 28, bold=True)
    fuente_grande = pygame.font.SysFont("consolas", 56, bold=True)

    def reiniciar():
        """(Re)inicia el estado de la partida y devuelve las variables."""
        jugador = pygame.Rect(
            (ANCHO - TAM_JUGADOR) // 2,
            ALTO - TAM_JUGADOR - 20,
            TAM_JUGADOR,
            TAM_JUGADOR,
        )
        return {
            "jugador": jugador,
            "disparos": [],       # rectángulos
            "enemigos": [],       # [rectángulo, velocidad_y]
            "puntuacion": 0,
            "perdido": False,
            "tiempo_ultimo_enemigo": pygame.time.get_ticks(),
            "tiempo_ultimo_sonido_disparo": 0,
        }

    estado = reiniciar()
    corriendo = True
    while corriendo:
        dt = reloj.tick(FPS) / 1000.0  # segundos desde el frame anterior
        ahora = pygame.time.get_ticks()

        # --- Eventos ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    corriendo = False
                elif evento.key == pygame.K_r and estado["perdido"]:
                    estado = reiniciar()

        teclas = pygame.key.get_pressed()

        if not estado["perdido"]:
            jugador = estado["jugador"]
            disparos = estado["disparos"]
            enemigos = estado["enemigos"]

            # --- Movimiento del jugador ---
            if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
                jugador.x -= int(VEL_JUGADOR * dt)
            if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
                jugador.x += int(VEL_JUGADOR * dt)
            jugador.clamp_ip(pantalla.get_rect())

            # --- Disparo (sin límite: un disparo por frame si mantienes pulsado) ---
            if teclas[pygame.K_SPACE]:
                bala = pygame.Rect(
                    jugador.centerx - ANCHO_DISPARO // 2,
                    jugador.top - ALTO_DISPARO,
                    ANCHO_DISPARO,
                    ALTO_DISPARO,
                )
                disparos.append(bala)
                if ahora - estado["tiempo_ultimo_sonido_disparo"] >= INTERVALO_SONIDO_DISPARO:
                    estado["tiempo_ultimo_sonido_disparo"] = ahora
                    reproducir(sonido_disparo)

            # --- Aparición de enemigos ---
            if ahora - estado["tiempo_ultimo_enemigo"] >= INTERVALO_ENEMIGO:
                estado["tiempo_ultimo_enemigo"] = ahora
                x = random.randint(RADIO_ENEMIGO, ANCHO - RADIO_ENEMIGO)
                enemigo = pygame.Rect(0, 0, RADIO_ENEMIGO * 2, RADIO_ENEMIGO * 2)
                enemigo.centerx = x
                enemigo.centery = -RADIO_ENEMIGO
                velocidad = random.uniform(VEL_ENEMIGO_MIN, VEL_ENEMIGO_MAX)
                enemigos.append([enemigo, velocidad])

            # --- Actualizar disparos ---
            for bala in disparos[:]:
                bala.y -= int(VEL_DISPARO * dt)
                if bala.bottom < 0:
                    disparos.remove(bala)

            # --- Actualizar enemigos ---
            for entrada in enemigos[:]:
                rect_enemigo, velocidad = entrada
                rect_enemigo.y += int(velocidad * dt)
                if rect_enemigo.bottom >= ALTO:
                    # Un enemigo ha llegado al fondo: fin de la partida.
                    estado["perdido"] = True
                    reproducir(sonido_explosion)

            # --- Colisiones disparo / enemigo ---
            for bala in disparos[:]:
                for entrada in enemigos[:]:
                    rect_enemigo, _ = entrada
                    if bala.colliderect(rect_enemigo):
                        if bala in disparos:
                            disparos.remove(bala)
                        enemigos.remove(entrada)
                        estado["puntuacion"] += PUNTOS_POR_ENEMIGO
                        reproducir(sonido_explosion)
                        break

        # --- Dibujar ---
        pantalla.fill(COLOR_FONDO)

        # Jugador (cuadrado)
        pygame.draw.rect(pantalla, COLOR_JUGADOR, estado["jugador"])

        # Disparos (rectángulos)
        for bala in estado["disparos"]:
            pygame.draw.rect(pantalla, COLOR_DISPARO, bala)

        # Enemigos (círculos)
        for rect_enemigo, _ in estado["enemigos"]:
            pygame.draw.circle(
                pantalla,
                COLOR_ENEMIGO,
                rect_enemigo.center,
                rect_enemigo.width // 2,
            )

        # Puntuación (esquina superior izquierda)
        crear_texto(fuente, f"Puntos: {estado['puntuacion']}", COLOR_TEXTO, 12, 10)

        # --- Pantalla de game over ---
        if estado["perdido"]:
            capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            capa.fill((0, 0, 0, 160))
            pantalla.blit(capa, (0, 0))

            crear_texto(fuente_grande, "GAME OVER", COLOR_ROJO, ANCHO // 2, ALTO // 2 - 60, centrado=True)
            crear_texto(
                fuente,
                f"Puntuación final: {estado['puntuacion']}",
                COLOR_TEXTO,
                ANCHO // 2,
                ALTO // 2 + 10,
                centrado=True,
            )
            crear_texto(
                fuente,
                "Pulsa R para reiniciar o Esc para salir",
                COLOR_TEXTO,
                ANCHO // 2,
                ALTO // 2 + 70,
                centrado=True,
            )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
