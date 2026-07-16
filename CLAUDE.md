# telinha — Minitela do Positivo Vision R15M

Display IPS 1,54", 240×240, embutido no chassi do notebook. Fala serial por
`/dev/ttyACM0` (CDC-ACM, `0324:0324`). O projeto exibe o mascote Clawd conforme
o modelo Claude em uso e o consumo de tokens. Visão geral: `README.md`.

## Guardas — quebrar estas trava o hardware

- **NUNCA envie `SwitchState` com `0x20`.** O único valor válido é `0x10` (entrar
  em download). `0x20` é um estado *reportado*, não argumento — mandá-lo já deixou
  o MCU mudo por dias.
- **MCU mudo recupera só com `sudo usbreset 0324:0324`.** Nenhum comando serial
  resolve. Rebind USB por software piora (a porta não re-enumera).
- **Upload ocupa o serial por ~6s.** Comando antes disso *parece* trave e não é.
  Dê o respiro antes de concluir que travou.
- **Não rode dois processos no serial ao mesmo tempo.** Pare o daemon antes de
  subir um `.acf`: `sudo systemctl stop minitela-daemon.service`.
- **Fundo claro é obrigatório** no que for compilado: o `AHMISimGenDemo` corrompe
  cores quase-pretas (viram branco lavado na tela).

## Limites provados — não reabrir

- **Só existem 3 páginas animadas** (5, 6, 7). Cinco bichinhos animados com troca
  instantânea é **impossível** sem re-flash do firmware. Todas as rotas foram
  refutadas com prova: página nova no `data.json`, forjar o bloco AHMI, registrador
  seletor de frame-set, update de firmware pelo app. Ver `docs/historico/`.
- **A page-def da animação vive no firmware**, não no `.acf`. O `.acf` só entrega
  pixels. É por isso que trocar o gif de origem por outro com o mesmo número de
  frames funciona.
- **Página nova (7/8/9) renderiza em branco** — o firmware não tem a definição.
  Para visual próprio, substitua os fundos das páginas 1/2/3 que já renderizam.
- **O slot `texture_gif` (0x08500000) é código morto.** Rejeita com `0x3B`. Tudo
  sobe como `texture` (0x08100000).

## Fatos que enganam

| | |
|---|---|
| Tecla física | **KEY_F16 (186)**, não o 148 do app oficial. O device é achado por bitmask — hoje é o `event15`; o `event3` do fallback **está errado** e a numeração muda entre boots |
| Frames 21/30/44 | é o que a **page-def do firmware** exige por página (5/6/7). **Não** é o nº de frames do gif de fábrica — esses têm 1 frame |
| CRC do protocolo | o algoritmo existe (CRC-16/IBM refletido), mas **ninguém o usa**: nós mandamos zerado e o firmware responde zerado |
| Modelo em uso | vem de `~/.claude/settings.json` campo `model`. **Nunca** do transcript `.jsonl` — ele só registra quando o assistant responde |
| Home no daemon | roda como root, então `~` seria `/root`. O caminho é fixo, com `MINITELA_HOME` para sobrescrever |
| Escalas de % | cor da tela usa **50/80**; alerta do daemon usa **70/90**. São escalas distintas, de propósito |
| Fonte | não há DejaVu nesta máquina; `carregar_fonte` resolve via `fc-match`. Cair no `load_default()` ignora o tamanho pedido |
| Overlay do Clawd | sprite de **64×64**. Ampliar além de 128 (2×) borra a pixel art e cobre o mascote — foi bug real |

## Estrutura

O pacote `src/minitela/` (core, dados, daemon, entrada, render, build) tem testes:
`pytest` roda sem hardware; `pytest -m hardware` exige a Minitela.

**O daemon que roda em produção ainda é o legado da raiz** (`minitela_clawd.py`,
importando `minitela.py`), via systemd com `WorkingDirectory`. A migração para o
pacote está planejada em `plans/` e **não foi executada**. Os dois coexistem: o
`minitela.py` da raiz sombreia o pacote quando se roda do diretório do projeto —
por isso o pytest usa `--import-mode=importlib`.

Material de terceiros (app da Positivo, compilador AHMI, SideCar) não é
versionado: `scripts/bootstrap-vendor.md`.

## Onde olhar

- `README.md` — o que é, como instalar, como usar
- `scripts/bootstrap-vendor.md` — obter o material de terceiros
- `docs/historico/fork-sidecar-bugs.md` — os 3 bugs do SideCar que corrigimos
- `docs/historico/2026-07-notas-de-sessao.md` — como o projeto foi descoberto.
  **Contém conclusões refutadas**; tem banner no topo listando quais
- `plans/` — o plano de reorganização (não versionado)
