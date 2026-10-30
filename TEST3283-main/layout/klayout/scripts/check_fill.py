"""Fill check: no filler shape within GAP um of any device or calibration core.

  klayout -zz -r scripts/klayout_run.py -rd script=scripts/check_fill.py -rd fill=<chip.gds> \
      -rd nofill=<chip_nofill.gds> -rd tiles=tiles.json -rd build=<..._build.json> -rd out=<report.json>

Fill = every shape of the filled GDS that is not in the nofill GDS, on any layer. The core of a device
tile is its array bbox; the core of OP, SHT and LS is the common keepout minus its margin (the largest
device bbox). Also reports the smallest gap from each core to the nearest fill shape.
"""
import json
import pya

FILL, NOFILL, TILES, BUILD, OUT = fill, nofill, tiles, build, out  # noqa: F821  (-rd)
X0, Y0, DX, DY = 244.9, 246.43, 425.0, 418.0
GAP = 2.0          # required clearance, um
WINDOW = 20.0      # search window around the core for the smallest gap, um
NOFILL_MARGIN = 5.0
CAL = ("OP", "SHT", "A33")

lf, ln = pya.Layout(), pya.Layout()
lf.read(FILL)
ln.read(NOFILL)
tf, tn = lf.top_cells()[0], ln.top_cells()[0]
dbu = lf.dbu
layers = [(i.layer, i.datatype) for i in lf.layer_infos()]


def shapes(ly, top, ld, box):
    li = ly.find_layer(*ld)
    if li is None:
        return pya.Region()
    r = pya.Region(pya.RecursiveShapeIterator(ly, top, li, box))
    return r & pya.Region(box)


def box_gap(a, b):
    dx = max(b.left - a.right, a.left - b.right, 0)
    dy = max(b.bottom - a.top, a.bottom - b.top, 0)
    return (dx * dx + dy * dy) ** 0.5


bj = json.load(open(BUILD))
dev = {d["tile"]: d["array_bbox"] for d in bj["report"]}
kx, ky = bj["cal_keepout_halfsize"]
cal_core = [-(kx - NOFILL_MARGIN), -(ky - NOFILL_MARGIN), kx - NOFILL_MARGIN, ky - NOFILL_MARGIN]
rows, fails = [], 0
for t in json.load(open(TILES)):
    name = t["role"] if t["role"] in CAL else (t.get("A") and f"B{t['A']}")
    core = cal_core if t["role"] in CAL else dev.get(name)
    if core is None:
        continue
    cx, cy = X0 + DX * t["col"], Y0 + DY * t["row"]
    cb = pya.DBox(cx + core[0], cy + core[1], cx + core[2], cy + core[3]).to_itype(dbu)
    win = cb.enlarged(int(WINDOW / dbu), int(WINDOW / dbu))
    near, gap_min, layers_hit = 0, None, set()
    for ld in layers:
        added = shapes(lf, tf, ld, win) - shapes(ln, tn, ld, win)
        for p in added.each():
            g = box_gap(cb, p.bbox()) * dbu
            gap_min = g if gap_min is None else min(gap_min, g)
            if g < GAP:
                near += 1
                layers_hit.add(f"{ld[0]}/{ld[1]}")
    ok = near == 0
    fails += not ok
    label = "LS" if t["role"] == "A33" else name
    rows.append(dict(tile=label, row=t["row"], col=t["col"], core_um=core, fill_within_gap=near,
                     layers=sorted(layers_hit), min_gap_um=None if gap_min is None else round(gap_min, 3), ok=ok))
    print(f"{label:4s} r{t['row']}c{t['col']}  fill<{GAP}um: {near:3d}  min gap: "
          f"{'none in window' if gap_min is None else f'{gap_min:.2f} um'}  {'ok' if ok else 'FAIL'}")
json.dump(dict(gap_um=GAP, window_um=WINDOW, tiles=rows), open(OUT, "w"), indent=1)
print(f"CHECKED CORES: {len(rows)}, FAILING: {fails}")
if fails:
    raise SystemExit(1)
