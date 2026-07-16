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
registradores e subir um `.acf` **já pronto** (os de `assets/acf/`). O que você
**não** pode é gerar um `.acf` novo com visual próprio.

## 3. Sprites do Clawd

**Já vendorizados** neste repo, em `src/minitela/render/sprites/` — são MIT e a
licença permite redistribuição com atribuição. Não precisa fazer nada.

Origem: https://github.com/MrSchrodingers/claude-usage-widget
(© 2026 Claude Usage Widget Contributors). Ver `src/minitela/render/sprites/LICENSE`.

## 4. Ferramentas do sistema

```bash
sudo dnf install -y git-lfs wine ImageMagick zip unzip usbutils
```

- `git-lfs` — os `.acf` de `assets/acf/` são ponteiros LFS
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
