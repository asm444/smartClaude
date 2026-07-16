"""Telas de dashboard: rótulo no topo, porcentagem grande, barra embaixo."""

from PIL import Image, ImageDraw

from .comum import (
    FUNDO_CLARO,
    TAMANHO,
    TEXTO_ESCURO,
    carregar_fonte,
    cor_por_pct,
)

_APAGADO = (120, 120, 132)
_TRILHO = (222, 222, 228)

_Y_ROTULO = 30
_Y_PCT = 112
_Y_LEGENDA = 168
_BARRA = (24, 196, TAMANHO - 48, 20)


def render_tela(rotulo: str, pct: float) -> Image.Image:
    img = Image.new("RGB", (TAMANHO, TAMANHO), FUNDO_CLARO)
    d = ImageDraw.Draw(img)
    cor = cor_por_pct(pct)

    d.text((TAMANHO // 2, _Y_ROTULO), rotulo, font=carregar_fonte(26),
           fill=TEXTO_ESCURO, anchor="mm")
    d.text((TAMANHO // 2, _Y_PCT), f"{pct:.0f}%", font=carregar_fonte(88),
           fill=cor, anchor="mm")
    d.text((TAMANHO // 2, _Y_LEGENDA), "usado", font=carregar_fonte(15),
           fill=_APAGADO, anchor="mm")

    x, y, largura, altura = _BARRA
    d.rounded_rectangle([x, y, x + largura, y + altura], radius=altura // 2,
                        fill=_TRILHO)
    preenchido = max(int(largura * min(pct, 100) / 100), altura)
    d.rounded_rectangle([x, y, x + preenchido, y + altura], radius=altura // 2,
                        fill=cor)
    return img
