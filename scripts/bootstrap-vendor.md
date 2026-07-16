# Bootstrap — obtendo o material de terceiros

Este repositório **não redistribui** material de terceiros. O que está aqui é o nosso
código, a nossa documentação e os nossos patches. Para reconstruir o ambiente
completo, você precisa obter os artefatos abaixo por conta própria.

Nada disto é versionado (ver `.gitignore`); tudo vive em diretórios ignorados.

## 1. SideCar (necessário para upload de textura)

MIT, © seus autores. Usamos para o upload — a única capacidade que o nosso cliente
serial não implementa. Precisa de Go ≥ 1.26 (o `GOTOOLCHAIN=auto` baixa o certo).

```bash
git clone https://github.com/FreyreCorona/SideCar.git sidecar-src
cd sidecar-src
git checkout d356c2b
git apply ../patches/sidecar/*.patch
GOTOOLCHAIN=auto go build -o ../sidecar/SideCar-fixed .
```

Os 4 patches corrigem 3 bugs que impedem o uso por CLI e adicionam um comando.
Ver `docs/historico/fork-sidecar-bugs.md`. Sem eles, `-mode` não funciona e as
escritas de registrador parecem travar.

Verifique que aplicou certo:

```bash
git diff --stat    # deve dar: 4 files changed, 104 insertions(+), 25 deletions(-)
```

## 2. Aplicativo oficial da Positivo (necessário para compilar visual próprio)

Propriedade da Positivo / Sigma (graphichina). **Não é redistribuído aqui.**
Obtenha o pacote `.deb` oficial da Positivo por conta própria e extraia para
`minitela-oficial/`.

O que é usado deste material:

| Artefato | Para quê |
|---|---|
| `ide-utils/file.zip` | projeto AHMI de fábrica (`data.json`, texturas, gifs) |
| `ide-utils/Gen/AHMISimGenDemo_og.exe` | compilador que gera o `Texture.acf` (roda via Wine) |
| `acf-fabrica/` | texturas de fábrica, úteis como referência |

O compilador é Windows; roda sob Wine (testado com wine-11.0), num `WINEPREFIX`
próprio. Ver `docs/03-projeto-ahmi-e-compilador.md`.

Sem este material você ainda pode: usar o daemon, trocar de página, ler
registradores e subir um `.acf` **já pronto**, se você tiver um. O que você
**não** pode é gerar um `.acf` novo com visual próprio.

Os `.acf` não são versionados neste repo (são artefatos de ~4MB, regeráveis pelo
pipeline de build a partir do material do item 2).

## 3. Sprites do Clawd

MIT, © 2026 Claude Usage Widget Contributors. **Não vendorizados aqui**: o
`render_bichinhos.py` lê os sprites da instalação local do widget, no caminho
`~/projects/claude-usage-widget/plasmoid/contents/icons/`.

```bash
git clone https://github.com/MrSchrodingers/claude-usage-widget.git ~/projects/claude-usage-widget
```

Os sprites são gerados por `scripts/generate-sprites.py` do próprio widget: a base
`clawd.svg` mais overlays de 6 frames cada — `halo` (genius), `smart`, `rain` (slow),
`fire` (dumb) e `skull` (braindead).

O widget também é a fonte do `~/.claude/widget-data.json`, que o daemon lê para
decidir o estado (percentual de uso) — então ele precisa estar instalado e ativo de
qualquer forma.

## 4. Ferramentas do sistema

```bash
sudo dnf install -y wine ImageMagick zip unzip usbutils
```

- `wine` — roda o compilador AHMI
- `ImageMagick` (`magick`) — rasterização de SVG (só no pipeline de sprites)
- `usbreset` (pacote `usbutils`) — **única** forma de destravar o MCU quando o
  serial fica mudo: `sudo usbreset 0324:0324`

## 5. Permissão do dispositivo

O `/dev/ttyACM0` pertence a `root:dialout`, modo `660`. Para não precisar de `chmod`
a cada replug:

```bash
sudo usermod -a -G dialout $USER    # requer logout/login
```

Alternativa (é o que o `.deb` oficial instala):

```
# /etc/udev/rules.d/99-ttyacm.rules
SUBSYSTEM=="tty", KERNEL=="ttyACM*", MODE="0666"
```
