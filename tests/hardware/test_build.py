"""Exige o file.zip de fábrica e o compilador via Wine. pytest -m hardware"""

from pathlib import Path

import pytest

from minitela.build import acf, file_zip_padrao

pytestmark = pytest.mark.hardware

BASELINE = Path.home() / "telinha" / "minitela-oficial" / "clawd-anim.acf"


def test_o_pipeline_python_gera_acf_compativel_com_o_do_shell(tmp_path):
    if not file_zip_padrao().exists():
        pytest.skip("file.zip de fábrica ausente — ver scripts/bootstrap-vendor.md")
    if not BASELINE.exists():
        pytest.skip("baseline clawd-anim.acf ausente")

    from minitela.build import montar_conjunto

    gerado = montar_conjunto("normal", tmp_path / "clawd-anim.acf")
    assert acf.compativel(gerado, BASELINE)
