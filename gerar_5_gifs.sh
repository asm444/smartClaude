#!/bin/bash
# Pre-gera os 5 .acf de 1-gif (um por estado do Clawd), todos na pagina Gif1 (val 5).
# O daemon (minitela_daemon.py --ciclo-gif) sobe o proximo a cada toque da tecla.
# Cada .acf tem SO o gif daquele estado na pag 5 (os outros gifs viram o de fabrica
# ou 1 frame) -> menor e mais rapido de subir (~11s) que o de 3 gifs (4.24MB).
#
# Uso: ./gerar_5_gifs.sh    -> salva minitela-oficial/clawd-gif-<estado>.acf (x5)
set -e
DIR=/home/asm/telinha
GEN="$DIR/minitela-oficial/ide-utils/Gen"
FILEZIP="$DIR/minitela-oficial/ide-utils/file.zip"
WINEPREFIX_DIR=${WINEPREFIX:-$HOME/.wine}
OUTDIR="$DIR/minitela-oficial"
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

# os 3 gifs das 3 paginas de animacao (5/6/7). Cada .acf de estado poe o MESMO
# Clawd nas 3 -> qualquer pagina de gif ativa mostra Clawd, NUNCA a tela da Positivo.
# (gif_de_origem  nº_frames)
GIF_SLOTS=("1i1h1e37393671471.gif 21" "1h1k1e37393671464.gif 30" "1h1m1e37393671466.gif 44")
STATES=(genius smart slow dumb braindead)

echo ">> gerando frames dos 5 estados"
python3 "$DIR/render_bichinhos.py" "$SCRATCH/frames" --frames

for state in "${STATES[@]}"; do
  echo ">> [$state] montando o Clawd nas 3 paginas de gif + compilando"
  rm -rf "$SCRATCH/zw" && mkdir -p "$SCRATCH/zw" && cd "$SCRATCH/zw"
  unzip -q "$FILEZIP"
  # 1) monta o gif do estado com o nº de frames de CADA slot, com a paleta global
  #    (fix do padrao geometrico), e injeta nos 3 gifs de origem do zip
  for slot in "${GIF_SLOTS[@]}"; do
    gif=$(echo "$slot" | awk '{print $1}')
    nf=$(echo "$slot" | awk '{print $2}')
    python3 - "$SCRATCH/frames" "$SCRATCH/zw/$gif" "$state" "$nf" <<'PY'
import sys
from PIL import Image
fdir, out, state, nf = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
base = [Image.open(f"{fdir}/bicho-{state}-{k}.png").convert("RGB")
        .resize((192,192), Image.LANCZOS) for k in range(6)]
order, i, d = [], 0, 1
while len(order) < nf:
    order.append(i); i += d
    if i == 5: d = -1
    if i == 0: d = 1
sample = Image.new("RGB", (192*6,192))
for k in range(6): sample.paste(base[k], (192*k,0))
pal = sample.quantize(colors=255, method=Image.MEDIANCUT)
fr = [base[k].quantize(palette=pal, dither=Image.NONE) for k in order]
fr[0].save(out, save_all=True, append_images=fr[1:], duration=100,
           loop=0, disposal=1, optimize=False)
PY
  done
  # 2) compila (os 3 gifs ja estao trocados no zw/)
  rm -f "$SCRATCH/f.zip"; zip -q -r -X "$SCRATCH/f.zip" .
  cd "$GEN"; rm -rf "$SCRATCH/ACF" && mkdir -p "$SCRATCH/ACF"
  printf '13\n' | WINEDEBUG=-all WINEPREFIX="$WINEPREFIX_DIR" \
    wine AHMISimGenDemo_og.exe -f "$SCRATCH/f.zip" -m 2 -c 0 -e 0 -d 1 \
    -o "$SCRATCH/ACF" >/dev/null 2>&1
  cp "$SCRATCH/ACF/Texture.acf" "$OUTDIR/clawd-gif-$state.acf"
  echo "   salvo: clawd-gif-$state.acf ($(wc -c < "$OUTDIR/clawd-gif-$state.acf") bytes)"
done
echo ">> pronto. 5 .acf de 1-gif gerados. O daemon --ciclo-gif sobe o proximo por toque."
