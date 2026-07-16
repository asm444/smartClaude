import io
import struct

import pytest

from minitela.entrada import tecla as t


def evento(code: int, valor: int = t.VALOR_PRESSIONADA, tipo: int = t.EV_KEY) -> bytes:
    return struct.pack(t.EV_FORMAT, 0, 0, tipo, code, valor)


def arquivo_com(*eventos_bytes: bytes) -> io.BytesIO:
    return io.BytesIO(b"".join(eventos_bytes))


class TestEventos:
    def test_um_toque_na_tecla_vira_um_evento(self):
        assert list(t.eventos(arquivo_com(evento(t.KEY_MINITELA)))) == [t.KEY_MINITELA]

    def test_tres_toques_viram_tres_eventos(self):
        f = arquivo_com(*[evento(t.KEY_MINITELA)] * 3)
        assert len(list(t.eventos(f))) == 3

    def test_soltar_a_tecla_nao_conta(self):
        f = arquivo_com(evento(t.KEY_MINITELA, valor=0))
        assert list(t.eventos(f)) == []

    def test_repeticao_por_segurar_nao_conta(self):
        f = arquivo_com(evento(t.KEY_MINITELA, valor=2))
        assert list(t.eventos(f)) == []

    def test_outra_tecla_e_ignorada(self):
        f = arquivo_com(evento(30), evento(t.KEY_MINITELA), evento(42))
        assert list(t.eventos(f)) == [t.KEY_MINITELA]

    def test_evento_que_nao_e_de_tecla_e_ignorado(self):
        f = arquivo_com(evento(t.KEY_MINITELA, tipo=0x04))
        assert list(t.eventos(f)) == []

    def test_ciclo_press_release_conta_uma_vez_so(self):
        f = arquivo_com(evento(t.KEY_MINITELA, 1), evento(t.KEY_MINITELA, 0))
        assert list(t.eventos(f)) == [t.KEY_MINITELA]

    def test_arquivo_vazio_nao_trava(self):
        assert list(t.eventos(arquivo_com())) == []

    def test_leitura_truncada_encerra_sem_estourar(self):
        assert list(t.eventos(io.BytesIO(b"\x00\x01\x02"))) == []

    def test_keycode_customizado_e_respeitado(self):
        f = arquivo_com(evento(148), evento(186))
        assert list(t.eventos(f, keycode=148)) == [148]


class TestQualquerTecla:
    def test_reporta_todo_keycode_pressionado(self):
        f = arquivo_com(evento(30), evento(186), evento(42))
        assert list(t.qualquer_tecla(f)) == [30, 186, 42]

    def test_ignora_o_release(self):
        f = arquivo_com(evento(30, valor=1), evento(30, valor=0))
        assert list(t.qualquer_tecla(f)) == [30]


class TestEncontrarTeclado:
    def test_acha_o_device_que_emite_a_tecla(self, monkeypatch):
        monkeypatch.setattr(t.glob, "glob", lambda p: ["/dev/input/event0", "/dev/input/event3"])
        monkeypatch.setattr(t, "_emite_tecla", lambda nome, key: nome == "event3")
        assert t.encontrar_teclado() == "/dev/input/event3"

    def test_cai_no_fallback_quando_ninguem_emite(self, monkeypatch):
        monkeypatch.setattr(t.glob, "glob", lambda p: ["/dev/input/event0"])
        monkeypatch.setattr(t, "_emite_tecla", lambda nome, key: False)
        assert t.encontrar_teclado() == t.DEV_FALLBACK

    def test_sem_nenhum_device_cai_no_fallback(self, monkeypatch):
        monkeypatch.setattr(t.glob, "glob", lambda p: [])
        assert t.encontrar_teclado() == t.DEV_FALLBACK


class TestEmiteTecla:
    def test_bit_da_tecla_ligado_no_bitmask(self, monkeypatch):
        # 186 = palavra 2, bit 58; a lista vem da palavra mais significativa p/ a menos
        conteudo = f"0 0 {hex(1 << 58)[2:]} 0 0"
        monkeypatch.setattr("builtins.open", lambda p, *a, **k: io.StringIO(conteudo))
        assert t._emite_tecla("event9", 186) is True

    def test_bit_desligado_significa_que_nao_emite(self, monkeypatch):
        monkeypatch.setattr("builtins.open", lambda p, *a, **k: io.StringIO("0 0 0 0 0"))
        assert t._emite_tecla("event9", 186) is False

    def test_arquivo_de_capabilities_ausente_nao_estoura(self, monkeypatch):
        def falha(*a, **k):
            raise OSError("não existe")
        monkeypatch.setattr("builtins.open", falha)
        assert t._emite_tecla("event9", 186) is False

    def test_bitmask_curto_demais_nao_estoura(self, monkeypatch):
        monkeypatch.setattr("builtins.open", lambda p, *a, **k: io.StringIO("f"))
        assert t._emite_tecla("event9", 186) is False

    def test_bitmask_corrompido_nao_estoura(self, monkeypatch):
        monkeypatch.setattr("builtins.open", lambda p, *a, **k: io.StringIO("x y z"))
        assert t._emite_tecla("event9", 186) is False


class TestAbrirTeclado:
    def test_sem_root_falha_na_hora_e_nao_em_loop(self, monkeypatch):
        def sem_permissao(*a, **k):
            raise PermissionError(13, "Permission denied")
        monkeypatch.setattr("builtins.open", sem_permissao)
        with pytest.raises(t.SemPermissao, match="root"):
            t.abrir_teclado("/dev/input/event3", tentativas=1)

    def test_device_ausente_e_tentado_de_novo(self, monkeypatch):
        chamadas = []

        def as_vezes(caminho, *a, **k):
            chamadas.append(caminho)
            if len(chamadas) < 3:
                raise FileNotFoundError(2, "no such")
            return io.BytesIO(b"")

        monkeypatch.setattr("builtins.open", as_vezes)
        monkeypatch.setattr(t.time, "sleep", lambda s: None)
        caminho, _ = t.abrir_teclado("/dev/input/event3", tentativas=5, espera=0)
        assert (caminho, len(chamadas)) == ("/dev/input/event3", 3)

    def test_desiste_depois_das_tentativas(self, monkeypatch):
        def nunca(*a, **k):
            raise FileNotFoundError(2, "no such")
        monkeypatch.setattr("builtins.open", nunca)
        monkeypatch.setattr(t.time, "sleep", lambda s: None)
        with pytest.raises(FileNotFoundError):
            t.abrir_teclado("/dev/input/event3", tentativas=2, espera=0)
