#!/usr/bin/env python3
"""
Renderiza 3 telas 240x240 (fundo CLARO — o compilador AHMI corrompe tons escuros)
para a Minitela, uma por métrica de uso do Claude:
  tela 0 = Semanal, tela 1 = Sessão atual, tela 2 = Fable.
Cada tela: label da métrica + % grande + barra de progresso.

Uso: python3 render_telas.py <dir_saida>
Gera <dir>/tela-semana.png, <dir>/tela-sessao.png, <dir>/tela-fable.png
Fundo claro porque o AHMISimGenDemo converte cores quase-pretas para branco/lavado;
telas de fábrica usam fundo claro e renderizam corretamente.
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

WIDGET_DATA = os.path.expanduser("~/.claude/widget-data.json")
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/tmp"

SIZE = 240
# fundo claro (renderiza certo), texto escuro
BG = (245, 245, 248)
FG = (30, 30, 38)
MUTED = (110, 110, 122)
TRACK = (210, 210, 218)
# cores de status (fortes, sobrevivem à conversão)
GOOD = (22, 163, 74)
WARN = (202, 138, 4)
BAD = (220, 38, 38)


def load_font(size):
    for path in (
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def color_for_pct(pct):
    if pct < 50:
        return GOOD
    if pct < 80:
        return WARN
    return BAD


def render_tela(label, pct):
    """Uma tela: label no topo, % gigante no centro, barra embaixo."""
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    col = color_for_pct(pct)

    f_label = load_font(26)
    f_pct = load_font(88)
    f_used = load_font(15)

    # label da métrica (topo, centralizado)
    d.text((SIZE // 2, 30), label, font=f_label, fill=FG, anchor="mm")

    # porcentagem gigante no centro
    d.text((SIZE // 2, 112), f"{pct:.0f}%", font=f_pct, fill=col, anchor="mm")

    # "usado" legenda
    d.text((SIZE // 2, 168), "usado", font=f_used, fill=MUTED, anchor="mm")

    # barra de progresso embaixo
    bx, by, bw, bh = 24, 196, SIZE - 48, 20
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=TRACK)
    fill_w = max(int(bw * min(pct, 100) / 100), bh)
    d.rounded_rectangle([bx, by, bx + fill_w, by + bh], radius=bh // 2, fill=col)

    return img


def main():
    with open(WIDGET_DATA) as f:
        data = json.load(f)

    rl = data.get("rateLimits", {})
    weekly = rl.get("weeklyAll", {}).get("percentUsed", 0)
    session = rl.get("session", {}).get("percentUsed", 0)
    fable = rl.get("weeklyFable", {}).get("percentUsed", 0)

    telas = [
        ("tela-semana.png", "Semanal", weekly),
        ("tela-sessao.png", "Sessao", session),
        ("tela-fable.png", "Fable", fable),
    ]
    for fname, label, pct in telas:
        img = render_tela(label, pct)
        path = os.path.join(OUT_DIR, fname)
        img.save(path)
        print(f"{path}  ({label} {pct:.0f}%)")


if __name__ == "__main__":
    main()
