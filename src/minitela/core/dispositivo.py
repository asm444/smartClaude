"""Fachada da Minitela: compõe protocolo + transporte."""

import time

from . import protocolo as p
from .paginas import REG_CURRENT_PAGE
from .transporte import DEVICE_PADRAO, PortaSerial

_TIMEOUT_HANDSHAKE = 1.5
_TIMEOUT_ACK = 0.6
_ESPERA_DRENAGEM = 0.3


class Minitela:
    def __init__(self, device: str = DEVICE_PADRAO, porta: PortaSerial | None = None):
        self.porta = porta if porta is not None else PortaSerial(device)

    def abrir(self) -> "Minitela":
        self.porta.abrir()
        return self

    def fechar(self) -> None:
        self.porta.fechar()

    def __enter__(self) -> "Minitela":
        return self.abrir()

    def __exit__(self, *a) -> None:
        self.fechar()

    def handshake(self) -> bool:
        self.porta.escrever(p.montar_frame(p.CMD_HANDSHAKE))
        bruto = self.porta.ler(_TIMEOUT_HANDSHAKE)
        if not p.eh_frame_completo(bruto):
            return False
        try:
            return p.parse_frame(bruto).cmd_type == p.CMD_HANDSHAKE_RESP
        except p.ErroProtocolo:
            return False

    def vivo(self) -> bool:
        """True se o MCU está drenando o serial.

        Fila de TX que não esvazia = MCU mudo; só `usbreset 0324:0324` recupera.
        """
        self.porta.descartar_buffers()
        self.porta.escrever(p.montar_frame(p.CMD_HANDSHAKE))
        time.sleep(_ESPERA_DRENAGEM)
        return self.porta.fila_saida() == 0

    def escrever_registradores(self, pares: list[tuple[int, int]]) -> None:
        for lote in p.lotes(pares):
            self.porta.escrever(
                p.montar_frame(p.CMD_SET_REGISTER, p.conteudo_escrita_num(lote))
            )
            self.porta.ler(_TIMEOUT_ACK)

    def mostrar_pagina(self, pagina: int) -> None:
        self.escrever_registradores([(REG_CURRENT_PAGE, pagina)])
