"""Montagem e parse dos frames seriais. Puro: não toca I/O.

Frame: AH | controlFlag(2 BE) | cmdType(2 BE) | conteudo | crc(2 BE) | MI
O campo de CRC é sempre 0x0000 nos dois sentidos — ver docs/01-hardware-e-protocolo.md.
"""

import struct
from dataclasses import dataclass

INICIO = b"\x41\x48"
FIM = b"\x4d\x49"

CMD_HANDSHAKE = 0x0080
CMD_HANDSHAKE_RESP = 0x00C0
CMD_SET_REGISTER = 0x0090
CMD_SET_REGISTER_RESP = 0x00D0

FUNC_ESCRITA_NUM = 0b1000
FUNC_ESCRITA_STR = 0b11010000
MAX_REGS_POR_LOTE = 16


class ErroProtocolo(ValueError):
    """Frame malformado."""


@dataclass(frozen=True)
class Resposta:
    cmd_type: int
    conteudo: bytes


def montar_frame(cmd_type: int, conteudo: bytes = b"") -> bytes:
    control = len(conteudo) + 2
    if control > 0x7FFF:
        raise ErroProtocolo(f"conteúdo grande demais: {len(conteudo)} bytes")
    corpo = struct.pack(">HH", control, cmd_type) + conteudo
    return INICIO + corpo + b"\x00\x00" + FIM


def parse_frame(buf: bytes) -> Resposta:
    if len(buf) < 10:
        raise ErroProtocolo(f"frame curto demais: {len(buf)} bytes")
    if not buf.startswith(INICIO):
        raise ErroProtocolo(f"início inválido: {buf[:2].hex()}")
    if not buf.endswith(FIM):
        raise ErroProtocolo(f"fim inválido: {buf[-2:].hex()}")

    control, cmd_type = struct.unpack(">HH", buf[2:6])
    tam_dados = control & 0x7FFF
    conteudo = buf[6:-4]

    if tam_dados != len(conteudo) + 2:
        raise ErroProtocolo(
            f"tamanho declarado {tam_dados} != real {len(conteudo) + 2}"
        )
    return Resposta(cmd_type=cmd_type, conteudo=conteudo)


def eh_frame_completo(buf: bytes) -> bool:
    return len(buf) >= 10 and buf.startswith(INICIO) and buf.endswith(FIM)


def conteudo_escrita_num(pares: list[tuple[int, int]]) -> bytes:
    if not pares:
        raise ErroProtocolo("nenhum registrador")
    if len(pares) > MAX_REGS_POR_LOTE:
        raise ErroProtocolo(f"máximo {MAX_REGS_POR_LOTE} por lote, veio {len(pares)}")

    out = bytes([(FUNC_ESCRITA_NUM << 4) | ((len(pares) - 1) & 0xF)])
    for reg, val in pares:
        out += struct.pack(">HI", reg, val & 0xFFFFFFFF)
    return out


def lotes(pares: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    return [
        pares[i:i + MAX_REGS_POR_LOTE]
        for i in range(0, len(pares), MAX_REGS_POR_LOTE)
    ]
