# Contexto del proyecto — Juego de disparos 2D (Pygame)

Última actualización: 2026-10-15

## Objetivo
Juego de disparos en 2D en Python con Pygame, usando únicamente figuras
geométricas simples (rectángulos y círculos). Incluye modo un jugador y
**multijugador cooperativo en línea** (2 jugadores).

## Reglas del juego
- Cada jugador controla un **cuadrado** en la parte inferior que se mueve horizontalmente y **dispara rectángulos** hacia arriba con la barra espaciadora.
- El disparo **no tiene límite ni enfriamiento**: mantén pulsado el espacio para spammear (un disparo por frame).
- **Círculos enemigos** caen desde la parte superior con velocidad aleatoria.
- Un disparo que colisiona con un enemigo lo elimina y suma **10 puntos** al jugador que disparó.
- **Condición de derrota**: si un enemigo toca el fondo, aparece la pantalla de GAME OVER; en multijugador, sólo el anfitrión puede reiniciar con R.
- La puntuación se muestra arriba (J1 a la izquierda, J2 a la derecha en multijugador).

## Controles
| Tecla | Acción |
|---|---|
| ← / → (o A / D) | Mover al jugador |
| Barra espaciadora | Disparar (mantener = spammear sin límite) |
| R | Reiniciar tras el game over (sólo el anfitrión en multijugador) |
| Esc | Salir / volver al menú |

## Multijugador cooperativo en línea
- **Modelo anfitrión/unirse por IP**: sin servidor dedicado. El anfitrión abre el puerto TCP y espera; el segundo jugador se une escribiendo la IP del anfitrión.
- **Cooperativo**: ambos jugadores comparten los mismos enemigos y suman puntos por separado.
- **Autoridad del anfitrión**: el anfitrión ejecuta la simulación completa; el cliente envía sus entradas y dibuja el estado recibido. Evita desfases y trampas.
- **Protocolo**: TCP con mensajes JSON delimitados por `\n`, usando sólo la librería estándar (`socket`, `threading`, `json`, `queue`). Sin dependencias nuevas.
- Mensajes: `bienvenida` (índice de jugador), `entrada` (teclas del cliente), `estado` (jugadores, disparos, enemigos, perdido).
- **Baja latencia**: se usa `TCP_NODELAY`, el cliente envía entradas ~30 veces/s y el anfitrión difunde estado a ~60 Hz.
- **Predicción local**: el cliente predice la posición de su propio cuadrado para que el movimiento sea fluido y se reajusta si se desincroniza más de 90 px.
- El anfitrión muestra su **IP local** en pantalla para que el otro jugador sepa a dónde conectarse (por defecto puerto 5555).

## Archivos del proyecto
| Archivo | Descripción |
|---|---|
| `juego_disparos.py` | Script único con todo el juego (~733 líneas): menú, un jugador, anfitrión, cliente y red |
| `requirements.txt` | Dependencias (`pygame-ce>=2.5.8`) |
| `context.md` | Este archivo: registro de avances y decisiones |
| `README.md` | Instrucciones de instalación y uso |
| `.gitignore` | Excluye `__pycache__`, venvs y archivos de sistema |

## Cómo ejecutarlo
```powershell
python -m pip install -r requirements.txt
python juego_disparos.py
```
En el menú: `1` un jugador, `2` anfitrión (crear partida), `3` unirse por IP.

## Detalles técnicos
- Ventana 600×800, 60 FPS, movimiento independiente del framerate mediante `dt`.
- Constantes de configuración agrupadas al inicio del script.
- Colisiones con `rect.colliderect()`; el jugador se mantiene en pantalla con `rect.clamp_ip()`.
- **Sonidos generados en memoria** al arrancar (sin archivos externos, para mantener el juego en un único script):
  - Disparo: barrido de tono descendente de 880 Hz a 220 Hz con envolvente cuadrática (0.12 s).
  - Explosión: ruido aleatorio + tono grave descendente con envolvente exponencial (0.45 s).
  - Se construyen con `struct.pack` como buffer PCM 16 bits mono a 22050 Hz y se crean con `pygame.mixer.Sound(buffer=...)`, sin depender de numpy.
  - El sonido del disparo se limita a 1 cada 70 ms para no saturar la tarjeta de audio (las balas sí son ilimitadas).
- Si el audio no está disponible (`pygame.mixer.init` falla), el juego avisa por consola y continúa sin sonido.
- La simulación está encapsulada en la clase `Mundo` (jugadores, disparos, enemigos) y se reutiliza en un jugador y en el anfitrión.
- La red se encapsula en `Conexion` (hilo lector + cola) y `ServidorAnfitrion` (acepta un cliente).

## Ideas que se completaron
- ~~Sonidos (disparo, impacto)~~ — Hecho: generados proceduralmente en el propio script.
- ~~Pantalla de game over~~ — Hecho: un enemigo que toca el fondo termina la partida; R reinicia.
- ~~Multijugador en línea~~ — Hecho: cooperativo, 2 jugadores, anfitrión/unirse por IP.

## Ideas futuras (pendientes)
- Vidas en lugar de una sola oportunidad.
- Aumento progresivo de la dificultad (más enemigos o mayor velocidad).
- Explosión visual (partículas) al destruir enemigos.
- Puntuación máxima (récord) guardada en un archivo.
- Soporte para más de 2 jugadores y chat.
- Partida pública con lista de salas (requiere servidor dedicado).

## Decisiones importantes
- **`pygame-ce` en lugar de `pygame`**: el entorno usa Python 3.14.2, para el cual el paquete `pygame` clásico (2.6.1) no ofrece rueda precompilada e intenta compilarse desde el código fuente, fallando con `ModuleNotFoundError: No module named 'distutils.msvccompiler'`. `pygame-ce` 2.5.8 sí tiene rueda para cp314 y se importa igual (`import pygame`), por lo que el código no requiere cambios.
- **Autoridad del anfitrión** en el multijugador: una sola máquina (el anfitrión) simula el mundo y difunde el estado. Es más sencillo y robusto que sincronizar dos simulaciones, e impide que el cliente manipule la puntuación.
- **TCP con JSON delimitado por `\n`** en vez de UDP: para 2 jugadores y este ritmo de mensajes, la fiabilidad de TCP simplifica el manejo de mensajes parciales y no perjudica el rendimiento (con `TCP_NODELAY` la latencia es mínima en LAN).
- **Sin servidor dedicado**: se optó por el modelo anfitrión/unirse por IP porque no hay infraestructura de servidor; funciona en red local y en internet reenviando el puerto.

## Historial de cambios
- **2026-10-15** — Se creó `juego_disparos.py` con el juego completo (jugador, disparos, enemigos, colisiones y puntuación).
- **2026-10-15** — Instalación de `pygame-ce 2.5.8` tras fallar `pygame` clásico con Python 3.14; se verificó la importación (`pygame-ce 2.5.8 (SDL 2.32.10, Python 3.14.2)`).
- **2026-10-15** — Se creó `requirements.txt` y se comprobó con `pip install -r requirements.txt`.
- **2026-10-15** — Se creó `context.md` como registro de avances del proyecto.
- **2026-10-15** — Se añadió:
  - **Forma de perder**: si un enemigo toca el fondo aparece GAME OVER (fondo atenuado, puntuación final) y se reinicia con R.
  - **Disparo sin límite**: se eliminó el enfriamiento de disparo; mantener el espacio dispara un proyectil por frame.
  - **Sonidos de disparo y explosión** generados proceduralmente en memoria (barrido descendente y ruido con envolvente), sin archivos externos ni numpy.
  - Prueba automática con drivers ficticios (dummy) que valida arranque, game over, sonido de explosión y reinicio con R: **PRUEBA OK**.
- **2026-10-15** — Se creó el repositorio de GitHub `Jclproyectos/shootertripleaaa` (público): `git init`, rama `main`, `.gitignore`, `README.md` y commit inicial `b43c9cd`; push realizado con éxito.
- **2026-10-15** — Se añadió **multijugador cooperativo en línea** (2 jugadores, anfitrión/unirse por IP):
  - Clases de red `Conexion` y `ServidorAnfitrion`; protocolo TCP + JSON con delimitador `\n`; `TCP_NODELAY`.
  - Menú principal con tres modos (un jugador / anfitrión / unirse por IP) y pantalla de campo de texto para la IP.
  - Clase `Mundo` que encapsula la simulación, reutilizada por un jugador y por el anfitrión.
  - El anfitrión muestra su IP local; autoridad del anfitrión con predicción local en el cliente.
  - Marcador dual (J1/J2) y colores diferenciados por jugador y por dueño de cada disparo.
  - Pruebas automáticas (drivers dummy) que validan: capa de red (bienvenida, entradas cliente→servidor, estado servidor→cliente), simulación (colisión +10, enemigo eliminado, game over, serialización), modo un jugador, e **integración anfitrión-cliente real** (cliente conecta, recibe bienvenida con índice 1, 146 estados con 2 jugadores y envía entradas): **TODAS LAS PRUEBAS PASARON**.
