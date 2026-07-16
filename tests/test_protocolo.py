import pytest

from minitela.core import protocolo as p


class TestMontarFrame:
    def test_handshake_bate_com_os_bytes_do_hardware(self):
        assert p.montar_frame(p.CMD_HANDSHAKE).hex() == "41480002008000004d49"

    def test_frame_comeca_em_AH_e_termina_em_MI(self):
        f = p.montar_frame(p.CMD_HANDSHAKE, b"\x01\x02\x03")
        assert f[:2] == b"AH"
        assert f[-2:] == b"MI"

    def test_tamanho_declarado_conta_o_cmdtype(self):
        f = p.montar_frame(p.CMD_SET_REGISTER, b"\xaa\xbb")
        assert int.from_bytes(f[2:4], "big") == 4

    def test_campo_de_crc_vai_zerado(self):
        f = p.montar_frame(p.CMD_HANDSHAKE, b"\xff" * 8)
        assert f[-4:-2] == b"\x00\x00"

    def test_conteudo_grande_demais_e_recusado(self):
        with pytest.raises(p.ErroProtocolo):
            p.montar_frame(p.CMD_SET_REGISTER, b"\x00" * 0x8000)


class TestParseFrame:
    def test_aceita_resposta_com_crc_zerado(self):
        bruto = bytes.fromhex("414800040" + "0c0" + "aabb" + "0000" + "4d49")
        assert p.parse_frame(bruto).cmd_type == p.CMD_HANDSHAKE_RESP

    def test_devolve_o_conteudo_sem_moldura(self):
        assert p.parse_frame(p.montar_frame(0x00D0, b"\xde\xad")).conteudo == b"\xde\xad"

    def test_ida_e_volta_preserva_cmd_e_conteudo(self):
        r = p.parse_frame(p.montar_frame(p.CMD_SET_REGISTER, b"\x01\x02\x03\x04"))
        assert (r.cmd_type, r.conteudo) == (p.CMD_SET_REGISTER, b"\x01\x02\x03\x04")

    def test_recusa_delimitador_de_inicio_errado(self):
        ruim = b"XX" + p.montar_frame(p.CMD_HANDSHAKE)[2:]
        with pytest.raises(p.ErroProtocolo, match="início"):
            p.parse_frame(ruim)

    def test_recusa_delimitador_de_fim_errado(self):
        ruim = p.montar_frame(p.CMD_HANDSHAKE)[:-2] + b"XX"
        with pytest.raises(p.ErroProtocolo, match="fim"):
            p.parse_frame(ruim)

    def test_recusa_frame_truncado(self):
        with pytest.raises(p.ErroProtocolo):
            p.parse_frame(b"AH\x00\x02MI")

    def test_recusa_tamanho_declarado_inconsistente(self):
        ruim = bytes.fromhex("4148") + bytes.fromhex("00ff") + bytes.fromhex("0080") \
            + b"\xaa" + bytes.fromhex("0000") + bytes.fromhex("4d49")
        with pytest.raises(p.ErroProtocolo, match="tamanho"):
            p.parse_frame(ruim)


class TestEhFrameCompleto:
    def test_reconhece_frame_inteiro(self):
        assert p.eh_frame_completo(p.montar_frame(p.CMD_HANDSHAKE))

    def test_rejeita_frame_pela_metade(self):
        assert not p.eh_frame_completo(p.montar_frame(p.CMD_HANDSHAKE)[:6])


class TestConteudoEscritaNum:
    def test_header_codifica_a_quantidade_menos_um(self):
        assert p.conteudo_escrita_num([(2, 5)])[0] == 0x80
        assert p.conteudo_escrita_num([(2, 5), (7, 9)])[0] == 0x81

    def test_cada_registrador_ocupa_reg2_valor4(self):
        out = p.conteudo_escrita_num([(2, 5)])
        assert len(out) == 1 + 6
        assert out[1:] == bytes.fromhex("0002") + bytes.fromhex("00000005")

    def test_trocar_de_pagina_gera_os_bytes_esperados(self):
        assert p.conteudo_escrita_num([(2, 6)]).hex() == "80" + "0002" + "00000006"

    def test_valor_e_truncado_em_32_bits(self):
        assert p.conteudo_escrita_num([(2, 0x1FFFFFFFF)])[3:] == b"\xff\xff\xff\xff"

    def test_recusa_lote_vazio(self):
        with pytest.raises(p.ErroProtocolo):
            p.conteudo_escrita_num([])

    def test_recusa_lote_acima_do_maximo(self):
        with pytest.raises(p.ErroProtocolo):
            p.conteudo_escrita_num([(1, 1)] * 17)


class TestLotes:
    def test_lote_unico_quando_cabe(self):
        assert len(p.lotes([(1, 1)] * 16)) == 1

    def test_divide_no_limite_de_16(self):
        assert [len(x) for x in p.lotes([(1, 1)] * 17)] == [16, 1]

    def test_nao_perde_nenhum_par(self):
        pares = [(i, i) for i in range(35)]
        assert [x for lote in p.lotes(pares) for x in lote] == pares
