#!/bin/bash
# Monta e sobe os GIFs ANIMADOS do Clawd nas 3 paginas de animacao da Minitela.
#
# Descoberta que torna isto possivel (ver minitela-oficial/BREAKTHROUGH-GIF-2026-07-15.md
# e CLAWD-GIF.md): a page-def de animacao (nº de frames, delays, offsets) vive no
# FIRMWARE, ligada a cada pagina de gif. O .acf so entrega os PIXELS. Basta trocar
# o gif de origem no file.zip por um gif do Clawd com o MESMO nº de frames e recompilar
# com _og.exe (o mesmo compilador dos bichinhos estaticos).
#
# Paginas de animacao (RegCurrentPage -> gif de origem -> nº de frames):
#   valor 5 = Gif1 -> 1i1h1e37393671471.gif -> 21 frames
#   valor 6 = Gif2 -> 1h1k1e37393671464.gif -> 30 frames
#   valor 7 = Gif3 -> 1h1m1e37393671466.gif -> 44 frames
#
# Estados do Clawd disponiveis (6 frames cada, em ~/projects/claude-usage-widget/...):
#   halo(genius) smart rain(slow) fire(dumb) skull(braindead)
#
# CORRECAO (2026-07-15): o defeito "padrao geometrico / frames pretos" NAO era
# offset do atlas — era o GIF salvo com paleta LOCAL por frame + otimizacao/disposal
# do Pillow. O decoder de GIF do _og.exe reconstruia os frames repetidos como
# frames PARCIAIS (buracos preenchidos de preto) -> lixo geometrico. FIX: salvar o
# GIF com paleta GLOBAL unica compartilhada, disposal=1 e optimize=False, de modo
# que cada frame seja um keyframe completo e auto-contido. Comprovado: o compilador
# passou a decodar os 6 frames distintos corretos (antes: 13 frames corrompidos).
# Ver minitela-oficial/CLAWD-GIF.md secao "## Correcao tela-preta + alinhamento".
#
# Uso:
#   ./montar_clawd_gif.sh            # gera + compila + sobe os 3 gifs
#   ./montar_clawd_gif.sh --no-upload  # so gera o .acf, nao toca no hardware
set -e

DIR=/home/asm/telinha
GEN="$DIR/minitela-oficial/ide-utils/Gen"
FILEZIP="$DIR/minitela-oficial/ide-utils/file.zip"
WINEPREFIX_DIR=${WINEPREFIX:-$HOME/.wine}
OUT_ACF="$DIR/minitela-oficial/clawd-anim.acf"
DEVICE=${DEVICE:-/dev/ttyACM0}
SIDECAR="$DIR/sidecar/SideCar-fixed"
NO_UPLOAD=0
[ "$1" = "--no-upload" ] && NO_UPLOAD=1

SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

# --- plano: qual estado do Clawd em cada pagina de gif, e quantos frames a pagina pede
#     (gif_de_origem  nº_frames  estado_do_clawd)
# Estados escolhidos pelos que TEM movimento real (medido): fogo 14%, chuva 4%,
# caveira 2.5%. genius/smart quase nao mudam entre frames -> ficam estaticos.
PLAN=(
  "1i1h1e37393671471.gif 21 dumb"
  "1h1k1e37393671464.gif 30 genius"
  "1h1m1e37393671466.gif 44 smart"
)

echo ">> [1/4] gerando frames do Clawd (6 por estado, fundo claro)"
python3 "$DIR/render_bichinhos.py" "$SCRATCH/frames" --frames

echo ">> [2/4] montando GIFs multi-frame (192x192, ping-pong dos 6 frames)"
python3 - "$SCRATCH/frames" "$SCRATCH" <<'PY'
import sys
from PIL import Image
frames_dir, out = sys.argv[1], sys.argv[2]
# (gif_alvo, nº_frames, estado)
plan = [
    ("1i1h1e37393671471.gif", 21, "dumb"),    # pag 5 = fogo (anima bem)
    ("1h1k1e37393671464.gif", 30, "genius"),  # pag 6 = genius (teste)
    ("1h1m1e37393671466.gif", 44, "smart"),   # pag 7 = smart (teste)
]
def pingpong(n):
    """sequencia ping-pong de indices 0..5 com comprimento n, loop suave."""
    order, i, d = [], 0, 1
    while len(order) < n:
        order.append(i)
        i += d
        if i == 5: d = -1
        if i == 0: d = 1
    return order
for gif, nframes, state in plan:
    base = [Image.open(f"{frames_dir}/bicho-{state}-{k}.png").convert("RGB")
            .resize((192, 192), Image.LANCZOS) for k in range(6)]
    # FIX (padrao geometrico/frames pretos): paleta GLOBAL unica p/ TODOS os frames.
    # Sem isto o Pillow gera paleta local por frame + disposal parcial, e o decoder
    # de GIF do _og.exe reconstroi frames partiais (buracos pretos) = lixo na tela.
    sample = Image.new("RGB", (192 * 6, 192))
    for k in range(6):
        sample.paste(base[k], (192 * k, 0))
    pal_img = sample.quantize(colors=255, method=Image.MEDIANCUT)
    fr = [base[k].quantize(palette=pal_img, dither=Image.NONE)
          for k in pingpong(nframes)]
    # disposal=1 (nao limpa) + optimize=False => cada frame e um keyframe completo.
    fr[0].save(f"{out}/{gif}", save_all=True, append_images=fr[1:],
               duration=100, loop=0, disposal=1, optimize=False)
    print(f"   {gif}: {nframes} frames ({state}, paleta global)")
PY

echo ">> [3/4] recompilando o projeto AHMI com os 3 gifs do Clawd (via _og.exe/Wine)"
mkdir -p "$SCRATCH/zwork" && cd "$SCRATCH/zwork"
unzip -q "$FILEZIP"
for row in "${PLAN[@]}"; do
  gif=$(echo "$row" | awk '{print $1}')
  cp -f "$SCRATCH/$gif" "./$gif"   # substitui o gif de origem mantendo o nome
done
# usar o `zip` de SISTEMA (o zipfile do Python e rejeitado pelo compilador)
rm -f "$SCRATCH/file_clawd.zip"
zip -q -r -X "$SCRATCH/file_clawd.zip" .

cd "$GEN"
rm -rf "$SCRATCH/ACF" && mkdir -p "$SCRATCH/ACF"
printf '13\n' | WINEDEBUG=-all WINEPREFIX="$WINEPREFIX_DIR" \
  wine AHMISimGenDemo_og.exe -f "$SCRATCH/file_clawd.zip" -m 2 -c 0 -e 0 -d 1 \
  -o "$SCRATCH/ACF" 2>&1 | grep -c 'STCRGBA compress completed' \
  | xargs -I{} echo "   frames assados (STCRGBA): {}"
cp "$SCRATCH/ACF/Texture.acf" "$OUT_ACF"
echo "   ACF salvo em $OUT_ACF ($(wc -c < "$OUT_ACF") bytes)"

if [ "$NO_UPLOAD" = "1" ]; then
  echo ">> [4/4] --no-upload: pulando o hardware. Suba com:"
  echo "   $SIDECAR -mode cli -cmd upload -file $OUT_ACF -type texture -device $DEVICE"
  exit 0
fi

echo ">> [4/4] subindo pra telinha (slot texture / 0x08100000)"
if ! timeout 15 "$SIDECAR" -mode cli -cmd read-reg -reg 2 -device "$DEVICE" >/dev/null 2>&1; then
  echo "   !! MCU mudo. Rode: sudo usbreset 0324:0324  e tente de novo."
  exit 1
fi
"$SIDECAR" -mode cli -cmd upload -file "$OUT_ACF" -type texture -device "$DEVICE" 2>&1 | tail -1
"$SIDECAR" -mode cli -cmd show-page -page 5 -device "$DEVICE" >/dev/null 2>&1
echo "   subido e ativada a pagina 5 (Gif1/genius). Alterne com a tecla via:"
echo "   sudo python3 $DIR/minitela_daemon.py   (tecla Minitela cicla 5 -> 6 -> 7)"
