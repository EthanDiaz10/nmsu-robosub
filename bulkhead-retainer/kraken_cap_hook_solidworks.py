"""
Kraken Submersibles - Nautilus end-cap retainer hook (option A, rev A)
SolidWorks builder
=======================================================================

Builds one native, editable part:

    CapHook_A.SLDPRT    L-shaped hook that bolts to a 1" T-slot end rail and
                        presses a padded thumb screw on a hull end cap.

and, with --sub, an assembly that places all 8 hooks on the sub:

    Nautilus_CapHooks.SLDASM   the sub (as one fixed component) + 8 hooks,
                               positioned from the Nautilus 1 STEP coordinates.
                               Your sub file is referenced, not changed.

The sub uses 8 identical hooks: on each of the 2 hulls, one on the top end
rail and one on the middle end rail, at both ends. The bottom hooks are the
same part turned upside down. All dimensions below were taken from the
Nautilus 1 STEP (hull 6.5" OD, Blue Robotics 6" caps, 1" T-slot frame).

Feature tree (all editable afterwards):
    1. Hook profile   L-shaped arm + drop leg, mid-plane extrude (P["T"] thick)
    2. Foot           plate that sits flat on the rail face, mid-plane extrude
    3. Foot holes     2 clearance holes for 1/4-20 bolts into one T-slot
    4. Pad screw hole 1/4-20 clearance (or tap drill with --aluminum)

Part coordinates (mm):
    origin = centre of the T-slot rail face the foot bolts to
    +X     = outward along the hull axis (away from the frame, toward the cap)
    -Y     = toward the hull centreline  (down for a top hook; flip the part for a bottom hook)
    Z      = across the sub (sketch normal)

Requirements
------------
    Windows, SolidWorks, Python 3.8+, pywin32
    (same micromamba env as the torpedo: micromamba activate kraken-torpedo)

Run
---
    micromamba run -n kraken-torpedo python kraken_cap_hook_solidworks.py [options]

    (no options)                                            # part only, saves to .\\solidworks_cap_hook
    --sub "C:\\path\\Nautilus 1.SLDASM"                     # part + assembly on the sub
    --sub "C:\\path\\Nautilus 1.STEP"                       # same; imports the STEP first (slow, 125 MB)
    --assembly-only --sub ...                               # reuse an existing CapHook_A.SLDPRT in --out
    python kraken_cap_hook_solidworks.py --out C:\\path\\to\\folder
    python kraken_cap_hook_solidworks.py --thickness 9.525  # thinner/lighter arm (3/8")
"""

import argparse
from pathlib import Path

import pythoncom
import win32com.client

# --------------------------------------------------------------------------
# Parameters (mm)
# --------------------------------------------------------------------------
P = dict(
    T=12.7,            # hook thickness across the sub (1/2" plate)
    ARM_H=25.4,        # arm height = height of a 1" T-slot face
    FOOT_W=50.8,       # foot width along the rail
    FOOT_T=11.1,       # foot thickness (along +X): 7/16" so a 3/4" bolt + washer leaves 1/4" in the T-nut
    BOLT_SPACING=31.8, # two 1/4-20 bolts in the same slot
    BOLT_CLEAR=6.8,    # 1/4-20 clearance
    REACH=107.0,       # rail face -> farthest cap face (front acrylic caps); rear caps are 101.5
    PAD_GAP=12.6,      # cap face -> inside of drop leg
    LEG_T=19.0,        # drop-leg thickness along X (thread length for the pad screw)
    DROP=52.65,        # rail centre -> pad screw axis (puts the pad ~68 mm from cap centre)
    LEG_PAST_PAD=10.0, # leg material beyond the screw axis
    CORNER=8.0,        # inside-corner chamfer between arm and leg
    TAP_DRILL=6.6,     # pad-screw hole: 6.6 = 1/4-20 clearance, screw held by a nut on each
                       # face of the leg (3D printed hook, all Home Depot hardware);
                       # --aluminum gives 5.1 to tap 1/4-20 directly
)
COLOR = (0.88, 0.54, 0.12)  # orange, same as the 3D viewer

MM = 0.001
swDefaultTemplatePart = 8
swEndCondBlind = 0
swEndCondThroughAllBoth = 9
swEndCondMidPlane = 6
swSaveAsCurrentVersion = 0
swSaveAsOptions_Silent = 1
swAllConfiguration = 2
swSolidBody = 0
swDocPART = 1
swDocASSEMBLY = 2
swOpenDocOptions_Silent = 1
swDefaultTemplateAssembly = 9

# Hook placements in the sub's coordinates (mm), measured from the Nautilus 1 STEP.
# Hulls run along Z; Y is up. Frame end-rail faces sit at Z = +/-215.9.
HULL_X = {"Battery": 105.05, "Camera": 301.7}
RAIL_Y = {"Top": 0.0, "Bottom": -241.3}       # top end rail / middle end rail centres
RAIL_FACE_Z = 215.9

NOTHING = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def darr(values):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in values])


def com_call(obj, name, *args):
    """pywin32 late binding sometimes treats no-arg methods as properties."""
    try:
        obj._FlagAsMethod(name)
    except AttributeError:
        pass
    return getattr(obj, name)(*args)


class Part:
    """Same thin wrapper as kraken_torpedo_solidworks.py."""

    def __init__(self, sw, name):
        self.sw = sw
        self.name = name
        template = sw.GetUserPreferenceStringValue(swDefaultTemplatePart)
        self.doc = sw.NewDocument(template, 0, 0, 0)
        if self.doc is None:
            raise RuntimeError("Could not create a part. Check the default part template "
                               "in Tools > Options > Default Templates.")
        self.sk = self.doc.SketchManager
        self.fm = self.doc.FeatureManager

    def start_sketch(self, plane="Front Plane"):
        self.doc.ClearSelection2(True)
        ok = self.doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
        if not ok:
            idx = {"Front Plane": 1, "Top Plane": 2, "Right Plane": 3}[plane]
            planes = []
            f = com_call(self.doc, "FirstFeature")
            while f is not None:
                if f.GetTypeName2() == "RefPlane":
                    planes.append(f)
                f = com_call(f, "GetNextFeature")
            planes[idx - 1].Select2(False, 0)
        self.sk.InsertSketch(True)
        self.sk.AddToDB = True

    def end_sketch(self, feature_name=None):
        self.sk.AddToDB = False
        self.sk.InsertSketch(True)
        sketch = self.doc.FeatureByPositionReverse(0)
        if feature_name:
            sketch.Name = feature_name + " sketch"
        self.doc.ClearSelection2(True)
        sketch.Select2(False, 0)
        return sketch

    def line(self, a, b):
        self.sk.CreateLine(a[0] * MM, a[1] * MM, 0, b[0] * MM, b[1] * MM, 0)

    def polyline(self, pts, closed=False):
        for a, b in zip(pts, pts[1:]):
            self.line(a, b)
        if closed:
            self.line(pts[-1], pts[0])

    def rect(self, x1, y1, x2, y2):
        self.sk.CreateCornerRectangle(x1 * MM, y1 * MM, 0, x2 * MM, y2 * MM, 0)

    def circle(self, x, y, d):
        self.sk.CreateCircleByRadius(x * MM, y * MM, 0, d / 2 * MM)

    def extrude_midplane(self, name, depth, cut=False):
        if cut:
            f = self.fm.FeatureCut4(
                True, False, False, swEndCondMidPlane, swEndCondBlind, depth * MM, 0.0,
                False, False, False, False, 0.0, 0.0, False, False, False, False,
                False, True, True, True, True, False, 0, 0.0, False, False)
        else:
            f = self.fm.FeatureExtrusion2(
                True, False, False, swEndCondMidPlane, swEndCondBlind,
                depth * MM, 0.0, False, False, False, False, 0.0, 0.0,
                False, False, False, False, True, False, True, 0, 0.0, False)
        if f is None:
            raise RuntimeError(f"{self.name}: '{name}' failed.")
        f.Name = name
        return f

    def color(self, rgb):
        vals = list(self.doc.MaterialPropertyValues)
        vals[0], vals[1], vals[2] = rgb
        arr = darr(vals)
        self.doc.MaterialPropertyValues = arr
        try:
            com_call(self.doc.Extension, "SetMaterialPropertyValues", arr, swAllConfiguration, None)
        except Exception as e:
            print(f"  (doc appearance not set: {e})")
        for body in com_call(self.doc, "GetBodies2", swSolidBody, False) or ():
            body.MaterialPropertyValues2 = arr
        com_call(self.doc, "GraphicsRedraw2")

    def finish(self, out_dir):
        self.doc.ForceRebuild3(False)
        self.doc.ShowNamedView2("*Isometric", 7)
        self.doc.ViewZoomtofit2()
        path = str(Path(out_dir) / f"{self.name}.SLDPRT")
        errors = self.doc.SaveAs3(path, swSaveAsCurrentVersion, swSaveAsOptions_Silent)
        if errors:
            raise RuntimeError(f"Saving {path} failed (error code {errors}).")
        print(f"  saved {path}")
        return path


def hook_geometry():
    """Key X/Y stations of the hook profile (mm), shared with the CadQuery check."""
    h = P["ARM_H"] / 2
    x_leg0 = P["REACH"] + P["PAD_GAP"]
    x_leg1 = x_leg0 + P["LEG_T"]
    y_pad = P["DROP"]
    y_end = y_pad + P["LEG_PAST_PAD"]
    return h, x_leg0, x_leg1, y_pad, y_end


def build_hook(sw, out):
    h, x0, x1, y_pad, y_end = hook_geometry()
    c = P["CORNER"]
    ft = P["FOOT_T"]
    p = Part(sw, "CapHook_A")

    # 1. L profile on the Front plane (X outward, drop leg toward -Y).
    #    The arm starts inside the foot so the two features fuse.
    p.start_sketch("Front Plane")
    p.polyline([
        (ft / 2, h), (x1, h), (x1, -y_end), (x0, -y_end),
        (x0, -h - c), (x0 - c, -h), (ft / 2, -h),
    ], closed=True)
    p.end_sketch("Hook profile")
    p.extrude_midplane("Hook profile", P["T"])

    # 2. Foot: rectangle on the Front plane, extruded mid-plane across the sub.
    p.start_sketch("Front Plane")
    p.rect(0.0, -h, ft, h)
    p.end_sketch("Foot")
    p.extrude_midplane("Foot", P["FOOT_W"])

    # 3. Foot bolt holes along X: circles on the Right plane (sketch X = part Z).
    #    Mid-plane cut deep enough to go through the foot only.
    p.start_sketch("Right Plane")
    for z in (-P["BOLT_SPACING"] / 2, P["BOLT_SPACING"] / 2):
        p.circle(z, 0.0, P["BOLT_CLEAR"])
    p.end_sketch("Foot holes")
    p.extrude_midplane("Foot holes", 2 * ft + 0.2, cut=True)

    # 4. Pad screw tap drill through the drop leg, along X.
    #    Sketch on Right plane, cut mid-plane wide enough to span the leg.
    p.start_sketch("Right Plane")
    p.circle(0.0, -y_pad, P["TAP_DRILL"])  # Right-plane sketch Y = model Y
    p.end_sketch("Pad screw hole")
    p.extrude_midplane("Pad screw hole", 2 * (x1 + 1), cut=True)

    p.color(COLOR)
    return p.finish(out)


def byref_int():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def open_doc(sw, path):
    """Open a part/assembly, or import a STEP and save it as an assembly."""
    path = str(Path(path).resolve())
    ext = Path(path).suffix.lower()
    err, warn = byref_int(), byref_int()
    if ext == ".sldprt":
        doc = sw.OpenDoc6(path, swDocPART, swOpenDocOptions_Silent, "", err, warn)
    elif ext == ".sldasm":
        doc = sw.OpenDoc6(path, swDocASSEMBLY, swOpenDocOptions_Silent, "", err, warn)
    elif ext in (".step", ".stp"):
        print("  importing STEP (this can take a few minutes)...")
        doc = sw.LoadFile4(path, "r", NOTHING, err)
        if doc is not None:
            asm_path = str(Path(path).with_suffix(".SLDASM"))
            com_call(doc, "SaveAs3", asm_path, swSaveAsCurrentVersion, swSaveAsOptions_Silent)
            print(f"  saved imported sub as {asm_path}")
            path = asm_path
    else:
        raise RuntimeError(f"Unsupported sub file type: {path}")
    if doc is None:
        raise RuntimeError(f"Could not open {path} (error {err.value}).")
    return doc, path


def hook_transform(mu, hull_x, rail, end):
    """Place the hook: part X -> outward along the hull, part Y -> up (top) or
    down (bottom, part flipped), part Z -> across the sub. SolidWorks uses
    row vectors: the first 9 values are the images of the part X, Y, Z axes."""
    s = 1 if end == "Rear" else -1          # rear caps are at +Z in the STEP
    fy = 1 if rail == "Top" else -1
    sz = -s * fy                            # keeps it a proper rotation (det = +1)
    rot = [0, 0, s,
           0, fy, 0,
           sz, 0, 0]
    t = [hull_x * MM, RAIL_Y[rail] * MM, s * RAIL_FACE_Z * MM]
    return com_call(mu, "CreateTransform", darr(rot + t + [1.0, 0, 0, 0]))


def build_sub_assembly(sw, out, hook_path, sub_path):
    print("Opening the sub...")
    _, sub_path = open_doc(sw, sub_path)
    template = sw.GetUserPreferenceStringValue(swDefaultTemplateAssembly)
    asm = com_call(sw, "NewDocument", template, 0, 0, 0)
    if asm is None:
        raise RuntimeError("Could not create an assembly. Check the default assembly template.")
    mu = com_call(sw, "GetMathUtility")
    identity = com_call(mu, "CreateTransform",
                        darr([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]))

    def add(path, xform, label):
        comp = com_call(asm, "AddComponent5", path, 0, "", False, "", 0, 0, 0)
        if comp is None:
            raise RuntimeError(f"Could not insert {path}")
        comp.Transform2 = xform
        com_call(comp, "Select4", False, NOTHING, False)
        com_call(asm, "FixComponent")
        com_call(asm, "ClearSelection2", True)
        print(f"  placed {label}")

    add(sub_path, identity, "sub")
    for end in ("Rear", "Front"):
        for hull, x in HULL_X.items():
            for rail in ("Top", "Bottom"):
                add(hook_path, hook_transform(mu, x, rail, end), f"hook {end}/{hull}/{rail}")

    com_call(asm, "ForceRebuild3", False)
    com_call(asm, "ShowNamedView2", "*Isometric", 7)
    com_call(asm, "ViewZoomtofit2")
    path = str(Path(out) / "Nautilus_CapHooks.SLDASM")
    errors = com_call(asm, "SaveAs3", path, swSaveAsCurrentVersion, swSaveAsOptions_Silent)
    if errors:
        raise RuntimeError(f"Saving {path} failed (error code {errors}).")
    print(f"  saved {path}")


def main():
    ap = argparse.ArgumentParser(description="Build the Nautilus end-cap retainer hook in SolidWorks.")
    ap.add_argument("--out", default="solidworks_cap_hook", help="folder for the SolidWorks files")
    ap.add_argument("--thickness", type=float, help="hook thickness in mm (default 12.7)")
    ap.add_argument("--aluminum", action="store_true",
                    help="1/4-20 tap-drill pad-screw hole (5.1 mm) instead of the clearance hole")
    ap.add_argument("--sub", help="sub assembly (.SLDASM) or STEP to place the 8 hooks on")
    ap.add_argument("--assembly-only", action="store_true",
                    help="skip rebuilding the part; use CapHook_A.SLDPRT already in --out")
    args = ap.parse_args()
    if args.thickness:
        P["T"] = args.thickness
    if args.aluminum:
        P["TAP_DRILL"] = 5.1

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    print("Connecting to SolidWorks...")
    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True
    for name in ("Nautilus_CapHooks.SLDASM",) + (() if args.assembly_only else ("CapHook_A.SLDPRT",)):
        try:
            com_call(sw, "CloseDoc", name)
        except Exception:
            pass
    if args.assembly_only:
        hook_path = str(out / "CapHook_A.SLDPRT")
        open_doc(sw, hook_path)
    else:
        print("Building CapHook_A...")
        hook_path = build_hook(sw, out)
    if args.sub:
        print("Building Nautilus_CapHooks assembly...")
        build_sub_assembly(sw, out, hook_path, args.sub)
    print(f"Done. Files in {out}. Make 8 hooks.")


if __name__ == "__main__":
    main()
