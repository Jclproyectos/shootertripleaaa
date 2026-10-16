"""Juego de disparos 2D con Pygame, con modo un jugador y multijugador en línea.

Modos:
    - Un jugador: la partida completa corre en local.
    - Anfitrión: crea una partida y espera a un segundo jugador (abre un puerto TCP).
    - Unirse: te conectas a la IP del anfitrión.

Multijugador:
    - Cooperativo: ambos jugadores comparten los mismos enemigos y suman puntos por separado.
    - El anfitrión es la simulación autoritativa; el cliente envía sus entradas
      y dibuja el estado que recibe.
    - Comunicación por TCP con mensajes JSON delimitados por salto de línea,
      usando únicamente la librería estándar (socket, threading, json, queue).

Controles:
    - Flechas izquierda / derecha (o A / D): mover al jugador.
    - Barra espaciadora: disparar (sin límite: mantén pulsado para spammear).
    - R: reiniciar tras el game over (sólo el anfitrión reinicia en multijugador).
    - Esc: salir / volver atrás.
"""

import json
import math
import queue
import random
import socket
import struct
import sys
import threading

import pygame

# --- Configuración general ---
ANCHO, ALTO = 600, 800
FPS = 60
PUERTO = 5555           # puerto TCP para el multijugador

COLOR_FONDO = (18, 18, 30)
COLOR_TEXTO = (240, 240, 240)
COLOR_ROJO = (235, 80, 80)
COLOR_AVISO = (240, 200, 90)

COLOR_JUGADOR_1 = (80, 200, 120)     # anfitrión / un jugador
COLOR_JUGADOR_2 = (80, 160, 235)     # cliente
COLOR_DISPARO_1 = (240, 230, 80)
COLOR_DISPARO_2 = (140, 200, 255)
COLOR_ENEMIGO = (220, 70, 70)

VEL_JUGADOR = 320          # píxeles por segundo
VEL_DISPARO = 520          # píxeles por segundo
VEL_ENEMIGO_MIN = 80       # píxeles por segundo
VEL_ENEMIGO_MAX = 200      # píxeles por segundo
INTERVALO_ENEMIGO = 700    # ms entre apariciones de enemigos

TAM_JUGADOR = 48
ANCHO_DISPARO, ALTO_DISPARO = 6, 18
RADIO_ENEMIGO = 18
Y_JUGADOR = ALTO - TAM_JUGADOR - 20

PUNTOS_POR_ENEMIGO = 10
INTERVALO_SONIDO_DISPARO = 70  # ms (limita el audio, no las balas)

UMBRAL_DESINCRONIA = 90        # px; el cliente se reajusta si se aleja mucho


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


def preparar_audio():
    """Inicializa el audio si es posible; devuelve los sonidos (o None si falla)."""
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        return generar_sonido_disparo(), generar_sonido_explosion()
    except pygame.error:
        print("Aviso: no se pudo inicializar el audio, el juego continúa sin sonido.")
        return None, None


def reproducir(sonido):
    if sonido is not None:
        sonido.play()


# --- Utilidades de dibujo ---
def crear_texto(pantalla, fuente, texto, color, x, y, centrado=False):
    superficie = fuente.render(texto, True, color)
    rect = superficie.get_rect()
    if centrado:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    pantalla.blit(superficie, rect)
    return rect


def ip_local():
    """Devuelve la IP local con la que esta máquina es accesible en la red."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


# --- Red: mensajes JSON delimitados por salto de línea ---
class Conexion:
    """Envía/recibe objetos JSON por un socket, con un hilo lector en segundo plano."""

    def __init__(self, sock):
        self.sock = sock
        self.buffer = b""
        self.cerrada = False
        self._lock = threading.Lock()
        self.bandeja = queue.Queue()
        self._hilo = threading.Thread(target=self._leer, daemon=True)
        self._hilo.start()

    def _leer(self):
        while not self.cerrada:
            try:
                trozo = self.sock.recv(4096)
            except OSError:
                break
            if not trozo:
                break
            self.buffer += trozo
            while b"\n" in self.buffer:
                linea, self.buffer = self.buffer.split(b"\n", 1)
                try:
                    self.bandeja.put(json.loads(linea.decode("utf-8")))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        self.cerrada = True

    def enviar(self, obj):
        try:
            datos = (json.dumps(obj) + "\n").encode("utf-8")
            with self._lock:
                self.sock.sendall(datos)
            return True
        except OSError:
            self.cerrada = True
            return False

    def recibir(self):
        """Devuelve el siguiente mensaje disponible o None."""
        try:
            return self.bandeja.get_nowait()
        except queue.Empty:
            return None

    def cerrar(self):
        self.cerrada = True
        try:
            self.sock.close()
        except OSError:
            pass


class ServidorAnfitrion:
    """Escucha en el puerto y acepta un único cliente."""

    def __init__(self, puerto):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", puerto))
        self.sock.listen(1)
        self.sock.settimeout(0.5)
        self.cliente = None

    def comprobar_cliente(self):
        """Intenta aceptar al cliente; devuelve la conexión o None."""
        if self.cliente is not None:
            return self.cliente
        try:
            sock, _ = self.sock.accept()
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
            self.cliente = Conexion(sock)
            return self.cliente
        except socket.timeout:
            return None
        except OSError:
            return None

    def cerrar(self):
        if self.cliente is not None:
            self.cliente.cerrar()
        try:
            self.sock.close()
        except OSError:
            pass


def conectar_a(host, puerto, espera=6):
    """Conecta con el anfitrión y devuelve la conexión."""
    sock = socket.create_connection((host, puerto), timeout=espera)
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass
    sock.settimeout(None)  # el hilo lector se bloquea en recv
    return Conexion(sock)


# --- Simulación del juego (usada por un jugador y por el anfitrión) ---
class Jugador:
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

    def paso(self, dt, entradas, ahora, pantalla, sonido_disparo, sonido_explosion):
        """Avanza la simulación. 'entradas' es una lista por jugador con
        las claves 'izq', 'der' y 'disparar' (True/False)."""
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
                if ahora - getattr(self, "_ultimo_sonido_disparo", 0) >= INTERVALO_SONIDO_DISPARO:
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
        for jugador in self.jugadores:
            pygame.draw.rect(pantalla, jugador.color, jugador.rect)
        for d in self.disparos:
            pygame.draw.rect(pantalla, self.jugadores[d["duenio"]].color_disparo, d["rect"])
        for e in self.enemigos:
            pygame.draw.circle(pantalla, COLOR_ENEMIGO, e["rect"].center, RADIO_ENEMIGO)


# --- Pantallas de dibujo del estado (para el cliente) ---
def dibujar_estado(pantalla, estado, indice_propio, mi_x_predicho):
    """Dibuja el estado recibido del anfitrión en el cliente."""
    # Jugadores
    for j in estado.get("jugadores", []):
        color = COLOR_JUGADOR_1 if j["indice"] == 0 else COLOR_JUGADOR_2
        x = j["x"]
        if j["indice"] == indice_propio and mi_x_predicho is not None:
            x = mi_x_predicho   # predicción local para que el movimiento sea fluido
        pygame.draw.rect(pantalla, color, pygame.Rect(x, j["y"], TAM_JUGADOR, TAM_JUGADOR))

    # Disparos
    for d in estado.get("disparos", []):
        color = COLOR_DISPARO_1 if d["duenio"] == 0 else COLOR_DISPARO_2
        pygame.draw.rect(pantalla, color, pygame.Rect(d["x"], d["y"], ANCHO_DISPARO, ALTO_DISPARO))

    # Enemigos
    for e in estado.get("enemigos", []):
        pygame.draw.circle(pantalla, COLOR_ENEMIGO, (e["x"], e["y"]), RADIO_ENEMIGO)


def puntuaciones(estado):
    puntos = [0, 0]
    for j in estado.get("jugadores", []):
        puntos[j["indice"]] = j["puntos"]
    return puntos


def dibujar_marcador(pantalla, fuente, puntos, dos_jugadores):
    crear_texto(pantalla, fuente, f"J1: {puntos[0]}", COLOR_TEXTO, 12, 10)
    if dos_jugadores:
        texto = f"J2: {puntos[1]}"
        superficie = fuente.render(texto, True, COLOR_TEXTO)
        pantalla.blit(superficie, (ANCHO - superficie.get_width() - 12, 10))


def pantalla_game_over(pantalla, fuente, fuente_grande, puntos, dos_jugadores, anfitrin):
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


# --- Bucles de juego ---
def leer_entradas():
    teclas = pygame.key.get_pressed()
    return {
        "izq": teclas[pygame.K_LEFT] or teclas[pygame.K_a],
        "der": teclas[pygame.K_RIGHT] or teclas[pygame.K_d],
        "disparar": teclas[pygame.K_SPACE],
    }


def bucle_un_jugador(pantalla, fuentes, sonidos):
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
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r and mundo is not None and mundo.perdido:
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
            # No enviamos nada más; la conexión se cierra al salir
    finally:
        conexion.cerrar()


def esperar_tecla():
    """Pulsa cualquier tecla para continuar."""
    esperando = True
    while esperando:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                esperando = False
            elif ev.type == pygame.KEYDOWN:
                esperando = False
        pygame.time.wait(30)


# --- Menús ---
def menu_principal(pantalla, fuente, fuente_grande):
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
    """Pide la IP del anfitrión con un campo de texto."""
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


def main():
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


if __name__ == "__main__":
    main()
