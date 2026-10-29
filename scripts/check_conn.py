"""Per-tile connectivity check: left signal pad, right signal pad and ground must be three
different nets, and each signal net must reach into the DUT window.

  klayout -zz -r scripts/klayout_run.py -rd script=scripts/check_conn.py -rd gds=<chip.gds> \
      -rd tiles=tiles.json -rd out=<report.json>

Run it on the original TEST9203 too: it must flag the shorted A1-A8 tiles.
"""
import json
import pya

GDS, TILES, OUT = gds, tiles, out  # noqa: F821  (-rd)
X0, Y0, DX, DY = 244.9, 246.43, 425.0, 418.0
STACK = [("M1", 8), ("V1", 19), ("M2", 10), ("V2", 29), ("M3", 30), ("V3", 49),
         ("M4", 50), ("TV1", 125), ("TM1", 126)]

ly = pya.Layout()
ly.read(GDS)
top = ly.top_cells()[0]
l2n = pya.LayoutToNetlist(pya.RecursiveShapeIterator(ly, top, []))
reg = {n: l2n.make_layer(ly.layer(g, 0), n) for n, g in STACK}
for (a, _), (b, _) in zip(STACK, STACK[1:]):
    l2n.connect(reg[a])
    l2n.connect(reg[a], reg[b])
l2n.connect(reg["TM1"])
l2n.extract_netlist()


def net_at(x, y, layer="TM1"):
    return l2n.probe_net(reg[layer], pya.DPoint(x, y))


def area_in(net, box):
    """M1..M4 area (um2) of `net` inside box (um)."""
    if net is None:
        return 0.0
    b = pya.Region(pya.DBox(*box).to_itype(ly.dbu))
    return sum((l2n.shapes_of_net(net, reg[m], True) & b).area() for m in ("M1", "M2", "M3", "M4")) * ly.dbu ** 2


def reaches(net, box):
    """Does `net` have M1..M4 geometry inside box (um)?"""
    if net is None:
        return False
    b = pya.Region(pya.DBox(*box).to_itype(ly.dbu))
    for m in ("M1", "M2", "M3", "M4"):
        if not (l2n.shapes_of_net(net, reg[m], True) & b).is_empty():
            return True
    return False


dev = {}
try:
    for d in json.load(open(build))["report"]:  # noqa: F821  (optional -rd build=<..._build.json>)
        dev[d["tile"]] = d["array_bbox"]
except NameError:
    pass
rows = []
for t in json.load(open(TILES)):
    cx, cy = X0 + DX * t["col"], Y0 + DY * t["row"]
    left, right = net_at(cx - 142.5, cy), net_at(cx + 142.5, cy)
    gnd = net_at(cx - 142.5, cy + 100.0)
    ids = [n.cluster_id if n else None for n in (left, right, gnd)]
    core = (cx - 72.0, cy - 60.0, cx + 72.0, cy + 60.0)
    row = dict(tile=t.get("A"), role=t["role"], row=t["row"], col=t["col"], nets=ids,
               left_right_short=ids[0] is not None and ids[0] == ids[1],
               signal_ground_short=ids[2] in ids[:2],
               left_in_dut=reaches(left, core), right_in_dut=reaches(right, core))
    bb = dev.get(f"B{t.get('A')}")
    if bb:
        # inside the cell, away from the leads: both nets must own a real share of the fingers
        inner = (cx + bb[0] + 1.0, cy + bb[1] + 0.5, cx + bb[2] - 1.0, cy + bb[3] - 0.5)
        al, ar = area_in(left, inner), area_in(right, inner)
        row.update(area_left=round(al, 1), area_right=round(ar, 1),
                   left_in_dut=row["left_in_dut"] and al > 0.2 * ar,
                   right_in_dut=row["right_in_dut"] and ar > 0.2 * al)
    if t["role"] == "cap":
        row["ok"] = not row["left_right_short"] and not row["signal_ground_short"] and row["left_in_dut"] and row["right_in_dut"]
    rows.append(row)

json.dump(rows, open(OUT, "w"), indent=1)
bad = [r for r in rows if r.get("ok") is False]
for r in rows:
    print(r)
print(f"CAP TILES: {sum(1 for r in rows if 'ok' in r)}, FAILING: {len(bad)}",
      [f"r{r['row']}c{r['col']}" for r in bad])
