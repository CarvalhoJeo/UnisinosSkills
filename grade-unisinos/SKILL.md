---
name: grade-unisinos
description: Use when the user asks to mount a class schedule (grade de horários) for Unisinos based on a PDF of course offerings. Generates an HTML at the PDF folder showing all valid maximal schedule combinations, ranked by current-semester priority and pending past-semester courses, and opens it in the browser. Triggers in pt-br/en — "monta a grade", "grades possíveis", "combinar cadeiras", "grade-unisinos", "horários da Unisinos".
---

# grade-unisinos

Generate an HTML file with all valid maximal schedule combinations the student
can build from a Unisinos course-offering PDF.

## When to use

- User has a `grade-*.pdf` file from Unisinos (system-generated, lists offered
  turmas per semester) and wants help building a schedule.
- User says something like "monta as grades possíveis pra mim", "vamos planejar
  minha matrícula", "grade-unisinos".

## Workflow

Run these steps in order. Use `AskUserQuestion` for the interactive prompts.

### 1. Ask for the PDF path

Always ask the user for the path of the grade PDF, even if one was passed as
argument or candidates exist on disk. To make selection easy, list the most
recent candidates first as suggestions:

```bash
ls -1t ~/Documents/Unisinos/*sem/grade-*.pdf 2>/dev/null | head -5
```

Then ask the user which file to use via `AskUserQuestion`, presenting the
candidates as options. If none exist, ask the user for the path via plain text.
Never auto-pick a file without confirmation.

### 2. Read and parse the PDF into JSON

Use the `Read` tool on the PDF. The file text follows this structure:

```
1º SEMESTRE
061921 - Cálculo Diferencial
  GR10006-00519   4   Segunda   19:30 às 22:23   3/8/2026 a 12/12/2026
  GR10006-00520   4   Terca     19:30 às 22:23   3/8/2026 a 12/12/2026
  ...
2º SEMESTRE
...
```

Build a JSON array with the schema below and write it to `/tmp/grade-parsed.json`:

```json
[
  {
    "semestre": 1,
    "cadeira_codigo": "061921",
    "cadeira_nome": "Cálculo Diferencial",
    "turma": "GR10006-00519",
    "creditos": 4,
    "dia": "Segunda",
    "hora_inicio": "19:30",
    "hora_fim": "22:23",
    "data_inicio": "2026-08-03",
    "data_fim": "2026-12-12"
  }
]
```

Parsing rules:

- Section headers like `4º SEMESTRE` set the current `semestre` for the
  following courses, until the next header. Map `1º..10º` to `1..10`. Treat
  the `OPTATIVAS` section as `semestre: null` (it will not be a candidate).
- Course header lines: `<codigo> - <nome>`. Code is 6 digits.
- Turma lines: `<turma_id>  <creditos>  <dia>  <hora_inicio> às <hora_fim>  <data_inicio> a <data_fim>`.
- Skip any course block that contains only `(Sem oferta de turma para este semestre)`.
- Skip turma rows where `dia` is `--` or empty (e.g., Estágio Supervisionado, Projeto Aplicado).
- Convert dates `d/m/yyyy` → ISO `yyyy-mm-dd`.
- Single-date entries (`29/8/2026`): use the date for both `data_inicio` and `data_fim`.
- Ignore `Info:` lines (they are descriptive metadata).

### 3. Ask the current semester

```
question: "Qual é o seu semestre atual?"
options: 1º, 2º, 3º, 4º (and so on, but AskUserQuestion limits to 4 options
per call). If the user already mentioned it in the conversation, skip this.
```

If more than 4 options are needed (unlikely — student knows their semester),
ask via plain text instead.

### 4. Ask which past-semester courses are pending

From the JSON, collect distinct courses where `semestre < <current>` that have
at least one offered turma. List them in a plain text message and ask the user
to reply with the codes (comma-separated) of the ones they have NOT taken yet
and want to consider. Example:

```
Cadeiras de semestres anteriores que ainda têm oferta neste semestre:

1º — 061921 Cálculo Diferencial
1º — 061929 Desafios da Área de Engenharia
2º — 061926 Álgebra Linear e Geometria Analítica
...

Quais você ainda não fez e quer incluir? Cole os códigos separados por
vírgula (ex.: 061921,061926). Mande "nenhuma" se for só o semestre atual.
```

Parse the reply into a comma-separated list of course codes.

### 5. Run the generator

Determine the output path: same directory as the PDF, filename `grades.html`.

```bash
python3 ~/.claude/skills/grade-unisinos/scripts/generate.py \
  --data /tmp/grade-parsed.json \
  --current <N> \
  --pending <codigos_csv_ou_vazio> \
  --out "<pdf_dir>/grades.html"
```

### 6. Open the HTML

```bash
open "<pdf_dir>/grades.html"
```

### 7. Report

In one sentence: how many combinations were generated and where the file is.

## Notes

- The generator does the combinatorics (Bron-Kerbosch on the compatibility
  graph). Do not enumerate combinations yourself.
- "Maximal" means: no additional turma can be added without conflict. Strict
  subsets are not shown.
- Half-semester courses (e.g., 03/08 → 10/10 vs 12/10 → 12/12) do NOT conflict
  even at the same day/time — the script handles this via date overlap.
- If the PDF parsing seems off, validate against the user: show a few parsed
  entries and ask for a sanity check before running the generator.
