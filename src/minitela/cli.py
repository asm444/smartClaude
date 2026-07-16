import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    print("minitela: nenhum subcomando implementado ainda", file=sys.stderr)
    return 1
