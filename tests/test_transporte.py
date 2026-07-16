from minitela.core import protocolo as p


class TestEscrever:
    def test_o_que_a_porta_escreve_chega_ao_mcu(self, minitela_falsa):
        frame = p.montar_frame(p.CMD_HANDSHAKE)
        minitela_falsa.porta.escrever(frame)
        assert minitela_falsa.recebido_pelo_mcu() == frame


class TestLer:
    def test_devolve_o_frame_que_o_mcu_respondeu(self, minitela_falsa):
        resp = p.montar_frame(p.CMD_HANDSHAKE_RESP)
        minitela_falsa.responder(resp)
        assert minitela_falsa.porta.ler(timeout=1.0) == resp

    def test_para_de_ler_assim_que_o_frame_fecha(self, minitela_falsa):
        minitela_falsa.responder(p.montar_frame(p.CMD_HANDSHAKE_RESP))
        assert minitela_falsa.porta.ler(timeout=5.0).endswith(b"MI")

    def test_junta_resposta_que_chega_em_pedacos(self, minitela_falsa):
        resp = p.montar_frame(p.CMD_HANDSHAKE_RESP, b"\xaa\xbb\xcc\xdd")
        minitela_falsa.responder(resp[:5])
        minitela_falsa.responder(resp[5:])
        assert minitela_falsa.porta.ler(timeout=1.0) == resp

    def test_mcu_mudo_devolve_vazio_sem_travar(self, minitela_falsa):
        assert minitela_falsa.porta.ler(timeout=0.3) == b""

    def test_respeita_o_timeout_quando_ninguem_responde(self, minitela_falsa):
        import time

        inicio = time.monotonic()
        minitela_falsa.porta.ler(timeout=0.5)
        assert 0.4 < time.monotonic() - inicio < 1.5


class TestFdExterno:
    def test_fechar_nao_fecha_fd_de_terceiro(self, minitela_falsa):
        minitela_falsa.porta.fechar()
        minitela_falsa.porta.escrever(p.montar_frame(p.CMD_HANDSHAKE))
        assert minitela_falsa.recebido_pelo_mcu() != b""
