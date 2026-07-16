#!/usr/bin/env python3
"""
Indicador de MODELO na Minitela: mostra o bichinho do Clawd conforme o modelo que
voce esta usando no Claude Code (o ultimo /model da SESSAO PRINCIPAL, ignorando
subagentes). Ao vivo — faz polling do transcript e troca a pagina quando o modelo
muda.

  opus   -> genius (coroa)   pagina 6
  sonnet -> smart (livro)    pagina 7
  fable  -> fogo             pagina 5
  (haiku/outro -> fogo, como fallback)

REQUER: o `clawd-anim.acf` (3 Clawds DIFERENTES nas paginas 5/6/7) ja subido no
hardware. Gere uma vez com: minitela build normal -o <saida.acf>; use o upload do
clawd-anim.acf. Este script so troca de pagina (instantaneo), nao sobe .acf.

Uso:
  python3 minitela_modelo.py            # loop, troca o bichinho conforme o modelo
  python3 minitela_modelo.py --once     # aplica uma vez e sai
  python3 minitela_modelo.py --print    # so imprime o modelo atual, nao toca hardware

Nao precisa de root (le transcript em ~/.claude e fala com /dev/ttyACM0 via dialout).
"""
import glob
import json
import os
import sys
import time

from minitela import Minitela

# modelo (substring no id, ex "claude-opus-4-8") -> pagina do bichinho (RegCurrentPage)
MODELO_PAGINA = [
    ("opus",   6, "genius"),   # Opus  = genio (coroa)
    ("sonnet", 7, "smart"),    # Sonnet = inteligente (livro)
    ("fable",  5, "fogo"),     # Fable = foguinho
    ("haiku",  5, "fogo"),     # fallback
]
PAGINA_FALLBACK = 5  # fogo, se o modelo nao casar com nenhum

# home do USUARIO fixo (nao "~"): o daemon pode rodar como root e ~ viraria /root.
_USER_HOME = os.environ.get("MINITELA_HOME", "/home/asm")
SETTINGS_JSON = os.path.join(_USER_HOME, ".claude", "settings.json")  # ultimo /model
POLL_SEC = 3  # de quanto em quanto tempo checa o modelo


def modelo_atual():
    """Le o modelo do ULTIMO /model de ~/.claude/settings.json (gravado na hora do
    /model). Nome curto: 'opus'/'sonnet'/'fable'."""
    try:
        with open(SETTINGS_JSON) as f:
            return (json.load(f) or {}).get("model")
    except (OSError, ValueError):
        return None


def pagina_do_modelo(modelo):
    """Mapeia o id do modelo pra pagina do bichinho. (nome_estado, pagina)."""
    ml = (modelo or "").lower()
    for chave, pagina, estado in MODELO_PAGINA:
        if chave in ml:
            return pagina, estado
    return PAGINA_FALLBACK, "fogo"


def aplicar(pagina, estado, modelo):
    """Troca a pagina ativa na Minitela (instantaneo, so show-page)."""
    with Minitela() as m:
        if not m.alive():
            print("  MCU mudo — rode: sudo usbreset 0324:0324", flush=True)
            return False
        m.show_page(pagina)
    print(f"  modelo={modelo} -> {estado} (pagina {pagina})", flush=True)
    return True


def main():
    if "--print" in sys.argv:
        mdl = modelo_atual()
        pg, est = pagina_do_modelo(mdl)
        print(f"modelo atual: {mdl} -> {est} (pagina {pg})")
        return

    once = "--once" in sys.argv
    ultimo = None
    print("Indicador de modelo na Minitela. opus=genio, sonnet=smart, fable=fogo.",
          flush=True)
    while True:
        mdl = modelo_atual()
        pg, est = pagina_do_modelo(mdl)
        if pg != ultimo:            # so troca quando o modelo (pagina) muda
            if aplicar(pg, est, mdl):
                ultimo = pg
        if once:
            break
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
