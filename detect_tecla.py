#!/usr/bin/env python3
"""
Detecta em QUAL device de input e com QUAL keycode a tecla Minitela chega.
Lê vários /dev/input/event* ao mesmo tempo. Rode com sudo e aperte a tecla.
"""
import struct
import select
import glob
import os

EV_FORMAT = "llHHi"
EV_SIZE = struct.calcsize(EV_FORMAT)
EV_KEY = 0x01
EV_MSC = 0x04  # MSC_SCAN traz o scancode cru (útil pra teclas sem keycode mapeado)

# abre todos os event* legíveis
fds = {}
for path in sorted(glob.glob("/dev/input/event*")):
    try:
        f = open(path, "rb")
        name = ""
        try:
            n = os.path.basename(path)
            name = open(f"/sys/class/input/{n}/device/name").read().strip()
        except Exception:
            pass
        fds[f.fileno()] = (f, path, name)
    except PermissionError:
        print(f"sem permissão: {path} (rode com sudo)")
    except Exception:
        pass

if not fds:
    print("nenhum device aberto — rode com sudo")
    raise SystemExit(1)

print(f"Monitorando {len(fds)} devices. APERTE a tecla Minitela (toque curto e segurar). Ctrl-C sai.\n")

while True:
    r, _, _ = select.select([f for f, _, _ in fds.values()], [], [])
    for fobj in r:
        f, path, name = fds[fobj.fileno()]
        data = f.read(EV_SIZE)
        if len(data) < EV_SIZE:
            continue
        _, _, etype, code, value = struct.unpack(EV_FORMAT, data)
        if etype == EV_KEY and value in (0, 1):  # press/release
            estado = "PRESS" if value == 1 else "release"
            print(f"[{name}] ({os.path.basename(path)}) KEY code={code} (0x{code:x}) {estado}")
        elif etype == EV_MSC:
            print(f"[{name}] ({os.path.basename(path)}) SCAN 0x{value:x}")
