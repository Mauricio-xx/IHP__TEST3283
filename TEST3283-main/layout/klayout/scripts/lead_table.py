"""Per-tile lead table, measured on the nofill GDS: the metal between the de-embedding reference plane
(end of the TopMetal1 stubs, |x| = 75 um) and the device terminals, which stays in every measurement.

  klayout -zz -r scripts/klayout_run.py -rd script=scripts/lead_table.py -rd gds=<chip_nofill.gds> \
      -rd slots=slots.csv -rd build=<..._build.json> -rd itf=<sg13cmos5l_typ.itf> -rd out=leads.csv

PLUS lead: from the left landing patch to the cell's left pad on the PLUS layer. MINUS lead: the mirror on
the right for feed=double. For feed=same the right lead lands on the right end of ONE MINUS finger row
(build json minus_tap); the MINUS rows only join at the stacked left pad, so the MINUS current also runs the
full length of that row. Its resistance (tap_row_R_ohm) is in series with the device and not in the PDK model.

R values are DC, typical RPSQ from the PDK ITF, plain squares count: lead R excludes the landing patch and
via stacks; tap row R treats the row on each metal as parallel strips and ignores the tooth vias.
"""
import csv
import json
import re
import pya

GDS, SLOTS, BUILD, ITF, OUT = gds, slots, build, itf, out  # noqa: F821  (-rd)
X0, Y0, DX, DY = 244.9, 246.43, 425.0, 418.0
REF_X = 75.0          # reference plane after open-short
PATCH_X = 77.1        # outer edge of the Metal4 landing patch
BAND = 5.0            # leads are clamped to |y| <= 5 um around the tile centre line
MET = {1: (8, 0), 2: (10, 0), 3: (30, 0), 4: (50, 0)}

rpsq = {}
for line in open(ITF):
    m = re.match(r"\s*CONDUCTOR\s+Metal(\d)\s*\{.*RPSQ=([\d.]+)", line)
    if m:
        rpsq[int(m.group(1))] = float(m.group(2))

ly = pya.Layout()
ly.read(GDS)
top = ly.top_cells()[0]
dbu = ly.dbu


def region(metal, box):
    b = pya.DBox(*box).to_itype(dbu)
    r = pya.Region(pya.RecursiveShapeIterator(ly, top, ly.find_layer(*MET[metal]), b)) & pya.Region(b)
    return r.merged()


def lead(metal, x_out, x_in, cx, cy):
    """Lead strip on `metal` between |x| = x_out (patch) and x_in (device edge), tile-relative."""
    lo, hi = sorted((x_out, x_in))
    r = region(metal, (cx + lo, cy - BAND, cx + hi, cy + BAND))
    if r.is_empty():
        return None
    bb = r.bbox().to_dtype(dbu)
    near = min(abs(bb.left - cx), abs(bb.right - cx))     # device end of the strip
    length, width = max(REF_X - near, 0.0), bb.height()
    return dict(len=round(length, 3), w=round(width, 3), R=round(rpsq[metal] * length / width, 4))


bj = json.load(open(BUILD))
rep = {d["tile"]: d for d in bj["report"]}
rows = []
for s in csv.DictReader(open(SLOTS)):
    d = rep[s["tile"]]
    cx, cy = X0 + DX * int(s["col"]), Y0 + DY * int(s["row"])
    x0, y0, x1, y1 = d["array_bbox"]
    pl, ml = d["plus_layer"], d["minus_layer"]
    p = lead(pl, -PATCH_X, x0, cx, cy)
    m = lead(ml, PATCH_X, x1, cx, cy)
    row = dict(tile=s["tile"], feed=s["feed"], stack=f"M{s['mmin']}-M{s['mmax']}",
               plus_layer=f"Metal{pl}", plus_lead_len_um=p["len"], plus_lead_w_um=p["w"], plus_lead_R_ohm=p["R"],
               plus_via_to_M4=pl < 4,
               minus_layer=f"Metal{ml}", minus_lead_len_um=m["len"], minus_lead_w_um=m["w"], minus_lead_R_ohm=m["R"],
               minus_via_to_M4=ml < 4, minus_tap=d["minus_tap"],
               tap_row_len_um="", tap_row_w_um="", tap_row_metals="", tap_row_R_ohm="")
    if s["feed"] == "same":
        ty = float(d["minus_tap"].split("=")[1])
        g = 0.0
        metals, w = [], None
        length = 0.0
        for k in range(int(s["mmin"]), int(s["mmax"]) + 1):
            # The bar runs on every metal of the stack, tied by the tooth vias; only mmax-1 reaches the
            # left MINUS pad. Per metal: the continuous run on the row centre line, then the widest band
            # around it that is solid metal over that run (the bar; the comb teeth carry no row current).
            line = region(k, (cx + x0, cy + ty - 0.005, cx + x1, cy + ty + 0.005))
            runs = [q.bbox().to_dtype(dbu) for q in line.each()]
            if not runs:
                continue
            run = max(runs, key=lambda b: b.width())
            bar = 0.0
            for i in range(1, 61):
                a = 0.005 * i
                band = (run.left, cy + ty - a, run.right, cy + ty + a)
                full = pya.Region(pya.DBox(*band).to_itype(dbu)).area()
                if region(k, band).area() < 0.999 * full:
                    break
                bar = 2 * a
            if bar == 0.0:
                continue
            w = round(bar, 3)
            g += 1.0 / (rpsq[k] * run.width() / bar)
            length = max(length, run.width())
            metals.append(f"M{k}")
        row.update(tap_row_len_um=round(length, 3), tap_row_w_um=w, tap_row_metals="+".join(metals),
                   tap_row_R_ohm=round(1.0 / g, 3) if g else "")
    rows.append(row)
    print(f"{s['tile']:4s} {s['feed']:6s} plus {p['len']:6.2f}x{p['w']:5.2f}  minus {m['len']:6.2f}x{m['w']:5.2f}"
          + (f"  tap row {row['tap_row_metals']} {row['tap_row_R_ohm']} ohm" if s["feed"] == "same" else ""))
with open(OUT, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0]))
    wr.writeheader()
    wr.writerows(rows)
print("wrote", OUT, len(rows), "tiles")
