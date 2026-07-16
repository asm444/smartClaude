import json
import zipfile

import pytest

from minitela.build.projeto import ProjetoAHMI, ProjetoInvalido


@pytest.fixture
def projeto(projeto_sintetico, tmp_path):
    return ProjetoAHMI.extrair(projeto_sintetico, tmp_path / "extraido")


class TestExtrair:
    def test_acha_o_data_json(self, projeto):
        assert projeto.ler_data()["author"] == "teste"

    def test_le_as_dez_paginas(self, projeto):
        assert len(projeto.paginas()) == 10

    def test_zip_sem_data_json_e_recusado(self, tmp_path):
        vazio = tmp_path / "vazio.zip"
        with zipfile.ZipFile(vazio, "w") as z:
            z.writestr("leiame.txt", "nada aqui")
        with pytest.raises(ProjetoInvalido, match="data.json"):
            ProjetoAHMI.extrair(vazio, tmp_path / "x")


class TestZerarWidgets:
    def test_esvazia_a_lista_de_widgets_da_pagina(self, projeto):
        projeto.zerar_widgets(1)
        sub = projeto.ler_data()["pageList"][1]["canvasList"][0]["subCanvasList"][0]
        assert sub["widgetList"] == []

    def test_devolve_quantos_widgets_saíram(self, projeto):
        assert projeto.zerar_widgets(1) == 2

    def test_nao_mexe_nas_outras_paginas(self, projeto):
        antes = json.dumps(projeto.ler_data()["pageList"][2])
        projeto.zerar_widgets(1)
        assert json.dumps(projeto.ler_data()["pageList"][2]) == antes

    def test_preserva_o_resto_da_pagina(self, projeto):
        projeto.zerar_widgets(1)
        pagina = projeto.ler_data()["pageList"][1]
        assert pagina["backgroundImage"] == "r-1-0.png"
        assert pagina["id"] == "pagina-1"

    def test_zerar_duas_vezes_nao_quebra(self, projeto):
        projeto.zerar_widgets(1)
        assert projeto.zerar_widgets(1) == 0


class TestValidarIndice:
    def test_pagina_alem_do_fim_e_recusada(self, projeto):
        with pytest.raises(ProjetoInvalido, match="fora do projeto"):
            projeto.zerar_widgets(99)

    def test_indice_negativo_e_recusado(self, projeto):
        with pytest.raises(ProjetoInvalido, match="fora do projeto"):
            projeto.zerar_widgets(-1)

    def test_a_ultima_pagina_e_valida(self, projeto):
        projeto.validar_indice(9)

    def test_data_json_sem_pagelist_e_recusado(self, projeto):
        projeto.gravar_data({"author": "x"})
        with pytest.raises(ProjetoInvalido, match="pageList"):
            projeto.paginas()


class TestSubstituirGif:
    def test_troca_o_conteudo_mantendo_o_nome(self, projeto, tmp_path):
        novo = tmp_path / "novo.gif"
        novo.write_bytes(b"GIF89a-conteudo-novo")
        destino = projeto.substituir_gif("1i1h1e37393671471.gif", novo)
        assert destino.name == "1i1h1e37393671471.gif"
        assert destino.read_bytes() == b"GIF89a-conteudo-novo"

    def test_gif_que_nao_existe_no_projeto_e_recusado(self, projeto, tmp_path):
        qualquer = tmp_path / "x.gif"
        qualquer.write_bytes(b"GIF89a")
        with pytest.raises(ProjetoInvalido, match="ausente"):
            projeto.substituir_gif("nao-existe.gif", qualquer)


class TestTrocarFundo:
    def test_troca_a_imagem_de_fundo(self, projeto):
        projeto.trocar_fundo(2, "nova.png")
        assert projeto.ler_data()["pageList"][2]["backgroundImage"] == "nova.png"

    def test_valida_o_indice_antes_de_trocar(self, projeto):
        with pytest.raises(ProjetoInvalido):
            projeto.trocar_fundo(50, "x.png")
