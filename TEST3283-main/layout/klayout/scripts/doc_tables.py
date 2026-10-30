"""Markdown tables for README.md and doc/Datasheet.md, straight from slots.csv.

  python3 scripts/doc_tables.py map|groups|datasheet   print one table
  python3 scripts/doc_tables.py render                 write README.md and doc/Datasheet.md from doc_templates/
"""
import contextlib
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slots = list(csv.DictReader(open(os.path.join(HERE, "slots.csv"))))
tiles = json.load(open(os.path.join(HERE, "tiles.json")))
STACK = {"14": "M1-M4", "34": "M3-M4", "13": "M1-M3", "24": "M2-M4"}
CAL = {"OP": "OP (open)", "SHT": "SHT (short)", "TH": "TH (not usable)", "A33": "LS (lead short)"}


def stack(s):
    return STACK[s["mmin"] + s["mmax"]]


def num(v):
    return f"{float(v):g}"


def chip_map():
    grid = {}
    for t in tiles:
        grid[(t["row"], t["col"])] = CAL.get(t["role"], "")
    for s in slots:
        grid[(int(s["row"]), int(s["col"]))] = s["tile"]
    cols = range(8)
    print("| row \\ col | " + " | ".join(str(c) for c in cols) + " |")
    print("| --- |" + " --- |" * len(cols))
    for r in reversed(range(6)):
        print(f"| {r} | " + " | ".join(grid.get((r, c), "") for c in cols) + " |")


def groups():
    print("| Tile | l (um) | w (um) | Stack | Feed | Copies | C model, total (fF) |")
    print("| --- | ---: | ---: | --- | --- | ---: | ---: |")
    for s in slots:
        print(f"| {s['tile']} | {num(s['l_um'])} | {num(s['w_um'])} | {stack(s)} | {s['feed']} | {s['mult']} "
              f"| {float(s['C_total_fF']):.1f} |")


def datasheet():
    print("| Tile | Row, col | TEST9203 position | momf same size | l (um) | w (um) | Stack | Feed | Copies "
          "| C model per cell (fF) | C model total (fF) | Purpose |")
    print("| --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- |")
    for s in slots:
        print(f"| {s['tile']} | {s['row']}, {s['col']} | {s['momf_tile']} | {s['momf_same_size']} "
              f"| {num(s['l_um'])} | {num(s['w_um'])} "
              f"| {stack(s)} | {s['feed']} | {s['mult']} | {float(s['C_model_cell_fF']):.2f} "
              f"| {float(s['C_total_fF']):.2f} | {' '.join(s['rationale'].split())} |")


def table(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue().rstrip("\n")


def render():
    root = os.path.join(HERE, "..", "..", "..")
    keys = {"{{MAP}}": table(chip_map), "{{DEVICES}}": table(groups), "{{DATASHEET}}": table(datasheet)}
    for tpl, out in (("README.md.in", "README.md"), ("Datasheet.md.in", os.path.join("doc", "Datasheet.md"))):
        s = open(os.path.join(HERE, "doc_templates", tpl)).read()
        for k, v in keys.items():
            s = s.replace(k, v)
        assert "{{" not in s, tpl
        open(os.path.join(root, out), "w").write(s)
        print("wrote", os.path.normpath(os.path.join(root, out)))


{"map": chip_map, "groups": groups, "datasheet": datasheet, "render": render}[sys.argv[1]]()
