# BENTO mini sub: hydrodynamics & analysis log

**Role:** Ethan Diaz, hydrodynamics and analysis lead, NMSU Kraken Submersibles (RoboSub 2027 season).
The mini sub (BENTO) was designed by a teammate. My job is to analyze it, find problems and propose fixes.
**Tools:** SolidWorks driven from Python (pywin32 COM API), Python/numpy, OpenCascade (STEP geometry), ArduSub frame models.

This log is written as it happens, so it can become a portfolio entry later. Each entry covers the question, the method, the result and the decision.

---

## 2026-11-25: Analysis plan
**Question:** Which analyses are worth running on a small RoboSub vehicle, given that the design is already done?
**Constraints from the RoboSub 2026 handbook:** must float at least 0.5 % positive when killed. Weight bonus below 22 kg.
Up to two vehicles, which together must fit in 0.9 x 0.9 x 1.8 m. The pool is 2.1 m (7 ft) deep.
**Plan, by priority:** (1) buoyancy and trim, (2) wall/lid pressure check, (3) seals, (4) thruster authority, (5) drag.

## 2026-11-25: Getting data out of SolidWorks
**Problem:** SolidWorks files are a compressed binary format, so nothing outside SolidWorks can read them.
**Method:** wrote `scripts/kraken_bento_survey.py`. It opens an assembly read-only through the COM API and exports
mass properties, the material and 4x4 transform of every component, and STEP geometry.
**Result:** STRUCTURE-ASSY rev C is 7.79 kg with materials assigned: 5052-H32 box with 6 mm walls and lid, an 8 mm bottom, and 5 mm acrylic windows.
I matched the STEP solids to components by bounding box to get per-part volumes and centroids.

## 2026-11-25: Buoyancy, trim and stability (`analysis/buoyancy_trim.py`)
**Method:** displaced volume = solid volume + the sealed air (the box cavity and window-extender pockets, measured from the STEP).
Added estimated thrusters (Blue Robotics T200 data), battery and electronics. Solved for the lead needed to trim to +1 %.
**Results:**
- About 12.8 L displaced, so the vehicle needs about 1.2 kg of lead. Weight in air after trim is about 12.7 kg.
- **Key insight:** once a sub is trimmed near neutral, its weight in air is set by its *volume*, not its wall thickness.
  Thinning walls only trades aluminum for lead. The way to save weight is to shrink the box.
- CB is only 3.6 mm above CG for the bare structure, and 12-16 mm with ballast. That gives weak self-righting (about 0.3 N*m at 10 deg).

## 2026-11-25: Lid and wall pressure check (hand calc, Roark)
21.5 kPa at 2.2 m. The 6 mm lid, treated as a simply supported plate over the 293 x 163 mm gasket span, deflects 0.10 mm at 9 MPa,
a safety factor of about 21 on 5052-H32. Pressure doesn't size these walls; fabrication and the latches do.
External pressure pushes the lid onto its face gasket, so the seal tightens with depth.

## 2026-11-25: Thruster authority (`analysis/thruster_allocation.py`)
**Layout:** ArduSub "Vectored" frame (BlueROV2): 4 horizontal T200s at 45 deg, 2 vertical. It controls 5 axes, but **not pitch**.
**Method:** I placed the six T200s on the mounts in a copy assembly, scripted through the API (all bolt holes aligned, no interference).
Then I built the 6 x 6 wrench matrix and found each axis's limit with pseudo-inverse allocation and thruster saturation.
**Results:** surge 114 N, sway 109 N, heave 103 N, yaw 41 N*m, roll 16 N*m. Cruise needs only about 10 N.
**Main finding:** the horizontal thrust line sits 15 mm above the trimmed CG, but almost exactly at the CB height. With no pitch control,
full surge pitches the vehicle about 60 deg. Because the thrust line sits at the CB, **ballast can't fix it**: lowering the CG grows the
lever arm and the restoring moment equally. The thrusters themselves must move down. The verticals also sit 15 mm aft of the CG,
so heave pitches the vehicle too.

## 2026-11-26: Rev D proposal, built through the SolidWorks API
**Decision:** rework a copy of the design instead of only reporting problems. The teammate's rev C stays untouched.
**Method:** copied the CAD set to `BENTO_REV-D_proposal` and repointed every reference to the copies (`ReplaceReferencedDocument`).
`rev_d_changes.py` then edits sketch and feature dimensions, rebuilds, and runs interference detection. The survey and analysis run on the result.
Each change is one parameter, so the team can rerun it with new numbers.
**Lesson learned:** Pack and Go re-saved the source assembly even though it was opened read-only, and didn't repoint the copies.
Copying files and calling `ReplaceReferencedDocument` on the copies is the safe way to fork a SolidWorks design.

| Change | Rev C | Rev D |
|---|---|---|
| Horizontal T200 axes | Y 968.1 (board mid-plane) | Y 948.1. Mounts 50 mm tall, hanging 20 mm below the board |
| Vertical T200s | X 769.6 | X 754.6 (15 mm forward). Board notches driven by one new dimension |
| Lid | 6 mm, 0.92 kg | 4 mm, 0.62 kg |
| Ballast | none | 1.42 kg U-shaped lead plate between the legs, clear of the bottom camera window |
| Box/board corners | R10 fillets clip the bay walls (8 overlaps) | Dog-bone corner relief cut, no overlap |

**Results (with T200 at its real 344 g and estimated internals):**

| | Rev C (trimmed) | Rev D |
|---|---|---|
| Buoyancy reserve | +1 % (with 1.24 kg lead) | +1.2 % |
| CB above CG | 16 mm | 20 mm |
| Horizontal thrust line vs CG | 15 mm above | 1.8 mm above |
| Full-surge pitch | ~60 deg | ~5 deg |
| Verticals vs CG (fore/aft) | 15 mm aft | 2 mm |
| Full-heave pitch | ~52 deg | ~5 deg |

**Problems the checks found:**
- The 16 M4 latch screws go through the 4 mm lid, and 8 of them cut into the lid gasket. Rev C already had only 4 mm of thread engagement (less than 1.5 x the screw diameter).
  The fix needs rivet nuts, thicker pads under the latches, or through-bolts outside the gasket line. This is open, and it's the designer's call.
- In both revisions, the base board has no clearance holes for the six M5 screws on the leg corner brackets.
- The lid gasket is modeled already compressed (it overlaps the lid by about 4.2 cm^3). That's fine for CAD, but worth knowing for any seal analysis.
- The rest of the 1127 interferences are fastener threads and overlaps inside the imported Blue Robotics T200 model.

## 2026-11-26: Ballast plate mounting (caught in review)
**Problem:** Ethan noticed in a screenshot that the lead plate was floating: about 1 mm of air to each leg and no attachment. The interference check
can't catch a part that touches nothing, so a visual review mattered here.
**Fix:** two 6061-T6 unequal angles (1-1/2 x 1 x 1/8 in, 69 mm, 35 g each). Each one bolts to the leg's front rail with 2 x M4 bolts, one above the other.
The plate hangs from the angle's top flange on 4 x M5 flat-head bolts, countersunk flush, so nothing sits below the plate's underside.
The legs are 16 mm-rail frames, so a 1 x 1 in angle left no room for an M4 head. The taller leg of the angle was needed.
**Effect:** +105 g. The sub is now about 0.07 kg heavier in water (buoyancy reserve about +0.6 %, still above the 0.5 % rule).
Lead stock for 1.42 kg is 7.20 mm thick in real 11.34 g/cc lead.
**Side effect:** adding holes to BASE-LEG made the rev C corner-bracket mates re-solve 0.09 mm. That causes 2 small new overlaps, and fully defining
those mates fixes them.

## 2026-11-26: Real T200 mass, re-trim, mate clean-up
**Correction:** Blue Robotics lists the current T200 at **427 g in air and 239 g in water**. Earlier I used 344 g / 156 g from an older listing.
Each thruster is 83 g heavier in water, about 0.5 kg for all six. With the real thrusters the 1.42 kg lead plate would make the sub
**sink (about -3 %)**. Lesson: check vendor data against the current datasheet before sizing ballast. Buoyancy margins on a small sub are only a few hundred grams.
**Re-trim:** lead cut to **0.80 kg**. The U-plate became two 44 x 112 mm bars, one under each bracket, still 7.2 mm real lead so the M5 countersinks keep their depth.
The ballast centroid moved 12 mm forward. The T200s in the proposal now carry a 0.427 kg mass override, so the SolidWorks totals are right.
**Mate clean-up:** the port leg was a SolidWorks *mirror component*, which positions itself from the part's own geometry.
Adding holes to the leg moved it, and with it 24 other parts, by 0.093 mm. Fix: dissolve the mirror and give the port leg the same 3 mates as the
starboard leg. All parts are back at rev C positions, and the 2 overlaps are gone.

| Rev D (real T200, 0.80 kg lead, est. internals) | |
|---|---|
| Weight in air | 12.6 kg |
| Buoyancy reserve | +1.0 % |
| CB above CG | 16 mm |
| Horizontal thrust line vs CG | 2.3 mm below |
| Full-surge / full-heave pitch | ~8 deg / ~4 deg |
| Static trim | CG ~2.6 mm aft of CB, so ~9 deg nose-up. Fix with the internal layout (e.g. move ~1 kg of electronics ~30 mm forward) |

## 2026-11-26: Lid latch screws, board holes, final trim pass
**Lid:** the plan was M4 closed-end rivet nuts. Mapping the 16 holes showed the outer hole of every keeper sits directly over the lid gasket and
its flange, so a rivet-nut body would push into the seal. Each keeper is one strap with two fixed holes, and moving the keepers was blocked
(latch reach inward, lid edge outward). **Solution:** a 6 mm raised aluminum pad under each of the 8 keepers, with blind M4 tapped holes
(7 mm thread, 6 mm engagement with M4 x 8 screws, compared with 4 mm in rev C). Nothing touches the gasket. The lid is still ~0.2 kg lighter than rev C,
but it now has to be machined from 10 mm plate. The latches sit 6 mm higher, and the box walls get 16 blind M4 holes at the new height.
(Rev C never had latch holes in the walls; the screws ran into solid wall.)
**Base board:** the corner-bracket screws are M3, not M5. Added 6 x Ø3.4 clearance holes, so the overlaps are gone.
**Trim:** pads + screws added ~0.08 kg in water, so the lead went 0.80 -> **0.72 kg** (6.48 mm real-lead bars).

| Rev D current (est. internals) | |
|---|---|
| Buoyancy reserve | +0.9 % |
| CB above CG | 14.5 mm |
| Horizontal thrust line vs CG | 4 mm below |
| Full-surge / full-heave pitch | ~15 deg / ~6 deg |
| Static trim | CG ~3 mm aft of CB, ~12 deg nose-up |

**Takeaway:** each correction (real thruster mass, less lead, lid pads) moved the CG up a few mm. On a 12.6 kg vehicle with a GM of about 15 mm,
the internal electronics layout now matters as much as any structural change. Next step: get real internals, then do one final tune of the
two script parameters (mount drop, ballast mass) and the electronics placement for level trim.

## 2026-11-26: CFD drag and pitch, lid/gasket FEA, window and wall checks
**Question:** How much drag does REV-D have, does the flow pitch it, and will the lid, gasket, windows and walls hold at 7 ft?
**Tools:** the team only has free SolidWorks (no Simulation or Flow Simulation), so everything ran on open-source solvers: OpenFOAM (snappyHexMesh + simpleFoam,
k-omega SST), gmsh + CalculiX for the lid, and Roark plate formulas for the windows and walls. ParaView makes the pictures. The case and scripts are in `cfd/` and `fea/`.

**CFD (full vehicle, 1.7 M cells, thrusters not spinning):**

| Speed | Drag | Cd (A = 0.0645 m²) | Vertical force | Pitch moment about CG |
|---|---|---|---|---|
| 0.25 m/s | 1.70 N | 0.84 | 0.3 N down | 0.04 N·m nose-down |
| 0.5 m/s | 6.8 N | 0.85 | 1.2 N down | 0.16 N·m nose-down |
| 1.0 m/s | 27.1 N | 0.84 | 5.1 N down | 0.57 N·m nose-down |
* Cd stays about 0.84 from 0.25 to 1 m/s, so drag goes with speed squared. With 114 N of surge thrust, the top speed is about **2 m/s**.
* More than 95 % of the drag is pressure drag from the flat front face and the window bulge (red in `cfd/results/renders/*_surface_cp.png`).
* **Pitch:** the flow pushes down on the front of the vehicle (net downforce acting about 135 mm ahead of the CG), so the moment is nose-down at about 21 mm × drag.
  The horizontal T200s sit only 4 mm below the CG, which leaves about 17 mm × drag of nose-down moment against a righting moment of 1.57 N·m/rad (GM 14.5 mm):
  about **5° at 0.5 m/s and about 17° at 1 m/s**.
  **Proposed fix:** lower the horizontal thrust line to about 21 mm below the CG (another ~17 mm of mount drop). In steady cruise, thrust equals drag, so that cancels
  the hydrodynamic pitch at every speed. Not applied yet; it's Ethan's call and depends on the real internals.
* Workaround worth noting: the Ubuntu OpenFOAM v1912 build crashes in every function object, so forces are integrated from the written fields by `forces_from_fields.py`.

**Lid + gasket FEA (CalculiX, 360 k nodes):** the McMaster 4432N117 latch is rated **25 lb (111 N)**, has a fixed draw distance and does not lock.
* The lid is fine: 24 MPa peak and 0.5 mm sag at 7 ft, against 276 MPa yield.
* **The gasket gets almost no squeeze.** Latched at the surface: 2 % average and 0.6 % at the corners. At 7 ft the water adds 1.24 kN on the lid, bringing it to 5 % average,
  but the corners stay under 0.5 %. A solid 8 mm × 3 mm EPDM band needs about 7 kN for 20 % squeeze, and 8 latches give 0.9 kN.
  Because the draw is fixed, the CAD's 0.6 mm interference would either keep the latches from closing or overload them.
* **Recommendation:** a closed-cell sponge EPDM or neoprene gasket (about 20 to 40 × softer, so the same latches give 20 to 30 %), or an O-ring cord in a groove (1 to 2.5 kN).
  Assumption to confirm: gasket compression modulus 5 MPa, typical for 60A solid EPDM.

**Windows and walls (Roark, 21.5 kPa):** acrylic windows 1.2 to 1.4 MPa (SF ≥ 7 against 10 MPa long-term). Side walls at 6 mm: 7 to 8 MPa (SF ≥ 7 against 55 MPa welded 6061).
**Decision input:** 4 mm walls would still give SF ≥ 3 (15 to 18 MPa), so wall thinning is structurally fine if the weight is wanted.

**Takeaway:** the structure is strong enough; the open risks are the **seal** and the **pitch at speed**. Both have cheap fixes (gasket material, thruster mount drop).

## 2026-11-26: Sponge gasket and slotted thruster mounts (d6), report for the team
**Decision:** freeze the structure for manufacturing and leave the internals-dependent tuning to the first pool test, instead of chasing exact numbers in CAD.
* **Lid gasket:** 3.0 mm solid EPDM changed to **1/8 in (3.175 mm) closed-cell sponge** EPDM or neoprene, medium firmness. The bottom still sits on the flange,
  and the modelled compression went 0.60 to 0.78 mm (24 %). Medium sponge needs about 0.3 to 0.4 kN for 25 %, inside the 0.9 kN the 8 latches give.
  The gasket mass went 24.9 to 3.4 g. In CAD it is "Rubber" with a 150 kg/m³ override, because the custom sponge material can't load until the proposal folder is
  added to SolidWorks' material File Locations. So the mass is right but the stiffness is not.
* **Straight thruster mounts:** the 4 T200 holes became **15 mm vertical slots**: 3.4 mm wide, with the countersink kept as a chamfer so the M3 flat heads sit flush.
  The plate went from 50 to 65 mm (43.4 g each). The T200s stay at the top of the slots. The horizontal thrust line can now be set anywhere from **5.8 to 20.8 mm below the CG**,
  which covers the ~21 mm the CFD says cancels the flow-induced nose-down moment. Interference: no new pairs, even with all thrusters at the bottom of the slots.
* **Mass:** 11.036 kg to **11.050 kg**. CoM moved from (753.53, 954.20) to (753.58, 953.93) mm.
* Team report (before/after, the reasons, results, renders): https://claude.ai/artifact/TrrndNj66PSfLTW4sB5Jxu

## 2026-11-26: Thruster adapter plates replace the slotted mount (d7)
**Problem (spotted by Ethan):** the d6 slots put the T200's top and bottom holes in one column only 19 mm apart. 15 mm slots left a 0.6 mm web,
and the countersinks cut through it, so the two centre slots merged into one. The printed PET mount would have torn out. Lesson: check the web between neighbouring slots, not just the edge margins.
**Fix:** each horizontal T200 bolts to a new **82 × 36 × 5 mm 6061 adapter plate** (round countersunk M3 holes in the original diamond). The adapter clamps to the mount
with **2 × M4 × 16 pan heads + nyloc nuts through 2 vertical slots** at ±34 mm, outside the T200 foot. The mount centre is solid again, and the plate is 63 mm tall.
* Travel: 0 to 20 mm down. 5 mm up was dropped because the M4 hardware reaches the base board after about 1 mm. Thrust line: **5.7 to 25.7 mm below the CG** (CFD target about 21 mm).
* Interference: no new pairs at either end of the travel. The T200s sit 5 mm further out, so the clearance to the board went 5 → 10 mm and to the legs 17 → 22 mm.
* Hardware: **M3 × 10 flat heads** for T200-to-adapter. The 12 mm screw in the CAD runs 1.55 mm past the T200 insert.
* Mass: 11.050 → **11.235 kg** (+184 g, about 125 g in water). That uses up the +0.9 % reserve, so the lead should go from 0.72 to about **0.58 kg** (in CAD or at the pool).
