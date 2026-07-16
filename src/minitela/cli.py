"""Linha de comando da Minitela."""

import argparse
import sys

from .core.dispositivo import Minitela
from .core.transporte import DEVICE_PADRAO
from .entrada import tecla as tecla_mod


def _cmd_detect_tecla(args) -> int:
    try:
        caminho, arquivo = tecla_mod.abrir_teclado(args.dev)
    except tecla_mod.SemPermissao as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"lendo {caminho} — pressione a tecla Minitela (Ctrl-C para sair)")
    with arquivo:
        try:
            for code in tecla_mod.qualquer_tecla(arquivo):
                marca = "  <- KEY_MINITELA" if code == tecla_mod.KEY_MINITELA else ""
                print(f"  keycode={code}{marca}")
        except KeyboardInterrupt:
            print()
    return 0


def _cmd_show_page(args) -> int:
    with Minitela(device=args.device) as m:
        if not m.vivo():
            print("MCU mudo — rode: sudo usbreset 0324:0324", file=sys.stderr)
            return 1
        m.mostrar_pagina(args.pagina)
    return 0


def _cmd_handshake(args) -> int:
    with Minitela(device=args.device) as m:
        ok = m.handshake()
    print("handshake:", "ok" if ok else "sem resposta")
    return 0 if ok else 1


def _cmd_build(args) -> int:
    from .build import CONJUNTOS, montar_conjunto

    try:
        acf = montar_conjunto(args.conjunto, args.saida, args.file_zip)
    except (FileNotFoundError, ValueError, RuntimeError) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"{acf} ({acf.stat().st_size} bytes)")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="minitela", description=__doc__)
    p.add_argument("--device", default=DEVICE_PADRAO, help="porta serial")
    sub = p.add_subparsers(dest="comando", required=True)

    d = sub.add_parser("detect-tecla", help="mostra o keycode de cada tecla")
    d.add_argument("--dev", default=None, help="forçar um /dev/input/event*")
    d.set_defaults(func=_cmd_detect_tecla)

    s = sub.add_parser("show-page", help="troca a página ativa")
    s.add_argument("pagina", type=int)
    s.set_defaults(func=_cmd_show_page)

    h = sub.add_parser("handshake", help="pergunta se o dispositivo responde")
    h.set_defaults(func=_cmd_handshake)

    b = sub.add_parser("build", help="gera o .acf de um conjunto de bichinhos")
    b.add_argument("conjunto", choices=["normal", "alerta"])
    b.add_argument("-o", "--saida", required=True, help="caminho do .acf")
    b.add_argument("--file-zip", default=None, help="projeto AHMI de fábrica")
    b.set_defaults(func=_cmd_build)

    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
