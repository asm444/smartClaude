import pytest

from minitela.core import protocolo as p
from minitela.core.dispositivo import Minitela
from minitela.core.paginas import REG_CURRENT_PAGE


@pytest.fixture
def minitela(minitela_falsa):
    return Minitela(porta=minitela_falsa.porta), minitela_falsa


class TestHandshake:
    def test_pergunta_ao_dispositivo_e_reconhece_a_resposta(self, minitela):
        m, falsa = minitela
        falsa.responder(p.montar_frame(p.CMD_HANDSHAKE_RESP))
        assert m.handshake() is True
        assert falsa.recebido_pelo_mcu() == p.montar_frame(p.CMD_HANDSHAKE)

    def test_silencio_do_mcu_nao_e_handshake(self, minitela):
        m, _ = minitela
        assert m.handshake() is False

    def test_resposta_de_outro_comando_nao_e_handshake(self, minitela):
        m, falsa = minitela
        falsa.responder(p.montar_frame(p.CMD_SET_REGISTER_RESP))
        assert m.handshake() is False

    def test_lixo_no_lugar_do_frame_nao_derruba(self, minitela):
        m, falsa = minitela
        falsa.responder(b"\x00\xff lixo qualquer \x12\x34")
        assert m.handshake() is False


class TestMostrarPagina:
    def test_escreve_o_registrador_de_pagina_ativa(self, minitela):
        m, falsa = minitela
        m.mostrar_pagina(6)
        esperado = p.montar_frame(
            p.CMD_SET_REGISTER, p.conteudo_escrita_num([(REG_CURRENT_PAGE, 6)])
        )
        assert falsa.recebido_pelo_mcu() == esperado

    def test_trocar_para_pagina_do_clawd_manda_os_bytes_certos(self, minitela):
        m, falsa = minitela
        m.mostrar_pagina(5)
        assert falsa.recebido_pelo_mcu().hex() == "41480009009080000200000005" + "00004d49"


class TestEscreverRegistradores:
    def test_um_lote_vira_um_frame(self, minitela):
        m, falsa = minitela
        m.escrever_registradores([(2, 5), (7, 200)])
        recebido = falsa.recebido_pelo_mcu()
        assert p.parse_frame(recebido).cmd_type == p.CMD_SET_REGISTER

    def test_mais_de_16_registradores_viram_varios_frames(self, minitela):
        m, falsa = minitela
        m.escrever_registradores([(i, i) for i in range(20)])
        bruto = falsa.recebido_pelo_mcu()
        assert bruto.count(p.INICIO) == 2
