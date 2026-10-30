# DRC evidence, TEST3283 v.1.0.0

Both runs are on the filled release `gds/TEST3283.gds.gz` (sha256 `c8f184c26fe726e90a4a312b7970eb2496d4f8c0f87598b912fff478668deec5`), top cell `TEST3283`,
deck `ihp-sg13cmos5l` `run_drc.py`.

| Run | Invocation | `precheck_drc` | Result | Log | Database |
| --- | --- | --- | --- | --- | --- |
| Minimum, the foundry precheck rule set | `--minimum_drc` | true | No DRC violations | [drc_min_fill.log](drc_min_fill.log) | [drc_min_fill.lyrdb](drc_min_fill.lyrdb) |
| Full deck | no `--minimum_drc` | false | No DRC violations | [drc_full_fill.log](drc_full_fill.log) | [drc_full_fill.lyrdb](drc_full_fill.lyrdb) |

`run_drc.py` sets the deck switch `precheck_drc` from `--minimum_drc`. The minimum run is the
precheck. The full run leaves that switch false because it checks the whole deck, not the reduced set.

There is no schematic netlist. `doc/info.json` does not reference `release.netlist`, so LVS is not run.
