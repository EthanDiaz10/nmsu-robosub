"""
BENTO rev C - thruster authority for the ArduSub "Vectored" frame (BlueROV2 layout, FRAME_CONFIG 1)
=================================================================================================

4 horizontal T200s on the corner mounts at 45 deg, 2 vertical T200s side by side on the curved mounts.
Thruster positions come from TOP-ASSY_BENTO_REV-C_T200.SLDASM (T200s seated on the mounts).

Body frame: origin at the trimmed CG, x forward (= -X in SolidWorks, the window side), y port/left
(= +Z... sign only matters for symmetry), z up (= +Y).

Run:  python mini-sub/analysis/thruster_allocation.py
"""
import numpy as np

# T200 @ 16 V (Blue Robotics data): max forward / reverse thrust
T_FWD, T_REV = 5.25 * 9.81, 4.10 * 9.81       # N

# trimmed vehicle (buoyancy_trim.py, lead on base legs, +1 %): SolidWorks frame, mm
CG_SW = np.array([754.5, 952.9, 1397.1])
MASS, GM = 12.69, 0.0159                      # kg, m  (CB above CG)

# prop-disk centers from TOP-ASSY_BENTO_REV-C_T200 (place_t200.py, thrusters.json, 2026-11-25)
THRUSTER_Y = 968.13         # horizontal T200 axis height = base-board mid-plane
HORIZ_XZ = [(609.7, 1195.1), (929.6, 1195.1), (609.7, 1599.1), (929.6, 1599.1)]
VERT_XZ = [(769.64, 1193.6), (769.64, 1600.6)]


def to_body(p_sw):
    d = (np.array(p_sw) - CG_SW) / 1000.0
    return np.array([-d[0], d[2], d[1]])       # x fwd, y lateral, z up


def thrusters(thr_y=THRUSTER_Y):
    T = []
    for x, z in HORIZ_XZ:
        r = to_body((x, thr_y, z))
        # vectored (ArduSub motor matrix): each axis at 45 deg, perpendicular to the line from
        # the vehicle center to its corner, so the four together give surge, sway and yaw
        d = np.array([np.sign(r[0]), -np.sign(r[1]), 0.0]) / np.sqrt(2)
        T.append((r, d))
    for x, z in VERT_XZ:
        T.append((to_body((x, thr_y, z)), np.array([0, 0, 1.0])))
    return T


def wrench_matrix(T):
    """6 x n: [Fx Fy Fz Mx My Mz] per unit thrust of each thruster."""
    return np.array([np.r_[d, np.cross(r, d)] for r, d in T]).T


def max_along(B, w):
    """Largest force/moment along unit wrench direction w, each thruster in [-T_REV, T_FWD].
    Brute force over the box corners is fine for 6 thrusters (64 corners) + LP-free projection."""
    best = 0.0
    n = B.shape[1]
    # pseudo-inverse direction, then scale until a thruster saturates
    u = np.linalg.pinv(B) @ w
    s = min((T_FWD / ui if ui > 0 else T_REV / -ui) for ui in u if abs(ui) > 1e-12)
    best = s
    return best, u * s


def main():
    T = thrusters()
    B = wrench_matrix(T)
    names = ["surge", "sway", "heave", "roll", "pitch", "yaw"]
    rank = np.linalg.matrix_rank(B, tol=1e-6)
    print(f"wrench matrix rank {rank} of 6 (vectored frame cannot command pitch)")
    print("\nauthority (pseudo-inverse allocation, first thruster to saturate sets the limit)")
    for i, n in enumerate(names):
        if n == "pitch":
            continue
        w = np.zeros(6); w[i] = 1
        mag, u = max_along(B, w)
        unit = "N*m" if i >= 3 else "N"
        side = B @ u
        print(f"  {n:6s} {mag:6.1f} {unit:3s}  parasitic pitch {side[4]:+.2f} N*m")

    print("\nparasitic pitch -> steady pitch angle (restoring = m g GM sin(theta), max "
          f"{MASS*9.81*GM:.2f} N*m)")
    print(f"  (as placed: horizontal axes {THRUSTER_Y - CG_SW[1]:+.1f} mm vs trimmed CG)")
    for dy in (-20, -10, 0, 10, round(THRUSTER_Y - CG_SW[1], 1), 20):
        Tt = thrusters(CG_SW[1] + dy)
        Bt = wrench_matrix(Tt)
        w = np.zeros(6); w[0] = 1
        mag, u = max_along(Bt, w)
        my = (Bt @ u)[4]
        Mmax = MASS * 9.81 * GM
        ang = np.degrees(np.arcsin(min(1, abs(my) / Mmax))) * np.sign(my)
        print(f"  horizontal thrusters {dy:+5.1f} mm vs CG: full surge {mag:5.1f} N -> pitch moment "
              f"{my:+5.2f} N*m -> {ang:+5.1f} deg" + ("  (saturates: tumbles)" if abs(my) >= Mmax else ""))
    vx = to_body((VERT_XZ[0][0], 0, 0))[0]
    for F in (20, 50, 2 * T_FWD):
        my = F * vx
        print(f"  verticals {abs(vx)*1000:.0f} mm {'aft' if vx < 0 else 'forward'} of CG, heave {F:5.1f} N -> pitch moment {my:+.2f} N*m "
              f"-> {np.degrees(np.arcsin(min(1, abs(my)/(MASS*9.81*GM)))):.0f} deg")


if __name__ == "__main__":
    main()
