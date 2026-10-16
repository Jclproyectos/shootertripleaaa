# Contexto del proyecto — Juego de disparos 2D (Pygame)

Última actualización: 2026-10-15

## Objetivo
Juego de disparos en 2D en Python con Pygame, usando únicamente figuras
geométricas simples (rectángulos y círculos), contenido en un único script.

## Reglas del juego
- El jugador controla un **cuadrado** en la parte inferior que se mueve horizontalmente y **dispara rectángulos** hacia arriba con la barra espaciadora.
- El disparo **no tiene límite ni enfriamiento**: mantén pulsado el espacio para spammear (un disparo por frame).
- **Círculos enemigos** caen desde la parte superior con velocidad aleatoria.
- Un disparo que colisiona con un enemigo lo elimina y suma **10 puntos**.
- **Condición de derrota**: si un enemigo toca el fondo, aparece la pantalla de GAME OVER con la puntuación final y se puede reiniciar con R.
- La puntuación se muestra en la **esquina superior izquierda**.

## Controles
| Tecla | Acción |
|---|---|
| ← / → (o A / D) | Mover al jugador |
| Barra espaciadora | Disparar (mantener = spammear sin límite) |
| R | Reiniciar tras el game over |
| Esc | Salir |

## Archivos del proyecto
| Archivo | Descripción |
|---|---|
| `juego_disparos.py` | Script único con todo el juego (~276 líneas) |
| `requirements.txt` | Dependencias (`pygame-ce>=2.5.8`) |
| `context.md` | Este archivo: registro de avances y decisiones |

## Cómo ejecutarlo
```powershell
python -m pip install -r requirements.txt
python juego_disparos.py
```

## Detalles técnicos
- Ventana 600×800, 60 FPS, movimiento independiente del framerate mediante `dt`.
- Constantes de configuración agrupadas al inicio del script (velocidades, tamaños, intervalos).
- Colisiones con `rect.colliderect()`.
- El jugador se mantiene dentro de la pantalla con `rect.clamp_ip()`.
- **Sonidos generados en memoria** al arrancar (sin archivos externos, para mantener el juego en un único script):
  - Disparo: barrido de tono descendente de 880 Hz a 220 Hz con envolvente cuadrática (0.12 s).
  - Explosión: ruido aleatorio + tono grave descendente con envolvente exponencial (0.45 s).
  - Se construyen con `struct.pack` como buffer PCM 16 bits mono a 22050 Hz y se crean con `pygame.mixer.Sound(buffer=...)`, sin depender de numpy.
  - El sonido del disparo se limita a 1 cada 70 ms para no saturar la tarjeta de audio (las balas sí son ilimitadas).
- Si el audio no está disponible (`pygame.mixer.init` falla), el juego avisa por consola y continúa sin sonido.
- La partida tiene estado en un diccionario con una función `reiniciar()`, lo que permite el reinicio con R sin recargar el proceso.

## Ideas que se completaron
- ~~Sonidos (disparo, impacto)~~ — Hecho: generados proceduralmente en el propio script.
- ~~Pantalla de game over~~ — Hecho: un enemigo que toca el fondo termina la partida; R reinicia.

## Ideas futuras (pendientes)
- Vidas en lugar de una sola oportunidad.
- Aumento progresivo de la dificultad (más enemigos o mayor velocidad).
- Explosión visual (partículas) al destruir enemigos.
- Puntuación máxima (récord) guardada en un archivo.

## Decisiones importantes
- **`pygame-ce` en lugar de `pygame`**: el entorno usa Python 3.14.2, para el cual el paquete `pygame` clásico (2.6.1) no ofrece rueda precompilada e intenta compilarse desde el código fuente, fallando con `ModuleNotFoundError: No module named 'distutils.msvccompiler'`. `pygame-ce` 2.5.8 sí tiene rueda para cp314 y se importa igual (`import pygame`), por lo que el código no requiere cambios.

## Historial de cambios
- **2026-10-15** — Se creó `juego_disparos.py` con el juego completo (jugador, disparos, enemigos, colisiones y puntuación).
- **2026-10-15** — Instalación de `pygame-ce 2.5.8` tras fallar `pygame` clásico con Python 3.14; se verificó la importación (`pygame-ce 2.5.8 (SDL 2.32.10, Python 3.14.2)`).
- **2026-10-15** — Se creó `requirements.txt` y se comprobó con `pip install -r requirements.txt`.
- **2026-10-15** — Se creó `context.md` como registro de avances del proyecto.
- **2026-10-15** — Se añadió:
  - **Forma de perder**: si un enemigo toca el fondo aparece GAME OVER (fondo atenuado, puntuación final) y se reinicia con R.
  - **Disparo sin límite**: se eliminó el enfriamiento de disparo; mantener el espacio dispara un proyectil por frame.
  - **Sonidos de disparo y explosión** generados proceduralmente en memoria (barrido descendente y ruido con envolvente), sin archivos externos ni numpy.
  - El estado de la partida se movió a un diccionario con función `reiniciar()`.
  - Prueba automática con drivers ficticios (dummy) que valida arranque, game over, sonido de explosión y reinicio con R: **PRUEBA OK**.
