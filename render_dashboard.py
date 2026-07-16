#!/usr/bin/env python3
"""Renders ~/.claude/widget-data.json as a 240x240 PNG for the Positivo minitela."""

import json
import os
import sys
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

WIDGET_DATA = os.path.expanduser("~/.claude/widget-data.json")
OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-dashboard.png"

SIZE = 240
BG = (18, 18, 23)
FG = (235, 235, 240)
MUTED = (150, 150, 160)
ACCENT = (217, 119, 87)  # Claude orange
GOOD = (34, 197, 94)
WARN = (234, 179, 8)
BAD = (239, 68, 68)


def load_font(size):
    for path in (
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def color_for_pct(pct):
    if pct < 50:
        return GOOD
    if pct < 80:
        return WARN
    return BAD


def bar(draw, x, y, w, h, pct, color):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(45, 45, 52))
    fill_w = max(int(w * min(pct, 100) / 100), h)
    draw.rounded_rectangle([x, y, x + fill_w, y + h], radius=h // 2, fill=color)


def main():
    with open(WIDGET_DATA) as f:
        data = json.load(f)

    rl = data.get("rateLimits", {})
    session = rl.get("session", {})
    weekly = rl.get("weeklyAll", {})
    today = data.get("today", {})

    session_pct = session.get("percentUsed", 0)
    weekly_pct = weekly.get("percentUsed", 0)
    plan = rl.get("plan", "")

    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    f_title = load_font(20)
    f_label = load_font(13)
    f_big = load_font(28)
    f_small = load_font(11)

    draw.text((14, 10), "Claude", font=f_title, fill=ACCENT)
    draw.text((14, 34), plan, font=f_small, fill=MUTED)

    y = 62
    draw.text((14, y), "Sessao (5h)", font=f_label, fill=FG)
    draw.text((226, y), f"{session_pct:.0f}%", font=f_label, fill=color_for_pct(session_pct), anchor="ra")
    bar(draw, 14, y + 20, 212, 14, session_pct, color_for_pct(session_pct))

    y += 50
    draw.text((14, y), "Semana", font=f_label, fill=FG)
    draw.text((226, y), f"{weekly_pct:.0f}%", font=f_label, fill=color_for_pct(weekly_pct), anchor="ra")
    bar(draw, 14, y + 20, 212, 14, weekly_pct, color_for_pct(weekly_pct))

    y += 56
    draw.line([(14, y), (226, y)], fill=(45, 45, 52), width=1)

    y += 12
    total_tokens = today.get("totalTokens", 0)
    draw.text((14, y), "Hoje", font=f_label, fill=MUTED)
    draw.text((14, y + 16), f"{total_tokens/1e6:.1f}M tokens", font=f_big, fill=FG)

    sessions = today.get("sessions", 0)
    msgs = today.get("messages", 0)
    draw.text((14, y + 52), f"{sessions} sessoes / {msgs} msgs", font=f_small, fill=MUTED)

    now = datetime.now(timezone.utc).astimezone()
    draw.text((14, 222), now.strftime("%H:%M"), font=f_small, fill=MUTED)

    img.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
