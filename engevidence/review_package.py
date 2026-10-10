"""Review package: matrix + gaps + signoff checklist → JSON + LaTeX → PDF."""
import json
import subprocess
import sys

sys.path.insert(0, "src")
from trace import gaps, init_db, matrix

db = init_db()
rows = matrix(db)
g = gaps(rows)
pkg = {
    "subject": "FICTIONAL overhead-bin latch retrofit (synthetic review package — "
               "not certification, not EASA evidence)",
    "matrix": rows,
    "gaps": g,
    "signoff": [
        {"item": "all requirements have tests", "ready": not g["orphans"]},
        {"item": "no revision conflicts", "ready": not g["conflicts"]},
        {"item": "all passes evidenced", "ready": not g["incomplete_evidence"]},
        {"item": "no pending tests", "ready": not g["pending"]},
        {"item": "no failed tests", "ready": not g["failed"]},
    ],
}
json.dump(pkg, open("results/review.json", "w"), indent=2)

def row(r):
    tests = ", ".join(f"{t['id']}({t['rev']}/{t['result']})" for t in r["tests"]) or "---"
    flags = ",".join([f for f, on in
                      [("ORPHAN", r["orphan"]), ("CONFLICT", r["conflict"]),
                       ("NO-EVIDENCE", r["incomplete_evidence"])] if on]) or "ok"
    return f"{r['req']} & {r['title']} & {tests} & {flags} \\\\"

body = "\n".join(row(r) for r in rows)
sign = "\n".join(f"\\item[$\\square$] {s['item']}: {'READY' if s['ready'] else 'NOT READY'}"
                 for s in pkg["signoff"])
open("results/review.tex", "w").write(r"""\documentclass[a4paper,11pt]{article}
\usepackage[T1]{fontenc}\usepackage{lmodern}\usepackage[margin=0.7in]{geometry}
\usepackage{longtable,amssymb}
\begin{document}
\section*{Synthetic review package (fictional mod --- NOT certification)}
\begin{longtable}{l l l l}
Req & Title & Tests(rev/result) & Flags\\\hline
""" + body + r"""
\end{longtable}
\section*{Signoff checklist}
\begin{itemize}
""" + sign + r"""
\end{itemize}
\end{document}""")
p = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                    "-output-directory=results", "results/review.tex"],
                   capture_output=True, text=True)
print("pdflatex exit:", p.returncode)
if p.returncode != 0:
    print(p.stdout[-1500:])
    sys.exit(1)
print(f"gaps: orphans={g['orphans']} conflicts={list(g['conflicts'])} "
      f"no-evidence={g['incomplete_evidence']} pending={g['pending']} failed={g['failed']}")
