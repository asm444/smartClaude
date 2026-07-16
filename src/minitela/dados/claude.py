"""Leitura do modelo em uso e do consumo de tokens.

O home é fixo, não "~": o daemon roda como root e "~" viraria /root, onde não há
settings.json nem widget-data.json. Foi bug real. MINITELA_HOME sobrescreve.
"""

import json
import os
from dataclasses import dataclass

HOME_PADRAO = "/home/asm"


def home() -> str:
    return os.environ.get("MINITELA_HOME", HOME_PADRAO)


def caminho_settings() -> str:
    return os.path.join(home(), ".claude", "settings.json")


def caminho_widget_data() -> str:
    return os.path.join(home(), ".claude", "widget-data.json")


def _ler_json(caminho: str) -> dict:
    try:
        with open(caminho) as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def modelo_atual() -> str | None:
    """Modelo do último /model. É gravado na hora, ao contrário do transcript."""
    return _ler_json(caminho_settings()).get("model")


@dataclass(frozen=True)
class Uso:
    sessao: float
    semana_modelo: float
    semana_geral: float

    @property
    def pior(self) -> float:
        return max(self.sessao, self.semana_modelo, self.semana_geral)


def _pct(limites: dict, chave: str) -> float:
    entrada = limites.get(chave)
    if not isinstance(entrada, dict):
        return 0.0
    valor = entrada.get("percentUsed")
    return float(valor) if isinstance(valor, (int, float)) else 0.0


def _chave_semanal(modelo: str | None) -> str:
    ml = (modelo or "").lower()
    if "fable" in ml:
        return "weeklyFable"
    if "sonnet" in ml:
        return "weeklySonnet"
    return "weeklyAll"


def uso(modelo: str | None = None) -> Uso:
    limites = _ler_json(caminho_widget_data()).get("rateLimits", {})
    return Uso(
        sessao=_pct(limites, "session"),
        semana_modelo=_pct(limites, _chave_semanal(modelo)),
        semana_geral=_pct(limites, "weeklyAll"),
    )


def pior_percentual(modelo: str | None = None) -> float:
    return uso(modelo).pior
