import json
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


def _pagina_sintetica(indice: int, n_widgets: int = 2) -> dict:
    return {
        "id": f"pagina-{indice}",
        "name": f"New-page-{indice}",
        "backgroundImage": f"r-{indice}-0.png",
        "backgroundColor": "#FFFFFF",
        "canvasList": [
            {
                "id": f"canvas-{indice}",
                "name": "canvas",
                "subCanvasList": [
                    {
                        "id": f"sub-{indice}",
                        "name": "sub",
                        "backgroundImage": "",
                        "widgetList": [
                            {"id": f"w-{indice}-{k}", "type": "MyTextInput"}
                            for k in range(n_widgets)
                        ],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def projeto_sintetico(tmp_path):
    """Um file.zip com a forma do projeto AHMI, sem um byte da Positivo (D15).

    Reproduz pageList[10] -> canvasList -> subCanvasList -> widgetList, os 3 gifs
    de origem e um fundo por página. É o suficiente para exercitar projeto.py.
    """
    import zipfile

    from PIL import Image

    origem = tmp_path / "fonte"
    origem.mkdir()

    dados = {
        "author": "teste",
        "CANId": 0,
        "pageList": [_pagina_sintetica(i) for i in range(10)],
        "resourceList": [],
        "tagList": [],
    }
    (origem / "data.json").write_text(json.dumps(dados))

    for nome in ("1i1h1e37393671471.gif", "1h1k1e37393671464.gif", "1h1m1e37393671466.gif"):
        Image.new("P", (192, 192), 0).save(origem / nome)
    for i in range(10):
        Image.new("RGBA", (240, 240), (245, 245, 248, 255)).save(origem / f"r-{i}-0.png")

    caminho_zip = tmp_path / "file.zip"
    with zipfile.ZipFile(caminho_zip, "w") as z:
        for f in sorted(origem.iterdir()):
            z.write(f, f.name)
    return caminho_zip
