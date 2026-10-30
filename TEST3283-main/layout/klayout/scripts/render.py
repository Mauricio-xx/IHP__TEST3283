"""Render doc images: the full chip and one tile per device family.

  klayout -zz -r scripts/klayout_run.py -rd script=scripts/render.py -rd gds=<chip.gds> -rd outdir=<dir>
"""
import pya

X0, Y0, DX, DY = 244.9, 246.43, 425.0, 418.0
VIEWS = {"full.png": None, "tile_B1.png": (2, 0), "tile_B24.png": (4, 7), "tile_B27.png": (5, 2), "tile_B34.png": (0, 2), "tile_LS.png": (0, 1)}

view = pya.LayoutView()
view.load_layout(gds, True)  # noqa: F821
view.set_config("background-color", "#ffffff")
view.max_hier()
for li in view.each_layer():
    src = li.source
    if "/23@" in src or "/25@" in src or "/22@" in src:
        li.visible = False
for name, rc in VIEWS.items():
    if rc is None:
        view.zoom_fit()
    else:
        cx, cy = X0 + DX * rc[1], Y0 + DY * rc[0]
        view.zoom_box(pya.DBox(cx - 110, cy - 80, cx + 110, cy + 80))
    view.save_image(f"{outdir}/{name}", 1600, 1200)  # noqa: F821
    print("wrote", name)
