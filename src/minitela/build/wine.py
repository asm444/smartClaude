"""Chamada do compilador AHMI (Windows) via Wine. Único subprocess do build.

Ponto cego declarado: sem teste automatizado — exige o .exe proprietário, que
não é redistribuído. Coberto pelo checkpoint visual no hardware.
Ver scripts/bootstrap-vendor.md.
"""

import os
import shutil
import subprocess
from pathlib import Path

COMPILADOR = "AHMISimGenDemo_og.exe"

# O compilador pede "pressione uma tecla" no fim; o app oficial manda 13 (Enter).
_STDIN_ENTER = "13\n"
_TIMEOUT_S = 600

# -m 2 modo textura | -c 0 GC9002 | -e 0 limite 15MB | -d 1 dither
_FLAGS = ("-m", "2", "-c", "0", "-e", "0", "-d", "1")


class CompiladorAusente(FileNotFoundError):
    pass


class FalhaCompilacao(RuntimeError):
    pass


def dir_gen() -> Path:
    """Onde mora o compilador. O cwd precisa ser esse diretório."""
    return Path(
        os.environ.get(
            "MINITELA_GEN",
            Path.home() / "telinha" / "minitela-oficial" / "ide-utils" / "Gen",
        )
    )


def prefixo_wine() -> str:
    return os.environ.get("WINEPREFIX", str(Path.home() / ".wine"))


def _zipar(raiz: Path, destino: Path) -> Path:
    """Usa o zip do SISTEMA: o compilador rejeita o zipfile do Python."""
    if not shutil.which("zip"):
        raise FalhaCompilacao("comando `zip` ausente — instale o pacote zip")
    destino = Path(destino).resolve()
    destino.unlink(missing_ok=True)
    subprocess.run(
        ["zip", "-q", "-r", "-X", str(destino), "."],
        cwd=raiz, check=True, timeout=_TIMEOUT_S,
    )
    return destino


def compilar_acf(raiz_projeto: Path, saida: Path, zip_tmp: Path) -> Path:
    """Projeto extraído -> Texture.acf. Devolve o caminho do .acf gerado."""
    gen = dir_gen()
    exe = gen / COMPILADOR
    if not exe.exists():
        raise CompiladorAusente(
            f"{COMPILADOR} não encontrado em {gen} — ver scripts/bootstrap-vendor.md"
        )
    if not shutil.which("wine"):
        raise CompiladorAusente("wine não instalado")

    zip_projeto = _zipar(Path(raiz_projeto), zip_tmp)
    dir_saida = Path(saida).parent / "_acf"
    shutil.rmtree(dir_saida, ignore_errors=True)
    dir_saida.mkdir(parents=True, exist_ok=True)

    ambiente = {**os.environ, "WINEPREFIX": prefixo_wine(), "WINEDEBUG": "-all"}
    proc = subprocess.run(
        ["wine", COMPILADOR, "-f", str(zip_projeto), *_FLAGS, "-o", str(dir_saida)],
        cwd=gen, input=_STDIN_ENTER, capture_output=True, text=True,
        timeout=_TIMEOUT_S, env=ambiente,
    )

    gerado = dir_saida / "Texture.acf"
    if not gerado.exists():
        raise FalhaCompilacao(
            f"compilador não gerou Texture.acf\n{proc.stdout[-500:]}\n{proc.stderr[-500:]}"
        )
    shutil.copyfile(gerado, saida)
    return Path(saida)


def frames_assados(saida_compilador: str) -> int:
    """Quantos frames o compilador reportou ter assado (STCRGBA)."""
    return saida_compilador.count("STCRGBA compress completed")
