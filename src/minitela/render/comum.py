"""Base do render. FUNDO CLARO é obrigatório: o compilador AHMI corrompe
cores quase-pretas — ver docs/03-projeto-ahmi-e-compilador.md.
"""

from functools import lru_cache

from PIL import ImageFont

TAMANHO = 240
FUNDO_CLARO = (245, 245, 248)
LARANJA_CLAWD = (217, 119, 87)
TEXTO_ESCURO = (32, 32, 40)

VERDE = (46, 160, 67)
AMARELO = (210, 153, 34)
VERMELHO = (218, 54, 51)

# Fronteiras de COR das telas — 50/80. Não confundir com as do ALERTA do daemon
# (70/90, em daemon/estado.py): são escalas diferentes de propósito. A cor gradua
# a leitura da tela; o alerta decide trocar o bichinho. Ver docs/06-runbook-dashboard.md.
PCT_ATENCAO = 50
PCT_CRITICO = 80

_FONTES = [
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/google-noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
]


@lru_cache(maxsize=1)
def _fonte_do_sistema() -> str | None:
    """Pergunta ao fontconfig. Sem isto, uma distro sem DejaVu cai no
    load_default(), que IGNORA o tamanho pedido — o texto sai todo do mesmo
    tamanho e a tela fica ilegível.
    """
    import shutil
    import subprocess

    if not shutil.which("fc-match"):
        return None
    try:
        saida = subprocess.run(
            ["fc-match", "-f", "%{file}", "sans-serif:bold"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    return saida or None


@lru_cache(maxsize=8)
def carregar_fonte(tamanho: int):
    for caminho in _FONTES:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue

    do_sistema = _fonte_do_sistema()
    if do_sistema:
        try:
            return ImageFont.truetype(do_sistema, tamanho)
        except OSError:
            pass
    return ImageFont.load_default()


def cor_por_pct(pct: float) -> tuple[int, int, int]:
    if pct >= PCT_CRITICO:
        return VERMELHO
    if pct >= PCT_ATENCAO:
        return AMARELO
    return VERDE
