"""Fronteira de I/O com a porta serial. Único lugar que fala com o fd."""

import fcntl
import os
import select
import struct
import termios
import time

from .protocolo import eh_frame_completo

DEVICE_PADRAO = "/dev/ttyACM0"

_TIOCOUTQ = 0x5411
_TAM_LEITURA = 256
_ESPERA_SELECT = 0.2


class PortaSerial:
    """Abre o /dev/ttyACM* em modo cru e não-bloqueante.

    Aceita um fd pronto (para teste); nesse caso não configura termios nem fecha
    o descritor — quem o criou é o dono.
    """

    def __init__(self, device: str = DEVICE_PADRAO, fd: int | None = None):
        self.device = device
        self.fd = fd
        self._fd_externo = fd is not None

    def abrir(self) -> "PortaSerial":
        if self._fd_externo:
            return self
        self.fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self._configurar_termios()
        return self

    def _configurar_termios(self) -> None:
        attrs = termios.tcgetattr(self.fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        try:
            attrs[4] = termios.B115200
            attrs[5] = termios.B115200
        except Exception:
            pass
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def fechar(self) -> None:
        if self.fd is None or self._fd_externo:
            return
        try:
            termios.tcflush(self.fd, termios.TCIOFLUSH)
            fcntl.fcntl(self.fd, fcntl.F_SETFL, os.O_RDWR | os.O_NONBLOCK)
        except Exception:
            pass
        os.close(self.fd)
        self.fd = None

    def __enter__(self) -> "PortaSerial":
        return self.abrir()

    def __exit__(self, *a) -> None:
        self.fechar()

    def escrever(self, frame: bytes) -> None:
        os.write(self.fd, frame)

    def ler(self, timeout: float = 1.5) -> bytes:
        buf = b""
        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            pronto, _, _ = select.select([self.fd], [], [], _ESPERA_SELECT)
            if not pronto:
                continue
            try:
                pedaco = os.read(self.fd, _TAM_LEITURA)
            except BlockingIOError:
                continue
            if pedaco:
                buf += pedaco
                if eh_frame_completo(buf):
                    break
        return buf

    def fila_saida(self) -> int:
        """Bytes ainda não drenados pelo MCU (TIOCOUTQ)."""
        empacotado = fcntl.ioctl(self.fd, _TIOCOUTQ, struct.pack("I", 0))
        return struct.unpack("I", empacotado)[0]

    def descartar_buffers(self) -> None:
        termios.tcflush(self.fd, termios.TCIOFLUSH)
