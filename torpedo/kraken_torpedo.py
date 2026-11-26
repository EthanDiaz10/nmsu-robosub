"""
Kraken Submersibles - RoboSub ring-tail torpedo (concept rev A)
================================================================

Builds both torpedo versions as colored CadQuery assemblies:

  * spring     - tail has a retention groove (pin / sear) and a spring seat
  * pneumatic  - tail has a solid push pad for a piston and thicker fins/ring

Both share the same nose cap and forebody. Part colors:

  nose cap  (TPU)   dark gray
  forebody  (PETG)  orange
  tail      (PETG)  blue

Install
-------
    pip install cadquery

Run
---
    python kraken_torpedo.py                      # both versions, full + cutaway
    python kraken_torpedo.py --variant spring     # one version only
    python kraken_torpedo.py --no-cutaway --out my_folder

Inside CQ-editor or VS Code with the OCP CAD Viewer extension the script
also displays the assemblies (it calls show_object / ocp_vscode.show when
either is available).

Outputs (in --out, default ./torpedo_out)
----------------------------------------
    torpedo_<variant>.step            colored assembly (opens with colors in
                                      SolidWorks, Fusion 360, Onshape, FreeCAD)
    torpedo_<variant>.glb             colored mesh for quick viewing / renders
    torpedo_<variant>_cutaway.step/.glb   half-section showing the cavities
    parts/<part>.stl                  one STL per printable part, for slicing
    mass_properties.json              volumes, masses, ballast, CG and CB

All dimensions are in millimetres, x = 0 at the nose tip, x increasing aft.
Masses assume 100% solid PETG walls with the internal cavities printed sealed;
weigh the first print and trim the nose ballast.
"""

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

# --------------------------------------------------------------------------
# Parameters (mm). Change these and re-run.
# --------------------------------------------------------------------------
P = dict(
    L_TOTAL=150.0,      # overall length; RoboSub limit is 152 mm (6.0 in)
    D_BODY=25.0,        # body diameter
    NOSE_L=32.0,        # elliptical nose length
    CAP_L=8.0,          # soft TPU tip cap length
    POCKET_D=14.0,      # ballast pocket diameter (opens under the cap)
    POCKET_END=40.0,    # ballast pocket runs from CAP_L back to this x
    PLUG_L=4.0,         # cap plug length that sits in the pocket
    CYL_END=115.0,      # forebody / tail joint
    SOCKET_D=14.0,      # tail spigot socket diameter
    SOCKET_DEPTH=10.0,
    WALL=2.0,           # forebody wall around the sealed cavity
    VOID_START=44.0,    # sealed buoyancy cavity in forebody
    VOID_END=97.0,
    BOATTAIL_START=8.0, # straight length of tail before the taper (from CYL_END)
    TAIL_D=16.0,        # diameter at the tail face
    RING_OD=38.0,       # ring outer diameter; RoboSub limit is 51 mm (2.0 in)
    RING_L=18.0,        # ring chord length
    GROOVE_X=119.0,     # spring tail: retention groove position from tip
    GROOVE_W=2.5,
    GROOVE_DEPTH=1.5,
    SEAT_D=9.0,         # spring tail: spring seat diameter
    SEAT_DEPTH=4.0,
    PAD_D=20.0,         # pneumatic tail: push pad diameter
    PAD_T=3.0,
    M3_CLEAR=3.4,       # axial M3 screw clearance hole
    INSERT_PILOT=4.0,   # heat-set insert pilot in forebody
    TAIL_VOID=(123.0, 140.0),  # sealed annular cavity in the boattail
)

# Per-variant structural differences
VARIANT = {
    "spring":    dict(fin_t=1.6, ring_t=1.6),
    "pneumatic": dict(fin_t=2.0, ring_t=2.0),
}

# Densities (g/cm^3)
RHO_PETG = 1.27
RHO_TPU = 1.21
RHO_WATER = 1.00          # pool is fresh water
NEG_BUOYANCY_G = 3.0      # target: this many grams heavier than neutral

# Part colors (RGBA, 0-1)
COLORS = {
    "nose_cap": cq.Color(0.23, 0.25, 0.27, 1.0),   # dark gray
    "forebody": cq.Color(0.85, 0.38, 0.11, 1.0),   # orange
    "tail":     cq.Color(0.18, 0.42, 0.60, 1.0),   # blue
}

R = P["D_BODY"] / 2


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def revolve_profile(pts):
    """Revolve an (x, r) profile 360 degrees about the X axis."""
    return cq.Workplane("XY").polyline(pts).close().revolve(360, (0, 0, 0), (1, 0, 0))


def disk(x0, length, d):
    """Solid cylinder on the X axis from x0 to x0 + length."""
    return cq.Workplane("YZ").workplane(offset=x0).circle(d / 2).extrude(length)


def tube(x0, length, od, id_):
    return cq.Workplane("YZ").workplane(offset=x0).circle(od / 2).circle(id_ / 2).extrude(length)


def nose_radius(x):
    """Elliptical nose: r = R * sqrt(1 - ((NOSE_L - x) / NOSE_L)^2)."""
    n = P["NOSE_L"]
    return R * math.sqrt(max(0.0, 1 - ((n - x) / n) ** 2))


def boattail_radius(x):
    x0 = P["CYL_END"] + P["BOATTAIL_START"]
    return R - (R - P["TAIL_D"] / 2) * (x - x0) / (P["L_TOTAL"] - x0)


# --------------------------------------------------------------------------
# Parts
# --------------------------------------------------------------------------
def outer_forward_solid():
    """Nose + cylindrical body envelope, tip to CYL_END."""
    pts = [(0.0, 0.0)]
    n = 48
    for i in range(1, n + 1):
        x = P["NOSE_L"] * i / n
        pts.append((x, nose_radius(x)))
    pts += [(P["CYL_END"], R), (P["CYL_END"], 0.0)]
    return revolve_profile(pts)


def build_nose_cap():
    """Soft TPU tip; its plug closes the ballast pocket."""
    env = outer_forward_solid()
    cap = env.intersect(disk(-1, P["CAP_L"] + 1, 100))
    cap = cap.union(disk(P["CAP_L"], P["PLUG_L"], P["POCKET_D"] - 0.4))
    return cap


def forebody_cavities():
    pocket = disk(P["CAP_L"], P["POCKET_END"] - P["CAP_L"], P["POCKET_D"])
    void = disk(P["VOID_START"], P["VOID_END"] - P["VOID_START"], P["D_BODY"] - 2 * P["WALL"])
    return pocket, void


def build_forebody():
    env = outer_forward_solid()
    fb = env.cut(disk(-1, P["CAP_L"] + 1, 100))
    pocket, void = forebody_cavities()
    fb = fb.cut(pocket).cut(void)
    # tail socket + heat-set insert pilot
    sock_x = P["CYL_END"] - P["SOCKET_DEPTH"]
    fb = fb.cut(disk(sock_x, P["SOCKET_DEPTH"] + 1, P["SOCKET_D"]))
    fb = fb.cut(disk(sock_x - 6, 6.1, P["INSERT_PILOT"]))
    return fb


def tail_cavity():
    a, b = P["TAIL_VOID"]
    return revolve_profile([(a, 3.5), (a, boattail_radius(a) - 1.6),
                            (b, boattail_radius(b) - 1.6), (b, 3.5)])


def build_tail(variant):
    v = VARIANT[variant]
    L, cyl = P["L_TOTAL"], P["CYL_END"]
    t = revolve_profile([(cyl, 0), (cyl, R), (cyl + P["BOATTAIL_START"], R),
                         (L, P["TAIL_D"] / 2), (L, 0)])
    # spigot into the forebody socket (0.15 mm radial clearance)
    t = t.union(disk(cyl - P["SOCKET_DEPTH"] + 0.5, P["SOCKET_DEPTH"] - 0.5, P["SOCKET_D"] - 0.3))
    # ring
    ring_x = L - P["RING_L"]
    t = t.union(tube(ring_x, P["RING_L"], P["RING_OD"], P["RING_OD"] - 2 * v["ring_t"]))
    # four fins in an X pattern, same chord as the ring
    fin_span = P["RING_OD"] / 2 - v["ring_t"] / 2
    for ang in (45, 135, 225, 315):
        fin = (cq.Workplane("XY")
               .box(P["RING_L"], fin_span, v["fin_t"], centered=(False, False, True))
               .translate((ring_x, 0, 0))
               .rotate((0, 0, 0), (1, 0, 0), ang))
        t = t.union(fin)

    if variant == "pneumatic":
        t = t.union(disk(L - P["PAD_T"], P["PAD_T"], P["PAD_D"]))

    # sealed annular cavity keeps the tail light (moves CG forward)
    t = t.cut(tail_cavity())
    # axial M3 screw hole
    t = t.cut(disk(cyl - P["SOCKET_DEPTH"], L, P["M3_CLEAR"]))

    if variant == "spring":
        t = t.cut(disk(L - P["SEAT_DEPTH"], P["SEAT_DEPTH"] + 1, P["SEAT_D"]))           # spring seat
        t = t.cut(tube(P["GROOVE_X"], P["GROOVE_W"], P["D_BODY"] + 2,
                       P["D_BODY"] - 2 * P["GROOVE_DEPTH"]))                             # retention groove
    else:
        t = t.cut(disk(L - P["PAD_T"], P["PAD_T"] + 1, 6.0))                             # screw head counterbore
    return t


# --------------------------------------------------------------------------
# Mass properties
# --------------------------------------------------------------------------
def vol_cx(wp):
    s = wp.val()
    return s.Volume() / 1000.0, s.Center().x     # cm^3, mm


def mass_properties(parts, variant):
    cap, fb, tail = parts["nose_cap"], parts["forebody"], parts["tail"]
    m = mx = 0.0
    disp = dx = 0.0
    for wp, rho in ((cap, RHO_TPU), (fb, RHO_PETG), (tail, RHO_PETG)):
        V, cx = vol_cx(wp)
        m += V * rho; mx += V * rho * cx
        disp += V; dx += V * cx
    # sealed cavities displace water too
    pocket, void = forebody_cavities()
    for wp in (void, tail_cavity()):
        V, cx = vol_cx(wp)
        disp += V; dx += V * cx
    # ballast pocket (minus the cap plug) is filled with ballast + epoxy
    Vp, _ = vol_cx(pocket)
    v_plug = math.pi * ((P["POCKET_D"] - 0.4) / 2) ** 2 * P["PLUG_L"] / 1000
    v_ballast_space = Vp - v_plug
    bx = (P["CAP_L"] + P["PLUG_L"] + P["POCKET_END"]) / 2
    disp += v_ballast_space; dx += v_ballast_space * bx

    total = disp * RHO_WATER + NEG_BUOYANCY_G
    ballast = total - m
    cg = (mx + ballast * bx) / total
    cb = dx / disp
    bb = cq.Workplane().add(cap.val()).add(fb.val()).add(tail.val()).combine().val().BoundingBox()
    return dict(
        variant=variant,
        length_mm=round(bb.xlen, 1),
        max_diameter_mm=round(max(bb.ylen, bb.zlen), 1),
        displaced_volume_cm3=round(disp, 1),
        printed_mass_g=round(m, 1),
        nose_ballast_g=round(ballast, 1),
        ballast_pocket_cm3=round(v_ballast_space, 2),
        total_mass_g=round(total, 1),
        in_water_g=f"{NEG_BUOYANCY_G:.1f} heavy",
        cg_from_tip_mm=round(cg, 1),
        cb_from_tip_mm=round(cb, 1),
        cg_ahead_of_cb_mm=round(cb - cg, 1),
        within_robosub_envelope=bb.xlen <= 152.4 and max(bb.ylen, bb.zlen) <= 50.8,
    )


# --------------------------------------------------------------------------
# Assemblies and export
# --------------------------------------------------------------------------
def build_parts(variant):
    return {"nose_cap": build_nose_cap(), "forebody": build_forebody(), "tail": build_tail(variant)}


def half_section(wp):
    """Remove the +Z half so the inside is visible."""
    return wp.cut(cq.Workplane("XY").box(400, 200, 200, centered=(True, True, False)))


def make_assembly(parts, variant, cutaway=False):
    name = f"torpedo_{variant}" + ("_cutaway" if cutaway else "")
    assy = cq.Assembly(name=name)
    for pname, wp in parts.items():
        assy.add(half_section(wp) if cutaway else wp, name=pname, color=COLORS[pname])
    return assy


def export_assembly(assy, out, stem):
    assy.export(str(out / f"{stem}.step"))
    try:
        assy.export(str(out / f"{stem}.glb"))
    except Exception as e:  # older CadQuery without glTF export
        print(f"  (skipped {stem}.glb: {e})")


def side_by_side(assys):
    """Place assemblies 60 mm apart in Y so they don't overlap in a viewer."""
    scene = cq.Assembly(name="torpedoes")
    for i, a in enumerate(assys):
        scene.add(a, loc=cq.Location(cq.Vector(0, 60 * i, 0)))
    return scene


def try_show(objs):
    """Display in CQ-editor or the VS Code OCP CAD Viewer when available."""
    objs = [side_by_side(objs)]
    try:
        show_object  # noqa: F821  (defined by CQ-editor)
        for o in objs:
            show_object(o)  # noqa: F821
        return
    except NameError:
        pass
    try:
        from ocp_vscode import show
        show(*objs)
    except Exception:
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the Kraken ring-tail torpedo.")
    ap.add_argument("--variant", choices=["spring", "pneumatic", "both"], default="both")
    ap.add_argument("--out", default="torpedo_out")
    ap.add_argument("--no-cutaway", action="store_true", help="skip the half-section models")
    ap.add_argument("--no-stl", action="store_true", help="skip per-part STL files")
    args = ap.parse_args(argv)

    out = Path(args.out)
    (out / "parts").mkdir(parents=True, exist_ok=True)
    variants = ["spring", "pneumatic"] if args.variant == "both" else [args.variant]

    props, shown = {}, []
    for v in variants:
        print(f"Building {v} torpedo...")
        parts = build_parts(v)
        assy = make_assembly(parts, v)
        export_assembly(assy, out, f"torpedo_{v}")
        shown.append(assy)
        if not args.no_cutaway:
            export_assembly(make_assembly(parts, v, cutaway=True), out, f"torpedo_{v}_cutaway")
        if not args.no_stl:
            for pname, wp in parts.items():
                fname = f"{pname}_{v}.stl" if pname == "tail" else f"{pname}.stl"
                cq.exporters.export(wp, str(out / "parts" / fname), tolerance=0.05, angularTolerance=0.1)
        props[v] = mass_properties(parts, v)
        for k, val in props[v].items():
            print(f"  {k:26s} {val}")

    (out / "mass_properties.json").write_text(json.dumps(props, indent=2))
    print(f"Done. Files in {out.resolve()}")
    try_show(shown)


if __name__ == "__main__":
    main()
elif "show_object" in globals():   # running inside CQ-editor
    show_object(side_by_side([make_assembly(build_parts(_v), _v)  # noqa: F821
                              for _v in ("spring", "pneumatic")]), name="torpedoes")
