# TEST3283-main

- `layout/klayout/`: the generator. `slots.csv` lists the 44 devices (tile, position, size, stack, feed,
  copies, model C); `tiles.json` is the TEST9203 tile map; `ref/` holds the TEST9203 nofill GDS the chip is
  derived from (with its checksum).
- `layout/klayout/leads.csv`: per tile lead geometry and DC resistance, measured on the nofill GDS by
  `lead_table.py` (the metal between the de-embedding reference plane and the device).
- `testbenches/em/`: EM simulation bench (Palace), expected values per tile. Pending, to be merged.

## Rebuilding

Requires KLayout 0.30 and an IHP-Open-PDK checkout with ihp-sg13cmos5l (set `PDK_TREE`, default is the
review worktree at dev 7b41fd10). KLayout runs in a clean environment (`scripts/env.sh`) so that only that
PDK tree is visible.

    cd layout/klayout
    PDK_TREE=/path/to/IHP-Open-PDK scripts/flow.sh

`flow.sh` runs, in order and holding a shared lock so it never overlaps with other heavy jobs:

1. `build.sh` / `build_chip.py`: cut the `cap_cmomf` devices out of TEST9203 (shapes fully inside the
   +-100 x +-72 um device window of each DUT tile, and the old tile labels), restore the Metal4 landing
   patches, generate each `cap_cmomi` from the pycell, route PLUS to the left patch and MINUS to the right
   patch, write labels, nofill keepouts and `build/TEST3283_nofill_build.json` (per tile report).
2. `check_conn.py`: per tile netlist extraction, M1 to TopMetal1. Fails if PLUS, MINUS and ground are not
   three separate nets or a signal net does not own the device. Run on TEST9203 it flags A1-A8, which are
   shorted there; that is the regression test of the check.
3. `check_fixture.py`: XOR against TEST9203 outside the device windows. Geometry must match. Text may
   differ only in the PDK version and the sealring area line.
4. `lead_table.py`: writes `leads.csv`.
5. PDK `filler.py`, then `check_fill.py` (no fill within 2 um of any device or calibration core).
6. PDK DRC: min deck with density, full deck on the filled GDS, full deck on the nofill GDS.
7. `release.sh`: gzip of the filled GDS to `release/v.1.0.0/gds/` with checksums, and the DRC logs of that
   GDS to `release/v.1.0.0/doc/`. It only runs when both DRC runs on the filled GDS are clean, and refuses
   to replace an existing, different release unless `FORCE=1`.

Every check exits non-zero on failure and stops the flow. KLayout writes the build time into the GDS, so a
rebuild has the same geometry but a new checksum.

`doc_tables.py render` writes the top README and doc/Datasheet.md from `doc_templates/` and `slots.csv`.
