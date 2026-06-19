#!/usr/bin/env python3
"""Gera HTML com grades possíveis a partir de oferta de turmas (JSON)."""
import argparse
import hashlib
import json
import sys
from datetime import date

DIAS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado"]
DIAS_LABEL = {
    "Segunda": "Seg", "Terca": "Ter", "Quarta": "Qua",
    "Quinta": "Qui", "Sexta": "Sex", "Sabado": "Sáb",
}


def parse_time(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def parse_date(s):
    return date.fromisoformat(s) if s else None


def overlap_time(a, b):
    return (
        parse_time(a["hora_inicio"]) < parse_time(b["hora_fim"])
        and parse_time(b["hora_inicio"]) < parse_time(a["hora_fim"])
    )


def overlap_date(a, b):
    da_i, da_f = parse_date(a["data_inicio"]), parse_date(a["data_fim"])
    db_i, db_f = parse_date(b["data_inicio"]), parse_date(b["data_fim"])
    if not da_i or not db_i:
        return True
    return da_i <= db_f and db_i <= da_f


def conflict(a, b):
    if a["dia"] != b["dia"]:
        return False
    if not overlap_time(a, b):
        return False
    if not overlap_date(a, b):
        return False
    return True


def compatible(a, b):
    if a["cadeira_codigo"] == b["cadeira_codigo"]:
        return False
    return not conflict(a, b)


def bron_kerbosch(R, P, X, neigh):
    if not P and not X:
        yield frozenset(R)
        return
    pool = P | X
    pivot = max(pool, key=lambda v: len(P & neigh[v]))
    for v in list(P - neigh[pivot]):
        yield from bron_kerbosch(R | {v}, P & neigh[v], X & neigh[v], neigh)
        P = P - {v}
        X = X | {v}


def enumerate_max_combos(turmas):
    n = len(turmas)
    neigh = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if compatible(turmas[i], turmas[j]):
                neigh[i].add(j)
                neigh[j].add(i)
    return bron_kerbosch(set(), set(range(n)), set(), neigh)


def score(combo, turmas, current_sem, pending_codes):
    items = [turmas[i] for i in combo]
    cur = sum(1 for t in items if t["semestre"] == current_sem)
    pen = sum(1 for t in items if t["cadeira_codigo"] in pending_codes)
    cred = sum(t["creditos"] for t in items)
    return (cur, pen, cred)


def color_for(code):
    h = int(hashlib.md5(code.encode()).hexdigest(), 16) % 360
    return f"hsl({h}, 65%, 82%)"


def half_label(t):
    di, df = parse_date(t["data_inicio"]), parse_date(t["data_fim"])
    if not di or not df:
        return ""
    if di == df:
        return f"<small>{di.strftime('%d/%m')}</small>"
    duration = (df - di).days
    if duration < 80:
        return "<small>1ª metade</small>" if di.month <= 9 else "<small>2ª metade</small>"
    return ""


CSS = """
  body { font-family: -apple-system, system-ui, sans-serif; margin: 24px; background: #f7f7f8; color: #111; }
  header { margin-bottom: 28px; }
  h1 { margin: 0 0 6px; font-size: 24px; }
  header p { color: #555; margin: 0; }
  .grade { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px; padding: 18px 20px; margin-bottom: 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
  .grade h2 { margin: 0 0 4px; font-size: 18px; }
  .score { color: #666; font-size: 13px; margin-bottom: 12px; }
  .badges { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 16px; }
  .badges li { padding: 4px 10px; border-radius: 14px; font-size: 12px; line-height: 1.4; }
  .badges li.atual { background: #d1f0d6; color: #19501f; }
  .badges li.pendente { background: #fbe6a2; color: #5b410a; }
  .badges li.fora { background: #eeeef0; color: #888; text-decoration: line-through; }
  table.semana { border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 12px; }
  table.semana th, table.semana td { border: 1px solid #e3e3e6; padding: 4px; vertical-align: top; min-height: 28px; }
  table.semana th { background: #f0f0f3; font-weight: 600; text-align: center; }
  table.semana th.hora { width: 90px; font-weight: 500; color: #555; background: #fafafa; }
  .slot { border-radius: 4px; padding: 4px 6px; font-weight: 600; line-height: 1.25; }
  .slot small { font-weight: 400; opacity: 0.75; display: block; font-size: 10.5px; }
  .nenhuma { padding: 18px; background: #fff; border: 1px dashed #aaa; border-radius: 8px; }
  .nenhuma ul { margin: 8px 0 0; padding-left: 22px; }
"""


def render_html(combos_with_score, turmas, candidates, current_sem, pending_codes, out_path):
    bands = sorted({(t["hora_inicio"], t["hora_fim"]) for t in turmas}, key=lambda x: (parse_time(x[0]), parse_time(x[1])))
    color_map = {t["cadeira_codigo"]: color_for(t["cadeira_codigo"]) for t in turmas}
    cand_by_code = {c["cadeira_codigo"]: c for c in candidates}
    cand_codes = set(cand_by_code.keys())

    out = []
    w = out.append
    w("<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>")
    w(f"<title>Grades possíveis — {current_sem}º semestre</title>")
    w(f"<style>{CSS}</style></head><body>")
    w("<header>")
    w(f"<h1>Grades possíveis — {current_sem}º semestre</h1>")
    w(f"<p>{len(combos_with_score)} combinação(ões) maximal(is) a partir de {len(candidates)} cadeira(s) candidata(s).</p>")
    w("</header><main>")

    if not combos_with_score:
        w("<div class='nenhuma'><strong>Nenhuma combinação encontrada.</strong>")
        if candidates:
            w("<p>Cadeiras candidatas:</p><ul>")
            for c in candidates:
                w(f"<li>{c['cadeira_codigo']} {c['cadeira_nome']}</li>")
            w("</ul>")
        w("</div>")

    for idx, (combo, sc) in enumerate(combos_with_score, 1):
        items = [turmas[i] for i in combo]
        items_by_day = {d: [] for d in DIAS}
        for t in items:
            if t["dia"] in items_by_day:
                items_by_day[t["dia"]].append(t)
        included_codes = {t["cadeira_codigo"] for t in items}
        excluded = sorted(cand_codes - included_codes)

        w("<section class='grade'>")
        w(f"<h2>Grade #{idx} — {sc[2]} créditos · {len(items)} cadeira(s)</h2>")
        w(f"<div class='score'>{sc[0]} do semestre atual · {sc[1]} pendente(s) anterior(es)</div>")
        w("<ul class='badges'>")
        for t in sorted(items, key=lambda x: (x["semestre"], x["cadeira_codigo"])):
            cls = "atual" if t["semestre"] == current_sem else "pendente"
            w(f"<li class='{cls}'>{t['cadeira_codigo']} {t['cadeira_nome']} · {t['turma']} · {t['dia']} {t['hora_inicio']}</li>")
        for code in excluded:
            c = cand_by_code[code]
            w(f"<li class='fora'>{code} {c['cadeira_nome']}</li>")
        w("</ul>")

        w("<table class='semana'><thead><tr><th class='hora'>Horário</th>")
        for d in DIAS:
            w(f"<th>{DIAS_LABEL[d]}</th>")
        w("</tr></thead><tbody>")
        for hi, hf in bands:
            has_any = any(
                (t["hora_inicio"], t["hora_fim"]) == (hi, hf)
                for t in items
            )
            if not has_any:
                continue
            w("<tr>")
            w(f"<th class='hora'>{hi}–{hf}</th>")
            for d in DIAS:
                cell_parts = []
                for t in items_by_day[d]:
                    if (t["hora_inicio"], t["hora_fim"]) == (hi, hf):
                        bg = color_map[t["cadeira_codigo"]]
                        note = half_label(t)
                        cell_parts.append(
                            f"<div class='slot' style='background:{bg}'>{t['cadeira_codigo']}"
                            f"<small>{t['cadeira_nome']}</small>"
                            f"<small>{t['turma']}</small>{note}</div>"
                        )
                w(f"<td>{''.join(cell_parts)}</td>")
            w("</tr>")
        w("</tbody></table></section>")

    w("</main></body></html>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--current", required=True, type=int)
    ap.add_argument("--pending", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    pending = {p.strip() for p in args.pending.split(",") if p.strip()}
    candidates_turmas = [
        t for t in all_data
        if t["semestre"] == args.current or t["cadeira_codigo"] in pending
    ]
    by_code = {}
    for t in candidates_turmas:
        by_code.setdefault(t["cadeira_codigo"], t)
    candidates = list(by_code.values())

    if not candidates_turmas:
        render_html([], candidates_turmas, candidates, args.current, pending, args.out)
        print(f"sem turmas candidatas. arquivo salvo em {args.out}", file=sys.stderr)
        return

    combos = list(enumerate_max_combos(candidates_turmas))
    scored = sorted(
        ((c, score(c, candidates_turmas, args.current, pending)) for c in combos),
        key=lambda x: x[1],
        reverse=True,
    )
    render_html(scored, candidates_turmas, candidates, args.current, pending, args.out)
    print(f"{len(scored)} combinações salvas em {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
