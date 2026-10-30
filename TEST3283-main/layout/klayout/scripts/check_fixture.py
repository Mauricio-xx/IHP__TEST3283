"""XOR the new chip against TEST9203 outside the DUT windows: the fixture must be untouched.

  klayout -zz -r scripts/klayout_run.py -rd script=scripts/check_fixture.py -rd a=<new.gds> \
      -rd b=<TEST9203_nofill.gds> -rd tiles=tiles.json

Exits non-zero on any geometry difference outside the windows, or any text difference other than the
two rewrites the build makes on purpose, each at the same layer and position as the fixture text:
  - "PDK version: <40 hex>" in place of the fixture's PDK version;
  - the sealring label with its size line unchanged and the area line recomputed from it
    ("Calculated area: <x*y/1e6> sq mm"; the fixture labels um*um as mm^2), the size matching the top bbox.
A fixture text that disappears, moves or gets any other value is a difference.
"""
import json
import re
import pya

X0, Y0, DX, DY = 244.9, 246.43, 425.0, 418.0
CUT_W = (100.0, 72.0)
LABEL_BOX = (38.86, 60.0, 102.5, 104.0)

la, lb = pya.Layout(), pya.Layout()
la.read(a)  # noqa: F821
lb.read(b)  # noqa: F821
ta, tb = la.top_cells()[0], lb.top_cells()[0]
dbu = la.dbu
excl = pya.Region()
for t in json.load(open(tiles)):  # noqa: F821
    cx, cy = X0 + DX * t["col"], Y0 + DY * t["row"]
    excl.insert(pya.DBox(cx - CUT_W[0], cy - CUT_W[1], cx + CUT_W[0], cy + CUT_W[1]).to_itype(dbu))
    excl.insert(pya.DBox(cx + LABEL_BOX[0], cy + LABEL_BOX[1], cx + LABEL_BOX[2], cy + LABEL_BOX[3]).to_itype(dbu))

SIZE = re.compile(r"Device registration size: x=([\d.]+) um ; y=([\d.]+) um")


def rewrite_ok(sa, sb):
    """True if sa is the build's rewrite of the fixture text sb."""
    if sb.startswith("PDK version:"):
        return re.fullmatch(r"PDK version: [0-9a-f]{40}", sa) is not None
    lines = sb.split("\n")
    m = SIZE.fullmatch(lines[0])
    if not (m and len(lines) == 2 and lines[1].startswith("Calculated area:")):
        return False
    x, y = float(m.group(1)), float(m.group(2))
    bb = ta.dbbox()
    if abs(bb.width() - x) > 1e-3 or abs(bb.height() - y) > 1e-3:
        return False
    return sa == f"{lines[0]}\nCalculated area: {x * y / 1e6:.5f} sq mm"


lds = sorted({(i.layer, i.datatype) for l in (la, lb) for i in l.layer_infos()})
diff = text_diff = 0
for ld in lds:
    ra = pya.Region(ta.begin_shapes_rec(la.layer(*ld)))
    rb = pya.Region(tb.begin_shapes_rec(lb.layer(*ld)))
    x = (ra ^ rb) - excl
    if x.count():  # count, not is_empty: text-only layers give a non-empty region with no polygons
        diff += 1
        print("DIFF", ld, x.count(), x.bbox().to_dtype(dbu))
    txa = sorted((s.text_string, s.text_pos.x, s.text_pos.y) for s in ta.shapes(la.layer(*ld)).each(pya.Shapes.STexts))
    txb = sorted((s.text_string, s.text_pos.x, s.text_pos.y) for s in tb.shapes(lb.layer(*ld)).each(pya.Shapes.STexts))
    ex = lambda p: not pya.Region(pya.Box(p[1], p[2], p[1] + 1, p[2] + 1)).inside(excl).is_empty()
    only_a = [p for p in set(txa) - set(txb) if not ex(p)]
    only_b = [p for p in set(txb) - set(txa) if not ex(p)]
    for pb in list(only_b):  # pair each changed fixture text with its rewrite at the same position
        pa = next((p for p in only_a if p[1:] == pb[1:] and rewrite_ok(p[0], pb[0])), None)
        if pa:
            only_a.remove(pa)
            only_b.remove(pb)
            print("REWRITE", ld, repr(pb[0]), "->", repr(pa[0]))
    if only_a or only_b:
        print("TEXT DIFF", ld, "new:", only_a[:6], "fixture:", only_b[:6])
        text_diff += len(only_a) + len(only_b)
print("LAYERS COMPARED", len(lds), "LAYERS WITH DIFF OUTSIDE WINDOWS", diff, "UNEXPECTED TEXT DIFFS", text_diff)
if diff or text_diff:
    raise SystemExit(1)
