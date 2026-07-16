#!/usr/bin/env python3
"""
Renderiza as telas 240x240 do bichinho Clawd, um estado por tela, FUNDO CLARO
(o compilador AHMI corrompe tons escuros).

Estados (mascote do claude-usage-widget): genius(coroa), smart(livro/café),
slow(chuva), dumb(fogo), braindead(caveira). Cada overlay tem 6 frames; aqui
compomos frames Clawd+overlay em 240x240 para virar um GIF/estático na telinha.

Uso: python3 render_bichinhos.py <dir_saida> [--frames]
  sem --frames: 1 PNG estático por estado (frame representativo)
  com --frames: 6 PNGs por estado (pra montar GIF), nomeados <estado>-N.png
"""
import os
import subprocess
import sys

from PIL import Image

ICONS = os.path.expanduser("~/projects/claude-usage-widget/plasmoid/contents/icons")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
WITH_FRAMES = "--frames" in sys.argv

SIZE = 240
BG = (245, 245, 248)          # fundo claro (renderiza certo)
CLAWD_ORANGE = (217, 119, 87)  # #D97757

# estado -> (prefixo do overlay, esconde o Clawd base?)
STATES = {
    "genius":    ("halo", False),
    "smart":     ("smart", False),
    "slow":      ("rain", False),
    "dumb":      ("fire", False),
    "braindead": ("skull", True),   # caveira substitui o Clawd
}


def raster_clawd(px=160):
    """Rasteriza clawd.svg para PNG RGBA via ImageMagick (cairosvg ausente)."""
    out = os.path.join(OUT, "_clawd_raster.png")
    subprocess.run(
        ["magick", "-background", "none", "-density", "600",
         os.path.join(ICONS, "clawd.svg"), "-resize", f"{px}x{px}", out],
        check=True,
    )
    return Image.open(out).convert("RGBA")


def compose(clawd, overlay_prefix, frame, hide_clawd):
    """Monta uma tela 240x240: fundo claro + Clawd centralizado + overlay por cima."""
    canvas = Image.new("RGBA", (SIZE, SIZE), BG + (255,))

    if not hide_clawd:
        cw, ch = clawd.size
        canvas.alpha_composite(clawd, ((SIZE - cw) // 2, (SIZE - ch) // 2 + 20))

    ov_path = os.path.join(ICONS, f"{overlay_prefix}-{frame}.png")
    if os.path.exists(ov_path):
        ov = Image.open(ov_path).convert("RGBA").resize((200, 200), Image.NEAREST)
        canvas.alpha_composite(ov, ((SIZE - 200) // 2, (SIZE - 200) // 2 - 10))

    return canvas.convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    clawd = raster_clawd()
    for state, (prefix, hide) in STATES.items():
        if WITH_FRAMES:
            for fr in range(6):
                img = compose(clawd, prefix, fr, hide)
                p = os.path.join(OUT, f"bicho-{state}-{fr}.png")
                img.save(p)
            print(f"{state}: 6 frames ({prefix})")
        else:
            img = compose(clawd, prefix, 0, hide)
            p = os.path.join(OUT, f"bicho-{state}.png")
            img.save(p)
            print(f"{p}  ({state}, overlay={prefix})")


if __name__ == "__main__":
    main()
