#!/bin/bash
# Gera UM .acf com 3 Clawds (um por pagina de gif 5/6/7), a partir de 3 estados.
# Usado pra montar os conjuntos que a tecla cicla:
#   normal: fogo/genius/smart   -> clawd-anim.acf
#   alerta: fogo/chuva/fantasma -> clawd-alerta.acf
#
# Uso: ./gerar_conjunto.sh <saida.acf> <estado_pag5> <estado_pag6> <estado_pag7>
#   estados: genius smart slow(chuva) dumb(fogo) braindead(fantasma)
# Ex: ./gerar_conjunto.sh minitela-oficial/clawd-alerta.acf dumb slow braindead
set -e
[ $# -eq 4 ] || { echo "uso: $0 <saida.acf> <est5> <est6> <est7>"; exit 1; }
OUT_ACF="$1"; E5="$2"; E6="$3"; E7="$4"

DIR=/home/asm/telinha
GEN="$DIR/minitela-oficial/ide-utils/Gen"
FILEZIP="$DIR/minitela-oficial/ide-utils/file.zip"
WINEPREFIX_DIR=${WINEPREFIX:-$HOME/.wine}
[ "${OUT_ACF:0:1}" = "/" ] || OUT_ACF="$DIR/$OUT_ACF"
SCRATCH=$(mktemp -d); trap 'rm -rf "$SCRATCH"' EXIT

# gif de origem de cada pagina (5/6/7) e nº de frames
SLOTS=("1i1h1e37393671471.gif 21 $E5" "1h1k1e37393671464.gif 30 $E6" "1h1m1e37393671466.gif 44 $E7")

echo ">> frames dos estados ($E5/$E6/$E7)"
python3 "$DIR/render_bichinhos.py" "$SCRATCH/frames" --frames

echo ">> montando os 3 gifs (paleta global) e trocando no zip"
mkdir -p "$SCRATCH/zw" && cd "$SCRATCH/zw"
unzip -q "$FILEZIP"
for slot in "${SLOTS[@]}"; do
  read -r gif nf state <<< "$slot"
  python3 - "$SCRATCH/frames" "$SCRATCH/zw/$gif" "$state" "$nf" "$gif" <<'PY'
import sys
from PIL import Image
fdir, out, state, nf, gifname = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
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
print(f"   {gifname}: {nf} frames ({state})")
PY
done
rm -f "$SCRATCH/f.zip"; zip -q -r -X "$SCRATCH/f.zip" .

echo ">> compilando via Wine (_og.exe)"
cd "$GEN"; rm -rf "$SCRATCH/ACF" && mkdir -p "$SCRATCH/ACF"
printf '13\n' | WINEDEBUG=-all WINEPREFIX="$WINEPREFIX_DIR" \
  wine AHMISimGenDemo_og.exe -f "$SCRATCH/f.zip" -m 2 -c 0 -e 0 -d 1 \
  -o "$SCRATCH/ACF" >/dev/null 2>&1
cp "$SCRATCH/ACF/Texture.acf" "$OUT_ACF"
echo ">> salvo: $OUT_ACF ($(wc -c < "$OUT_ACF") bytes) — pag5=$E5 pag6=$E6 pag7=$E7"
