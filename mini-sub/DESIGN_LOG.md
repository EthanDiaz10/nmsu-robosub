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

## 2026-11-26: Rev D proposal (in progress)
**Decision:** rework a copy of the design through the SolidWorks API instead of only reporting problems. The teammate's rev C stays untouched.
Planned changes, each as a script parameter:
- Corner thruster mounts extended so the horizontal T200 axes drop 15 mm, to the CG height
- Vertical thruster mounts moved 15 mm forward, onto the CB line
- Lid 6 mm -> 4 mm (safety factor about 9, and it takes weight off the top)
- 1.2 kg lead plate low and forward on the base legs
- Check that the electronics bay box seats in the base board
- Walls kept at 6 mm (changing them would change the weld design, which is the designer's call)
