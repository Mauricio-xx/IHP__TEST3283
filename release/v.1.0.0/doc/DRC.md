# DRC evidence, TEST3283 v.1.0.0

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

There is no schematic netlist. `doc/info.json` does not reference `release.netlist`, so LVS is not run.
