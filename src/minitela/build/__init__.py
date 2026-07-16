"""Pipeline de build do .acf: sprites -> gif -> projeto -> compilador -> .acf."""

import tempfile
from pathlib import Path

from ..core.paginas import FRAMES_POR_PAGINA
from ..render import clawd as render_clawd
from . import wine
from .gif import montar_gif
from .projeto import ProjetoAHMI

# página de gif -> gif de origem no projeto de fábrica. O NOME é o que liga o
# arquivo à página; trocar o conteúdo mantendo o nome é o pipeline inteiro.
GIF_DE_ORIGEM = {
    5: "1i1h1e37393671471.gif",
    6: "1h1k1e37393671464.gif",
    7: "1h1m1e37393671466.gif",
}

# Conjunto = um .acf com os 3 bichinhos das páginas 5/6/7.
CONJUNTOS = {
    "normal": {5: "dumb", 6: "genius", 7: "smart"},
    "alerta": {5: "dumb", 6: "slow", 7: "braindead"},
}


def file_zip_padrao() -> Path:
    return Path.home() / "telinha" / "minitela-oficial" / "ide-utils" / "file.zip"


def montar_conjunto(
    nome: str,
    saida: Path,
    file_zip: Path | None = None,
) -> Path:
    """Gera o .acf de um conjunto. Exige o file.zip de fábrica (ver bootstrap)."""
    if nome not in CONJUNTOS:
        raise ValueError(f"conjunto desconhecido: {nome} (há {sorted(CONJUNTOS)})")
    origem = Path(file_zip) if file_zip else file_zip_padrao()
    if not origem.exists():
        raise FileNotFoundError(
            f"file.zip de fábrica ausente: {origem} — ver scripts/bootstrap-vendor.md"
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        projeto = ProjetoAHMI.extrair(origem, tmp / "projeto")

        for pagina, estado in CONJUNTOS[nome].items():
            gif = montar_gif(
                render_clawd.compor_frames(estado),
                tmp / GIF_DE_ORIGEM[pagina],
                FRAMES_POR_PAGINA[pagina],
            )
            projeto.substituir_gif(GIF_DE_ORIGEM[pagina], gif)

        return wine.compilar_acf(projeto.raiz, Path(saida), tmp / "projeto.zip")
