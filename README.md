**English** · [Português (Brasil)](README.pt-BR.md)

# telinha

Client, daemon and build pipeline for the **Minitela** on the **Positivo Vision
R15M** laptop — a 1.54" IPS display, 240×240, embedded in the chassis.

Out of the box it only shows WhatsApp notifications, weather and photos, through
a closed-source Positivo app that doesn't run on Fedora. This project talks to
the display directly and shows whatever we want: today, the **Clawd** mascot from
[claude-usage-widget](https://github.com/MrSchrodingers/claude-usage-widget),
which changes with the Claude model in use and warns when token usage gets tight.

## The critters

**By the model in use** — instant switch, just one serial register:

![opus, the genius Clawd with a crown](docs/img/clawd-genius.gif)
![sonnet, the smart Clawd with a book and coffee](docs/img/clawd-smart.gif)
![fable, Clawd on fire](docs/img/clawd-dumb.gif)

`opus` → genius (page 6) · `sonnet` → smart (page 7) · `fable` → on fire (page 5)

**By token usage** — the whole set swaps (re-upload, ~15s):

![70-90%, Clawd in the rain](docs/img/clawd-slow.gif)
![90% or more, the little ghost on a gravestone](docs/img/clawd-braindead.gif)

70–90% → rain · ≥ 90% → little ghost

The physical "Minitela" key cycles through the three critters of the active set.
Priority: key (20s override) > alert > model.

The GIFs above are the real render — the same function that generates what goes
to the display. Reproduce them with `minitela build normal -o clawd.acf`.

## How it works

The display runs an **AHMI** firmware with fixed, compiled pages. You can't
"draw on the screen": what you do is **recompile the factory project** swapping
the resources, upload the resulting `.acf`, and switch the active page through a
serial register.

The discovery that unlocks everything: **the animation definition (frame count,
delays) lives in the firmware**, tied to each gif page. The `.acf` only delivers
pixels. So you just swap the source gif for one with the same frame count.

```
sprites  ->  gif (global palette)  ->  file.zip  ->  AHMISimGenDemo (Wine)  ->  .acf
                                                                                 |
                                               /dev/ttyACM0  <-  upload (SideCar)
                                                     |
                                           show-page 5|6|7  (register 2)
```

**Hardware limit:** there are only **3 pages with animation** (5, 6 and 7).
Having 5 animated critters with instant switching is impossible without
re-flashing the firmware — this is proven, don't reopen it. See `docs/`.

## Installation

```bash
git clone <this-repo> telinha && cd telinha
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

System dependencies and third-party material (the Positivo app, the AHMI
compiler, SideCar) are **not redistributed here** — see
[`scripts/bootstrap-vendor.md`](scripts/bootstrap-vendor.md) to obtain them.

Without that material you can still use the daemon, switch pages and upload a
prebuilt `.acf`. What requires it is **generating a new `.acf`**.

## Usage

```bash
minitela handshake                      # does the device answer?
minitela show-page 6                    # switch the active page
minitela detect-tecla                   # print the keycode of each key (root)
minitela build normal -o clawd-anim.acf # build the .acf for a set
```

Uploading the `.acf` to the display (the upload still uses SideCar):

```bash
sudo systemctl stop minitela-daemon.service   # avoid contention on the serial port
./sidecar/SideCar-fixed -mode cli -cmd upload -file clawd-anim.acf \
    -type texture -device /dev/ttyACM0
sleep 6                                       # the upload holds the serial for ~6s
minitela show-page 5
```

The daemon (`minitela_clawd.py`) follows the model in use, the token alert and
the physical key. It needs root to read `/dev/input/event*`:

```bash
sudo .venv/bin/python minitela_clawd.py
```

## Tests

```bash
pytest              # 192 tests, no hardware, on any machine
pytest -m hardware  # requires the Minitela connected
```

The default suite opens neither `/dev/ttyACM0` nor `/dev/input/*`: the serial
port is a `socketpair` and the key is a `BytesIO` with `input_event` bytes.

## Layout

```
src/minitela/
├── core/       protocol (pure), transport (I/O), device, pages
├── dados/      model in use and token usage
├── daemon/     pure decision: model + alert + key -> what to show
├── entrada/    the physical key, straight from /dev/input
├── render/     Clawd composition (pure Pillow) + vendored sprites
├── build/      gif -> AHMI project -> compiler -> .acf
└── cli.py

patches/sidecar/  our fixes to SideCar (3 bugs), on top of upstream d356c2b
docs/historico/   the investigations, including the refuted routes
```

The repo root still holds `minitela_clawd.py`, `minitela_daemon.py`,
`minitela.py` and `minitela_modelo.py` — the legacy daemon, still in production.
The migration to the package is planned and has not been carried out; see
"Status" below.

## Status

It works on real hardware: animated critter, switching by model, token alert and
physical key — all confirmed on the device.

The reorganization into a package is **partial**. Done: serial core, state
decision, key input, render and build, all with tests. Missing: migrating the
daemon and the systemd service to the package (the legacy code at the root is
still what runs), and rewriting the documentation — the current `CLAUDE.md` has
known contradictions.

## License

MIT for the code in this repository. It **does not extend** to the
Positivo/Sigma material nor to SideCar; the Clawd sprites are MIT from
claude-usage-widget, redistributed with attribution in
`src/minitela/render/sprites/LICENSE`. See [LICENSE](LICENSE).

The reverse engineering work described here documents observed behavior for
interoperability purposes; it neither contains nor redistributes proprietary
code.
