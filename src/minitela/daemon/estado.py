"""Decisão do que a Minitela deve mostrar. Puro: não lê arquivo nem toca hardware.

Precedência: override da tecla > alerta de tokens > modelo em uso.
"""

from dataclasses import dataclass

CONJUNTO_NORMAL = "normal"
CONJUNTO_ALERTA = "alerta"

# (substring do id do modelo, página, estado) — a ordem decide o empate.
MODELO_PARA_ESTADO = [
    ("opus", 6, "genius"),
    ("sonnet", 7, "smart"),
    ("fable", 5, "fogo"),
    ("haiku", 5, "fogo"),
]
PAGINA_FALLBACK = 5
ESTADO_FALLBACK = "fogo"

PAGINAS = {
    CONJUNTO_NORMAL: {5: "fogo", 6: "genius", 7: "smart"},
    CONJUNTO_ALERTA: {5: "fogo", 6: "chuva", 7: "fantasminha"},
}

PCT_CHUVA = 70
PCT_FANTASMA = 90


@dataclass(frozen=True)
class Decisao:
    conjunto: str
    pagina: int
    estado: str


def decidir_por_modelo(modelo: str | None) -> Decisao:
    ml = (modelo or "").lower()
    for chave, pagina, estado in MODELO_PARA_ESTADO:
        if chave in ml:
            return Decisao(CONJUNTO_NORMAL, pagina, estado)
    return Decisao(CONJUNTO_NORMAL, PAGINA_FALLBACK, ESTADO_FALLBACK)


def decidir_por_alerta(pior_pct: float) -> Decisao | None:
    if pior_pct >= PCT_FANTASMA:
        return Decisao(CONJUNTO_ALERTA, 7, "fantasminha")
    if PCT_CHUVA <= pior_pct < PCT_FANTASMA:
        return Decisao(CONJUNTO_ALERTA, 6, "chuva")
    return None


def decidir(
    modelo: str | None,
    pior_pct: float,
    pagina_override: int | None = None,
    conjunto_ativo: str = CONJUNTO_NORMAL,
) -> Decisao:
    """A decisão única do daemon.

    pagina_override: página escolhida na mão pela tecla física (vence tudo).
    conjunto_ativo: qual .acf está no hardware — o override cicla dentro dele.
    """
    if pagina_override is not None:
        estado = PAGINAS[conjunto_ativo][pagina_override]
        return Decisao(conjunto_ativo, pagina_override, estado)

    alerta = decidir_por_alerta(pior_pct)
    if alerta is not None:
        return alerta

    return decidir_por_modelo(modelo)


def proxima_pagina(conjunto: str, pagina: int | None) -> int:
    """Próxima página no ciclo da tecla, dentro do conjunto ativo."""
    paginas = sorted(PAGINAS[conjunto])
    if pagina not in paginas:
        return paginas[0]
    return paginas[(paginas.index(pagina) + 1) % len(paginas)]
