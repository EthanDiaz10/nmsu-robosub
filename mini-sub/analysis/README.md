# BENTO rev C: analysis

Source CAD: `BENTO_REV-C\STRUCTURE-ASSY_BENTO_REV-C.SLDASM` (surveyed 2026-11-25 with `scripts/kraken_bento_survey.py`,
raw output in `data/survey_revC_structure.json`). Frame: +Y up; the -X face carries the forward window (assumed),
so X is fore/aft.

## What's in the structure assembly

| | |
|---|---|
| Envelope | 375 x 213 x 398 mm (X x Y x Z), base board and thruster mounts included |
| Pressure box | 312 x 164 x 182 mm outside, 6 mm 5052-H32 walls and lid, 8 mm bottom, 300 x 150 x 170 mm (7.65 L) cavity |
| Mass (SolidWorks, materials assigned) | **7.79 kg**, solid volume 4.01 L |
| Heaviest parts | base board ~1.8 kg (30 mm thick, "Epoxy, Unfilled" placeholder), box sides 1.45, bottom 1.0, **lid 0.92**, screws 0.6 |
| Windows | two 5 mm cast acrylic panes, 82 x 152 mm: one on the -X face, one on the bottom |
| Thrusters | 6 mounts (4 corner, 2 curved fore/aft) in the base-board plane (Y 953-983). **The T200s are not in this assembly**, so their axes are still unknown |

## 1. Buoyancy, trim, stability (`buoyancy_trim.py`)

| Case | Weight in air | Net buoyancy | CB above CG |
|---|---|---|---|
| Structure only | 7.79 kg | +3.79 kg | **3.6 mm** |
| + 6 T200 + est. battery 0.6 kg + electronics 1.0 kg | 11.45 kg | +1.25 kg (+11 %) | 6.9 mm |
| + 1.24 kg lead inside on the bottom plate, trimmed to +1 % | 12.69 kg | +0.13 kg | 12.4 mm |
| + 1.24 kg lead under the box on the base legs | 12.69 kg | +0.13 kg | 15.9 mm |

Findings
* **It floats with room to spare.** Displaced volume is ~12.8 L, so it needs ~1.2 kg of ballast to sit at the rules'
  0.5 % minimum with margin. Once trimmed, weight in air is set by displaced volume (~12.7 kg, weight bonus ~ +103 pts),
  **not** by wall thickness. Shrinking the box is what saves weight; thinning walls just swaps aluminum for lead.
* **Self-righting is weak.** Even with lead below the box, CB is only ~12-16 mm above CG. That's ~0.3 N*m at 10 deg heel,
  which one T200 at partial throttle overpowers easily. The structure alone is almost neutral (3.6 mm) because the
  heaviest aluminum (lid, side walls, flange) sits at or above the CB.
* **Fore/aft trim:** the structure's CG sits 6.7 mm toward +X from the CB (9 mm with thrusters/internals), because the window extenders add
  buoyancy on the -X side. Ballast centered near X 668 fixes it.

Ways to get GM to ~25-30 mm (rough, from the same model)
* Lid 6 mm -> 3 mm (0.46 kg off the top, same mass back as lead on the legs): about **+7 mm**
* ~0.5 L of foam on top + 0.5 kg more lead low: about **+8 mm** (costs ~1 weight-bonus point)
* Keep battery and heavy electronics on the bottom plate

## 2. Wall / lid pressure check (hand calc)

Deepest case 2.2 m -> 21.5 kPa (3.1 psi). Lid as a simply supported plate over the 293 x 163 mm gasket span (Roark):

| Lid thickness | Center deflection | Max stress | Safety factor on 5052-H32 yield (193 MPa) |
|---|---|---|---|
| 6 mm (current) | 0.10 mm | 9 MPa | ~21 |
| 4 mm | 0.33 mm | 21 MPa | ~9 |
| 3 mm | 0.8 mm | 37 MPa | ~5 |

Pressure isn't what drives wall thickness here. Welding, flatness and latch stiffness are. Outside pressure pushes the lid
onto the gasket, so the gasket seal gets tighter with depth.

## Open items
* Survey `TOP-ASSY_BENTO_REV-C` (it has the T200s) to get thrust axes -> thruster authority / allocation matrix
* Real base-board material (it's the heaviest part; G10 at 1.85 g/cc vs HDPE at 0.95 changes trim a lot)
* Real battery and electronics masses and positions -> rerun `buoyancy_trim.py`
* Lid gasket compression between the 8 draw latches; window flange bolt preload

## 3. Thruster authority (`thruster_allocation.py`)

Layout: ArduSub **Vectored** frame (BlueROV2, FRAME_CONFIG 1): 4 horizontal T200s on the corner mounts at 45 deg,
2 vertical T200s side by side on the curved mounts. It controls roll, yaw, heave, surge and sway, **but not pitch**.
Thruster positions come from `TOP-ASSY_BENTO_REV-C_T200.SLDASM` (a copy assembly with the T200s bolted to the mounts.
All holes line up. Built by `place_t200.py` in the CAD folder). The horizontal axes sit at the base-board mid-plane (Y 968.1),
and the verticals sit on the board center line (X 769.6).

| Axis | Max (T200 @ 16 V) |
|---|---|
| Surge | 114 N |
| Sway | 109 N |
| Heave | 103 N |
| Roll | 16 N*m |
| Yaw | 41 N*m |

Plenty of force: drag is roughly 33 N at 1 m/s (frontal area ~0.06 m^2, Cd ~1.1), so cruise thrust is ~10 N.

**Pitch is the weak spot.** Nothing can correct pitch, so it relies on the passive restoring moment, max m g GM = 2.0 N*m.
* As placed, the horizontal thrust line is **15 mm above the trimmed CG**. Full surge pitches the sub ~60 deg, and a 10 N cruise ~4-5 deg.
* The thrusters sit almost exactly at the **CB height** (968.1 vs 968.8). So ballast can't fix this: lowering the CG grows the
  offset and the GM together, and full surge still pitches ~65 deg whatever the ballast. The thrust line has to move down
  toward the CG.
* The verticals sit ~15 mm aft of the trimmed CG: half heave (50 N) pitches it ~22 deg, full heave ~52 deg.

What to do
* Lower the horizontal T200s ~15 mm by extending the straight mounts below the base board, so their axes sit at the trimmed CG height (+/- 3 mm).
* Move the vertical pair ~15 mm forward, or use slotted holes, so they sit on the CG/CB fore/aft line.
* Raise GM (section 1). It cuts the pitch from whatever offset is left.
* In ArduSub, cap surge and heave throttle until pool tests show the pitch behaves.
