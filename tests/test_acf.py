import struct

import pytest

from minitela.build import acf


def cabecalho_falso(project_id=b"67004c7703ad6966e4fe0d13", largura=240, altura=240,
                    magic=acf.MAGIC):
    buf = bytearray(0x110)
    buf[0:4] = magic
    buf[0x0C:0x0C + len(project_id)] = project_id
    buf[0x104:0x106] = struct.pack("<H", largura)
    buf[0x106:0x108] = struct.pack("<H", altura)
    return bytes(buf)


class TestLerCabecalho:
    def test_le_o_project_id_do_projeto_de_fabrica(self, tmp_path):
        p = tmp_path / "x.acf"
        p.write_bytes(cabecalho_falso())
        assert acf.ler_cabecalho(p).project_id == "67004c7703ad6966e4fe0d13"

    def test_le_a_resolucao_da_minitela(self, tmp_path):
        p = tmp_path / "x.acf"
        p.write_bytes(cabecalho_falso())
        info = acf.ler_cabecalho(p)
        assert (info.largura, info.altura) == (240, 240)

    def test_reporta_o_tamanho_do_arquivo(self, tmp_path):
        p = tmp_path / "x.acf"
        p.write_bytes(cabecalho_falso() + b"\x00" * 1000)
        assert acf.ler_cabecalho(p).tamanho == 0x110 + 1000

    def test_magic_errado_e_recusado(self, tmp_path):
        p = tmp_path / "x.acf"
        p.write_bytes(cabecalho_falso(magic=b"\xde\xad\xbe\xef"))
        with pytest.raises(acf.ACFInvalido, match="magic"):
            acf.ler_cabecalho(p)

    def test_arquivo_truncado_e_recusado(self, tmp_path):
        p = tmp_path / "x.acf"
        p.write_bytes(acf.MAGIC + b"\x00" * 10)
        with pytest.raises(acf.ACFInvalido, match="curto"):
            acf.ler_cabecalho(p)


class TestCompativel:
    def test_mesmo_projeto_e_tamanho_igual_e_compativel(self, tmp_path):
        a, b = tmp_path / "a.acf", tmp_path / "b.acf"
        a.write_bytes(cabecalho_falso() + b"\x00" * 1000)
        b.write_bytes(cabecalho_falso() + b"\x00" * 1000)
        assert acf.compativel(a, b)

    def test_projeto_diferente_nao_e_compativel(self, tmp_path):
        a, b = tmp_path / "a.acf", tmp_path / "b.acf"
        a.write_bytes(cabecalho_falso(project_id=b"outro-projeto-qualquer00"))
        b.write_bytes(cabecalho_falso())
        assert not acf.compativel(a, b)

    def test_resolucao_diferente_nao_e_compativel(self, tmp_path):
        a, b = tmp_path / "a.acf", tmp_path / "b.acf"
        a.write_bytes(cabecalho_falso(largura=320, altura=240))
        b.write_bytes(cabecalho_falso())
        assert not acf.compativel(a, b)

    def test_tamanho_dentro_da_tolerancia_e_compativel(self, tmp_path):
        a, b = tmp_path / "a.acf", tmp_path / "b.acf"
        a.write_bytes(cabecalho_falso() + b"\x00" * 1020)
        b.write_bytes(cabecalho_falso() + b"\x00" * 1000)
        assert acf.compativel(a, b)

    def test_tamanho_muito_fora_nao_e_compativel(self, tmp_path):
        a, b = tmp_path / "a.acf", tmp_path / "b.acf"
        a.write_bytes(cabecalho_falso() + b"\x00" * 5000)
        b.write_bytes(cabecalho_falso() + b"\x00" * 1000)
        assert not acf.compativel(a, b)
