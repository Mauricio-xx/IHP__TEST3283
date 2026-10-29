"""Assemble the cap_cmomi twin of TEST9203.

Takes the flat TEST9203 (cap_cmomf) GDS, removes the 44 DUTs with the fixture/device
cut rule, and drops cap_cmomi cells from the SG13_dev pycell library into the same
tiles, routed to the existing signal stubs. Pads, straps, calibration tiles and
sealring stay as they are.

Run in batch mode with the sg13cmos5l pycell library on KLAYOUT_PATH:

  klayout -zz -r scripts/build_chip.py -rd ref=<TEST9203_nofill.gds> \
      -rd slots=slots.csv -rd out=build/<name>_nofill.gds -rd name=<TOP> -rd pdk_rev=<sha>
"""
import csv
import inspect
import json
import time
import pya

T0 = time.time()

REF = ref          # noqa: F821  (-rd)
SLOTS = slots      # noqa: F821
OUT = out          # noqa: F821
TOP_NAME = name    # noqa: F821
PDK_REV = pdk_rev  # noqa: F821

# ---------------------------------------------------------------------------
# Fixture geometry of TEST9203 (um, relative to the tile centre).
# ---------------------------------------------------------------------------
X0, Y0, DX, DY = 244.9, 246.43, 425.0, 418.0
CUT_W = (100.0, 72.0)                 # device window: centre +-100 x +-72
PATCH = (75.0, 77.1, 5.0)             # M4 landing patch [+-75, +-77.1] x +-5
LABEL_BOX = (38.86, 60.0, 102.5, 104.0)
LABEL_POS = (70.3, 82.9)              # centre of the original tile-name glyphs
LABEL_H = 12.0
LEAD_HMAX = 10.0                      # leads no wider than the patch (and < Mn_f_w)
ARRAY_GAP = 1.0                       # gap between multiplied copies
NOFILL_MARGIN = 5.0
CAL_TILES = ("OP", "SHT", "A33")      # tiles that get the common DUT keepout

M = {1: (8, 0), 2: (10, 0), 3: (30, 0), 4: (50, 0)}
V = {1: (19, 0), 2: (29, 0), 3: (49, 0)}
CUT_LAYERS = [M[1], V[1], M[2], V[2], M[3], V[3], M[4], (189, 4), (50, 25), (30, 25)]
NOFILL = [(1, 23), (5, 23), (8, 23), (10, 23), (30, 23), (50, 23), (126, 23)]

VIA_A, VIA_S, VIA_ENC = 0.19, 0.29, 0.05   # Vn_a, Vn_b1 (array), Vn_c1

ly = pya.Layout()
ly.read(REF)
ly.technology_name = "sg13cmos5l"   # without it create_cell("cap_cmomi", ...) returns None
assert len(ly.top_cells()) == 1
top = ly.top_cells()[0]
top.name = TOP_NAME
dbu = ly.dbu


def L(ld):
    return ly.layer(*ld)


def ibox(x0, y0, x1, y1):
    return pya.DBox(x0, y0, x1, y1).to_itype(dbu)


def centre(r, c):
    return X0 + DX * c, Y0 + DY * r


# ---------------------------------------------------------------------------
# 1) Cut the cap_cmomf devices out of the DUT tiles.
# ---------------------------------------------------------------------------
slot_rows = list(csv.DictReader(open(SLOTS)))
tiles = json.load(open(SLOTS.replace("slots.csv", "tiles.json")))
dut_tiles = {(int(s["row"]), int(s["col"])) for s in slot_rows}
cap_tiles = {(t["row"], t["col"]) for t in tiles if t["role"] == "cap"}
assert dut_tiles == cap_tiles, "slot table does not cover exactly the cap tiles"

wins, labs = pya.Region(), pya.Region()
for (r, c) in sorted(dut_tiles):
    cx, cy = centre(r, c)
    wins.insert(ibox(cx - CUT_W[0], cy - CUT_W[1], cx + CUT_W[0], cy + CUT_W[1]))
    labs.insert(ibox(cx + LABEL_BOX[0], cy + LABEL_BOX[1], cx + LABEL_BOX[2], cy + LABEL_BOX[3]))


def cut_inside(ld, area):
    """Remove every shape of layer ld lying fully inside `area` (texts by origin)."""
    shapes = top.shapes(L(ld))
    texts = [s.text for s in shapes.each(pya.Shapes.STexts)]
    polys = pya.Region(shapes)
    polys.merged_semantics = False
    keep = polys.not_inside(area)
    n = polys.count() - keep.count()
    keep_t = [t for t in texts if pya.Region(pya.Box(t.x, t.y, t.x + 1, t.y + 1)).inside(area).is_empty()]
    shapes.clear()
    shapes.insert(keep)
    for t in keep_t:
        shapes.insert(t)
    return n + len(texts) - len(keep_t)


removed = {ld: cut_inside(ld, wins) for ld in CUT_LAYERS}
# tile-name glyphs (M4) are fixture-side but get a new name
removed["label"] = cut_inside(M[4], labs)
# restore the full landing patches (9 momf tiles had them trimmed to +-4.83)
for (r, c) in sorted(dut_tiles):
    cx, cy = centre(r, c)
    for sgn in (-1, 1):
        x0, x1 = sorted((sgn * PATCH[0], sgn * PATCH[1]))
        top.shapes(L(M[4])).insert(ibox(cx + x0, cy - PATCH[2], cx + x1, cy + PATCH[2]))
print("REMOVED", {str(k): v for k, v in removed.items()}, f"{time.time() - T0:.1f}s")

# ---------------------------------------------------------------------------
# 2) cap_cmomi cells from the pycell, frozen to static cells.
# ---------------------------------------------------------------------------
from sg13cmos5l_pycell_lib.ihp import cap_cmomi_code  # noqa: E402
print("PYCELL_FILE", inspect.getfile(cap_cmomi_code))

cache = {}


def momi_cell(l, w, mmin, mmax, feed):
    key = (l, w, mmin, mmax, feed)
    if key in cache:
        return cache[key]
    params = {"l": f"{l}u", "w": f"{w}u", "mmin": int(mmin), "mmax": int(mmax),
              "feed": feed, "subblock": False}
    var = ly.create_cell("cap_cmomi", "SG13_dev", params)
    if var is None:
        raise SystemExit(f"cap_cmomi not available for {params}")
    ci = ly.convert_cell_to_static(var.cell_index())
    cell = ly.cell(ci)
    cell.name = f"cmomi_{feed[0]}_l{l}_w{w}_m{mmin}{mmax}".replace(".", "p")
    cache[key] = cell
    return cell


def flat_region(cell, ld, trans=pya.Trans()):
    return pya.Region(cell.begin_shapes_rec(L(ld))).transformed(trans)


l2n_cache = {}


def net_regions(cell, seed_layer, seed_box):
    """Shapes of the net through M1..M4/V1..V3 that touches seed_box, per metal."""
    if cell.cell_index() not in l2n_cache:
        l2n = pya.LayoutToNetlist(pya.RecursiveShapeIterator(ly, cell, []))
        met = {k: l2n.make_layer(L(v), f"M{k}") for k, v in M.items()}
        via = {k: l2n.make_layer(L(v), f"V{k}") for k, v in V.items()}
        for k in M:
            l2n.connect(met[k])
        for k in V:
            l2n.connect(via[k])
            l2n.connect(met[k], via[k])
            l2n.connect(via[k], met[k + 1])
        l2n.extract_netlist()
        l2n_cache[cell.cell_index()] = (l2n, met)
    l2n, met = l2n_cache[cell.cell_index()]
    net = l2n.probe_net(met[seed_layer], seed_box.center())
    assert net is not None, f"no net under pin {seed_box} on M{seed_layer}"
    return {k: l2n.shapes_of_net(net, met[k], True) for k in M}


def pins(cell):
    """PLUS / MINUS pin boxes and their layers, from the x/2 pin shapes."""
    found = []
    for k in M:
        for p in flat_region(cell, (M[k][0], 2)).each():
            if (k, p.bbox()) not in found:   # the pycell draws some pins twice
                found.append((k, p.bbox()))
    return found


def via_array(box, lower):
    """Vn array between metal `lower` and lower+1 filling box (dbu) with enclosure."""
    b = box.to_dtype(dbu)
    x0, y0, x1, y1 = b.left + VIA_ENC, b.bottom + VIA_ENC, b.right - VIA_ENC, b.top - VIA_ENC
    pitch = VIA_A + VIA_S
    nx = int((x1 - x0 + VIA_S) / pitch + 1e-9)
    ny = int((y1 - y0 + VIA_S) / pitch + 1e-9)
    assert nx >= 1 and ny >= 1, f"via box too small: {b}"
    ox = x0 + ((x1 - x0) - (nx * pitch - VIA_S)) / 2
    oy = y0 + ((y1 - y0) - (ny * pitch - VIA_S)) / 2
    reg = pya.Region()
    for i in range(nx):
        for j in range(ny):
            vx, vy = ox + i * pitch, oy + j * pitch
            reg.insert(ibox(vx, vy, vx + VIA_A, vy + VIA_A))
    return reg


def drop_to_patch(side, cx, cy, layer, y0, y1):
    """Metal landing on `layer` under the patch plus the via stack up to M4."""
    x0, x1 = sorted((side * PATCH[0], side * PATCH[1]))
    land = ibox(cx + x0, cy + y0, cx + x1, cy + y1)
    for k in range(layer, 4):
        top.shapes(L(M[k])).insert(land)
        top.shapes(L(V[k])).insert(via_array(land, k))


def tile_label(text, cx, cy, layer=M[4]):
    gen = pya.TextGenerator.default_generator()
    reg = gen.text(text, dbu, 1.0)
    h = reg.bbox().height() * dbu
    reg = gen.text(text, dbu, LABEL_H / h)
    bb = reg.bbox()
    reg.move(int(round((cx + LABEL_POS[0]) / dbu)) - bb.center().x,
             int(round((cy + LABEL_POS[1]) / dbu)) - bb.center().y)
    lab = ibox(cx + LABEL_BOX[0], cy + LABEL_BOX[1], cx + LABEL_BOX[2], cy + LABEL_BOX[3])
    assert lab.contains(reg.bbox().p1) and lab.contains(reg.bbox().p2), text
    top.shapes(L(layer)).insert(reg)


# ---------------------------------------------------------------------------
# 3) Place, route, label.
# ---------------------------------------------------------------------------
report = []
keepouts = []
for s in slot_rows:
    r, c = int(s["row"]), int(s["col"])
    cx, cy = centre(r, c)
    l, w, mmin, mmax, feed, mult = s["l_um"], s["w_um"], int(s["mmin"]), int(s["mmax"]), s["feed"], int(s["mult"])
    cell = momi_cell(l, w, mmin, mmax, feed)
    cb = cell.bbox()
    pl = sorted(pins(cell), key=lambda p: (p[1].center().x, -p[0]))

    if feed == "double":
        (plus_layer, plus_pin), (minus_layer, minus_pin) = pl[0], pl[-1]
        assert plus_pin.center().x < 0 < minus_pin.center().x and plus_layer == minus_layer == mmax
    else:
        # stacked pins on the left: PLUS on mmax, MINUS on mmax-1
        assert len(pl) == 2 and all(p[1].center().x < 0 for p in pl)
        plus_layer, plus_pin = [p for p in pl if p[0] == mmax][0]
        minus_layer, minus_pin = [p for p in pl if p[0] == mmax - 1][0]

    plus = net_regions(cell, plus_layer, plus_pin)
    minus = net_regions(cell, minus_layer, minus_pin)
    for k in M:
        assert (plus[k] & minus[k]).is_empty(), f"{s['tile']}: nets overlap on M{k}"

    # orientations of the stacked copies: facing outer bars must belong to the same net
    trans = [pya.Trans()]
    if mult > 1:
        assert feed == "double"
        core = pya.Region(cb)
        top_net = "P" if (plus[mmin] & core).bbox().top >= (minus[mmin] & core).bbox().top else "M"
        bot_net = "P" if (plus[mmin] & core).bbox().bottom <= (minus[mmin] & core).bbox().bottom else "M"
        pitch = cb.height() + int(round(ARRAY_GAP / dbu))
        prev_top = top_net
        for i in range(1, mult):
            if bot_net == prev_top:
                t, nt = pya.Trans(0, False, 0, 0), top_net
            else:
                t, nt = pya.Trans(0, True, 0, 0), bot_net   # MX: bottom <-> top
            # MX mirrors about y=0: re-centre the mirrored bbox on the same slot
            mb = cb.transformed(t)
            dy = i * pitch + (cb.bottom - mb.bottom)
            trans.append(pya.Trans(t.rot, t.is_mirror(), 0, dy))
            prev_top = nt
    # centre the whole array on the tile centre
    arr_bb = pya.Box()
    for t in trans:
        arr_bb += cb.transformed(t)
    shift = pya.Vector(int(round(cx / dbu)) - arr_bb.center().x, int(round(cy / dbu)) - arr_bb.center().y)
    trans = [pya.Trans(shift) * t for t in trans]
    for t in trans:
        top.insert(pya.CellInstArray(cell.cell_index(), t))
    arr_bb = arr_bb.moved(shift)
    abb = arr_bb.to_dtype(dbu)
    assert abs(abb.left - cx) < 75 and abs(abb.right - cx) < 75 and abs(abb.top - cy) <= 60 and abs(abb.bottom - cy) <= 60, s["tile"]

    def pad_strip(net, layer, side):
        """Outermost 0.6 um of the terminal on `side`, over all copies (the pad)."""
        reg = pya.Region()
        for t in trans:
            reg += net[layer].transformed(t)
        reg.merge()
        bb, w06 = reg.bbox(), int(round(0.6 / dbu))
        x0, x1 = (bb.left, bb.left + w06) if side < 0 else (bb.right - w06, bb.right)
        return (reg & pya.Region(pya.Box(x0, bb.bottom, x1, bb.top))).bbox()

    # PLUS: left pad on plus_layer -> left landing
    pad = pad_strip(plus, plus_layer, -1)
    if mult > 1:   # bus the PLUS pads of all copies
        top.shapes(L(M[plus_layer])).insert(pad)
    pdy = pad.to_dtype(dbu)
    h = min(LEAD_HMAX, pdy.height())
    ly0, ly1 = max(pdy.center().y - cy - h / 2, -PATCH[2]), min(pdy.center().y - cy + h / 2, PATCH[2])
    top.shapes(L(M[plus_layer])).insert(ibox(cx - PATCH[1], cy + ly0, pdy.left + 0.1, cy + ly1))
    if plus_layer < 4:
        drop_to_patch(-1, cx, cy, plus_layer, ly0, ly1)

    if feed == "double":
        pad = pad_strip(minus, minus_layer, +1)
        if mult > 1:
            top.shapes(L(M[minus_layer])).insert(pad)
        mdy = pad.to_dtype(dbu)
        h = min(LEAD_HMAX, mdy.height())
        ry0, ry1 = max(mdy.center().y - cy - h / 2, -PATCH[2]), min(mdy.center().y - cy + h / 2, PATCH[2])
        top.shapes(L(M[minus_layer])).insert(ibox(mdy.right - 0.1, cy + ry0, cx + PATCH[1], cy + ry1))
        minus_tap = "right pad"
    else:
        # MINUS: extend the MINUS row on mmax-1 that ends on the right cell edge nearest y=0
        t = trans[0]
        mr = minus[minus_layer].transformed(t)
        xr = cb.transformed(t).right
        # a 20 nm slice at the cell edge cuts only the bar ends, not the teeth
        ends = [p.bbox() for p in (mr & pya.Region(pya.Box(xr - 20, mr.bbox().bottom, xr, mr.bbox().top))).each()]
        assert ends, f"{s['tile']}: no MINUS row on the right edge"
        row = min(ends, key=lambda b: abs(b.center().y - int(round(cy / dbu))))
        rdy = row.to_dtype(dbu)
        # the row keeps its own width for 0.7 um past the cell edge, so the wide
        # lead stays 0.6 um away from the PLUS row ends next to it
        top.shapes(L(M[minus_layer])).insert(ibox(rdy.right - 0.001, rdy.bottom, rdy.right + 0.7, rdy.top))
        h = min(LEAD_HMAX, 2 * PATCH[2])
        ry0, ry1 = -h / 2, h / 2
        top.shapes(L(M[minus_layer])).insert(ibox(rdy.right + 0.6, cy + ry0, cx + PATCH[1], cy + ry1))
        minus_tap = f"row y={rdy.center().y - cy:.3f}"
    if minus_layer < 4:
        drop_to_patch(+1, cx, cy, minus_layer, ry0, ry1)

    # terminal labels, as in TEST9203 (c1 -> left pad, c2 -> right pad)
    top.shapes(L((50, 25))).insert(pya.Text("c1", pya.Trans(int(round((cx - 76.0) / dbu)), int(round(cy / dbu)))))
    top.shapes(L((50, 25))).insert(pya.Text("c2", pya.Trans(int(round((cx + 76.0) / dbu)), int(round(cy / dbu)))))
    tile_label(s["tile"], cx, cy)

    ko = abb.enlarged(NOFILL_MARGIN, NOFILL_MARGIN)
    keepouts.append(ko.moved(-cx, -cy))
    for ld in NOFILL:
        top.shapes(L(ld)).insert(ko.to_itype(dbu))
    report.append(dict(tile=s["tile"], cell=cell.name, copies=len(trans),
                       mirrored=sum(t.is_mirror() for t in trans), plus_layer=plus_layer,
                       minus_layer=minus_layer, minus_tap=minus_tap,
                       array_bbox=[round(v, 3) for v in (abb.left - cx, abb.bottom - cy, abb.right - cx, abb.top - cy)]))
    print(f"{time.time() - T0:.1f}s slot {s['tile']} done", flush=True)

# ---------------------------------------------------------------------------
# 4) Same keepout in the calibration tiles, chip texts.
# ---------------------------------------------------------------------------
kx = max(max(-b.left, b.right) for b in keepouts)
ky = max(max(-b.bottom, b.top) for b in keepouts)
for t in tiles:
    if t["role"] in CAL_TILES:
        cx, cy = centre(t["row"], t["col"])
        for ld in NOFILL:
            top.shapes(L(ld)).insert(ibox(cx - kx, cy - ky, cx + kx, cy + ky))

texts = top.shapes(L((63, 0)))
for sh in list(texts.each(pya.Shapes.STexts)):
    if sh.text.string.startswith("PDK version:"):
        t = sh.text.dup()
        t.string = f"PDK version: {PDK_REV}"
        sh.text = t

ly.write(OUT)
json.dump(dict(report=report, cal_keepout_halfsize=[kx, ky], removed={str(k): v for k, v in removed.items()}),
          open(OUT.replace(".gds", "_build.json"), "w"), indent=1)
for row in report:
    print(row)
print("WROTE", OUT)
