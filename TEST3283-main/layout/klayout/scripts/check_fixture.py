"""XOR the new chip against TEST9203 outside the DUT windows: the fixture must be untouched.

  klayout -zz -r scripts/klayout_run.py -rd script=scripts/check_fixture.py -rd a=<new.gds> \
      -rd b=<TEST9203_nofill.gds> -rd tiles=tiles.json

Exits non-zero on any geometry difference outside the windows, or any text difference other than the
two the build updates on purpose: the "PDK version:" string, and the sealring area line (the fixture
labels um*um as mm^2; the size line x=3465.0 um, y=2582.0 um must stay).
"""
import json
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

def allowed(s):
    if s.startswith("PDK version:"):
        return True
    return (s.startswith("Device registration size: x=3465.0 um ; y=2582.0 um")
            and "Calculated area:" in s)

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
    da = [p for p in set(txa) ^ set(txb) if not ex(p)]
    if da:
        print("TEXT DIFF", ld, da[:6])
        text_diff += sum(1 for p in da if not allowed(p[0]))
print("LAYERS COMPARED", len(lds), "LAYERS WITH DIFF OUTSIDE WINDOWS", diff, "UNEXPECTED TEXT DIFFS", text_diff)
if diff or text_diff:
    raise SystemExit(1)
