import os
import socket

import pytest

from minitela.core.transporte import PortaSerial


class MinitelaFalsa:
    """Um socketpair fingindo de /dev/ttyACM0.

    Bidirecional num só fd, como a porta real. O que a porta escreve aparece em
    `recebido_pelo_mcu()`; o que `responder()` manda volta no `ler()` da porta.
    Sem hardware, sem root.
    """

    def __init__(self):
        self._host, self._mcu = socket.socketpair()
        self._host.setblocking(False)
        self._mcu.setblocking(False)
        self.porta = PortaSerial(fd=self._host.fileno())

    def recebido_pelo_mcu(self, n: int = 4096) -> bytes:
        try:
            return self._mcu.recv(n)
        except BlockingIOError:
            return b""

    def responder(self, dados: bytes) -> None:
        self._mcu.sendall(dados)

    def fechar(self) -> None:
        self._host.close()
        self._mcu.close()


@pytest.fixture
def minitela_falsa():
    m = MinitelaFalsa()
    yield m
    m.fechar()
