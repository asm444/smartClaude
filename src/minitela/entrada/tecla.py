"""Leitura da tecla física "Minitela" direto do /dev/input/event*.

Sem evdev: o formato do input_event é struct estável do kernel.
No hardware real a tecla é KEY_F16 (186) — o app oficial usava KEY_PROG1 (148),
que não é o que chega no Fedora/KDE. Ver docs/06-runbook-dashboard.md.
"""

import glob
import os
import select
import struct
import time
from collections.abc import Iterator

KEY_MINITELA = 186
DEV_FALLBACK = "/dev/input/event3"

EV_FORMAT = "llHHi"
EV_SIZE = struct.calcsize(EV_FORMAT)
EV_KEY = 0x01
VALOR_PRESSIONADA = 1

_BITS_POR_PALAVRA = 64


class SemPermissao(PermissionError):
    """Falta root para ler o /dev/input/event*."""


def _emite_tecla(nome_event: str, keycode: int) -> bool:
    palavra, bit = divmod(keycode, _BITS_POR_PALAVRA)
    caminho = f"/sys/class/input/{nome_event}/device/capabilities/key"
    try:
        with open(caminho) as f:
            # hex, da palavra mais significativa para a menos
            palavras = f.read().split()[::-1]
    except OSError:
        return False
    if palavra >= len(palavras):
        return False
    try:
        return bool((int(palavras[palavra], 16) >> bit) & 1)
    except ValueError:
        return False


def encontrar_teclado(keycode: int = KEY_MINITELA) -> str:
    """O primeiro event* capaz de emitir a tecla. Fallback: event3."""
    for caminho in sorted(glob.glob("/dev/input/event*")):
        if _emite_tecla(os.path.basename(caminho), keycode):
            return caminho
    return DEV_FALLBACK


def abrir_teclado(dev: str | None = None, tentativas: int = 30, espera: float = 2.0):
    """Abre o device, esperando ele aparecer (boot/replug).

    Sem permissão falha na hora — ficar em loop silencioso esconde o problema.
    """
    for tentativa in range(tentativas):
        caminho = dev or encontrar_teclado()
        try:
            return caminho, open(caminho, "rb")
        except PermissionError as erro:
            raise SemPermissao(
                f"sem permissão para ler {caminho} — rode como root"
            ) from erro
        except FileNotFoundError:
            if tentativa == tentativas - 1:
                raise
            time.sleep(espera)
    raise FileNotFoundError("device da tecla não apareceu")


def eventos(arquivo, keycode: int = KEY_MINITELA) -> Iterator[int]:
    """Cada toque (press) da tecla vira um item. Não bloqueia."""
    while True:
        dados = arquivo.read(EV_SIZE)
        if not dados or len(dados) < EV_SIZE:
            return
        _, _, tipo, code, valor = struct.unpack(EV_FORMAT, dados)
        if tipo == EV_KEY and code == keycode and valor == VALOR_PRESSIONADA:
            yield code


def qualquer_tecla(arquivo) -> Iterator[int]:
    """Todo keycode pressionado — para descobrir qual é a tecla."""
    while True:
        dados = arquivo.read(EV_SIZE)
        if not dados or len(dados) < EV_SIZE:
            return
        _, _, tipo, code, valor = struct.unpack(EV_FORMAT, dados)
        if tipo == EV_KEY and valor == VALOR_PRESSIONADA:
            yield code


class Teclado:
    """A tecla física como recurso: abre, espera toque, fecha."""

    def __init__(self, dev: str | None = None, keycode: int = KEY_MINITELA):
        self.keycode = keycode
        self.caminho, self._arquivo = abrir_teclado(dev)
        os.set_blocking(self._arquivo.fileno(), False)

    def fileno(self) -> int:
        return self._arquivo.fileno()

    def toques(self) -> Iterator[int]:
        yield from eventos(self._arquivo, self.keycode)

    def esperar_toque(self, timeout: float | None = None) -> bool:
        pronto, _, _ = select.select([self._arquivo], [], [], timeout)
        if not pronto:
            return False
        return any(True for _ in self.toques())

    def fechar(self) -> None:
        self._arquivo.close()

    def __enter__(self) -> "Teclado":
        return self

    def __exit__(self, *a) -> None:
        self.fechar()
