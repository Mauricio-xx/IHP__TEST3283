# TEST3283 Specification

| Item | Value |
| --- | --- |
| Process | IHP SG13CMOS5L (ihp-sg13cmos5l PDK, IHP-Open-PDK dev 7b41fd10) |
| Die size (sealring) | 3465 x 2582 um |
| Top cell | TEST3283 |
| Device under test | `cap_cmomi` (PDK pycell, unmodified), 44 tiles |
| Test structure | two-port GSG-GSG, device in series, 8 x 6 tiles on 425 x 418 um |
| Pads | signal 60 um octagon, ground 80 um square, TopMetal1, GSG pitch 100 um |
| Calibration | OP (open), SHT (short), LS (lead short, Metal4); TH present but off pitch |
| Fill | PDK filler, device + 5 um keepout on every DUT and on OP/SHT/LS |
| Measurement range | to be decided |

Expected capacitance per tile: [Datasheet.md](./Datasheet.md). Measurement procedure: [../measurement/README.md](../measurement/README.md).
