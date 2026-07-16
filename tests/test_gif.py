import pytest
from PIL import Image

from minitela.build import gif
from minitela.render import clawd


def quadros(n=6, cores=None):
    cores = cores or [(i * 40, 60, 200 - i * 30) for i in range(n)]
    return [Image.new("RGB", (240, 240), c) for c in cores[:n]]


def quadros_reais():
    """Sprites de verdade: cores chapadas não reproduzem o bug da tela-preta."""
    return clawd.compor_frames("dumb")


def reabrir(caminho):
    im = Image.open(caminho)
    return im, getattr(im, "n_frames", 1)


class TestPingpong:
    def test_vai_e_volta_sem_repetir_a_ponta(self):
        assert gif.pingpong(10, 6) == [0, 1, 2, 3, 4, 5, 4, 3, 2, 1]

    def test_tem_exatamente_o_comprimento_pedido(self):
        for n in (21, 30, 44):
            assert len(gif.pingpong(n, 6)) == n

    def test_todo_indice_esta_no_intervalo(self):
        assert all(0 <= i < 6 for i in gif.pingpong(44, 6))

    def test_o_loop_fecha_suave(self):
        # o último quadro precisa ser vizinho do primeiro, senão a volta salta
        ordem = gif.pingpong(21, 6)
        assert abs(ordem[-1] - ordem[0]) <= 1

    def test_um_quadro_so_vira_sequencia_constante(self):
        assert gif.pingpong(5, 1) == [0, 0, 0, 0, 0]

    def test_zero_quadros_e_recusado(self):
        with pytest.raises(ValueError):
            gif.pingpong(10, 0)


class TestMontarGif:
    @pytest.mark.parametrize("n_frames", [21, 30, 44])
    def test_gera_exatamente_os_frames_que_o_firmware_pede(self, tmp_path, n_frames):
        destino = gif.montar_gif(quadros(), tmp_path / "x.gif", n_frames)
        _, total = reabrir(destino)
        assert total == n_frames

    def test_o_gif_tem_o_tamanho_que_o_projeto_espera(self, tmp_path):
        destino = gif.montar_gif(quadros(), tmp_path / "x.gif", 21)
        im, _ = reabrir(destino)
        assert im.size == (192, 192)

    def test_todo_frame_e_keyframe_completo(self, tmp_path):
        """O bug da tela-preta: frames parciais viram lixo geométrico no decoder."""
        destino = gif.montar_gif(quadros(), tmp_path / "x.gif", 21)
        im, total = reabrir(destino)
        for i in range(total):
            im.seek(i)
            quadro = im.convert("RGBA")
            assert quadro.size == (192, 192)
            # nenhum pixel transparente = nada herdado do frame anterior
            assert quadro.getextrema()[3][0] == 255

    def test_todo_frame_decodifica_a_cor_certa(self, tmp_path):
        """Prova prática da paleta global: sem ela o decoder erra as cores.

        Não se inspeciona getpalette() — o Pillow encolhe a paleta por frame
        quando ele usa poucas cores. O que vale é o pixel decodificado.
        """
        esperadas = [(i * 40, 60, 200 - i * 30) for i in range(6)]
        destino = gif.montar_gif(quadros(), tmp_path / "x.gif", 21)
        im, _ = reabrir(destino)
        ordem = gif.pingpong(21, 6)
        for posicao, indice in enumerate(ordem):
            im.seek(posicao)
            r, g, b = im.convert("RGB").getpixel((96, 96))
            alvo = esperadas[indice]
            # quantização mexe alguns tons; o frame certo tem que estar perto
            assert abs(r - alvo[0]) < 30 and abs(b - alvo[2]) < 30

    def test_frames_diferentes_tem_conteudo_diferente(self, tmp_path):
        destino = gif.montar_gif(quadros(), tmp_path / "x.gif", 21)
        im, _ = reabrir(destino)
        im.seek(0)
        a = im.convert("RGB").tobytes()
        im.seek(3)
        b = im.convert("RGB").tobytes()
        assert a != b

    def test_o_gif_repete_em_loop(self, tmp_path):
        destino = gif.montar_gif(quadros(), tmp_path / "x.gif", 21)
        im, _ = reabrir(destino)
        assert im.info.get("loop") == 0

    def test_sem_quadros_e_recusado(self, tmp_path):
        with pytest.raises(ValueError, match="nenhum quadro"):
            gif.montar_gif([], tmp_path / "x.gif", 21)

    def test_n_frames_invalido_e_recusado(self, tmp_path):
        with pytest.raises(ValueError, match="n_frames"):
            gif.montar_gif(quadros(), tmp_path / "x.gif", 0)


class TestPaletaGlobal:
    def test_uma_paleta_cobre_todos_os_quadros(self):
        p = gif.paleta_global([q.resize((192, 192)) for q in quadros()])
        assert p.mode == "P"
        assert len(p.getpalette()) >= 3


class TestOpcoesQueOCompiladorExige:
    """O bug da tela-preta (frames parciais / lixo geométrico) é do decoder do
    _og.exe, NÃO do Pillow — que lê corretamente o GIF que ele mesmo escreveu.
    Nenhum teste em Python o reproduz; a prova real é o checkpoint visual no
    hardware. O que dá para verificar aqui é que as opções que o corrigem foram
    de fato aplicadas. Ver docs/05-runbook-clawd.md.
    """

    def test_grava_com_disposal_1_e_sem_otimizacao(self, tmp_path, monkeypatch):
        capturado = {}
        original = Image.Image.save

        def espiao(self, fp, *a, **k):
            capturado.update(k)
            return original(self, fp, *a, **k)

        monkeypatch.setattr(Image.Image, "save", espiao)
        gif.montar_gif(quadros_reais(), tmp_path / "clawd.gif", 21)

        assert capturado.get("disposal") == 1, "disposal!=1 gera frames parciais"
        assert capturado.get("optimize") is False, "optimize=True gera frames parciais"
        assert capturado.get("save_all") is True

    def test_todos_os_frames_quantizam_pela_mesma_paleta(self, tmp_path, monkeypatch):
        paletas = []
        original = Image.Image.quantize

        def espiao(self, colors=256, method=None, kmeans=0, palette=None, dither=1):
            paletas.append(id(palette) if palette is not None else None)
            return original(self, colors, method, kmeans, palette, dither)

        monkeypatch.setattr(Image.Image, "quantize", espiao)
        gif.montar_gif(quadros_reais(), tmp_path / "clawd.gif", 21)

        dos_frames = [p for p in paletas if p is not None]
        assert len(dos_frames) == 21, "todo frame passa pela paleta compartilhada"
        assert len(set(dos_frames)) == 1, "a paleta precisa ser a MESMA em todos"
