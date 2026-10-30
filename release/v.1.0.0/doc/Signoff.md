# DRC and LVS evidence, TEST3283 v.1.0.0

## DRC

Both runs are on the filled release `gds/TEST3283.gds.gz` (sha256 `c8f184c26fe726e90a4a312b7970eb2496d4f8c0f87598b912fff478668deec5`), top cell `TEST3283`,
deck `ihp-sg13cmos5l` `run_drc.py`.

| Run | Invocation (`flow.sh`) | Switch, from the log | Result, from the log | Log | Database |
| --- | --- | --- | --- | --- | --- |
| Minimum, the foundry precheck rule set | `--min_drc` | Minimum DRC enabled: true | No DRC violations | [drc_min_fill.log](drc_min_fill.log) | [drc_min_fill.lyrdb](drc_min_fill.lyrdb) |
| Full deck | no `--min_drc` | Minimum DRC enabled: false | No DRC violations | [drc_full_fill.log](drc_full_fill.log) | [drc_full_fill.lyrdb](drc_full_fill.lyrdb) |

`--min_drc` is an alias of `run_drc.py --minimum_drc`, which sets the deck switch `precheck_drc`. The
logs do not print the invocation; the deck prints that switch as `Minimum DRC enabled` (main and density
decks). The minimum run is the precheck. The full run leaves the switch false because it checks the whole
deck, not the reduced set. Neither database has a violation item.

## LVS

Filled release GDS against [`netlist/TEST3283.cdl`](../netlist/TEST3283.cdl), deck `ihp-sg13cmos5l`
`run_lvs.py`, flat, `--purge --purge_nets --ignore_top_ports_mismatch`.
Result, from the log: Netlists match (Status | PASS).
Log: [lvs.log](lvs.log), extracted netlist: [lvs_extracted.cir](lvs_extracted.cir).

The netlist (`scripts/lvs_netlist.py`, from `slots.csv`) has one `cap_cmomi` per placed cell between
its tile's PLUS and MINUS pad nets: 90 instances in 44 tiles. OP, SHT, TH, LS, the
ground frame and the fill hold no device and are purged. What the comparison establishes, and what not:

- Checked: every tile has its capacitor (all copies of an array), between two nets of its own, with no net
  shared or shorted between tiles. Removing a tile's device or one copy of an array, adding a device, or
  moving a terminal to another tile's net fails (mutation runs of this netlist, 2026-10-30).
- Not checked, by the deck's design (`lvs/testing/README.md` of the PDK): `w`, `l`, `mmin`/`mmax`
  and `feed` (a device declared on the wrong metal band matches), and which pad is PLUS (the two terminals
  are equivalent). The build places the cells from `slots.csv`
  and `check_conn.py` checks PLUS on the left pad per tile.
- Port names are not compared: every tile labels its pads `c1`/`c2` (TEST9203 fixture), so the layout's
  top-level names repeat and cannot equal per-tile net names. Without the option the run reports only those
  88 name mismatches.
