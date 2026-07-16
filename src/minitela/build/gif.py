"""Montagem dos GIFs multi-frame que o compilador AHMI consegue decodificar.

A paleta GLOBAL única + disposal=1 + optimize=False não são preferência: sem
elas o Pillow gera paleta local por frame e disposal parcial, e o decoder do
_og.exe reconstrói frames PARCIAIS (buracos pretos) — lixo geométrico na tela.
Cada frame precisa ser um keyframe completo e auto-contido.
Ver docs/05-runbook-clawd.md.
"""

from pathlib import Path

from PIL import Image

TAMANHO_GIF = 192
CORES_PALETA = 255
DURACAO_MS = 100


def pingpong(total: int, quadros: int) -> list[int]:
    """Índices 0..quadros-1 em vaivém, para o loop fechar sem salto."""
    if quadros < 1:
        raise ValueError("é preciso ao menos 1 quadro")
    if quadros == 1:
        return [0] * total
    ordem, i, passo = [], 0, 1
    ultimo = quadros - 1
    while len(ordem) < total:
        ordem.append(i)
        i += passo
        if i == ultimo:
            passo = -1
        elif i == 0:
            passo = 1
    return ordem


def paleta_global(quadros: list[Image.Image]) -> Image.Image:
    """Uma paleta só para todos os quadros: emenda tudo e quantiza junto."""
    largura = TAMANHO_GIF * len(quadros)
    amostra = Image.new("RGB", (largura, TAMANHO_GIF))
    for i, q in enumerate(quadros):
        amostra.paste(q, (TAMANHO_GIF * i, 0))
    return amostra.quantize(colors=CORES_PALETA, method=Image.MEDIANCUT)


def _preparar(quadros: list[Image.Image]) -> list[Image.Image]:
    return [
        q.convert("RGB").resize((TAMANHO_GIF, TAMANHO_GIF), Image.LANCZOS)
        for q in quadros
    ]


def montar_gif(quadros: list[Image.Image], destino: Path, n_frames: int) -> Path:
    """Grava um GIF com exatamente n_frames, em vaivém sobre os quadros dados.

    n_frames vem da page-def do FIRMWARE (5=21, 6=30, 7=44), nunca do gif de
    fábrica — os de fábrica têm 1 frame só.
    """
    if not quadros:
        raise ValueError("nenhum quadro")
    if n_frames < 1:
        raise ValueError(f"n_frames inválido: {n_frames}")

    base = _preparar(quadros)
    paleta = paleta_global(base)
    sequencia = [
        base[i].quantize(palette=paleta, dither=Image.NONE)
        for i in pingpong(n_frames, len(base))
    ]

    destino = Path(destino)
    sequencia[0].save(
        destino,
        save_all=True,
        append_images=sequencia[1:],
        duration=DURACAO_MS,
        loop=0,
        disposal=1,
        optimize=False,
    )
    return destino
