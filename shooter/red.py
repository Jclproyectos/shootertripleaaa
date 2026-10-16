"""Comunicación de red para el multijugador.

Implementa un cliente/servidor TCP con mensajes JSON delimitados por
salto de línea, usando únicamente la librería estándar (socket,
threading, json, queue). No requiere dependencias externas.
"""

import json
import queue
import socket
import threading


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
        """Envía un objeto JSON; devuelve False si la conexión falló."""
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
