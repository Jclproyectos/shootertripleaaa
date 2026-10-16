# Juego de disparos 2D

Juego de disparos en 2D hecho en Python con Pygame, usando únicamente figuras
geométricas simples (rectángulos y círculos).

## Instalación

```powershell
python -m pip install -r requirements.txt
```

## Cómo jugar

```powershell
python juego_disparos.py
```

| Tecla | Acción |
|---|---|
| ← / → (o A / D) | Mover al jugador |
| Barra espaciadora | Disparar (mantener = spammear sin límite) |
| R | Reiniciar tras el game over |
| Esc | Salir |

## Reglas

- El jugador es un **cuadrado** verde en la parte inferior que dispara rectángulos amarillos hacia arriba.
- Los **círculos rojos** enemigos caen desde la parte superior.
- Cada disparo que acierta a un enemigo lo elimina y suma **10 puntos**.
- Si un enemigo toca el fondo, pierdes la partida.

## Características

- Disparo continuo sin límite de balas ni enfriamiento.
- Sonidos de disparo y explosión **generados proceduralmente en memoria** (sin archivos externos ni numpy).
- Movimiento independiente del framerate (60 FPS, ventana 600×800).
- Pantalla de game over con puntuación final y reinicio inmediato.

## Requisitos

- Python 3.14+
- `pygame-ce` (ver `requirements.txt`)
