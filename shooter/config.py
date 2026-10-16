"""Configuración y constantes del juego.

Todos los valores ajustables están aquí para que sea fácil modificar
el comportamiento del juego sin tocar la lógica.
"""

# --- Pantalla y tiempo ---
ANCHO, ALTO = 600, 800
FPS = 60

# --- Red (multijugador) ---
PUERTO = 5555           # puerto TCP para el multijugador

# --- Paleta de colores ---
COLOR_FONDO = (18, 18, 30)
COLOR_TEXTO = (240, 240, 240)
COLOR_ROJO = (235, 80, 80)
COLOR_AVISO = (240, 200, 90)

COLOR_JUGADOR_1 = (80, 200, 120)     # anfitrión / un jugador
COLOR_JUGADOR_2 = (80, 160, 235)     # cliente
COLOR_DISPARO_1 = (240, 230, 80)
COLOR_DISPARO_2 = (140, 200, 255)
COLOR_ENEMIGO = (220, 70, 70)

# --- Velocidades (píxeles por segundo) ---
VEL_JUGADOR = 320
VEL_DISPARO = 520
VEL_ENEMIGO_MIN = 80
VEL_ENEMIGO_MAX = 200
INTERVALO_ENEMIGO = 700    # ms entre apariciones de enemigos

# --- Tamaños ---
TAM_JUGADOR = 48
ANCHO_DISPARO, ALTO_DISPARO = 6, 18
RADIO_ENEMIGO = 18
Y_JUGADOR = ALTO - TAM_JUGADOR - 20

# --- Reglas ---
PUNTOS_POR_ENEMIGO = 10

# --- Multijugador ---
INTERVALO_SONIDO_DISPARO = 70  # ms (limita el audio, no las balas)
UMBRAL_DESINCRONIA = 90        # px; el cliente se reajusta si se aleja mucho
