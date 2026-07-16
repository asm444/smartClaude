"""Leitura do cabeçalho do .acf, para conferir o que o compilador gerou.

Offsets confirmados por hexdump do .acf de fábrica. Atenção: a tabela de
offsets do core/acf.go do SideCar está deslocada em 2 bytes na região do
deviceID — aqui vale o que os bytes dizem.
"""

import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = bytes.fromhex("00404000")

_OFF_PROJECT_ID = 0x000C
_TAM_PROJECT_ID = 24
_OFF_LARGURA = 0x0104
_OFF_ALTURA = 0x0106
_TAM_CABECALHO = 0x0110


class ACFInvalido(ValueError):
    pass


@dataclass(frozen=True)
class InfoACF:
    project_id: str
    largura: int
    altura: int
    tamanho: int


def ler_cabecalho(caminho: Path) -> InfoACF:
    caminho = Path(caminho)
    bruto = caminho.read_bytes()[:_TAM_CABECALHO]
    if len(bruto) < _TAM_CABECALHO:
        raise ACFInvalido(f"arquivo curto demais: {caminho}")
    if not bruto.startswith(MAGIC):
        raise ACFInvalido(f"magic inesperado: {bruto[:4].hex()}")

    project_id = (
        bruto[_OFF_PROJECT_ID:_OFF_PROJECT_ID + _TAM_PROJECT_ID]
        .rstrip(b"\x00")
        .decode("ascii", errors="replace")
    )
    largura = struct.unpack("<H", bruto[_OFF_LARGURA:_OFF_LARGURA + 2])[0]
    altura = struct.unpack("<H", bruto[_OFF_ALTURA:_OFF_ALTURA + 2])[0]

    return InfoACF(
        project_id=project_id,
        largura=largura,
        altura=altura,
        tamanho=caminho.stat().st_size,
    )


def compativel(gerado: Path, referencia: Path, tolerancia: float = 0.05) -> bool:
    """O .acf gerado casa com o de referência? (mesmo projeto e tela, tamanho ±5%)"""
    a, b = ler_cabecalho(gerado), ler_cabecalho(referencia)
    if a.project_id != b.project_id:
        return False
    if (a.largura, a.altura) != (b.largura, b.altura):
        return False
    return abs(a.tamanho - b.tamanho) <= b.tamanho * tolerancia
