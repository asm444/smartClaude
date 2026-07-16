import pytest

from minitela.daemon import estado as e


class TestDecidirPorModelo:
    @pytest.mark.parametrize(
        "modelo, pagina, nome",
        [
            ("claude-opus-4-8", 6, "genius"),
            ("opus", 6, "genius"),
            ("claude-sonnet-5", 7, "smart"),
            ("sonnet", 7, "smart"),
            ("claude-fable-5", 5, "fogo"),
            ("fable", 5, "fogo"),
            ("claude-haiku-4-5", 5, "fogo"),
        ],
    )
    def test_cada_modelo_tem_seu_bichinho(self, modelo, pagina, nome):
        d = e.decidir_por_modelo(modelo)
        assert (d.pagina, d.estado) == (pagina, nome)

    def test_modelo_desconhecido_cai_no_fogo(self):
        assert e.decidir_por_modelo("modelo-que-nao-existe").pagina == 5

    def test_sem_modelo_cai_no_fogo(self):
        assert e.decidir_por_modelo(None).pagina == 5

    def test_o_id_completo_e_o_curto_dao_o_mesmo_bichinho(self):
        assert e.decidir_por_modelo("claude-opus-4-8") == e.decidir_por_modelo("opus")

    def test_maiuscula_nao_muda_a_decisao(self):
        assert e.decidir_por_modelo("CLAUDE-OPUS-4-8").estado == "genius"

    def test_modelo_nunca_ativa_o_conjunto_de_alerta(self):
        for m in ["opus", "sonnet", "fable", None, "xpto"]:
            assert e.decidir_por_modelo(m).conjunto == e.CONJUNTO_NORMAL


class TestDecidirPorAlerta:
    @pytest.mark.parametrize(
        "pct, esperado",
        [
            (0, None),
            (69.9, None),
            (70, "chuva"),
            (89.9, "chuva"),
            (90, "fantasminha"),
            (100, "fantasminha"),
            (150, "fantasminha"),
        ],
    )
    def test_fronteiras_do_alerta(self, pct, esperado):
        d = e.decidir_por_alerta(pct)
        assert (d.estado if d else None) == esperado

    def test_alerta_sempre_usa_o_conjunto_de_alerta(self):
        assert e.decidir_por_alerta(95).conjunto == e.CONJUNTO_ALERTA


class TestPrecedencia:
    def test_tecla_vence_o_alerta(self):
        d = e.decidir("opus", 95, pagina_override=5, conjunto_ativo=e.CONJUNTO_ALERTA)
        assert (d.pagina, d.estado) == (5, "fogo")

    def test_tecla_vence_o_modelo(self):
        d = e.decidir("opus", 0, pagina_override=7)
        assert (d.pagina, d.estado) == (7, "smart")

    def test_alerta_vence_o_modelo(self):
        d = e.decidir("opus", 95)
        assert (d.conjunto, d.estado) == (e.CONJUNTO_ALERTA, "fantasminha")

    def test_sem_alerta_nem_tecla_manda_o_modelo(self):
        d = e.decidir("opus", 10)
        assert (d.conjunto, d.estado) == (e.CONJUNTO_NORMAL, "genius")

    def test_override_cicla_dentro_do_conjunto_ativo(self):
        d = e.decidir("opus", 95, pagina_override=6, conjunto_ativo=e.CONJUNTO_ALERTA)
        assert d.estado == "chuva"

    def test_mesma_pagina_muda_de_bichinho_conforme_o_conjunto(self):
        normal = e.decidir("x", 0, pagina_override=6, conjunto_ativo=e.CONJUNTO_NORMAL)
        alerta = e.decidir("x", 0, pagina_override=6, conjunto_ativo=e.CONJUNTO_ALERTA)
        assert (normal.estado, alerta.estado) == ("genius", "chuva")


class TestProximaPagina:
    def test_cicla_as_tres_paginas_de_gif(self):
        assert [
            e.proxima_pagina(e.CONJUNTO_NORMAL, 5),
            e.proxima_pagina(e.CONJUNTO_NORMAL, 6),
            e.proxima_pagina(e.CONJUNTO_NORMAL, 7),
        ] == [6, 7, 5]

    def test_volta_ao_inicio_depois_da_ultima(self):
        assert e.proxima_pagina(e.CONJUNTO_NORMAL, 7) == 5

    def test_pagina_desconhecida_comeca_do_inicio(self):
        assert e.proxima_pagina(e.CONJUNTO_NORMAL, None) == 5
        assert e.proxima_pagina(e.CONJUNTO_NORMAL, 99) == 5

    def test_ciclo_completo_passa_por_todas_sem_repetir(self):
        vistas, pag = [], 5
        for _ in range(3):
            vistas.append(pag)
            pag = e.proxima_pagina(e.CONJUNTO_NORMAL, pag)
        assert sorted(vistas) == [5, 6, 7]
        assert pag == 5


class TestConsistenciaDosConjuntos:
    def test_os_dois_conjuntos_cobrem_as_mesmas_paginas(self):
        assert set(e.PAGINAS[e.CONJUNTO_NORMAL]) == set(e.PAGINAS[e.CONJUNTO_ALERTA])

    def test_todo_estado_do_modelo_existe_no_conjunto_normal(self):
        for _, pagina, nome in e.MODELO_PARA_ESTADO:
            assert e.PAGINAS[e.CONJUNTO_NORMAL][pagina] == nome
