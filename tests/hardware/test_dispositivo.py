"""Exige a Minitela conectada. Rodar com: pytest -m hardware

Se o MCU estiver mudo, o único recurso é `sudo usbreset 0324:0324`.
Estes testes NÃO trocam a página ativa: o daemon está no ar e a tela é do usuário.
"""

import os

import pytest

from minitela.core.dispositivo import Minitela
from minitela.core.transporte import DEVICE_PADRAO

pytestmark = pytest.mark.hardware


@pytest.fixture
def minitela():
    if not os.path.exists(DEVICE_PADRAO):
        pytest.skip(f"{DEVICE_PADRAO} não existe — Minitela desconectada")
    if not os.access(DEVICE_PADRAO, os.R_OK | os.W_OK):
        pytest.skip(f"sem permissão em {DEVICE_PADRAO} — ver scripts/bootstrap-vendor.md")
    with Minitela() as m:
        yield m


def test_o_dispositivo_responde_ao_handshake(minitela):
    assert minitela.handshake() is True


def test_o_mcu_esta_drenando_o_serial(minitela):
    assert minitela.vivo() is True
