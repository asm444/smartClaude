# Fork local do SideCar — 3 bugs corrigidos + 1 comando novo

O [SideCar](https://github.com/FreyreCorona/SideCar) (MIT, Go) é um projeto de
terceiros, não-oficial, que fez engenharia reversa do protocolo serial da Minitela.
Usamos ele para o **upload de textura** — a única capacidade que o nosso
`minitela.py` não implementa.

O binário oficial da release v0.1.26 tinha bugs que impediam o uso por linha de
comando. Corrigimos localmente. As correções vivem em `patches/sidecar/`, aplicáveis
sobre o upstream fixado em `d356c2b`. Ver `scripts/bootstrap-vendor.md` para
reconstruir o binário.

Não vendorizamos o código do SideCar: os patches contêm apenas as nossas
modificações (104 inserções, 25 remoções em 4 arquivos).

## Bug 1 — dispatch de `-mode` quebrado (`main.go`)

`patches/sidecar/0001-fix-mode-dispatch.patch`

O código original chamava `runDaemonMode(os.Args, ...)` / `runCLI(os.Args, ...)`
passando a lista **crua e completa** de argumentos — incluindo o par `-mode X` já
consumido — para o `FlagSet` do daemon/cli, que não conhece a flag `-mode`.

Resultado: `flag provided but not defined: -mode`, **sempre**. Tanto `-mode daemon`
quanto `-mode cli` eram inutilizáveis no binário oficial.

Correção: uma função `splitMode()` extrai o par `-mode X` manualmente antes do
dispatch e repassa só o restante dos argumentos ao sub-parser.

## Bug 2 — validação de CRC incorreta (`core/command.go`)

`patches/sidecar/0002-fix-crc-zerado.patch`

Confirmado empiricamente, enviando frames brutos por Python com `os.open`/`os.write`
direto no `/dev/ttyACM0` (bypass do binário):

> O dispositivo real **ativa** o bit "CRC habilitado" no `controlFlag` das respostas,
> mas **sempre manda o campo de CRC como `0x0000`** — o firmware não calcula CRC das
> próprias respostas.

O código original comparava esse `0x0000` contra um CRC calculado de verdade, dava
mismatch, e `ReadResponse` entrava num laço de descarte silencioso até estourar o
timeout. Era por isso que `SetRegister` e o ajuste de brilho **pareciam travar para
sempre** — mesmo com o dispositivo respondendo em ~200ms.

Correção: em `ParseFrame`, se o campo de CRC vier zerado, a resposta é aceita sem
tentativa de validação.

## Bug 3 — ACK de escrita tem formato diferente do de leitura (`core/register.go`)

`patches/sidecar/0003-fix-ack-escrita.patch`

Também confirmado por bytes brutos:

- Resposta de **leitura** de registrador: layout assumido pelo código
  (header + regID(2) + valor(4) = 6 bytes por registro), `functionCode = 0`.
- Resposta de **escrita**: layout mais curto e diferente, `functionCode = 2`.

Esse segundo formato não está documentado em lugar nenhum — nem o autor original o
conhecia (o comentário dele diz que o protocolo foi feito "by trial and error").

Correção: `parseNumRegResponse` só valida o formato estrito quando
`functionCode == 0` (leitura). Qualquer outro caso é tratado como confirmação de
sucesso, sem tentar decodificar valores. A escrita em si sempre funcionou — só o eco
da resposta é que tinha formato desconhecido.

## Comando novo — `show-image` (`cli.go`)

`patches/sidecar/0004-add-show-image.patch`

Adiciona `-cmd show-image -file <PNG 240x240>`: decodifica o PNG, converte para
RGB565 little-endian (`loadRGB565PNG()`), monta o `.acf` via `core.BuildACF` (já
existente no projeto) e faz upload como `FileTypeTexture`.

Nota histórica: este comando **funciona** (upload completa 0→100%), mas subir uma
textura solta **não muda o que a tela exibe** — no AHMI o vínculo textura→página é
fixado na compilação do projeto. É por isso que o caminho real do nosso visual
próprio passa por recompilar o projeto AHMI, e não por este comando.
