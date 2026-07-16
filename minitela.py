#!/usr/bin/env python3
"""
minitela.py — cliente serial para a Minitela do Positivo Vision R15M.

Protocolo confirmado por engenharia reversa do app oficial da Positivo
(js-src/utils/command.js + messageProcessor.js) e do SideCar. Ver
minitela-oficial/ACHADOS-RE.md.

Estratégia comprovada (2026-07-15): NÃO faz upload de textura. Escreve os
registradores de dados de fábrica (strings/numéricos) via SET_REGISTER e troca
a página ativa (RegCurrentPage=2) para uma página ESTÁVEL de fábrica. Páginas
1-4 são estáveis; a página 5 (imagens/gifs) reinicia o MCU e é evitada.

Recuperação de travamento: se o serial parar de responder (fila de TX enche),
rodar `sudo usbreset 0324:0324` — reset de protocolo USB reinicia o MCU.
"""

import os
import time
import select
import termios
import fcntl
import struct

DEVICE = "/dev/ttyACM0"

# ── CommandTypes (de command.js) ─────────────────────────────────────────────
CMD_HANDSHAKE = 0x0080
CMD_HANDSHAKE_RESP = 0x00C0
CMD_SET_REGISTER = 0x0090
CMD_SET_REGISTER_RESP = 0x00D0

# ── Registradores (de tagUtils.js / tags.go) ─────────────────────────────────
REG_CURRENT_PAGE = 2
REG_BRIGHTNESS = 7
# Reminders (string) — renderizados na página 2 (Notas)
REG_REMINDER = {
    1: (1090, 1091),  # (content, time)
    2: (1092, 1093),
    3: (1094, 1095),
}
# Notificações (string) — título/conteúdo
REG_NOTIF = {
    1: (1140, 1141),
    2: (1142, 1143),
    3: (1144, 1145),
}

PAGE_NOTAS = 2
PAGE_MONITOR = 3

_TIOCOUTQ = 0x5411


class Minitela:
    def __init__(self, device=DEVICE):
        self.device = device
        self.fd = None

    def open(self):
        self.fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(self.fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        try:
            attrs[4] = termios.B115200
            attrs[5] = termios.B115200
        except Exception:
            pass
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        return self

    def close(self):
        if self.fd is not None:
            # fecha sem bloquear: descarta TX pendente (evita travar num MCU mudo)
            try:
                termios.tcflush(self.fd, termios.TCIOFLUSH)
                fcntl.fcntl(self.fd, fcntl.F_SETFL, os.O_RDWR | os.O_NONBLOCK)
            except Exception:
                pass
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *a):
        self.close()

    # ── frame ────────────────────────────────────────────────────────────────
    @staticmethod
    def _frame(cmd_type, content=b""):
        """Monta um frame. CRC sempre 0x0000 (app oficial usa enableCRC=false)."""
        data_len = len(content) + 2  # +2 do cmdType (confirmado em command.js)
        control = data_len  # bit15=crcFlag=0
        body = struct.pack(">HH", control, cmd_type) + content
        return b"\x41\x48" + body + b"\x00\x00" + b"\x4D\x49"

    def _outq(self):
        return struct.unpack("I", fcntl.ioctl(self.fd, _TIOCOUTQ, struct.pack("I", 0)))[0]

    def _write(self, frame):
        os.write(self.fd, frame)

    def _read(self, timeout=1.5):
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            r, _, _ = select.select([self.fd], [], [], 0.2)
            if r:
                try:
                    chunk = os.read(self.fd, 256)
                    if chunk:
                        buf += chunk
                        # frame completo termina em 'MI'
                        if buf.endswith(b"\x4D\x49"):
                            break
                except BlockingIOError:
                    pass
        return buf

    # ── comandos ───────────────────────────────────────────────────────────────
    def handshake(self):
        self._write(self._frame(CMD_HANDSHAKE))
        resp = self._read(1.5)
        return len(resp) >= 6 and resp[4:6] == b"\x00\xC0"

    def alive(self):
        """True se o MCU está lendo o serial (fila de TX drena)."""
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        self._write(self._frame(CMD_HANDSHAKE))
        time.sleep(0.3)
        return self._outq() == 0

    def set_num_registers(self, pairs):
        """pairs: lista de (regId, value). Escreve em lotes de 16.
        Header: (0b1000<<4)|(n-1); depois n×[regId(2 BE)+value(4 BE)]."""
        for i in range(0, len(pairs), 16):
            batch = pairs[i:i + 16]
            content = bytes([(0b1000 << 4) | ((len(batch) - 1) & 0xF)])
            for reg, val in batch:
                content += struct.pack(">HI", reg, val & 0xFFFFFFFF)
            self._write(self._frame(CMD_SET_REGISTER, content))
            self._read(0.6)  # drena ACK (formato de escrita não é decodificado)

    def set_string_register(self, reg_id, text):
        """Header 0b11010000, regId(2 BE), len(2 BE), bytes. (de messageProcessor.js)"""
        raw = text.encode("utf-8", errors="replace")
        content = bytes([0b11010000]) + struct.pack(">HH", reg_id, len(raw)) + raw
        self._write(self._frame(CMD_SET_REGISTER, content))
        self._read(0.6)

    def show_page(self, page):
        """Troca a página ativa (RegCurrentPage=2). Evite page 5 (reinicia o MCU)."""
        self.set_num_registers([(REG_CURRENT_PAGE, page)])

    def set_brightness(self, value):
        self.set_num_registers([(REG_BRIGHTNESS, max(0, min(255, value)))])


if __name__ == "__main__":
    import sys
    with Minitela() as m:
        if not m.alive():
            print("MCU mudo — rode: sudo usbreset 0324:0324", file=sys.stderr)
            sys.exit(1)
        print("handshake:", m.handshake())
