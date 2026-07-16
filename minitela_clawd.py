#!/usr/bin/env python3
"""
Daemon da Minitela — o Clawd reflete o MODELO em uso no Claude Code; um ALERTA de
tokens sobrepoe fantasminha/chuva quando o limite aperta; e a tecla fisica cicla os
3 bichinhos do conjunto ATIVO.

ESTADOS (cada um = um .acf com 3 Clawds nas paginas 5/6/7):
  NORMAL (clawd-anim.acf):  pag5=fogo, pag6=genius, pag7=smart
  ALERTA (clawd-alerta.acf): pag5=fogo, pag6=chuva, pag7=fantasminha

- MODELO: opus->genius(pag6), sonnet->smart(pag7), fable->fogo(pag5). Le o ultimo
  /model de settings.json. Troca instantanea (so show-page) dentro do conjunto normal.
- ALERTA de tokens: a cada 1h verifica max(sessao%, semana%) do widget-data. >=90% =
  fantasminha, 70-90% = chuva, <70% = normal. Ao entrar/sair de alerta, troca o
  CONJUNTO (re-upload ~15s, raro). Dura 20min.
- TECLA (F16): override manual. Cicla os 3 bichinhos do CONJUNTO ATIVO (no normal:
  fogo/genius/smart; no alerta: fogo/chuva/fantasminha). Apos OVERRIDE_SEC, volta ao
  automatico (modelo, ou alerta se ainda ativo).

Precisa de ROOT (le a tecla em /dev/input/event3). Requer clawd-anim.acf e
clawd-alerta.acf ja gerados (minitela build normal|alerta -o <saida>).

Uso:
  sudo python3 minitela_clawd.py
  sudo python3 minitela_clawd.py --no-key   # sem tecla (nao precisa root)
  sudo python3 minitela_clawd.py --print    # imprime o estado atual e sai
"""
import glob
import json
import os
import select
import struct
import subprocess
import sys
import time

from minitela import Minitela

# home do USUARIO fixo (o daemon roda como root, e "~" viraria /root — onde nao ha
# settings.json/widget-data.json; foi bug real). Env MINITELA_HOME sobrescreve.
_USER_HOME = os.environ.get("MINITELA_HOME", "/home/asm")
_BASE = os.path.join(_USER_HOME, "telinha")
SETTINGS_JSON = os.path.join(_USER_HOME, ".claude", "settings.json")
WIDGET_DATA = os.path.join(_USER_HOME, ".claude", "widget-data.json")
SIDECAR = os.path.join(_BASE, "sidecar", "SideCar-fixed")

# --- conjuntos (.acf) e o que cada pagina mostra em cada um ---
ACF_NORMAL = os.path.join(_BASE, "minitela-oficial", "clawd-anim.acf")
ACF_ALERTA = os.path.join(_BASE, "minitela-oficial", "clawd-alerta.acf")
# pagina (RegCurrentPage) -> nome do bichinho, por conjunto
PAGS_NORMAL = {5: "fogo", 6: "genius", 7: "smart"}
PAGS_ALERTA = {5: "fogo", 6: "chuva", 7: "fantasminha"}

# --- modelo -> pagina (no conjunto NORMAL) ---
MODELO_PAGINA = [("opus", 6), ("sonnet", 7), ("fable", 5), ("haiku", 5)]
PAGINA_FALLBACK = 5

# --- alerta de tokens ---
ALERTA_CHECK_SEC = 3600   # verifica a regra a cada 1h
ALERTA_DUR_SEC = 20 * 60  # dura 20min em alerta
ALERTA_CHUVA = (70, 90)   # 70-90% -> chuva (pag 6 do conjunto alerta)
ALERTA_FANTASMA = 90      # >=90% -> fantasminha (pag 7)

# --- tecla ---
KEY_MINITELA = 186  # KEY_F16
OVERRIDE_SEC = 20   # override manual antes de voltar ao automatico
POLL_SEC = 3        # frequencia de checagem do modelo

EV_FORMAT = "llHHi"
EV_SIZE = struct.calcsize(EV_FORMAT)
EV_KEY = 0x01


# ----------------------------------------------------------------------------- IO
def find_keyboard_dev():
    word, bit = KEY_MINITELA // 64, KEY_MINITELA % 64
    for path in sorted(glob.glob("/dev/input/event*")):
        n = os.path.basename(path)
        try:
            caps = open(f"/sys/class/input/{n}/device/capabilities/key").read().split()[::-1]
            if word < len(caps) and (int(caps[word], 16) >> bit) & 1:
                return path
        except Exception:
            continue
    return "/dev/input/event3"


def modelo_atual():
    """Ultimo /model de settings.json (nome curto). None se indisponivel."""
    try:
        with open(SETTINGS_JSON) as f:
            return (json.load(f) or {}).get("model")
    except (OSError, ValueError):
        return None


def pagina_do_modelo(modelo):
    ml = (modelo or "").lower()
    for chave, pagina in MODELO_PAGINA:
        if chave in ml:
            return pagina
    return PAGINA_FALLBACK


def pior_percentual(modelo):
    """Maior % usado entre sessao atual e semana do modelo (o mais critico)."""
    try:
        with open(WIDGET_DATA) as f:
            rl = (json.load(f) or {}).get("rateLimits", {})
    except (OSError, ValueError):
        return 0.0
    def pct(k):
        v = (rl.get(k) or {}).get("percentUsed")
        return float(v) if isinstance(v, (int, float)) else 0.0
    ml = (modelo or "").lower()
    if "fable" in ml:
        semana = pct("weeklyFable")
    elif "sonnet" in ml:
        semana = pct("weeklySonnet")
    else:
        semana = pct("weeklyAll")
    return max(pct("session"), semana, pct("weeklyAll"))


def alerta_pagina(pct):
    """Dado o pior%, retorna a pagina do bichinho de alerta no CONJUNTO ALERTA, ou
    None se nao ha alerta (normal). fantasminha=7, chuva=6."""
    if pct >= ALERTA_FANTASMA:
        return 7   # fantasminha
    if ALERTA_CHUVA[0] <= pct < ALERTA_CHUVA[1]:
        return 6   # chuva
    return None


def _show(pagina):
    """Troca a pagina ativa (instantaneo). True se o MCU aceitou."""
    try:
        with Minitela() as m:
            if not m.alive():
                print("  MCU mudo — sudo usbreset 0324:0324", flush=True)
                return False
            m.show_page(pagina)
        return True
    except Exception as e:
        print(f"  erro ao trocar pagina: {e}", flush=True)
        return False


def _subir_conjunto(acf):
    """Re-sobe o .acf de um conjunto (normal/alerta) e da respiro. Raro (~15s)."""
    if not os.path.exists(acf):
        print(f"  conjunto ausente: {acf}", flush=True)
        return False
    r = subprocess.run([SIDECAR, "-mode", "cli", "-cmd", "upload",
                        "-file", acf, "-type", "texture"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"  upload falhou: {r.stderr.strip()[:80]}", flush=True)
        return False
    time.sleep(6)  # respiro: upload deixa o serial ocupado ~6s
    return True


# --------------------------------------------------------------------------- LOOP
def run(escuta_tecla=True):
    # estado
    conjunto = None        # 'normal' | 'alerta' — qual .acf esta no hardware
    pagina_atual = None
    override_ate = 0.0
    alerta_ate = 0.0       # ate quando o alerta vale
    ultimo_poll = 0.0
    ultima_check_alerta = 0.0

    def paginas_ativas():
        return PAGS_ALERTA if conjunto == "alerta" else PAGS_NORMAL

    def garantir_conjunto(nome, acf):
        """Garante que o .acf certo esta no hardware. Retorna True se ok."""
        nonlocal conjunto
        if conjunto == nome:
            return True
        if _subir_conjunto(acf):
            conjunto = nome
            return True
        return False

    # abre a tecla
    f = None
    if escuta_tecla:
        if os.geteuid() != 0:
            print("  AVISO: sem root — nao vai ler a tecla (use sudo ou --no-key).",
                  flush=True)
        dev = find_keyboard_dev()
        try:
            f = open(dev, "rb")
            os.set_blocking(f.fileno(), False)
            print(f"  tecla: {dev} (F16={KEY_MINITELA})", flush=True)
        except (PermissionError, OSError) as e:
            print(f"  sem tecla ({e}); seguindo so o automatico.", flush=True)
            f = None

    print("Clawd na Minitela: modelo (opus=genio/sonnet=smart/fable=fogo) + alerta de "
          "tokens (fantasminha/chuva). Tecla cicla os 3 do conjunto ativo.", flush=True)

    # estado inicial: sobe o conjunto normal e aplica o modelo
    garantir_conjunto("normal", ACF_NORMAL)
    pg = pagina_do_modelo(modelo_atual())
    if _show(pg):
        pagina_atual = pg

    poller = select.poll()
    if f is not None:
        poller.register(f.fileno(), select.POLLIN)

    while True:
        # 1) TECLA: override, cicla os 3 do conjunto ATIVO
        if f is not None and poller.poll(200):
            data = f.read(EV_SIZE)
            while data and len(data) == EV_SIZE:
                _, _, etype, code, value = struct.unpack(EV_FORMAT, data)
                if etype == EV_KEY and code == KEY_MINITELA and value == 1:
                    pags = sorted(paginas_ativas())       # [5,6,7]
                    i = (pags.index(pagina_atual) + 1) % len(pags) \
                        if pagina_atual in pags else 0
                    pg = pags[i]
                    if _show(pg):
                        pagina_atual = pg
                        override_ate = time.time() + OVERRIDE_SEC
                        print(f"  [tecla] {paginas_ativas()[pg]} (pag {pg}) — "
                              f"override {OVERRIDE_SEC}s", flush=True)
                data = f.read(EV_SIZE)
        else:
            time.sleep(0.05)

        agora = time.time()
        em_override = agora < override_ate

        # 1b) FIM do override manual: restaura o estado AUTOMATICO correto.
        #     Se ainda em alerta -> a pagina do alerta; senao -> a pagina do modelo.
        #     (sem isto, a tela ficaria presa onde a tecla parou — era o bug do
        #      "apertei a tecla e nao voltou pra fantasminha").
        if override_ate and not em_override:
            override_ate = 0.0
            if conjunto == "alerta" and agora < alerta_ate:
                pg = alerta_pagina(pior_percentual(modelo_atual())) or 7
            else:
                pg = pagina_do_modelo(modelo_atual())
            if pg != pagina_atual and _show(pg):
                pagina_atual = pg
                nome = paginas_ativas().get(pg, "?")
                print(f"  [auto] fim do override -> {nome} (pag {pg})", flush=True)

        # 2) ALERTA: verifica de hora em hora (nao durante override)
        if not em_override and agora - ultima_check_alerta >= ALERTA_CHECK_SEC:
            ultima_check_alerta = agora
            mdl = modelo_atual()
            pct = pior_percentual(mdl)
            pg_alerta = alerta_pagina(pct)
            if pg_alerta is not None:
                # entra/renova alerta: garante o conjunto alerta e mostra o bichinho
                if garantir_conjunto("alerta", ACF_ALERTA):
                    alerta_ate = agora + ALERTA_DUR_SEC
                    if _show(pg_alerta):
                        pagina_atual = pg_alerta
                    print(f"  [alerta] tokens {pct:.0f}% -> "
                          f"{PAGS_ALERTA[pg_alerta]} por 20min", flush=True)
            else:
                print(f"  [alerta] tokens {pct:.0f}% -> normal", flush=True)

        # 3) FIM do alerta: passou 20min -> volta ao conjunto normal + modelo
        if conjunto == "alerta" and not em_override and agora >= alerta_ate:
            if garantir_conjunto("normal", ACF_NORMAL):
                pg = pagina_do_modelo(modelo_atual())
                if _show(pg):
                    pagina_atual = pg
                print(f"  [alerta] fim -> volta ao modelo (pag {pg})", flush=True)

        # 4) MODELO: segue o /model (so no conjunto normal, fora de override/alerta)
        if (conjunto == "normal" and not em_override
                and agora >= alerta_ate and agora - ultimo_poll >= POLL_SEC):
            ultimo_poll = agora
            mdl = modelo_atual()
            pg = pagina_do_modelo(mdl)
            if pg != pagina_atual:
                if _show(pg):
                    pagina_atual = pg
                    print(f"  [modelo] {mdl} -> {PAGS_NORMAL[pg]} (pag {pg})",
                          flush=True)


def _print_estado():
    mdl = modelo_atual()
    pct = pior_percentual(mdl)
    pg_alerta = alerta_pagina(pct)
    if pg_alerta:
        print(f"modelo={mdl}  tokens={pct:.0f}%  -> ALERTA {PAGS_ALERTA[pg_alerta]} "
              f"(conjunto alerta, pag {pg_alerta})")
    else:
        pg = pagina_do_modelo(mdl)
        print(f"modelo={mdl}  tokens={pct:.0f}%  -> {PAGS_NORMAL[pg]} "
              f"(conjunto normal, pag {pg})")


if __name__ == "__main__":
    if "--print" in sys.argv:
        _print_estado()
    else:
        run(escuta_tecla="--no-key" not in sys.argv)
