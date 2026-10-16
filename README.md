# Juego de disparos 2D

Juego de disparos en 2D hecho en Python con Pygame, usando únicamente figuras
geométricas simples (rectángulos y círculos). Incluye modo **un jugador** y
**multijugador cooperativo en línea** para 2 jugadores.

## Instalación

```powershell
python -m pip install -r requirements.txt
```

## Cómo jugar

```powershell
python juego_disparos.py
```

Al arrancar aparece un menú:

| Opción | Modo |
|---|---|
| `1` | Un jugador |
| `2` | Anfitrión (crear partida en línea) |
| `3` | Unirse por IP |

### Controles

| Tecla | Acción |
|---|---|
| ← / → (o A / D) | Mover al jugador |
| Barra espaciadora | Disparar (mantener = spammear sin límite) |
| R | Reiniciar tras el game over (sólo el anfitrión en multijugador) |
| Esc | Salir / volver al menú |

## Multijugador en línea (cooperativo)

1. El **anfitrión** pulsa `2`. En pantalla aparece su **IP local**; compártela.
2. El **segundo jugador** en su PC pulsa `3`, escribe esa IP y pulsa Enter.
3. Ambos juegan contra los mismos enemigos y suman puntos por separado (J1 a la izquierda, J2 a la derecha).

Detalles:
- **Modelo anfitrión/unirse por IP**, sin servidor dedicado. El anfitrión mantiene la simulación autoritativa.
- Comunicación por **TCP** con mensajes JSON usando sólo la librería estándar (sin dependencias nuevas).
- Puerto por defecto `5555` (constante `PUERTO` en el script). Para jugar por internet, reenvía ese puerto en el router del anfitrión o usa una VPN/RED LAN.

## Reglas

- Cada jugador es un **cuadrado** (J1 verde, J2 azul) que dispara rectángulos hacia arriba.
- Los **círculos rojos** enemigos caen desde la parte superior.
- Cada disparo que acierta a un enemigo lo elimina y suma **10 puntos** a su dueño.
- Si un enemigo toca el fondo, pierden ambos (game over).

## Características

- Disparo continuo sin límite de balas ni enfriamiento.
- Sonidos de disparo y explosión **generados proceduralmente en memoria** (sin archivos externos ni numpy).
- Movimiento independiente del framerate (60 FPS, ventana 600×800).
- Pantalla de game over con puntuaciones y reinicio inmediato.
- Multijugador cooperativo con predicción local para movimiento fluido.

## Requisitos

- Python 3.14+
- `pygame-ce` (ver `requirements.txt`)

## Estructura del código

El juego está modularizado en el paquete `shooter/`:

| Módulo | Responsabilidad |
|---|---|
| `shooter/config.py` | Constantes y ajustes (pantalla, colores, velocidades, red) |
| `shooter/sonidos.py` | Generación procedural de sonidos (sin archivos externos) |
| `shooter/red.py` | Comunicación TCP + JSON para el multijugador |
| `shooter/mundo.py` | Simulación (jugadores, disparos, enemigos, colisiones) |
| `shooter/interfaz.py` | Dibujado, menús y pantallas |
| `shooter/bucles.py` | Bucles de juego (un jugador, anfitrión, cliente) |
| `shooter/app.py` | Punto de entrada: inicializa Pygame y gestiona los menús |
| `juego_disparos.py` | Lanzador fino (delega en `shooter.app.main`) |

Para cambiar el comportamiento (velocidades, puerto, colores, etc.) basta con
editar `shooter/config.py`.

También se puede ejecutar directamente con:

```powershell
python -m shooter
```
