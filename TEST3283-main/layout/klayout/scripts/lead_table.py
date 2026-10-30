"""Per-tile lead table, measured on the nofill GDS: the metal between the de-embedding reference plane
(end of the TopMetal1 stubs, |x| = 75 um) and the device terminals, which stays in every measurement.

  klayout -zz -r scripts/klayout_run.py -rd script=scripts/lead_table.py -rd gds=<chip_nofill.gds> \
      -rd slots=slots.csv -rd build=<..._build.json> -rd itf=<sg13cmos5l_typ.itf> -rd out=leads.csv

feed=double: PLUS lead from the left landing patch straight to the cell's left pad, MINUS the mirror on the
right. feed=same: the cell is turned R90 and its stacked pad runs along the bottom; PLUS contacts the left half
of it on mmax, MINUS the right half on mmax-1, each lead going down, out and up a riser beside the cell to its
landing. Their length is the lead area divided by the lead width (centre line, corners approximate).

R values are DC, typical RPSQ from the PDK ITF, plain squares count; they exclude the landing patch and the
via stacks.
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
LEAD_W = 10.0         # lead width (build_chip LEAD_HMAX)
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


def same_lead(metal, side, abb, cx, cy):
    """Same feed lead on `metal`: from the reference plane to the half of the bottom pad on `side`."""
    x0, y0, x1, y1 = abb
    xm = (x0 + x1) / 2
    lo, hi = sorted((side * REF_X, xm))
    r = region(metal, (cx + lo, cy + y0 - 3 * LEAD_W, cx + hi, cy + BAND)) - region(metal, (cx + x0, cy + y0, cx + x1, cy + y1))
    assert not r.is_empty()
    w = LEAD_W
    length = r.area() * dbu * dbu / w
    return dict(len=round(length, 3), w=w, R=round(rpsq[metal] * length / w, 4))


bj = json.load(open(BUILD))
rep = {d["tile"]: d for d in bj["report"]}
rows = []
for s in csv.DictReader(open(SLOTS)):
    d = rep[s["tile"]]
    cx, cy = X0 + DX * int(s["col"]), Y0 + DY * int(s["row"])
    x0, y0, x1, y1 = d["array_bbox"]
    pl, ml = d["plus_layer"], d["minus_layer"]
    if s["feed"] == "same":
        p = same_lead(pl, -1, d["array_bbox"], cx, cy)
        m = same_lead(ml, +1, d["array_bbox"], cx, cy)
    else:
        p = lead(pl, -PATCH_X, x0, cx, cy)
        m = lead(ml, PATCH_X, x1, cx, cy)
    row = dict(tile=s["tile"], feed=s["feed"], stack=f"M{s['mmin']}-M{s['mmax']}",
               plus_layer=f"Metal{pl}", plus_lead_len_um=p["len"], plus_lead_w_um=p["w"], plus_lead_R_ohm=p["R"],
               plus_via_to_M4=pl < 4,
               minus_layer=f"Metal{ml}", minus_lead_len_um=m["len"], minus_lead_w_um=m["w"], minus_lead_R_ohm=m["R"],
               minus_via_to_M4=ml < 4, minus_tap=d["minus_tap"])
    rows.append(row)
    print(f"{s['tile']:4s} {s['feed']:6s} plus {p['len']:6.2f}x{p['w']:5.2f}  minus {m['len']:6.2f}x{m['w']:5.2f}")
with open(OUT, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0]))
    wr.writeheader()
    wr.writerows(rows)
print("wrote", OUT, len(rows), "tiles")
