> **NOTA HISTÓRICA — não use como referência.**
>
> Este arquivo era o `CLAUDE.md` do projeto até 2026-07-16. É o log de sessão de
> como o projeto foi descoberto, preservado porque explica *por que* chegamos
> aqui e quais rotas já foram refutadas.
>
> **Ele se contradiz.** Cada sessão empilhava a descoberta nova sem voltar para
> marcar a antiga como morta. As 13 contradições conhecidas estão resolvidas no
> `CLAUDE.md` atual e no `README.md` — quando este arquivo divergir deles, eles
> vencem. Os pontos mais enganosos:
>
> | Aqui você lê | O fato, verificado |
> |---|---|
> | "página 5 REINICIA o MCU — EVITAR" (§ Detalhes) | é estável com textura válida no slot; o Clawd roda nela |
> | "Tecla física é KEY_PROG1 (148)" (§ Tecla física) | é **KEY_F16 (186)**, no `event15` — não no `event3` |
> | "`asm` não está no grupo dialout" (§ Hardware) | está |
> | 3 seções de "GIF bloqueado/impossível" | o GIF animado **funciona** desde 2026-07-15 |
> | "`_og.exe` nunca assa mais de 1 frame" | falso; assa N frames |
> | "21/30/44 = nº de frames do gif de fábrica" | os de fábrica têm **1 frame**; 21/30/44 é o que a page-def do **firmware** exige |
> | "precisa do `file_gif.zip`" | não precisa |
> | "montar o dashboard nas páginas 7/8/9" | página nova dá tela branca; substituir os fundos de 1/2/3 |

---

# telinha — Minitela do Positivo Vision R15M

## O que é isto

Notebook **Positivo Vision R15M** (Ryzen, Fedora 43 KDE/Wayland), com uma **Minitela**
secundária: display IPS 1.54", 240x240px, embutida no chassi perto do botão de força.
Tecla física dedicada **"Minitela"** no teclado: toque rápido = alterna conteúdo,
segurar 2s = liga/desliga.

De fábrica, a Minitela só mostra notificações do WhatsApp, clima, fotos/gifs, via
app fechado da Positivo (só Windows/Debian oficialmente — não roda no Fedora).
**Objetivo do usuário:** construir algo próprio que se conecte na Minitela e exiba
o que quisermos — hoje, especificamente, dados do `claude-usage-widget`
(`~/.claude/widget-data.json`): limite semanal, sessão atual, tier "fable",
contagem regressiva pro reset. Alternar entre essas telas ao tocar a tecla física.

## Hardware / identificação do dispositivo

- Aparece como `/dev/ttyACM0` (USB CDC-ACM), `idVendor=0324 idProduct=0324`,
  manufacturer `CherryUSB`, product `sxw-admin_CDC_DEMO` (firmware customizado da
  Positivo rodando no MCU da telinha, stack CherryUSB embarcado).
- **Permissão**: o dispositivo pertence a `root:dialout`, modo `660` — o usuário
  `asm` não está no grupo `dialout` ainda. Toda vez que o cabo/dispositivo
  reconecta (replug, reboot), a permissão volta ao padrão e precisa liberar nas mãos:
  ```
  sudo chmod 666 /dev/ttyACM0     # temporário, até o próximo replug/reboot
  sudo usermod -a -G dialout asm  # definitivo, só vale após logout/login (ainda não fizemos o logout)
  ```

## SideCar — ferramenta usada para falar com a Minitela

Achamos um projeto de terceiros no GitHub, **não-oficial mas ativo**, que já tinha
feito engenharia reversa do protocolo serial: https://github.com/FreyreCorona/SideCar
(MIT license, Go, single maintainer). Baixamos o binário oficial (release v0.1.26,
checksum conferido) mas ele tinha bugs que impediam o uso via linha de comando —
por isso clonamos o código-fonte e corrigimos localmente.

- **Fonte clonada em**: `/home/asm/telinha/sidecar-src/` (git clone do upstream)
- **Binário corrigido, compilado localmente**: `/home/asm/telinha/sidecar/SideCar-fixed`
- Requer Go ≥1.26 (`GOTOOLCHAIN=auto go build -o /home/asm/telinha/sidecar/SideCar-fixed .`
  dentro de `sidecar-src/` — baixa o toolchain certo sozinho).
- O binário oficial baixado (não corrigido) também existe em `/home/asm/telinha/sidecar/SideCar` —
  **não usar**, tem os bugs abaixo.

### Bugs encontrados e corrigidos no fork local

1. **`main.go` — dispatch de `-mode` quebrado.** O código original faz
   `runDaemonMode(os.Args, ...)` / `runCLI(os.Args, ...)`, passando a lista CRUA
   e completa de argumentos (incluindo `-mode X` já consumido) pro FlagSet
   específico do daemon/cli, que não conhece a flag `-mode` — erro
   `flag provided but not defined: -mode` sempre, tornando `-mode daemon` e
   `-mode cli` **inutilizáveis** no binário oficial. Corrigido com uma função
   `splitMode()` que extrai manualmente o par `-mode X` antes de despachar,
   e só passa o restante dos args pro sub-parser.

2. **`core/command.go` — validação de CRC incorreta.** Confirmado enviando frames
   brutos manualmente (bypass do binário, via Python + `os.open`/`os.write` direto
   no `/dev/ttyACM0`): o dispositivo real ativa o bit "CRC habilitado" no
   controlFlag das respostas, mas **sempre manda o campo de CRC como `0x0000`**
   (não calcula um CRC de verdade pras próprias respostas). O código original
   comparava esse `0x0000` contra um CRC calculado de verdade, dava mismatch,
   e `ReadResponse` entrava num loop de descarte silencioso até estourar o timeout
   — por isso `SetRegister`/brilho pareciam travar pra sempre, mesmo o dispositivo
   respondendo em ~200ms. Corrigido em `ParseFrame`: se o campo CRC vier zerado,
   aceita a resposta (sem tentar validar), em vez de comparar.

3. **`core/register.go` — formato de ACK de escrita diferente do de leitura.**
   Confirmado via bytes brutos: a resposta de **leitura** de registrador usa o
   layout assumido (header + regID(2) + valor(4) = 6 bytes por registro,
   functionCode=0). A resposta de **escrita** usa um layout mais curto e diferente
   (functionCode=2, menos bytes do que o esperado) que ninguém documentou direito
   — nem o autor original (comentário dele: protocolo feito "by trial and error").
   `parseNumRegResponse` foi relaxado: só valida o formato estrito no caso
   `functionCode==0` (leitura); qualquer outro caso é tratado como confirmação de
   sucesso sem tentar decodificar valores (a escrita em si funciona, só o eco da
   resposta que tem formato desconhecido).

4. **Comando novo adicionado**: `-cmd show-image -file <PNG 240x240>` em `cli.go`
   — decodifica PNG, converte pra RGB565 little-endian (`loadRGB565PNG()`),
   monta o `.acf` via `core.BuildACF` (já existente no projeto), e faz upload
   como `FileTypeTexture`. Isso já funcionou uma vez: upload completou 0→100%
   sem erro (`done: image shown on minitela`).

### Protocolo serial (referência rápida, confirmada empiricamente)

Frame: `[0x41,0x48] start | controlFlag(2 BE, bit15=crcFlag, bits14:0=dataLen) |
cmdType(2 BE) | content(N) | crc16(2 BE, ou 0x0000) | [0x4D,0x49] end`

CRC-16/IBM reflected (poly 0xA001), mas **na prática as respostas do device vêm
sempre com esse campo zerado** — ver bug #2 acima.

Comandos principais (`core/command.go`, `core/tags.go`):
- `CmdHandshake` 0x0080 → `CmdHandshakeResponse` 0x00C0
- `CmdSetRegister` 0x0090 → `CmdSetRegisterResp` 0x00D0 (leitura E escrita de registrador passam por aqui, diferenciados pelo function code no header do content)
- `CmdRequestDownload`/`CmdDownloadData`/`CmdDownloadComplete` — fluxo de upload de textura/firmware
- `CmdSwitchState` 0x0071 → `CmdSwitchStateResp` 0x00B1 — troca de "modo" do dispositivo. Valor `0x10` = sai do modo AHMI (exibição) e entra em modo download (usado internamente pelo upload). **Não existe no código original nenhuma chamada de volta pro modo de exibição depois do upload terminar** — isso é suspeito de ser a causa de "upload completou mas a tela não mudou visualmente".
- Registradores úteis: `RegBrightness=7`, `RegCurrentPage=2` (`core/tags.go` tem a lista completa: bateria, wifi, clima, notificações, mídia, etc — pensado originalmente pra um dashboard tipo o nosso).

## `render_dashboard.py`

Em `/home/asm/telinha/render_dashboard.py`: lê `~/.claude/widget-data.json`
(escrito pelo coletor do projeto `~/projects/claude-usage-widget`, que já roda
instalado/ativo na máquina) e renderiza um PNG 240x240 com sessão/semana/tokens
de hoje, usando Pillow. Uso: `python3 render_dashboard.py /caminho/saida.png`.

Pipeline completo testado (uma vez, com sucesso):
```bash
python3 /home/asm/telinha/render_dashboard.py /tmp/dashboard.png
sudo chmod 666 /dev/ttyACM0   # sempre que resetar/religar
/home/asm/telinha/sidecar/SideCar-fixed -mode cli -cmd show-image \
  -file /tmp/dashboard.png -device /dev/ttyACM0
```

## ESTADO ATUAL (2026-07-15) — RESOLVIDO o essencial, projeto destravado

Sessão de 2026-07-15 fez a engenharia reversa do APP OFICIAL da Positivo e
resolveu as pendências antigas. Ver `minitela-oficial/ACHADOS-RE.md` (análise
completa) e `minitela.py` (cliente serial próprio, funcionando).

### RESOLVIDOS E FUNCIONANDO (checklist, tudo testado no hardware real)

- [x] **Recuperar firmware travado**: `sudo usbreset 0324:0324` (reset de protocolo
      USB). É a ÚNICA coisa que destrava o MCU quando o serial fica mudo.
- [x] **Cliente serial próprio** `minitela.py`: handshake, escrita de registrador
      numérico e de string, troca de página — sem depender do SideCar (que tinha
      bug no parse de ACK de string).
- [x] **Exibir dados na tela**: escrever registrador de string na página Notas (2)
      FAZ o texto aparecer na telinha. Comprovado com dados reais do Claude
      ("Semana 81% / reset Sab 05h").
- [x] **Trocar de página**: `SetRegister reg=2 (RegCurrentPage)` = número da página.
      Páginas 1-4 estáveis. **CORREÇÃO (2026-07-15): página 5 (gif) é ESTÁVEL** se
      houver uma textura válida no slot antes de ativá-la — ver
      `minitela-oficial/BREAKTHROUGH-GIF-2026-07-15.md`. O reinício antigo vinha de
      ativar a página 5 sem textura. Subir `Texture21.acf` de fábrica + `show-page 5`
      FEZ o gif de fábrica ANIMAR (confirmado visualmente), MCU vivo.
- [x] **Ler registrador**: handshake + read-reg funcionam (ex: página ativa, brilho).
- [x] **Permissão**: usuário `asm` já está no grupo `dialout` (logout/login feito).
      Falta só aplicar a regra udev pra evitar o chmod a cada replug (ver abaixo).
- [x] **RE do app oficial completa**: código JS legível e binários com símbolos em
      `minitela-oficial/`. Protocolo, geração de ACF e mapa de registradores confirmados.
- [x] **Tecla física mapeada e FUNCIONANDO**: no hardware real é **KEY_F16
      (keycode 186)** no "AT Translated Set 2 keyboard" (`/dev/input/event3`) — NÃO
      o 148 que o app oficial usava (roteamento difere no Fedora/KDE). Confirmado
      via `sudo libinput debug-events --show-keycodes`. O `minitela_daemon.py` lê
      essa tecla e alterna as telas — TESTADO, alterna perfeitamente.
- [x] **3 páginas vazias descobertas** (New-page 7/8/9) no projeto AHMI de fábrica —
      canvas livre pra montar nosso dashboard visual próprio.
- [x] **Compilador AHMI roda via Wine** (wine-11.0). `AHMISimGenDemo_og.exe` extrai
      o `file.zip`, processa páginas/tags/texturas e GERA `Texture.acf` válido
      (851976 bytes, mesmo projectID/versão/deviceID da textura de fábrica).
      Comando testado (rodar com `cwd` em `ide-utils/Gen/`, WINEPREFIX próprio):
      `printf '13\n' | wine AHMISimGenDemo_og.exe -f ../file.zip -m 2 -c 0 -e 0 -d 1 -o ACF_out`
      (o `13\n` no stdin é o "pressione tecla" que o acfGenerator.js manda). Saída
      em `ACF_out/Texture.acf`. **Caminho do visual próprio está VIÁVEL e provado.**

### VISUAL PRÓPRIO — RESOLVIDO E FUNCIONANDO

O dashboard com visual próprio ESTÁ FUNCIONANDO na telinha. As descobertas que
destravaram:

1. **Não há ConfigData em endereço separado** (RE do `electron.js` oficial
   confirmou o mapa de flash completo). A definição das páginas mora DENTRO do
   `Texture.acf` (bloco AHMI na cauda + header de 16KB). Subir a `Texture.acf` pra
   `texture=0x08100000` (via SideCar `-cmd upload -type texture`) É o caminho certo
   — não precisa cartão TF. O SideCar já passa o md5 do arquivo como fileId (certo).

2. **NÃO criar página nova (7/8/9) — SUBSTITUIR o fundo de páginas de fábrica que
   já renderizam.** Criar página nova dá tela branca (o firmware físico não tem a
   definição). Substituir `r-1-0.png` / `r-2-0.png` / `r-3-0.png` (fundos das
   páginas Reminder/SystemInfo/Weather) e ZERAR os widgets dessas páginas no
   `data.json` funciona perfeitamente.

3. **FUNDO CLARO obrigatório.** O compilador `AHMISimGenDemo` corrompe cores
   quase-pretas (fundo escuro vira branco/lavado na tela; só cores fortes tipo
   vermelho sobrevivem). Telas com FUNDO CLARO e texto escuro/colorido renderizam
   perfeito (igual às telas de fábrica). Ver `render_telas.py`.

**Pipeline completo que funciona (as 3 telas de porcentagem estão na telinha):**
```
python3 render_telas.py <dir>                 # gera 3 PNGs 240x240 fundo claro
# num work-dir: unzip file.zip, cp telas p/ r-1-0/r-2-0/r-3-0.png (RGBA 240x240),
#   zerar widgetList das páginas 1,2,3 no data.json, rezip
cd ide-utils/Gen && printf '13\n' | WINEPREFIX=... wine AHMISimGenDemo_og.exe \
   -f <file.zip> -m 2 -c 0 -e 0 -d 1 -o <out>  # recompila via Wine
./sidecar/SideCar-fixed -mode cli -cmd upload -file <Texture.acf> -type texture ...
./sidecar/SideCar-fixed -mode cli -cmd show-page -page 2 ...   # 2=Semana,3=Sessao,4=Fable
```

**Mapeamento página->valor RegCurrentPage (confirmado no hardware):**
valor 2 = Semanal, 3 = Sessão, 4 = Fable (projeto páginas 1/2/3, 1-based no reg).

**Daemon da tecla (`minitela_daemon.py`) — FUNCIONA:** lê KEY_F16 (186) do
event3, auto-detecta o device, cicla valor 2->3->4 a cada toque. Rodar com sudo
(ou pôr `asm` no grupo `input`).

Arquivos do projeto: `render_telas.py` (3 telas), `minitela.py` (cliente serial),
`minitela_daemon.py` (tecla), `detect_tecla.py` (descobrir keycode).

### BICHINHO CLAWD — GIF ANIMADO FUNCIONANDO (2026-07-15, RESOLVIDO no hardware)

O Clawd ANIMADO roda na telinha. Confirmado visualmente ("ficou perfeito"): o estado
fogo (dumb) na página 6 anima em sequência, imagem reconhecível, fundo claro.

**TETO DE 3 PÁGINAS ANIMADAS — provado, NÃO reabrir sem re-flash.** O hardware tem só
3 páginas com page-def de animação (Gif1/2/3 = valores 5/6/7). Ter 5 animadas INSTANTÂNEAS
foi investigado a fundo e é IMPOSSÍVEL sem re-flash de firmware (que também não existe pela
via do app). Todas as rotas refutadas com prova (ver `EXPLORAR-5-GIFS.md`, `FORJAR-AHMI.md`,
`FIRMWARE-UPDATE-RE.md`):
- Criar página nova no data.json -> compilador não gera page-def de animação nova.
- Forjar o bloco AHMI no .acf -> o .acf NÃO carrega page-def de animação; os "21/30/44"
  são COORDENADAS de widget, não frame-counts. A animação vive no firmware.
- Registrador que troque o frame-set de uma página -> não existe.
- Firmware update pela via do app -> enum serial fechada de 10 comandos, sem opcode de
  firmware/erase/bootloader. Re-flash real = imagem ausente + risco de brick.
Para os 5 estados animados: ou 3 instantâneos (páginas 5/6/7) + 2 estáticos, ou os 5 via
re-upload de ~15s por troca (`minitela_daemon.py` modo padrão). É o teto do dispositivo.

- Registrador que troque frame-set sem re-upload: TESTADO NO HARDWARE, não existe
  (ver `REG-SLICE-TESTE.md`). Reg 1 (Animation control) é playback, não seletor de
  conteúdo; reg 8 (frame rate) é read-only na prática; nenhum dos 57 tags troca o
  atlas de uma página. Conteúdo animado = atlas subido; trocar = re-upload. FIM da
  linha — não reabrir sem re-flash de firmware.
- Estabilidade do re-upload (descoberta): upload de 1.6-4.2MB deixa o serial ocupado
  ~6s; mandar comando antes disso parece "MCU mudo" mas NÃO é trave. O daemon dá
  respiro de 6s após upload (não precisa usbreset no caso normal). usbreset só se
  ficar mudo APÓS o respiro.
- Dois .acf diferentes por modo (NÃO confundir — foi fonte de bug):
  - `--gif3` (troca instantânea, só show-page): precisa do `clawd-anim.acf` (3 Clawds
    DIFERENTES nas páginas 5/6/7). Subir 1x, tecla cicla instantâneo.
  - padrão/ciclo-gif (5 estados, re-upload ~15s/toque): usa os `clawd-gif-<estado>.acf`
    (cada um com o MESMO Clawd nas 3 páginas gif, pra nunca mostrar tela da Positivo).
  - Subir um `clawd-gif-*` e testar no `--gif3` mostra o MESMO Clawd nas 3 (bug visto).
- Daemon: precisa de ROOT (lê /dev/input/event3). Sem sudo, avisa e sai (não trava
  mudo). Tecla confirmada = KEY_F16 (186) no event3.

### INDICADOR DE MODELO — `minitela_clawd.py` (2026-07-15, FUNCIONANDO)

A Minitela mostra o bichinho do Clawd conforme o MODELO em uso no Claude Code:
- **opus -> genius (coroa), pág 6 | sonnet -> smart (livro), pág 7 | fable -> fogo, pág 5.**
- Fonte do modelo: **`~/.claude/settings.json`** campo `"model"` (nome curto
  opus/sonnet/fable). O `/model` grava ali NA HORA ("saved as your default"). NÃO usar
  o transcript .jsonl — ele só registra o modelo quando o assistant RESPONDE, então um
  /model trocado rápido (sem resposta no meio) nunca aparece lá — foi o bug inicial.
  Subagentes não interferem: o settings.json guarda só o /model da sessão, não deles.
- Troca INSTANTÂNEA (só `show-page`, sem re-upload). REQUER `clawd-anim.acf` (3 Clawds
  DIFERENTES nas pág 5/6/7) já subido no hardware.
- **Tecla F16 = override manual**: um toque cicla fogo/genius/smart na mão por 20s;
  depois volta a seguir o modelo sozinho. Loop único com `select` (tecla nao-bloqueante
  + polling do modelo a cada 3s).
- Rodar: `sudo python3 minitela_clawd.py` (precisa root p/ a tecla; `--no-key` dispensa
  root e só segue o modelo). Serviço systemd `minitela-daemon.service` já aponta p/ ele.
- Testado: opus->genius aplicado no hardware; troca de /model reflete em ~3s.
- **Bug corrigido (home do root):** o daemon roda como root p/ ler a tecla, então
  `~` = /root e o settings.json (no home do usuário) não era achado -> lia None ->
  fogo. FIX: caminho fixo `/home/asm` (env `MINITELA_HOME` sobrescreve). Vale p/
  settings.json E widget-data.json.

**Dois CONJUNTOS (cada um = 1 .acf com 3 Clawds nas pág 5/6/7), gerados por
`gerar_conjunto.sh <saida> <est5> <est6> <est7>`:**
- NORMAL = `clawd-anim.acf`: pág5=fogo, 6=genius, 7=smart.
- ALERTA = `clawd-alerta.acf`: pág5=fogo, 6=chuva, 7=fantasminha.

**ALERTA de tokens:** a cada 1h o daemon verifica `max(session%, weekly-do-modelo%)`
do widget-data.json. >=90% -> fantasminha; 70-90% -> chuva; <70% -> normal. Considera
sessão E semana (o pior). Ao ENTRAR/SAIR de alerta troca o CONJUNTO (re-upload ~15s,
raro); dura 20min. A tecla cicla os 3 bichinhos do CONJUNTO ATIVO — no normal
fogo/genius/smart, no alerta fogo/chuva/fantasminha (é o "cicla entre os ativos").
Prioridade: tecla (override 20s) > alerta > modelo. Daemon reescrito limpo em
`minitela_clawd.py` (estado `conjunto` = normal|alerta, `garantir_conjunto()` só
re-sobe se mudou). `--print` mostra o estado sem tocar hardware.

**Como funciona (o que destravou):**
1. A page-def de animação (nº frames, delays, offsets) vive no FIRMWARE, ligada a cada
   página de gif (Gif1/2/3 = valores 5/6/7). O `.acf` só entrega os PIXELS. Basta trocar
   o gif de origem no `file.zip` por um gif do Clawd com o MESMO nº de frames e recompilar
   com `_og.exe` (o mesmo dos estáticos). NÃO precisa de `file_gif.zip`, `_gif.exe -g`,
   nem do slot texture_gif (0x08500000, código morto). Ver `BREAKTHROUGH-GIF-2026-07-15.md`.
2. Páginas: Gif1(val 5)=`1i1h1e...471.gif`=21 frames; Gif2(val 6)=`1h1k1e...464.gif`=30;
   Gif3(val 7)=`1h1m1e...466.gif`=44. O gif do Clawd precisa ter o MESMO nº de frames.
3. **BUG CRÍTICO resolvido (padrão geométrico/preto):** salvar o gif com paleta LOCAL
   por frame + disposal/optimize do Pillow fazia o decoder do `_og.exe` reconstruir
   frames PARCIAIS (buracos pretos) = lixo geométrico na tela. FIX: paleta GLOBAL única
   compartilhada + `disposal=1` + `optimize=False` → cada frame vira keyframe completo.
   Ver `CLAWD-GIF.md` seção "Correção tela-preta + alinhamento".
4. Limite de animação sutil: o overlay `halo` (genius) muda só ~2.5% dos pixels entre
   frames (parece congelado); `fire` (fogo) muda ~19%, anima bem. É limitação da FONTE
   dos sprites, não do pipeline.

**Pipeline (script pronto):** `./montar_clawd_gif.sh` gera os 3 gifs do Clawd, troca no
zip, compila num `.acf` único (`clawd-anim.acf`, ~4.24MB, firmware aceita), sobe no slot
texture e ativa a página 5. A tecla física cicla 5->6->7 via `minitela_daemon.py`.

**Clawd ESTÁTICO (5 estados):** `./montar_clawd_estatico.sh` sobe 1 imagem parada por
estado (genius/smart/slow/dumb/braindead) nas páginas 1-5 (`clawd-estatico.acf`, ~393KB).
Tecla cicla 1..5 via `minitela_daemon.py --estatico`.

**Daemon da tecla (`minitela_daemon.py`) — 3 modos:** sem flag = gifs (5/6/7);
`--estatico` = 5 estáticos (1-5); `--dash` = dashboards de uso (2/3/4). Tecla KEY_F16 (186).

### BICHINHO CLAWD — ESTÁTICOS FUNCIONANDO

Os sprites do mascote Clawd estão em `~/projects/claude-usage-widget/plasmoid/
contents/icons/` (gerados por `scripts/generate-sprites.py`): base `clawd.svg` +
overlays de 6 frames cada — halo (genius/coroa), smart (livro+café), rain
(slow/chuva), fire (dumb/fogo), skull (braindead/caveira). Estado atual vem de
`widget-data.json` -> `dumbness.level`.

- `render_bichinhos.py` compõe Clawd+overlay em 240x240 fundo claro (rasteriza o
  clawd.svg via ImageMagick `magick`, cairosvg ausente). `--frames` gera 6 frames.
- `montar_bichinhos.sh` gera + compila + sobe os 4 bichinhos (genius/smart/slow/
  dumb) nas páginas 0-3. ACF salvo em `minitela-oficial/bichinhos.acf`. TESTADO,
  todos aparecem certinhos e alternam pela tecla.
- Limite: só 4 páginas de fundo estático (0-3); o 5º (braindead) fica de fora até
  o GIF ou re-upload. Cores CLARAS obrigatórias (compilador corrompe escuro).

### GIF animado — BARREIRA no firmware (rejeita 0x3B)

Progresso: descobrimos como GERAR os artefatos de GIF. O `_gif.exe` **SEM a flag
`-g`** (só `-f zip -m 2 -c 0 -e 0 -d 1 -o out`) processa o GIF e gera `GIF_0.acf`,
`GIF_1.acf`, `GIF_2.acf` no dir `Gen/` (magic 0x4947 "GI", ~37KB, contêm GIF8
real) + estruturas de animação (`gAnimationClass`, `FrameBuffer`). A flag `-g`
dispara a checagem "Texture address over 0MB" que precisa do `file_gif.zip`
ausente — mas SEM `-g` funciona.

BARREIRA REAL: subir `GIF_0.acf` como `-type texture_gif` (endereço 0x08500000) é
**rejeitado pelo firmware com `requestDownload rejected: 0x0000003B`** (código 59),
mesmo com a página GIF (valor 5) ativa antes. O app oficial não trata 0x3B
especialmente (qualquer resposta != 0/0xFFFFFFFF = falha). Hipóteses não
esgotadas: (a) precisa de erase do flash de GIF antes (há EraseStoreSpace.bin em
0x080FC000, sem chamada no fluxo visto); (b) o firmware deste hardware não aceita
GIF via serial, só via re-flash; (c) falta um estado/sequência do MiniPanel não
replicado. Upload de imagem estática (texture, 0x08100000) funciona 100%; só o
slot de GIF (0x08500000) recusa. Os artefatos ficam em `Gen/GIF_0.acf`.

DECISÃO: bichinhos ESTÁTICOS funcionam e é o entregável atual.

### GIF animado — CONCLUSÃO da investigação (2026-07-15): bloqueado por falta do file_gif.zip

Investigação exaustiva fechou o diagnóstico do GIF:
1. **O slot `texture_gif` (0x08500000) é CÓDIGO MORTO.** RE do app oficial (bundle
   React + App.o) provou que ele NUNCA sobe pra 0x08500000 — todos os 21 botões de
   GIF sobem `TextureN.acf` como `-type texture` (0x08100000). O `0x3B` no
   RequestDownload pra 0x08500000 é o firmware recusando um endereço não-usado.
   Confirmado: até o GIF de fábrica (idêntico byte-a-byte) dá 0x3B nesse slot.
2. **O app embute o GIF DENTRO do Texture.acf** (frames viram bitmaps no ACF),
   subido no slot normal. Mas isso exige o `_gif.exe` COM a flag `-g`.
3. **`_gif.exe` sem `-g`**: compila, mas o GIF resultante renderiza PRETO na tela
   (testado com propaganda de fábrica — página Gif fica preta). Inútil.
4. **`_gif.exe` com `-g`**: erro "Texture address over 0MB" — precisa do
   **`Zip/file_gif.zip`** (projeto-base de GIF) que NÃO veio no `.deb`. A Positivo
   o gera pela nuvem da Sigma (graphichina). Nenhuma combinação de flags
   (`-g 3/7/15`, `-m 3`, `-t`) contorna — o valor de textura vem do file_gif.zip,
   não da CLI. O `data.json` do file.zip normal não tem campo de texture address.

### GIF — AVANÇO: compilador destravado, mas firmware recusa o GIF_0.acf

CAUSA DO "over 0MB" ERA BUG DE FLAG (resolvido via disassembly do _gif.exe):
a flag `-e` exige argumento numérico colado. O comando certo é
`-e 0 -g 1` (NÃO `-e -g 1 0` — aí o getopt engole o `-g` como arg do `-e` e o
limite de textura fica 0). `-e 0`=15MB, `-e 1`=256MB, `-e 2`=1024MB. O `0` solto
depois de `-g 1` é ignorado. NÃO precisa de file_gif.zip, products.json com 9002,
nem texture_path.cfg — o disassembly provou que o limite vem SÓ do `-e`.

Comando que FUNCIONA (gera GIF_0.acf com N frames reais):
```
printf '13\n' | wine AHMISimGenDemo_gif.exe -f projeto.zip -m 2 -c 0 -e 0 -g 1 -d 1 -o out
```
O `_gif.exe -g` gera só `GIF_0.acf` (no cwd Gen/) + filevectors (no -o dir). Com 6
frames o GIF_0.acf fica ~221KB (header GIF8, w/h 192, byte20=numframes, byte24=delay).

NOVO BLOQUEIO (firmware): o `GIF_0.acf` (magic "GIF8") não é aceito por nenhum
slot testado: como `texture` (0x08100000) o firmware pisca azul e mostra símbolo
de erro (information); como `texture_gif` (0x08500000) rejeita com 0x3B. Mesmo o
GIF de fábrica de 1 frame dá o mesmo erro — não é nº de frames nem conteúdo. O
`GIF_0.acf` precisa estar EMBUTIDO num Texture.acf completo (frames viram bitmaps
dentro do ACF principal), mas o modo `-g` NÃO monta esse Texture.acf — só produz o
GIF_0.acf solto. Falta descobrir como o app monta o Texture.acf final embutindo o
GIF (o fluxo real usa replaceGif no file_gif.zip + genAcf, que depende do
file_gif.zip ausente). Bichinhos ESTÁTICOS seguem como entregável funcional.

### Detalhes do que foi provado e está funcionando

1. **Recuperação do firmware travado = USB reset** (`sudo usbreset 0324:0324`),
   NÃO comandos serial. Quando o MCU para de ler o serial (fila TX `TIOCOUTQ`
   enche em 1280 e não drena), só o reset de protocolo USB reinicia a task serial.
   Testado e comprovado. O `.deb` oficial traz a regra udev definitiva:
   `/etc/udev/rules.d/99-ttyacm.rules` → `SUBSYSTEM=="tty", KERNEL=="ttyACM*", MODE="0666"`
   (aplicar isso acaba com o chmod manual a cada replug).

2. **Causa do travamento da sessão anterior**: `SwitchState(0x20)` foi um comando
   inválido. `0x20` é um ESTADO reportado (downloadStateAHMI), não argumento. O
   ÚNICO valor válido de SwitchState é `0x10` (sair do AHMI/entrar em download).
   CORREÇÃO (2026-07-15, captura do `electron.js` shipado — ver
   `minitela-oficial/CAPTURA-APP-OFICIAL.md`): o app oficial **SIM** envia
   `SwitchState 0x71 content 0x10` no início do upload, quando GET_DOWNLOAD_STATUS
   retorna 0x20 (estado AHMI). A nota antiga "NUNCA envia SwitchState" estava
   ERRADA. O que trava é mandar `0x20` como argumento, não o `0x10`.

3. **`minitela.py`** — cliente serial próprio (não depende do SideCar, que tinha
   bug no parse de ACK de string). Faz handshake, escreve registradores numéricos
   e de string (formato exato de `messageProcessor.js`), troca página. Testado:
   escrever `RegReminder1` (1090/1091) na página Notas (2) EXIBE o texto na tela.

4. **Mapa das páginas de fábrica** (só 1-4 são estáveis; 5+ = gif reinicia o MCU):
   - Página 1=WhatsApp, 2=Notas (1 bloco de TEXTO LIVRE: reg 1090 content + 1091
     time — único canvas de texto útil), 3=Monitor (só ícones wifi/bat/BT),
     4=Clima (layout fixo), 5=Imagens/GIFs (REINICIA o MCU ao ativar — EVITAR).

5. **Por que subir PNG nunca exibiu**: no AHMI o vínculo textura→página é fixado
   na COMPILAÇÃO. Exibir imagem própria exige recompilar o projeto AHMI com o
   compilador `AHMISimGenDemo_og.exe` (Windows, via Wine), não subir textura solta.

### CAMINHO ESCOLHIDO (em andamento): recompilar ACF com página própria

O `file.zip` do projeto AHMI de fábrica está em `minitela-oficial/ide-utils/`
(extraído em `projeto/`). O `data.json` (410KB) é o projeto editável completo:
`pageList[10]`, `resourceList[62]`, `tagList[57]`. **Descoberta chave: as páginas
7, 8, 9 são "New-page" VAZIAS** — dá pra montar nosso dashboard nelas (widgets +
texto ligado a registradores + fundo próprio), recompilar via Wine, e ter as
barrinhas do widget ocupando a tela toda, alternando com a tecla física.

Compilação (de `acfGenerator.js`), roda em `ide-utils/Gen/`:
```
AHMISimGenDemo_og.exe -f file.zip -m 2 -c 0 -e 0 -d 1 -o <saveDir>   # GC9002=0, dither=1
```

### Tecla física "Minitela" (provado no disassembly de main.o)

É `KEY_PROG1` (keycode **148**, ou alternativo 97), lida via libevdev de
`/dev/input/event*` do device chamado `"AT Translated Set 2 keyboard"` (teclado
interno). `EV_KEY code==148 value==1` = press. Toque curto → troca tela; segurar
>1s → abre config. Podemos rodar NOSSO listener independente do app da Positivo.
Alternar tela = SetRegister reg=2 (RegCurrentPage) com a próxima página.

### Próximos passos

1. Instalar Wine no Fedora e rodar `AHMISimGenDemo_og.exe` (testar se roda o .exe
   chinês; pode precisar de winetricks/DLLs). Recompilar o projeto SEM alteração
   primeiro, pra validar que o gerador funciona e o ACF resultante sobe e exibe.
2. Entender o formato de `canvasList`/widgets no `data.json` pra montar o dashboard
   nas páginas New-page (7/8/9): barras de progresso (sessão/semana/fable), texto
   ligado aos registradores de dados, contagem regressiva.
3. Daemon próprio que: lê `~/.claude/widget-data.json`, escreve os registradores,
   escuta a tecla KEY_PROG1 e alterna entre as páginas New-page do nosso dashboard.

---

## HISTÓRICO — estado anterior (resolvido, mantido para contexto)

**O hardware estava instável e era rastreável, não um mistério:**

1. O primeiro upload completou (log mostrou 0→100%, `done: image shown on minitela`),
   mas o usuário reportou que a tela física **não mudou visualmente** — continuou
   mostrando o WhatsApp de sempre. Hipótese: falta o passo de "voltar ao modo AHMI/
   exibição" depois do `DownloadComplete` (ver bug do SwitchState acima).

2. Tentei validar essa hipótese mandando **`SwitchState(0x20)` na mão, via bytes
   crus, SEM confirmar antes que esse valor era seguro/correto** — foi um palpite
   baseado só no nome da constante `downloadStateAHMI = 0x20` em `upload.go`.
   Depois desse comando, o dispositivo **parou de responder a handshake** via
   serial (mas a tela continuava mostrando o WhatsApp, então o MCU não travou
   totalmente).

3. Tentei recuperar via: rebind USB por software (`unbind`/`bind` em
   `/sys/bus/usb/drivers/usb/`) — piorou, a porta nem re-enumerou
   (`can't set config #1, error -110`). Tentei `uhubctl` pra cortar energia só
   da porta — **esse hub interno não suporta controle de energia por porta**
   (`No compatible devices detected!`), então essa via não existe nesse hardware.

4. Usuário fez **desligamento completo do notebook** (não reboot — power off
   de verdade, ~10s, religar). Isso trouxe o `/dev/ttyACM0` de volta (dispositivo
   USB reaparece corretamente), mas o handshake continua **inconsistente**:
   às vezes não responde nada, uma vez respondeu incompleto (8 de 14 bytes
   esperados). Tela física continua presa no WhatsApp o tempo todo, mesmo depois
   do reboot completo.

**Não sabemos ainda se isso é:**
- (a) o MCU da telinha genuinamente precisando de mais tempo pra inicializar
  depois do cold boot (testamos até ~20s de espera, pode precisar de mais),
- (b) uma sequência de re-sincronização que falta mandar (tipo um Handshake
  duplo, ou drenar lixo do buffer serial antes),
- (c) dano real de ter mandado o `SwitchState(0x20)` sem confirmação — mas isso
  parece improvável já que sobreviveu a um power-cycle completo sem sinal de
  brick real (a tela renderiza, só não responde via serial).

**Próximos passos recomendados:**
1. Tentar handshake várias vezes espaçadas (30s+, 60s+) depois de um boot frio,
   pra descartar (a).
2. Testar tocar a tecla física "Minitela" (toque curto, não segurar) e tentar o
   handshake imediatamente em seguida — pode ser que o MCU só escute a serial
   logo após um evento de UI.
3. Considerar capturar tráfego USB real do app oficial da Positivo rodando no
   Debian/Windows (via `usbmon` no Linux, ou Wireshark+usbpcap no Windows) pra
   confirmar a sequência exata de "voltar ao modo de exibição" em vez de
   adivinhar valores de `SwitchState`. Isso é o jeito certo de validar a hipótese
   do item 1 acima sem arriscar mais comandos não confirmados no hardware real.
4. Não mandar mais comandos `SwitchState`/`write-reg` não documentados direto
   no hardware sem antes achar confirmação (issues do repo SideCar, código do
   app oficial, ou captura de tráfego real).

## Preferências de design da Minitela (do usuário, ainda não implementadas)

- Mostrar: limite semanal, sessão atual, tier "fable", tempo até resetar
  (sessão e/ou semanal).
- As barrinhas de progresso comprimidas iguais ao widget original já estão boas
  — não precisa reinventar o visual.
- Ao tocar a tecla física "Minitela", alternar entre as telas (sessão / semana /
  outras infos), cada uma ocupando a tela toda de forma mais legível (não
  espremer tudo numa tela só).
- Isso provavelmente requer ler `RegCurrentPage` (ou detectar o toque da tecla de
  outra forma, ainda não investigado) e trocar a textura ativa em resposta.
