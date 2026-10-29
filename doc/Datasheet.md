# TEST3283 Datasheet

Per tile list of the `cap_cmomi` devices. Generated from `TEST3283-main/layout/klayout/slots.csv`
(`scripts/doc_tables.py datasheet`); edit the CSV, not this table.

- `Row, col`: tile position, rows from the bottom, columns from the left, pitch 425 x 418 um.
- `momf twin`: the TEST9203 tile in the same position.
- `C model`: PDK model `cap_cmomi` (`libs.tech/verilog-a/cap_cmomi/cap_cmomi.va`, `ngspice/models/cap_cmomi.lib`,
  PDK commit `7b41fd10`): `C = density[N] * active_area + Cfeed`, per cell and times `Copies`.
  It does not include the leads and landing patches inside the tile, see measurement/README.md.
- Left signal pad = PLUS, right signal pad = MINUS in every tile.



## Model caveats

- The `same` feed term of the model (`Cfeed = 0.1625 * pad_len + 0.0916`) was fitted on pycell geometry
  without the tip vias the current pycell draws. B24-B28, B32, B39 and B45 test it.
- The reduced stack densities (N = 2, 3) are extrapolated in the model; the largest expected deviation is M3-M4.
- Expected values from EM simulation are in `TEST3283-main/testbenches/em`.
