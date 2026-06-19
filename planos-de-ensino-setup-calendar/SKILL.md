---
name: planos-de-ensino-setup-calendar
description: Use when the user wants to extract important dates (Grau A/B/C exams, lab activities, project deliveries) from one or more Unisinos "Plano de Ensino" PDFs and create events on Google Calendar. Triggers in pt-br/en — "marca os planos de ensino", "datas das provas no calendar", "extrai do plano de ensino", "planos-de-ensino-setup-calendar".
---

# planos-de-ensino-setup-calendar

Parse Unisinos "Plano de Ensino" PDFs and create Google Calendar events for
the key graded milestones: Grau A/B/C exams, Atividade Integradora (lab and
final delivery), and any other graded delivery (proposta de projeto, roteiros
de estudo, seminários).

## When to use

- User has a folder with `Plano de ensino *.pdf` files (one per discipline)
  and wants the important dates in their Google Calendar.
- User says something like "marca as provas dos meus planos", "joga as datas
  no calendar", "planos-ensino-unisinos".

## Workflow

### 0. Verify prerequisites

A Google Calendar tool must be available before doing anything else.

```
ToolSearch query: "google calendar create_event"
```

If a tool matching `mcp__*Google_Calendar*create_event` (or similar
`*calendar*create*`) is available, continue. If not, stop and instruct the
user:

> Você não tem uma integração com o Google Calendar disponível. Opções:
>
> **A. Conector do Claude.ai (mais simples):**
> Acesse https://claude.ai/settings/connectors → conecte "Google Calendar".
> Depois reinicie o Claude Code (`/exit` e reabra) e rode o comando de novo.
>
> **B. MCP local:**
> `claude mcp add google-calendar -- npx -y @cocal/google-calendar-mcp`
> (requer credenciais OAuth — siga a doc do servidor escolhido).
>
> Qual caminho prefere?

Wait for the user. Re-check tool availability before continuing.

### 1. Ask for the folder

Ask the user for the absolute path of the folder containing the PDFs. To
help, list recent candidates first:

```bash
ls -1td ~/Documents/Unisinos/*sem/ 2>/dev/null | head -5
```

Use `AskUserQuestion` with these directories as options (plus an implicit
"Other" for custom paths). Never auto-pick.

### 2. List the PDFs

```bash
ls -1 "<folder>"/Plano*.pdf "<folder>"/plano*.pdf 2>/dev/null
```

Show the list and confirm with the user which PDFs to process. If none are
found, ask the user to point you to the right folder.

### 3. Extract events from each PDF

For each PDF, use `Read` to load it, then extract a JSON record. **Do not
write a parser script** — formats vary between professors, so your reasoning
handles variations better than regex.

Target schema per PDF:

```json
{
  "codigo": "061983",
  "nome": "Física: Ondas e Eletromagnetismo",
  "periodo": "2026/1",
  "dia_semana": "Quarta",
  "hora_inicio": "19:30",
  "hora_fim": "22:23",
  "sala": "C06-102",
  "professor": "Cândida Cristina Klein",
  "eventos": [
    {"tipo": "LAB",          "titulo": "Atividade Integradora GA (Laboratório)", "data": "2026-04-01", "peso": "2,0 pontos", "descricao": "..."},
    {"tipo": "PROVA_GA",     "titulo": "Prova Grau A (AAI)",                     "data": "2026-04-22", "peso": "6,0 pontos"},
    {"tipo": "ENTREGA",      "titulo": "Entrega proposta de projeto AI GB",      "data": "2026-04-29"},
    {"tipo": "PROVA_GB",     "titulo": "Prova Grau B (AAI)",                     "data": "2026-05-13", "peso": "2,0 pontos"},
    {"tipo": "APRESENTACAO", "titulo": "Atividade Integradora GB (apresentação)","data": "2026-06-17", "peso": "3,0 pontos"},
    {"tipo": "PROVA_GC",     "titulo": "Prova Grau C",                           "data": "2026-07-01", "peso": "6,0 pontos"}
  ]
}
```

**Extraction rules:**

- **Identify the course:** look for a header with `ATIVIDADE ACADÊMICA <codigo>
  – <nome>` or similar. The code is 6 digits.
- **Class time:** look for a line like `Aulas: <dia>, das <HHhMMmin> às
  <HHhMMmin>, na sala <sala>`. Convert to 24h `HH:MM`. This is the default
  event time.
- **Period → year:** the `Período: AAAA/N` line gives the year. `N=1` runs
  Feb–Jul; `N=2` runs Aug–Dec. Use it to resolve month abbreviations
  (`fev=02, mar=03, abr=04, mai=05, jun=06, jul=07, ago=08, set=09, out=10,
  nov=11, dez=12, jan=01`). Single-digit months → zero-pad.
- **Cronograma / Schedule:** find the weekly schedule table. Each row has a
  date (e.g., `22/abr`) and content describing what happens that week.
- **What to include (graded events only):**
  - Provas / AAI / Atividade Avaliativa Individual / Grau A / B / C / GA / GB
    / GC → `PROVA_GA`, `PROVA_GB`, `PROVA_GC`
  - Atividade Integradora — when it's lab/experimental → `LAB`
  - Atividade Integradora — when it's the protótipo/apresentação final → `APRESENTACAO`
  - Roteiros de estudo, seminários em grupos, entrega de proposta, entrega
    de relatório, qualquer entrega com `(X pontos)` → `ENTREGA`
- **What to skip:**
  - Aulas normais (apenas conteúdo + leitura recomendada, sem `(X pontos)`)
  - Tarefas semanais genéricas sem data específica fora da aula
  - Linhas só com leitura recomendada (`HALLIDAY. ...`)
- **Heuristic for "graded":** if the row mentions `(X,Y pontos)`, `(X ponto)`,
  `Grau A/B/C`, `AAI`, `Atividade Integradora`, `Entrega`, `Apresentação`,
  `Seminário`, `Roteiro de Estudo` — include it.
- **If date is missing/ambiguous:** flag in the preview as `data: "?"` and
  surface to the user, do not invent.

### 4. Show the preview

Print a consolidated table (one row per event) grouped by discipline, e.g.:

```
[061983] Física: Ondas e Eletromagnetismo — Quarta 19:30–22:23
  01/04/2026  LAB           Atividade Integradora GA (Lab)
  22/04/2026  PROVA_GA      Prova Grau A (AAI) — 6,0 pontos
  29/04/2026  ENTREGA       Proposta de projeto AI GB
  13/05/2026  PROVA_GB      Prova Grau B (AAI) — 2,0 pontos
  17/06/2026  APRESENTACAO  Atividade Integradora GB — 3,0 pontos
  01/07/2026  PROVA_GC      Prova Grau C — 6,0 pontos

[061944] Organização e Arquitetura de Computadores — Terça 19:30–22:23
  ...

Total: N eventos em M matérias.
```

Then ask via `AskUserQuestion`: "Criar todos esses eventos no Google
Calendar?" with options `Sim, criar tudo` / `Quero remover alguns` /
`Cancelar`. If the user picks remove, ask which indices to drop.

### 5. Create the Calendar events

For each event, call the Calendar create_event tool (e.g.,
`mcp__claude_ai_Google_Calendar__create_event`) with:

- **calendar:** primary
- **summary:** `[<codigo>] <nome_curto> — <titulo_evento>`
  (truncate `nome` to ~30 chars if very long)
- **start / end:** the event date + the discipline's `hora_inicio` /
  `hora_fim` (timezone `America/Sao_Paulo`).
- **description:** `Tipo: <TIPO>\nPeso: <peso>\nSala: <sala>\nProfessor:
  <professor>\n\n<descricao>`
- **reminders:** two custom reminders — `30 minutes before` (popup) and
  `1 week before` (popup). If the MCP supports only a single reminder
  override, fall back to the closer one (30 min) and mention it in the
  report.

After each create, capture the returned event ID/URL for the final report.

If a create call fails, report the failure but continue with the rest.

### 6. Report

One short message:

```
✅ Criados X eventos no Google Calendar (primária) em N matérias.
Falhas: Y (listadas acima, se houver).
```

## Notes

- **Why no script?** Extraction is judgment-heavy (different professors use
  different wording: "AAI", "Prova", "Atividade Avaliativa", red-highlighted
  cells, footnotes). Your reading handles it; regex would fragment.
- **Year inference safety:** verify each extracted date falls inside the
  period window (1st semester: Feb 1 – Jul 31; 2nd: Aug 1 – Dec 31). If
  outside, flag in preview rather than committing silently.
- **Idempotency:** this skill does not deduplicate. If run twice, you get
  duplicate events. Warn the user in the preview if it's clear they've
  already imported (e.g., "se você já rodou antes, vai duplicar — confirme").
- **Multiple PDFs in parallel:** for a folder with 5+ PDFs, you may dispatch
  one Explore-style subagent per PDF to extract in parallel (returns JSON),
  then consolidate. Optional optimization.
- **PDF text issues:** if a PDF is scanned (image-only), `Read` will return
  garbled text. Stop and tell the user that PDF needs OCR.
