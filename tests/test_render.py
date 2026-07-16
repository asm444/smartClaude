import pytest

from minitela.render import clawd, comum, telas


def luminancia_media(img, caixa=None):
    px = img.convert("L").crop(caixa) if caixa else img.convert("L")
    dados = list(px.getdata())
    return sum(dados) / len(dados)


class TestSpritesVendorizados:
    def test_o_clawd_rasterizado_esta_no_pacote(self):
        assert (clawd.dir_sprites() / "clawd-160.png").exists()

    @pytest.mark.parametrize("prefixo", ["halo", "smart", "rain", "fire", "skull"])
    def test_cada_overlay_tem_os_seis_frames(self, prefixo):
        for f in range(clawd.FRAMES_POR_ESTADO):
            assert (clawd.dir_sprites() / f"{prefixo}-{f}.png").exists()

    def test_a_licenca_dos_sprites_acompanha(self):
        licenca = (clawd.dir_sprites() / "LICENSE").read_text()
        assert "MIT" in licenca and "claude-usage-widget" in licenca

    def test_env_sobrescreve_o_diretorio(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MINITELA_SPRITES", str(tmp_path))
        assert clawd.dir_sprites() == tmp_path


class TestComporClawd:
    @pytest.mark.parametrize("estado", ["genius", "smart", "slow", "dumb", "braindead"])
    def test_todo_estado_gera_uma_tela_do_tamanho_certo(self, estado):
        assert clawd.compor(estado).size == (240, 240)

    def test_a_tela_e_opaca_rgb(self):
        assert clawd.compor("dumb").mode == "RGB"

    def test_o_fundo_e_claro_como_o_compilador_exige(self):
        # o compilador AHMI corrompe tons escuros; canto = fundo puro
        assert luminancia_media(clawd.compor("dumb"), (0, 0, 20, 20)) > 200

    def test_os_apelidos_do_daemon_resolvem(self):
        assert clawd.resolver_estado("fogo") == "dumb"
        assert clawd.resolver_estado("chuva") == "slow"
        assert clawd.resolver_estado("fantasminha") == "braindead"

    def test_estado_desconhecido_e_recusado(self):
        with pytest.raises(ValueError, match="desconhecido"):
            clawd.compor("inexistente")

    def test_frames_diferentes_geram_imagens_diferentes(self):
        # se os frames fossem iguais, o gif não animaria
        assert clawd.compor("dumb", 0).tobytes() != clawd.compor("dumb", 3).tobytes()

    def test_o_frame_da_a_volta(self):
        assert clawd.compor("dumb", 6).tobytes() == clawd.compor("dumb", 0).tobytes()

    def test_compor_frames_devolve_os_seis(self):
        assert len(clawd.compor_frames("genius")) == 6

    def test_a_caveira_esconde_o_clawd(self):
        # braindead substitui o mascote; sem ele sobra mais fundo claro
        com_clawd = luminancia_media(clawd.compor("dumb"))
        caveira = luminancia_media(clawd.compor("braindead"))
        assert caveira > com_clawd

    def test_sprite_ausente_da_erro_claro(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MINITELA_SPRITES", str(tmp_path))
        with pytest.raises(clawd.SpriteAusente, match="não encontrado"):
            clawd.compor("dumb")


class TestSemOWidgetInstalado:
    def test_render_nao_depende_do_diretorio_do_widget(self, monkeypatch):
        """R5 dissolvido: os sprites são do pacote, não de ~/projects/."""
        monkeypatch.setenv("HOME", "/tmp/home-que-nao-existe")
        assert clawd.compor("genius").size == (240, 240)

    def test_render_nao_dispara_processo_externo(self, monkeypatch):
        """D16: o magick sai do caminho de render; o SVG já vem rasterizado."""
        import subprocess

        def proibido(*a, **k):
            raise AssertionError("render não pode chamar subprocess")

        monkeypatch.setattr(subprocess, "run", proibido)
        monkeypatch.setattr(subprocess, "Popen", proibido)
        assert clawd.compor("genius").size == (240, 240)


class TestRenderTela:
    def test_a_tela_tem_o_tamanho_da_minitela(self):
        assert telas.render_tela("Semanal", 42).size == (240, 240)

    def test_fundo_claro(self):
        assert luminancia_media(telas.render_tela("Semanal", 42), (0, 60, 10, 80)) > 200

    def test_percentuais_diferentes_geram_telas_diferentes(self):
        a = telas.render_tela("Semanal", 10).tobytes()
        b = telas.render_tela("Semanal", 90).tobytes()
        assert a != b

    def test_rotulos_diferentes_geram_telas_diferentes(self):
        a = telas.render_tela("Semanal", 50).tobytes()
        b = telas.render_tela("Sessao", 50).tobytes()
        assert a != b

    def test_pct_acima_de_cem_nao_estoura_a_barra(self):
        assert telas.render_tela("Semanal", 150).size == (240, 240)

    def test_zero_por_cento_ainda_desenha_a_barra(self):
        assert telas.render_tela("Semanal", 0).size == (240, 240)


class TestCorPorPct:
    @pytest.mark.parametrize(
        "pct, cor",
        [
            (0, comum.VERDE),
            (49.9, comum.VERDE),
            (50, comum.AMARELO),
            (79.9, comum.AMARELO),
            (80, comum.VERMELHO),
            (100, comum.VERMELHO),
        ],
    )
    def test_fronteiras_de_cor(self, pct, cor):
        assert comum.cor_por_pct(pct) == cor

    def test_cor_da_tela_nao_usa_as_fronteiras_do_alerta(self):
        """50/80 (cor) e 70/90 (alerta) são escalas distintas, de propósito."""
        from minitela.daemon import estado

        assert (comum.PCT_ATENCAO, comum.PCT_CRITICO) != (estado.PCT_CHUVA, estado.PCT_FANTASMA)


class TestCarregarFonte:
    def test_sempre_devolve_uma_fonte(self):
        assert comum.carregar_fonte(26) is not None

    def test_tamanhos_diferentes_dao_metricas_diferentes(self):
        pequena = comum.carregar_fonte(15).getbbox("100%")
        grande = comum.carregar_fonte(88).getbbox("100%")
        assert grande[2] > pequena[2]
