# TEST3283 measurement guide

This guide is for the person measuring TEST3283 on wafer. Read it before the first die. Expected values
per tile are in `doc/Datasheet.md` (PDK model). EM expected values will be in `TEST3283-main/testbenches/em`
(pending, not in this release). The metal inside each tile that is not part of the device (leads) is listed
in `TEST3283-main/layout/klayout/leads.csv`, measured on the released layout.

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
2. Measure `OP` (row 1, col 0), `SHT` (row 1, col 1) and `LS` (row 0, col 1) on **every die** you measure,
   before its DUTs.
3. De-embed every DUT with open-short using that die's OP and SHT:
   `Y_open = Y(OP)`, `Z_short = (Y(SHT) - Y_open)^-1`, `Y_dut = ((Y_meas - Y_open)^-1 - Z_short)^-1`.
4. Do **not** use `TH`: its pads are at +-105 um, not on the 285 um pitch of the DUTs.

Reference plane after open-short: the end of the TopMetal1 signal stubs, |x| = 75 um from the tile centre.
Still inside the de-embedded result, and therefore NOT in the PDK model numbers: the TopVia1/Metal4 landing
patch at |x| 75-77.1 um and the lead from the patch to the capacitor terminal (up to 10 um wide, on the
terminal's metal, with a via stack up to Metal4 at the patch when that metal is below Metal4). `leads.csv` gives
per tile and side the lead layer, length from the reference plane, width and typical DC resistance; the EM
bench will give the full correction (R, L and shunt C). Compare R and L against the model only after
subtracting the leads.

`LS` (lead short) measures that residual directly. It is the DUT fixture with a 10 um wide Metal4 bar from
landing patch to landing patch (|x| <= 77.1 um), on the same open-short reference plane, so its
`Z = -1/Y21` is `2 x landing + Metal4 bar`. Per DUT, scale it to that tile's actual lead length and width
(`leads.csv`; the LS bar is 154.2 x 10 um, 2 x 77.1 um from the tile centre). `LS` does not cover the Metal3
leads (row 0, M1-M3 tiles) or the via stacks of leads below Metal4; use `leads.csv` and, once available, the
EM value for those.

`same` feed tiles (B24-B28, B32, B39, B45): the right lead lands on the right end of a single MINUS finger
row, and the MINUS rows only join at the left pad, so the whole row is in series with the device
(`tap_row_R_ohm` in `leads.csv`: about 1 ohm for B24, 9 ohm for B27, 17 ohm for B32). Use these tiles for C
only. Their R, Q, L and SRF include the row and are NOT comparable with the model.

## Extraction

For a series element, with the de-embedded two-port admittance:

- `C = -Im(Y21) / (2 pi f)` at the low frequency end (series capacitance).
- `Y11 + Y21` and `Y22 + Y21` are the shunts from PLUS and MINUS to ground (substrate and fringe).
- With `Z_dut = -1/Y21`: series resistance `R = Re(Z_dut)` and `Q = -Im(Z_dut) / Re(Z_dut)`, versus
  frequency. Series R matters for this device: the inner fingers reach the terminal bars through single vias.
  R is only resolvable where `|Im(Z_dut)|` is not orders of magnitude above it: at 1 GHz a 4 fF cap has
  `|X|` = 39 kohm and `Re(Z_dut)` is noise (it can come out negative). Read R and Q near 10 GHz and above,
  and on the large `double` feed tiles (C model above about 1 pF in the Datasheet); do not report R from the
  small tiles at low frequency, nor from the `same` feed tiles at all (see above).
- `same` feed tiles: the tap row R lowers the apparent C by `(2 pi f R C)^2`; take C where
  `2 pi f R C < 0.1` (under 1 %), which is below about 250 MHz for B27.
- The self-resonance is where `Im(Z_dut)` crosses zero. The model expects it in band for the large
  `double` feed devices.

## Settings

- Frequency range: **to be decided**. Use the same range for every die, and for OP and SHT.
- Record per session: VNA, probes, cal kit and method, source power, IF bandwidth, averaging, temperature,
  date, operator, wafer and die id.

## File naming

One Touchstone file per tile and die, raw (before de-embedding) data only. De-embedding is done in
post-processing so it can be re-run and audited.

    TEST3283_w<wafer>_d<die>_<tile>_raw.s2p        tile = B1..B45, OP, SHT, LS
    TEST3283_w<wafer>_d<die>_session.json          the settings above

Results are compared per tile in a single table with the model, the EM value, the lead correction and the
measured value.
