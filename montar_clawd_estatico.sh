#!/bin/bash
# Monta e sobe o Clawd ESTATICO (1 frame representativo por estado) nos 5 estados.
#
# Diferente do montar_clawd_gif.sh (que sobe os GIFs animados nas paginas de
# animacao 5/6/7), este sobe UMA imagem parada por estado, substituindo o FUNDO
# das paginas de fabrica que ja renderizam. Metodo provado (ver CLAUDE.md secao
# "BICHINHO CLAWD — ESTATICOS FUNCIONANDO"): trocar backgroundImage + zerar os
# widgets da pagina no data.json, recompilar com _og.exe, subir como texture.
#
# 5 estados do Clawd -> paginas (RegCurrentPage):
#   reg 1 = genius     (fundo da pag WhatsApp)
#   reg 2 = smart      (fundo da pag Reminder)
#   reg 3 = slow       (fundo da pag SystemInfo)
#   reg 4 = dumb       (fundo da pag Weather)
#   reg 5 = braindead  (pag Gif1, subindo 1 frame estatico)
# (as 4 primeiras paginas tem fundo substituivel; a 5a reaproveita a pag de gif
#  com um frame unico. Cores CLARAS obrigatorias — o compilador corrompe escuro.)
#
# Uso:
#   ./montar_clawd_estatico.sh             # gera + compila + sobe
#   ./montar_clawd_estatico.sh --no-upload # so gera o .acf, nao toca no hardware
set -e

DIR=/home/asm/telinha
GEN="$DIR/minitela-oficial/ide-utils/Gen"
FILEZIP="$DIR/minitela-oficial/ide-utils/file.zip"
WINEPREFIX_DIR=${WINEPREFIX:-$HOME/.wine}
OUT_ACF="$DIR/minitela-oficial/clawd-estatico.acf"
DEVICE=${DEVICE:-/dev/ttyACM0}
SIDECAR="$DIR/sidecar/SideCar-fixed"
NO_UPLOAD=0
[ "$1" = "--no-upload" ] && NO_UPLOAD=1

SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

echo ">> [1/4] gerando 1 PNG por estado do Clawd (fundo claro)"
python3 "$DIR/render_bichinhos.py" "$SCRATCH/frames"

echo ">> [2/4] montando projeto AHMI: fundo das paginas 0-3 + gif slot p/ o 5o estado"
mkdir -p "$SCRATCH/work" && cd "$SCRATCH/work"
unzip -q "$FILEZIP"
python3 - "$SCRATCH/frames" <<'PY'
import json, sys
from PIL import Image
base = sys.argv[1]
d = json.load(open('data.json'))
proj = "67004c7703ad6966e4fe0d13"
# estado do Clawd -> indice de pagina (0-based) cujo FUNDO substituimos
plan = {0: 'genius', 1: 'smart', 2: 'slow', 3: 'dumb'}
for pid, state in plan.items():
    p = d['pageList'][pid]
    img = Image.open(f'{base}/bicho-{state}.png').convert('RGBA').resize((240, 240))
    img.save(f'r-{pid}-0.png')
    p['backgroundImage'] = f'/project/{proj}/resources/r-{pid}-0.png'
    p['backgroundColor'] = 'rgb(245,245,248)'
    for c in p.get('canvasList', []):
        for sub in c.get('subCanvasList', []):
            sub['widgetList'] = []
# 5o estado (braindead) na pagina Gif1 (idx 4): trocamos o gif de origem por um
# gif de 1 frame (imagem estatica). O gif de 21 slices vira 21x o mesmo frame.
sk = Image.open(f'{base}/bicho-braindead.png').convert('RGB').resize((192, 192))
sk.save('1i1h1e37393671471.gif')  # 1 frame -> estatico na pag 5
print("  paginas 1-4 = genius/smart/slow/dumb (fundo); pag 5 = braindead (gif estatico)")
json.dump(d, open('data.json', 'w'), ensure_ascii=False)
PY
rm -f "$SCRATCH/file_est.zip"
zip -q -r -X "$SCRATCH/file_est.zip" .

echo ">> [3/4] recompilando via Wine (_og.exe)"
cd "$GEN"
rm -rf "$SCRATCH/ACF" && mkdir -p "$SCRATCH/ACF"
printf '13\n' | WINEDEBUG=-all WINEPREFIX="$WINEPREFIX_DIR" \
  wine AHMISimGenDemo_og.exe -f "$SCRATCH/file_est.zip" -m 2 -c 0 -e 0 -d 1 \
  -o "$SCRATCH/ACF" >/dev/null 2>&1
cp "$SCRATCH/ACF/Texture.acf" "$OUT_ACF"
echo "   ACF salvo em $OUT_ACF ($(wc -c < "$OUT_ACF") bytes)"

if [ "$NO_UPLOAD" = "1" ]; then
  echo ">> [4/4] --no-upload: pulando o hardware. Suba com:"
  echo "   $SIDECAR -mode cli -cmd upload -file $OUT_ACF -type texture -device $DEVICE"
  exit 0
fi

echo ">> [4/4] subindo pra telinha"
if ! timeout 15 "$SIDECAR" -mode cli -cmd read-reg -reg 2 -device "$DEVICE" >/dev/null 2>&1; then
  echo "   !! MCU mudo. Rode: sudo usbreset 0324:0324  e tente de novo."
  exit 1
fi
"$SIDECAR" -mode cli -cmd upload -file "$OUT_ACF" -type texture -device "$DEVICE" 2>&1 | tail -1
"$SIDECAR" -mode cli -cmd show-page -page 1 -device "$DEVICE" >/dev/null 2>&1
echo "   subido. Alterne com a tecla via:"
echo "   sudo python3 $DIR/minitela_daemon.py --estatico   (cicla 1->2->3->4->5)"
