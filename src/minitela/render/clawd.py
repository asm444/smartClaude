"""Composição do mascote Clawd. Pillow puro: sem subprocess, sem ImageMagick.

O clawd.svg é rasterizado na vendorização (sprites/clawd-160.png), não aqui —
assim o render não depende de ferramenta externa nem do widget instalado.
"""

import os
from pathlib import Path

from PIL import Image

from .comum import FUNDO_CLARO, TAMANHO

FRAMES_POR_ESTADO = 6
_TAM_OVERLAY = 200
_DESLOCAMENTO_CLAWD_Y = 20
_DESLOCAMENTO_OVERLAY_Y = -10

# estado -> (prefixo do overlay, a caveira substitui o Clawd?)
ESTADOS = {
    "genius": ("halo", False),
    "smart": ("smart", False),
    "slow": ("rain", False),
    "dumb": ("fire", False),
    "braindead": ("skull", True),
}

# nomes que o daemon usa -> estado do sprite
APELIDOS = {
    "fogo": "dumb",
    "chuva": "slow",
    "fantasminha": "braindead",
}


class SpriteAusente(FileNotFoundError):
    pass


def dir_sprites() -> Path:
    return Path(os.environ.get("MINITELA_SPRITES", Path(__file__).parent / "sprites"))


def _abrir(nome: str) -> Image.Image:
    caminho = dir_sprites() / nome
    if not caminho.exists():
        raise SpriteAusente(f"sprite não encontrado: {caminho}")
    return Image.open(caminho).convert("RGBA")


def resolver_estado(nome: str) -> str:
    estado = APELIDOS.get(nome, nome)
    if estado not in ESTADOS:
        raise ValueError(f"estado desconhecido: {nome!r} (conhecidos: {sorted(ESTADOS)})")
    return estado


def compor(nome_estado: str, frame: int = 0) -> Image.Image:
    """Uma tela 240x240: fundo claro + Clawd + overlay do estado."""
    estado = resolver_estado(nome_estado)
    prefixo, esconde_clawd = ESTADOS[estado]

    tela = Image.new("RGBA", (TAMANHO, TAMANHO), FUNDO_CLARO + (255,))

    if not esconde_clawd:
        clawd = _abrir("clawd-160.png")
        largura, altura = clawd.size
        tela.alpha_composite(
            clawd,
            ((TAMANHO - largura) // 2, (TAMANHO - altura) // 2 + _DESLOCAMENTO_CLAWD_Y),
        )

    overlay = _abrir(f"{prefixo}-{frame % FRAMES_POR_ESTADO}.png").resize(
        (_TAM_OVERLAY, _TAM_OVERLAY), Image.NEAREST
    )
    tela.alpha_composite(
        overlay,
        (
            (TAMANHO - _TAM_OVERLAY) // 2,
            (TAMANHO - _TAM_OVERLAY) // 2 + _DESLOCAMENTO_OVERLAY_Y,
        ),
    )
    return tela.convert("RGB")


def compor_frames(nome_estado: str) -> list[Image.Image]:
    return [compor(nome_estado, f) for f in range(FRAMES_POR_ESTADO)]
