"""
BENTO rev C - buoyancy, trim and stability estimate
===================================================

Inputs
  * mini-sub/data/survey_revC_structure.json  (from scripts/kraken_bento_survey.py)
    -> structure mass, center of gravity, solid volume
  * enclosed air: the electronics bay cavity + the two window-extender pockets,
    measured from the STRUCTURE-ASSY STEP (boxes below, assembly frame, mm)
  * estimates for everything not in STRUCTURE-ASSY yet (thrusters, battery, electronics)
    -> edit EXTRA below when real numbers exist

Frame (SolidWorks assembly): +Y is up. Window on the -X face looks forward (assumed), so X = fore/aft.

Run:  python mini-sub/analysis/buoyancy_trim.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SURVEY = HERE.parent / "data" / "survey_revC_structure.json"

RHO_WATER = 997.0      # kg/m^3, fresh pool water
RHO_LEAD = 11340.0
TARGET_RESERVE = 0.01  # aim for +1 % positive; rules minimum is 0.5 %

# solid-material centroid from the STEP (survey gives the CoM, not the volume centroid)
SOLID_CENTROID = np.array([762.83, 965.84, 1397.11])

# enclosed air (mm). cavity = inside faces of the 6 mm walls, 8 mm bottom plate top to lid underside
CAVITY = ((601.2, 897.1, 1312.1), (901.2, 1047.1, 1482.1))
CAVITY_PARTS_CM3 = 151.1 + 61.1 + 15.0          # battery partition, gasket flange, lid gasket (inside part)
EXTENDER_POCKETS = [                               # (air cm3, centroid mm)
    (92.3, (585.2, 927.1, 1397.1)),                # side (-X) window extender
    (92.3, (641.2, 879.1, 1397.1)),                # bottom window extender
]

# things not in STRUCTURE-ASSY: (name, mass kg, displaced volume cm3, position mm)
T200 = (0.344, 188.0)   # Blue Robotics: 344 g in air, 156 g in water
THRUSTER_XZ = [(609.7, 1195.1), (929.6, 1195.1), (609.7, 1599.1), (929.6, 1599.1), (769.64, 1600.6), (769.64, 1193.6)]  # from TOP-ASSY_..._T200
EXTRA = [(f"T200 #{i+1}", *T200, (x, 968, z)) for i, (x, z) in enumerate(THRUSTER_XZ)] + [
    ("battery (est. 4S 5 Ah LiPo)", 0.60, 0.0, (871, 925, 1397)),   # inside hull: no extra volume
    ("electronics + wiring (est.)", 1.00, 0.0, (720, 945, 1397)),
]


def box_vol_centroid(lo, hi):
    lo, hi = np.array(lo), np.array(hi)
    return float(np.prod(hi - lo)) / 1000.0, (lo + hi) / 2


def totals(masses, vols):
    M = sum(m for m, _ in masses)
    CG = sum(m * np.array(p) for m, p in masses) / M
    V = sum(v for v, _ in vols)
    CB = sum(v * np.array(p) for v, p in vols) / V
    return M, CG, V, CB


def report(tag, M, CG, V, CB):
    B = V * RHO_WATER / 1e6
    gm = CB[1] - CG[1]
    print(f"\n[{tag}]")
    print(f"  weight in air      {M:6.2f} kg")
    print(f"  buoyancy           {B:6.2f} kg   ({V/1000:.2f} L displaced)")
    print(f"  net                {B-M:+6.2f} kg  ({(B-M)/M*100:+.1f} % of mass)")
    print(f"  CB above CG        {gm:6.1f} mm")
    print(f"  CG - CB  X / Z     {CG[0]-CB[0]:+6.1f} / {CG[2]-CB[2]:+6.1f} mm")
    print(f"  righting moment    {M*9.81*gm/1000*np.sin(np.radians(10)):.3f} N*m at 10 deg heel")
    return B


def main():
    s = json.loads(SURVEY.read_text())
    m = s["mass"]
    M0, CG0 = m["mass_kg"], np.array(m["center_of_mass_mm"])
    Vs = m["volume_cm3"]

    cav_v, cav_c = box_vol_centroid(*CAVITY)
    vols = [(Vs, SOLID_CENTROID), (cav_v - CAVITY_PARTS_CM3, cav_c)] + list(EXTENDER_POCKETS)
    masses = [(M0, CG0)]
    report("structure only (STRUCTURE-ASSY as modeled)", *totals(masses, vols))

    for _, mk, vk, p in EXTRA:
        masses.append((mk, p))
        if vk:
            vols.append((vk, p))
    M, CG, V, CB = totals(masses, vols)
    B = report("+ 6 T200 + estimated battery/electronics", M, CG, V, CB)

    for y_lead in (900.0, 860.0):        # inside on the bottom plate / under the box on the base legs
        mL = 0.0
        for _ in range(30):              # lead adds its own (small) volume
            vL = mL / RHO_LEAD * 1e6
            mL = (V + vL) * RHO_WATER / 1e6 / (1 + TARGET_RESERVE) - M
        xL = (CB[0] * (M + mL) - CG[0] * M) / mL     # puts the CG under the CB fore/aft
        vL = mL / RHO_LEAD * 1e6
        tot = totals(masses + [(mL, (xL, y_lead, 1397))], vols + [(vL, (xL, y_lead, 1397))])
        report(f"+ {mL:.2f} kg lead at Y={y_lead:.0f}, X={xL:.0f} (trimmed to +{TARGET_RESERVE*100:.0f} %)", *tot)


if __name__ == "__main__":
    main()
