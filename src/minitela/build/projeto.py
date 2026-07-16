"""Manipulação do projeto AHMI (file.zip): troca de gifs e edição do data.json.

O zip de saída é montado pelo `zip` do sistema, não pelo zipfile do Python — o
compilador rejeita o segundo. É a única razão de haver subprocess por perto, e
ele mora em wine.py.
"""

import json
import shutil
import zipfile
from pathlib import Path

NOME_DATA = "data.json"


class ProjetoInvalido(ValueError):
    pass


class ProjetoAHMI:
    """Um file.zip extraído, pronto para ter gifs trocados e widgets zerados."""

    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)
        self._data_path = self._achar_data()

    def _achar_data(self) -> Path:
        achados = list(self.raiz.rglob(NOME_DATA))
        if not achados:
            raise ProjetoInvalido(f"{NOME_DATA} não encontrado em {self.raiz}")
        return achados[0]

    @classmethod
    def extrair(cls, zip_origem: Path, destino: Path) -> "ProjetoAHMI":
        destino = Path(destino)
        destino.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_origem) as z:
            z.extractall(destino)
        return cls(destino)

    def ler_data(self) -> dict:
        with open(self._data_path) as f:
            return json.load(f)

    def gravar_data(self, dados: dict) -> None:
        with open(self._data_path, "w") as f:
            json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))

    def substituir_gif(self, nome: str, novo: Path) -> Path:
        """Troca um gif de origem mantendo o nome — é o nome que liga à página."""
        alvos = list(self.raiz.rglob(nome))
        if not alvos:
            raise ProjetoInvalido(f"gif de origem ausente no projeto: {nome}")
        shutil.copyfile(novo, alvos[0])
        return alvos[0]

    def paginas(self) -> list:
        dados = self.ler_data()
        lista = dados.get("pageList")
        if not isinstance(lista, list):
            raise ProjetoInvalido("data.json sem pageList")
        return lista

    def validar_indice(self, indice: int) -> None:
        """R4: os índices de pageList são POSICIONAIS; nada garante que o índice
        ainda aponte a página certa. Falhar aqui é melhor que corromper o projeto.
        """
        paginas = self.paginas()
        if not 0 <= indice < len(paginas):
            raise ProjetoInvalido(
                f"página {indice} fora do projeto (tem {len(paginas)} páginas)"
            )

    def zerar_widgets(self, indice: int) -> int:
        """Esvazia os widgets de uma página, deixando só o fundo. Devolve quantos saíram."""
        self.validar_indice(indice)
        dados = self.ler_data()
        removidos = 0
        for canvas in dados["pageList"][indice].get("canvasList", []):
            for sub in canvas.get("subCanvasList", []):
                removidos += len(sub.get("widgetList", []))
                sub["widgetList"] = []
        self.gravar_data(dados)
        return removidos

    def trocar_fundo(self, indice: int, imagem: str) -> None:
        self.validar_indice(indice)
        dados = self.ler_data()
        dados["pageList"][indice]["backgroundImage"] = imagem
        self.gravar_data(dados)
