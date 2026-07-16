#!/usr/bin/env python3
"""
Detector: escuta TODOS os /dev/input/event* ao mesmo tempo e mostra qual device +
qual keycode cada tecla dispara. Use pra descobrir o que a tecla fisica Minitela
emite (device e codigo reais), ja que ela pode nao vir pelo teclado AT (event3).

Uso: sudo python3 detectar_tecla_todos.py
     -> aperte a tecla Minitela; ele imprime device + keycode. Ctrl-C pra sair.
"""
import glob
import os
import select
import struct

EV_FORMAT = "llHHi"
EV_SIZE = struct.calcsize(EV_FORMAT)
EV_KEY = 0x01

fds = {}
for path in sorted(glob.glob("/dev/input/event*")):
    try:
        f = open(path, "rb")
        os.set_blocking(f.fileno(), False)
        name = ""
        try:
            n = os.path.basename(path)
            name = open(f"/sys/class/input/{n}/device/name").read().strip()
        except Exception:
            pass
        fds[f.fileno()] = (f, path, name)
    except (PermissionError, OSError) as e:
        print(f"  (nao abriu {path}: {e})")

if not fds:
    raise SystemExit("nenhum event device aberto — rode com sudo")

print(f"Escutando {len(fds)} devices. APERTE a tecla Minitela (Ctrl-C pra sair).\n")
poller = select.poll()
for fd in fds:
    poller.register(fd, select.POLLIN)

while True:
    for fd, _ in poller.poll():
        f, path, name = fds[fd]
        data = f.read(EV_SIZE)
        while data and len(data) == EV_SIZE:
            _, _, etype, code, value = struct.unpack(EV_FORMAT, data)
            if etype == EV_KEY and value == 1:  # press
                print(f"  >>> {path}  ({name})  keycode={code}")
            data = f.read(EV_SIZE)
