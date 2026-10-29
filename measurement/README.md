# TEST3283 measurement guide

This guide is for the person measuring TEST3283 on wafer. Read it before the first die. Expected values
per tile are in `doc/Datasheet.md` (PDK model) and `TEST3283-main/testbenches/em` (EM simulation).

## What is measured

Each tile is a two-port: a GSG probe on the left pad group, a GSG probe on the right pad group, and the
capacitor in series between the two signal pads. Left signal = PLUS, right signal = MINUS in every tile.
Ground pads of both sides are tied together on TopMetal1 (straps above and below the device).

- Pads: signal 60 um octagons at (+-142.5, 0) from the tile centre, ground 80 um squares at (+-142.5, +-100).
  GSG pitch 100 um. Signal-to-signal distance 285 um.
- Tile pitch 425 x 418 um. Tile centre of (row, col) = (244.9 + 425 col, 246.43 + 418 row) um from the
  lower left corner of the sealring. The tile map is in the top level README.

## Calibration and de-embedding

1. Calibrate at the probe tips on the impedance standard substrate that matches the probes (SOLT or LRRM, as
   the lab normally does). Record the method and the cal kit file.
2. Measure `OP` (row 1, col 0) and `SHT` (row 1, col 1) on **every die** you measure, before its DUTs.
   `A33` (row 0, col 1) is a second open, measure it too: OP vs A33 is a free repeatability check.
3. De-embed every DUT with open-short using that die's OP and SHT:
   `Y_open = Y(OP)`, `Z_short = (Y(SHT) - Y_open)^-1`, `Y_dut = ((Y_meas - Y_open)^-1 - Z_short)^-1`.
4. Do **not** use `TH`: its pads are at +-105 um, not on the 285 um pitch of the DUTs.

Reference plane after open-short: the end of the TopMetal1 signal stubs, |x| = 75 um from the tile centre.
Still inside the de-embedded result, and therefore NOT in the PDK model numbers: the TopVia1/Metal4 landing
patch at |x| 75-77.1 um and the lead from the patch to the capacitor terminal (up to 10 um wide, on the
terminal's metal, with a via stack up to Metal4 at the patch when that metal is below Metal4). The EM bench gives this lead correction per tile;
compare against the model only after subtracting it.

## Extraction

For a series element, with the de-embedded two-port admittance:

- `C = -Im(Y21) / (2 pi f)` at the low frequency end (series capacitance).
- `Y11 + Y21` and `Y22 + Y21` are the shunts from PLUS and MINUS to ground (substrate and fringe).
- With `Z_dut = -1/Y21`: series resistance `R = Re(Z_dut)` and `Q = -Im(Z_dut) / Re(Z_dut)`, versus
  frequency. Series R matters for this device: the inner fingers reach the terminal bars through single vias.
- The self-resonance is where `Im(Z_dut)` crosses zero. The model expects it in band for the large
  `double` feed devices.

## Settings

- Frequency range: **to be decided**. Use the same range for every die, and for OP and SHT.
- Record per session: VNA, probes, cal kit and method, source power, IF bandwidth, averaging, temperature,
  date, operator, wafer and die id.

## File naming

One Touchstone file per tile and die, raw (before de-embedding) data only. De-embedding is done in
post-processing so it can be re-run and audited.

    TEST3283_w<wafer>_d<die>_<tile>_raw.s2p        tile = B1..B45, OP, SHT, A33
    TEST3283_w<wafer>_d<die>_session.json          the settings above

Results are compared per tile in a single table with the model, the EM value, the lead correction and the
measured value.
