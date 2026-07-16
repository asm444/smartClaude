#!/usr/bin/env python3
"""
Daemon da Minitela: escuta a tecla física "Minitela" (KEY_PROG1) e alterna entre
as 3 telas de uso do Claude (Semanal / Sessão / Fable) na telinha.

As telas já estão gravadas no firmware (via ACF recompilado); este daemon só troca
a página ativa (RegCurrentPage) a cada toque da tecla. Mapeamento:
  valor 2 = Semanal, valor 3 = Sessão, valor 4 = Fable.

Requer acesso a /dev/input/event3 (teclado "AT Translated Set 2 keyboard") e a
/dev/ttyACM0. Rode com sudo, ou adicione o usuário aos grupos input e dialout.

Uso:
  python3 minitela_daemon.py            # roda o loop, alterna nas teclas
  python3 minitela_daemon.py --detect   # modo detecção: mostra o keycode de cada tecla
"""

import glob
import os
import struct
import sys

from minitela import Minitela

# páginas a ciclar (valor de RegCurrentPage) — em ordem de rotação.
# Default: os 3 GIFs animados do Clawd (páginas de animação 5/6/7).
# Modos (por flag na linha de comando):
#   (default)   gifs animados do Clawd     -> páginas 5,6,7
#   --estatico  Clawd estático nos 5 estados -> páginas 1,2,3,4,5
#   --dash      dashboards de uso do Claude   -> páginas 2,3,4
GIF_PAGES = [5, 6, 7]        # Gif1(fogo), Gif2(chuva), Gif3(caveira) — os que animam
ESTATICO_PAGES = [1, 2, 3, 4, 5]  # genius, smart, slow, dumb, braindead
DASH_PAGES = [2, 3, 4]      # Semanal, Sessao, Fable

# modo --ciclo-gif: os 5 estados ANIMADOS, um por vez, todos na página de gif 5.
# A cada toque sobe o .acf do próximo estado (~11s de upload) e ativa a página 5.
CICLO_GIF_STATES = ["dumb", "genius", "smart", "slow", "braindead"]
CICLO_GIF_NAMES = {"dumb": "fogo", "genius": "genius", "smart": "smart",
                   "slow": "chuva", "braindead": "caveira"}
CICLO_GIF_PAGE = 5
_HERE = os.path.dirname(os.path.abspath(__file__))
SIDECAR = os.path.join(_HERE, "sidecar", "SideCar-fixed")
def _acf_for(state):
    return os.path.join(_HERE, "minitela-oficial", f"clawd-gif-{state}.acf")
PAGES = GIF_PAGES           # default; sobrescrito por flag em __main__
PAGE_NAMES = {
    1: "Clawd-genius", 2: "Clawd-smart/Semanal", 3: "Clawd-slow/Sessao",
    4: "Clawd-dumb/Fable", 5: "Clawd-fogo-gif",
    6: "Clawd-chuva-gif", 7: "Clawd-caveira-gif",
}

KEYBOARD_DEV = "/dev/input/event3"  # AT Translated Set 2 keyboard
KEY_MINITELA = 186  # KEY_F16 — a tecla física Minitela neste hardware (Fedora/KDE).

# struct input_event: (tv_sec, tv_usec, type, code, value) — long,long,H,H,i
# em x86_64: 16 bytes de timeval + H + H + i = 24 bytes
EV_FORMAT = "llHHi"
EV_SIZE = struct.calcsize(EV_FORMAT)
EV_KEY = 0x01


def find_keyboard_dev():
    """Acha o event* cujo device consegue emitir KEY_MINITELA. Fallback: KEYBOARD_DEV."""
    # bit KEY_MINITELA no bitmask de capabilities/key (long de 64 bits por palavra)
    word = KEY_MINITELA // 64
    bit = KEY_MINITELA % 64
    for path in sorted(glob.glob("/dev/input/event*")):
        n = os.path.basename(path)
        try:
            caps = open(f"/sys/class/input/{n}/device/capabilities/key").read().split()
            # caps é hex, palavra mais significativa primeiro
            caps_rev = caps[::-1]
            if word < len(caps_rev) and (int(caps_rev[word], 16) >> bit) & 1:
                return path
        except Exception:
            continue
    return KEYBOARD_DEV


def detect_mode():
    """Mostra o keycode de cada tecla pressionada — pra achar a tecla Minitela."""
    print(f"Lendo {KEYBOARD_DEV}. Pressione a tecla Minitela (Ctrl-C pra sair).")
    with open(KEYBOARD_DEV, "rb") as f:
        while True:
            data = f.read(EV_SIZE)
            if len(data) < EV_SIZE:
                continue
            _, _, etype, code, value = struct.unpack(EV_FORMAT, data)
            if etype == EV_KEY and value == 1:  # key press
                print(f"  tecla pressionada: keycode={code}")


def _open_keyboard(retries=30, delay=2):
    """Abre o device da tecla, esperando ele aparecer (boot/replug). Robusto p/ systemd.
    PermissionError => precisa de root; falha na hora com mensagem clara (não fica em
    loop silencioso). FileNotFound => device ainda não apareceu; aí sim espera."""
    import time
    for tent in range(retries):
        dev = find_keyboard_dev()
        try:
            return dev, open(dev, "rb")
        except PermissionError:
            raise SystemExit(
                f"\n  ERRO: sem permissão pra ler a tecla ({dev}).\n"
                f"  Rode com sudo:  sudo python3 {os.path.abspath(__file__)} "
                + " ".join(a for a in sys.argv[1:]) + "\n"
                f"  (ou via serviço: sudo systemctl restart minitela-daemon.service)\n")
        except (FileNotFoundError, OSError) as e:
            print(f"  aguardando teclado ({dev}) [{tent+1}/{retries}]: {e}", flush=True)
            time.sleep(delay)
    raise SystemExit(f"teclado nao disponivel apos {retries} tentativas")


def run():
    idx = 0
    dev, f = _open_keyboard()
    print(f"Daemon Minitela iniciado. Device: {dev}. Tecla {KEY_MINITELA} (KEY_F16) "
          f"alterna telas: " + " -> ".join(PAGE_NAMES[p] for p in PAGES))
    # mostra a primeira tela ao iniciar (nao falha o daemon se o MCU estiver mudo)
    try:
        with Minitela() as m:
            if m.alive():
                m.show_page(PAGES[idx])
                print(f"  tela inicial: {PAGE_NAMES[PAGES[idx]]}")
    except Exception as e:
        print(f"  MCU indisponivel no inicio ({e}); tecla ainda vai funcionar")

    with f:
        while True:
            data = f.read(EV_SIZE)
            if len(data) < EV_SIZE:
                continue
            _, _, etype, code, value = struct.unpack(EV_FORMAT, data)
            if etype == EV_KEY and code == KEY_MINITELA and value == 1:
                idx = (idx + 1) % len(PAGES)
                page = PAGES[idx]
                try:
                    with Minitela() as m:
                        if not m.alive():
                            print("  MCU mudo — rode: sudo usbreset 0324:0324")
                            continue
                        m.show_page(page)
                    print(f"  -> {PAGE_NAMES[page]} (página {page})")
                except Exception as e:
                    print(f"  erro ao trocar página: {e}")


def run_ciclo_gif():
    """Modo --ciclo-gif: 5 estados animados, um por vez na página 5. Cada toque
    sobe o .acf do próximo estado (~11s de upload).
    Gere os .acf antes com: minitela build <conjunto> -o <saida.acf>"""
    import subprocess
    faltando = [s for s in CICLO_GIF_STATES if not os.path.exists(_acf_for(s))]
    if faltando:
        raise SystemExit("faltam .acf: gere com `minitela build` primeiro "
                         f"(ausentes: {', '.join(faltando)})")
    idx = 0
    dev, f = _open_keyboard()
    print(f"Daemon Minitela (ciclo-gif). Tecla {KEY_MINITELA} cicla os 5 GIFs "
          f"(~11s/troca): " + " -> ".join(CICLO_GIF_NAMES[s] for s in CICLO_GIF_STATES))

    import time

    def _mcu_vivo():
        """True se o MCU responde a read-reg. O upload em rajada trava o serial;
        precisamos confirmar que voltou antes de mandar o próximo comando."""
        r = subprocess.run([SIDECAR, "-mode", "cli", "-cmd", "read-reg", "-reg", "2"],
                           capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and "reg[" in r.stdout

    def _usbreset():
        """Recupera o MCU travado (serial mudo). Precisa de root — o daemon roda como
        root (via sudo/systemd), então isto funciona. Testado: é o ÚNICO que destrava."""
        print("  MCU mudo -> usbreset 0324:0324 ...")
        subprocess.run(["usbreset", "0324:0324"], capture_output=True, text=True, timeout=20)
        time.sleep(4)  # re-enumerar leva alguns segundos

    def subir(state, tentativas=3):
        """Sobe o .acf do estado e ativa a página 5, com respiro entre operações e
        recuperação via usbreset. O teste no hardware mostrou que upload+show-page
        colados travam o serial — daí os time.sleep e a checagem de MCU vivo."""
        acf = _acf_for(state)
        for t in range(tentativas):
            # 0) garante MCU vivo antes de mandar 1.6MB; recupera se preciso
            if not _mcu_vivo():
                _usbreset()
                if not _mcu_vivo():
                    print(f"  MCU nao voltou (tentativa {t+1})"); time.sleep(3); continue
            # 1) upload
            r = subprocess.run([SIDECAR, "-mode", "cli", "-cmd", "upload",
                                "-file", acf, "-type", "texture"],
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                print(f"  upload de {state} falhou (tent {t+1}): {r.stderr.strip()[:80]}")
                _usbreset(); continue
            time.sleep(6)  # RESPIRO: upload de 1.6MB deixa o serial drenando ~6s.
            #                Testado: com 6s o MCU responde; com <3s parece "mudo".
            # 2) ativa a página; só usa usbreset se AINDA estiver mudo após o respiro
            if not _mcu_vivo():
                _usbreset()
            subprocess.run([SIDECAR, "-mode", "cli", "-cmd", "show-page",
                            "-page", str(CICLO_GIF_PAGE)],
                           capture_output=True, text=True, timeout=20)
            time.sleep(1)
            return True
        print(f"  desisti de {state} apos {tentativas} tentativas.")
        return False

    print(f"  subindo estado inicial: {CICLO_GIF_NAMES[CICLO_GIF_STATES[idx]]} ...")
    subir(CICLO_GIF_STATES[idx])

    with f:
        while True:
            data = f.read(EV_SIZE)
            if len(data) < EV_SIZE:
                continue
            _, _, etype, code, value = struct.unpack(EV_FORMAT, data)
            if etype == EV_KEY and code == KEY_MINITELA and value == 1:
                idx = (idx + 1) % len(CICLO_GIF_STATES)
                state = CICLO_GIF_STATES[idx]
                print(f"  -> {CICLO_GIF_NAMES[state]} (subindo, ~11s) ...")
                if subir(state):
                    print(f"     {CICLO_GIF_NAMES[state]} no ar")


if __name__ == "__main__":
    # PADRÃO: paginação só do Clawd — os 5 estados ANIMADOS, ciclados pela tecla
    # (cada troca re-sobe o .acf do estado, ~11s). É o modo principal do projeto.
    # Modos alternativos por flag:
    #   --gif3      os 3 estados que cabem nas páginas gif, troca instantânea (5/6/7)
    #   --estatico  Clawd estático nos 5 estados (páginas 1-5)
    #   --dash      dashboards de uso do Claude (páginas 2-4) — não é Clawd
    #   --detect    mostra o keycode de cada tecla
    # aviso imediato se não for root (a tecla exige ler /dev/input/event3)
    if os.geteuid() != 0 and "--detect" not in sys.argv:
        print("  AVISO: não está como root — a leitura da tecla vai falhar.", flush=True)
        print(f"  Rode: sudo python3 {os.path.abspath(__file__)} "
              + " ".join(sys.argv[1:]), flush=True)
    if "--detect" in sys.argv:
        detect_mode()
    elif "--gif3" in sys.argv:        # 3 estados animados, troca instantânea
        PAGES = GIF_PAGES
        run()
    elif "--estatico" in sys.argv:    # Clawd estático nos 5 estados (pág 1-5)
        PAGES = ESTATICO_PAGES
        run()
    elif "--dash" in sys.argv:        # dashboards de uso do Claude (pág 2-4)
        PAGES = DASH_PAGES
        run()
    else:                             # PADRÃO: 5 Clawds animados (ciclo-gif)
        run_ciclo_gif()
