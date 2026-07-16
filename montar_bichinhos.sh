#!/bin/bash
# Monta e sobe as telas dos 4 bichinhos (Clawd) na Minitela.
# genius(coroa)=pág1, smart(livro)=pág2, slow(chuva)=pág3, dumb(fogo)=pág4.
# (RegCurrentPage: valor = pág do projeto + 1)
# Uso: ./montar_bichinhos.sh
set -e
DIR=/home/asm/telinha
SCRATCH=$(mktemp -d)
WINEPREFIX_DIR=${WINEPREFIX:-$HOME/.wine-minitela}
GEN=$DIR/minitela-oficial/ide-utils/Gen

echo ">> gerando bichinhos 240x240 (fundo claro)"
python3 "$DIR/render_bichinhos.py" "$SCRATCH/bichos"

echo ">> montando projeto AHMI (páginas 0-3 = 4 bichinhos)"
mkdir -p "$SCRATCH/work" && cd "$SCRATCH/work"
unzip -q "$DIR/minitela-oficial/ide-utils/file.zip"
python3 - "$SCRATCH/bichos" << 'PY'
import json, sys
from PIL import Image
base = sys.argv[1]
d = json.load(open('data.json'))
plan = {0:'genius', 1:'smart', 2:'slow', 3:'dumb'}  # braindead fica pro re-upload/gif
for pid, state in plan.items():
    p = d['pageList'][pid]
    Image.open(f'{base}/bicho-{state}.png').convert('RGBA').resize((240,240)).save(f'r-{pid}-0.png')
    p['backgroundImage'] = f'/project/67004c7703ad6966e4fe0d13/resources/r-{pid}-0.png'
    p['backgroundColor'] = 'rgb(245,245,248)'
    for c in p.get('canvasList', []):
        for sub in c.get('subCanvasList', []):
            sub['widgetList'] = []
json.dump(d, open('data.json','w'), ensure_ascii=False)
print('  páginas 0-3 =', list(plan.values()))
PY
rm -f "$SCRATCH/file.zip" && zip -q -r "$SCRATCH/file.zip" .

echo ">> recompilando via Wine"
cd "$GEN"
rm -rf "$SCRATCH/ACF" && mkdir -p "$SCRATCH/ACF"
printf '13\n' | WINEDEBUG=-all WINEPREFIX="$WINEPREFIX_DIR" \
  wine AHMISimGenDemo_og.exe -f "$SCRATCH/file.zip" -m 2 -c 0 -e 0 -d 1 -o "$SCRATCH/ACF" >/dev/null 2>&1
cp "$SCRATCH/ACF/Texture.acf" "$DIR/minitela-oficial/bichinhos.acf"
echo ">> ACF salvo em minitela-oficial/bichinhos.acf"

echo ">> subindo pra telinha"
"$DIR/sidecar/SideCar-fixed" -mode cli -cmd upload -file "$DIR/minitela-oficial/bichinhos.acf" -type texture -device /dev/ttyACM0 2>&1 | tail -1
echo ">> pronto. Use minitela_daemon.py pra alternar (valores 1-4)."
rm -rf "$SCRATCH"
