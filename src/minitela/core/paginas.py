"""Registradores e páginas do projeto AHMI de fábrica.

Mapa confirmado no hardware — ver docs/04-limites-do-dispositivo.md.
"""

REG_CURRENT_PAGE = 2

PAGINA_SEMANA = 2
PAGINA_SESSAO = 3
PAGINA_FABLE = 4

PAGINAS_GIF = (5, 6, 7)

# Quantidade de frames que a page-def do FIRMWARE espera por página de gif.
# Não é derivável do gif de fábrica (que tem 1 frame): é constante do firmware.
FRAMES_POR_PAGINA = {5: 21, 6: 30, 7: 44}
