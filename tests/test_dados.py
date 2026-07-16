import json

import pytest

from minitela.dados import claude


@pytest.fixture
def home_falso(tmp_path, monkeypatch):
    """Um ~/.claude sintético. Nunca lê o widget-data.json real (é perfil pessoal)."""
    (tmp_path / ".claude").mkdir()
    monkeypatch.setenv("MINITELA_HOME", str(tmp_path))

    def escrever(nome, dados):
        (tmp_path / ".claude" / nome).write_text(json.dumps(dados))

    return escrever


def limites(sessao=0, semana_all=0, semana_fable=0, semana_sonnet=0):
    return {
        "rateLimits": {
            "session": {"percentUsed": sessao},
            "weeklyAll": {"percentUsed": semana_all},
            "weeklyFable": {"percentUsed": semana_fable},
            "weeklySonnet": {"percentUsed": semana_sonnet},
            "plan": "Max (20x)",
            "source": "api",
        }
    }


class TestHome:
    def test_usa_o_home_do_usuario_e_nao_o_do_root(self, monkeypatch):
        monkeypatch.delenv("MINITELA_HOME", raising=False)
        assert claude.home() == "/home/asm"
        assert "/root" not in claude.caminho_settings()

    def test_env_sobrescreve_o_home(self, monkeypatch):
        monkeypatch.setenv("MINITELA_HOME", "/outro/lugar")
        assert claude.caminho_settings() == "/outro/lugar/.claude/settings.json"


class TestModeloAtual:
    def test_le_o_model_do_settings(self, home_falso):
        home_falso("settings.json", {"model": "opus"})
        assert claude.modelo_atual() == "opus"

    def test_settings_sem_model_devolve_none(self, home_falso):
        home_falso("settings.json", {"theme": "dark"})
        assert claude.modelo_atual() is None

    def test_settings_ausente_devolve_none_sem_estourar(self, home_falso):
        assert claude.modelo_atual() is None

    def test_settings_corrompido_devolve_none_sem_estourar(self, tmp_path, monkeypatch):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{ nao é json")
        monkeypatch.setenv("MINITELA_HOME", str(tmp_path))
        assert claude.modelo_atual() is None


class TestUso:
    def test_o_pior_considera_sessao_e_semana(self, home_falso):
        home_falso("widget-data.json", limites(sessao=30, semana_all=80))
        assert claude.pior_percentual() == 80

    def test_sessao_alta_ganha_da_semana_baixa(self, home_falso):
        home_falso("widget-data.json", limites(sessao=95, semana_all=10))
        assert claude.pior_percentual() == 95

    def test_fable_olha_a_semana_do_fable(self, home_falso):
        home_falso("widget-data.json", limites(semana_fable=88, semana_all=5))
        assert claude.pior_percentual("claude-fable-5") == 88

    def test_sonnet_olha_a_semana_do_sonnet(self, home_falso):
        home_falso("widget-data.json", limites(semana_sonnet=72, semana_all=5))
        assert claude.pior_percentual("sonnet") == 72

    def test_opus_cai_na_semana_geral(self, home_falso):
        home_falso("widget-data.json", limites(semana_all=60, semana_fable=99))
        assert claude.pior_percentual("claude-opus-4-8") == 60

    def test_semana_geral_sempre_conta_mesmo_com_modelo_especifico(self, home_falso):
        home_falso("widget-data.json", limites(semana_fable=10, semana_all=91))
        assert claude.pior_percentual("fable") == 91

    def test_arquivo_ausente_devolve_zero_sem_estourar(self, home_falso):
        assert claude.pior_percentual() == 0.0

    def test_campo_de_texto_no_lugar_de_numero_nao_derruba(self, home_falso):
        home_falso("widget-data.json", {"rateLimits": {"session": "indisponível"}})
        assert claude.pior_percentual() == 0.0

    def test_percentual_nulo_conta_como_zero(self, home_falso):
        home_falso("widget-data.json", {"rateLimits": {"session": {"percentUsed": None}}})
        assert claude.pior_percentual() == 0.0
