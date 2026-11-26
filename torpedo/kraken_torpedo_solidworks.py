"""
Kraken Submersibles - RoboSub ring-tail torpedo (concept rev A)
SolidWorks builder
================================================================

Drives SolidWorks through its API and builds native, editable parts:

    Torpedo_NoseCap.SLDPRT            TPU tip      (dark gray)
    Torpedo_Forebody.SLDPRT           PETG body    (orange)
    Torpedo_Tail_Spring.SLDPRT        PETG tail    (blue)  - groove + spring seat
    Torpedo_Tail_Pneumatic.SLDPRT     PETG tail    (blue)  - push pad, thicker fins
    Torpedo_Spring.SLDASM             cap + forebody + spring tail
    Torpedo_Pneumatic.SLDASM          cap + forebody + pneumatic tail

Each part is a short feature tree you can edit afterwards:
    Forebody : one revolve (profile includes ballast pocket, sealed cavity,
               tail socket and insert pilot)
    Tail     : revolve (outer shape + ring) -> fins (2 mid-plane extrudes)
               -> revolve cut (screw hole, sealed cavity, groove / seat)
    Nose cap : one revolve

Requirements
------------
    Windows, SolidWorks installed (any recent version), Python 3.8+
    pip install pywin32

Run
---
    python kraken_torpedo_solidworks.py                 # saves to .\\solidworks_torpedo
    python kraken_torpedo_solidworks.py --out C:\\path\\to\\folder

SolidWorks opens (or the running session is used) and you can watch the
parts being built. Dimensions are in mm in the P dictionary below, the same
values as kraken_torpedo.py (the CadQuery version). x = 0 at the nose tip,
x increases aft, and the torpedo axis is the model X axis.

After it runs, assign materials if you want SolidWorks mass properties:
PETG ~1270 kg/m^3, TPU ~1210 kg/m^3 (custom materials).
"""

import argparse
import math
from pathlib import Path

import pythoncom
import win32com.client

# --------------------------------------------------------------------------
# Parameters (mm) - keep in sync with kraken_torpedo.py
# --------------------------------------------------------------------------
P = dict(
    L_TOTAL=150.0, D_BODY=25.0, NOSE_L=32.0, CAP_L=8.0,
    POCKET_D=14.0, POCKET_END=40.0, PLUG_L=4.0,
    CYL_END=115.0, SOCKET_D=14.0, SOCKET_DEPTH=10.0,
    WALL=2.0, VOID_START=44.0, VOID_END=97.0,
    BOATTAIL_START=8.0, TAIL_D=16.0,
    RING_OD=38.0, RING_L=18.0,
    GROOVE_X=119.0, GROOVE_W=2.5, GROOVE_DEPTH=1.5,
    SEAT_D=9.0, SEAT_DEPTH=4.0,
    PAD_D=20.0, PAD_T=3.0,
    M3_CLEAR=3.4, INSERT_PILOT=4.0,
    TAIL_VOID=(123.0, 140.0),
)
VARIANT = {
    "Spring":    dict(fin_t=1.6, ring_t=1.6),
    "Pneumatic": dict(fin_t=2.0, ring_t=2.0),
}
# RGB 0-1, same as the CadQuery script
COLORS = {
    "NoseCap":  (0.23, 0.25, 0.27),
    "Forebody": (0.85, 0.38, 0.11),
    "Tail":     (0.18, 0.42, 0.60),
}

R = P["D_BODY"] / 2
MM = 0.001  # SolidWorks API works in metres

# SolidWorks enum values used below
swDefaultTemplatePart = 8
swDefaultTemplateAssembly = 9
swEndCondBlind = 0
swEndCondMidPlane = 6
swSaveAsCurrentVersion = 0
swSaveAsOptions_Silent = 1
swAllConfiguration = 2
swSolidBody = 0

NOTHING = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def darr(values):
    """Python list -> COM array of doubles."""
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in values])


def com_call(obj, name, *args):
    """Call a SolidWorks API method that takes no arguments (or a few).

    pywin32's late binding treats some no-argument SolidWorks methods as
    properties, so `sw.GetMathUtility()` fails with "Member not found".
    Flagging the name as a method first makes the call work either way.
    """
    try:
        obj._FlagAsMethod(name)
    except AttributeError:
        pass
    return getattr(obj, name)(*args)


def nose_r(x):
    n = P["NOSE_L"]
    return R * math.sqrt(max(0.0, 1 - ((n - x) / n) ** 2))


def boattail_r(x):
    x0 = P["CYL_END"] + P["BOATTAIL_START"]
    return R - (R - P["TAIL_D"] / 2) * (x - x0) / (P["L_TOTAL"] - x0)


# --------------------------------------------------------------------------
# Thin wrapper around a SolidWorks part document
# --------------------------------------------------------------------------
class Part:
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

    # ----- sketching (all inputs in mm, sketch on the Front plane) -----
    def start_sketch(self, plane="Front Plane"):
        self.doc.ClearSelection2(True)
        ok = self.doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
        if not ok:
            # Non-English installs name the planes differently; fall back to the
            # 1st/2nd/3rd reference plane in the tree.
            idx = {"Front Plane": 1, "Top Plane": 2, "Right Plane": 3}[plane]
            planes = []
            f = com_call(self.doc, "FirstFeature")
            while f is not None:
                if f.GetTypeName2() == "RefPlane":
                    planes.append(f)
                f = com_call(f, "GetNextFeature")
            planes[idx - 1].Select2(False, 0)
        self.sk.InsertSketch(True)
        self.sk.AddToDB = True           # no snapping / auto relations

    def end_sketch(self, feature_name=None):
        self.sk.AddToDB = False
        self.sk.InsertSketch(True)
        sketch = self.doc.FeatureByPositionReverse(0)
        if feature_name:
            sketch.Name = feature_name + " sketch"
        self.doc.ClearSelection2(True)
        sketch.Select2(False, 0)
        return sketch

    def axis(self):
        self.sk.CreateCenterLine(-5 * MM, 0, 0, (P["L_TOTAL"] + 5) * MM, 0, 0)

    def line(self, a, b):
        self.sk.CreateLine(a[0] * MM, a[1] * MM, 0, b[0] * MM, b[1] * MM, 0)

    def polyline(self, pts, closed=False):
        for a, b in zip(pts, pts[1:]):
            self.line(a, b)
        if closed:
            self.line(pts[-1], pts[0])

    def spline(self, pts):
        flat = []
        for x, y in pts:
            flat += [x * MM, y * MM, 0.0]
        self.sk.CreateSpline2(darr(flat), True)

    def rect(self, x1, y1, x2, y2):
        self.sk.CreateCornerRectangle(x1 * MM, y1 * MM, 0, x2 * MM, y2 * MM, 0)

    # ----- features -----
    def revolve(self, name, cut=False):
        f = self.fm.FeatureRevolve2(
            True, True, False, cut, False, False,
            swEndCondBlind, swEndCondBlind, 2 * math.pi, 0.0,
            False, False, 0.0, 0.0, 0, 0.0, 0.0,
            True, False, True)
        if f is None:
            raise RuntimeError(f"{self.name}: revolve '{name}' failed (open or crossing profile).")
        f.Name = name
        return f

    def extrude_midplane(self, name, thickness):
        f = self.fm.FeatureExtrusion2(
            True, False, False, swEndCondMidPlane, swEndCondBlind,
            thickness * MM, 0.0, False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, False, True,
            0, 0.0, False)
        if f is None:
            raise RuntimeError(f"{self.name}: extrude '{name}' failed.")
        f.Name = name
        return f

    # ----- appearance and saving -----
    def color(self, rgb):
        """Apply the color so it shows in SolidWorks (tested on SolidWorks 2026).

        SolidWorks 2016+ only displays colors applied as appearances, so the
        color is set at the document, display-state and body level. The body
        level is what actually renders; under pywin32 late binding IBody2
        exposes it as the MaterialPropertyValues2 property.
        """
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


# --------------------------------------------------------------------------
# Part builders. Profiles are (x, r) in mm drawn above the X axis.
# --------------------------------------------------------------------------
def build_nose_cap(sw, out):
    p = Part(sw, "Torpedo_NoseCap")
    p.start_sketch()
    p.axis()
    cap, plug_r = P["CAP_L"], (P["POCKET_D"] - 0.4) / 2
    tip = [(cap * i / 12, nose_r(cap * i / 12)) for i in range(13)]
    p.spline(tip)
    p.polyline([tip[-1], (cap, plug_r), (cap + P["PLUG_L"], plug_r),
                (cap + P["PLUG_L"], 0.0), (0.0, 0.0)])
    p.end_sketch("Nose cap")
    p.revolve("Nose cap")
    p.color(COLORS["NoseCap"])
    return p.finish(out)


def build_forebody(sw, out):
    p = Part(sw, "Torpedo_Forebody")
    p.start_sketch()
    p.axis()
    cap, n = P["CAP_L"], P["NOSE_L"]
    pr, cyl = P["POCKET_D"] / 2, P["CYL_END"]
    sock_x = cyl - P["SOCKET_DEPTH"]
    vr = R - P["WALL"]
    nose = [(cap + (n - cap) * i / 24, nose_r(cap + (n - cap) * i / 24)) for i in range(25)]
    p.spline(nose)
    # One closed outline: nose -> body -> socket -> insert pilot -> along the
    # axis -> sealed cavity -> along the axis -> ballast pocket -> front face.
    p.polyline([
        nose[-1], (cyl, R), (cyl, P["SOCKET_D"] / 2), (sock_x, P["SOCKET_D"] / 2),
        (sock_x, P["INSERT_PILOT"] / 2), (sock_x - 6, P["INSERT_PILOT"] / 2), (sock_x - 6, 0.0),
        (P["VOID_END"], 0.0), (P["VOID_END"], vr), (P["VOID_START"], vr), (P["VOID_START"], 0.0),
        (P["POCKET_END"], 0.0), (P["POCKET_END"], pr), (cap, pr), nose[0],
    ])
    p.end_sketch("Forebody")
    p.revolve("Forebody")
    p.color(COLORS["Forebody"])
    return p.finish(out)


def build_tail(sw, out, variant):
    v = VARIANT[variant]
    L, cyl = P["L_TOTAL"], P["CYL_END"]
    ring_x = L - P["RING_L"]
    ro, ri = P["RING_OD"] / 2, P["RING_OD"] / 2 - v["ring_t"]
    spig_x = cyl - P["SOCKET_DEPTH"] + 0.5
    spig_r = (P["SOCKET_D"] - 0.3) / 2
    p = Part(sw, f"Torpedo_Tail_{variant}")

    # 1. Outer shape: spigot + boattail (+ push pad), and the ring as a
    #    second closed region in the same sketch.
    p.start_sketch()
    p.axis()
    end_r = P["PAD_D"] / 2 if variant == "Pneumatic" else P["TAIL_D"] / 2
    body = [(spig_x, 0.0), (spig_x, spig_r), (cyl, spig_r), (cyl, R),
            (cyl + P["BOATTAIL_START"], R)]
    if variant == "Pneumatic":
        pad_x = L - P["PAD_T"]
        body += [(pad_x, boattail_r(pad_x)), (pad_x, end_r), (L, end_r)]
    else:
        body += [(L, end_r)]
    body += [(L, 0.0)]
    p.polyline(body, closed=True)
    p.polyline([(ring_x, ri), (ring_x, ro), (L, ro), (L, ri)], closed=True)
    p.end_sketch("Tail body and ring")
    p.revolve("Tail body and ring")

    # 2. Fins: two mid-plane plates in a + pattern, joining body and ring.
    span = ro - v["ring_t"] / 2
    for plane, label in (("Front Plane", "Fins vertical"), ("Top Plane", "Fins horizontal")):
        p.start_sketch(plane)
        p.rect(ring_x, -span, L, span)
        p.end_sketch(label)
        p.extrude_midplane(label, v["fin_t"])

    # 3. Cuts: axial M3 hole, sealed boattail cavity, and variant details.
    p.start_sketch()
    p.axis()
    a, b = P["TAIL_VOID"]
    hr = P["M3_CLEAR"] / 2
    if variant == "Spring":
        seat_x, seat_r = L - P["SEAT_DEPTH"], P["SEAT_D"] / 2
        p.polyline([(spig_x - 1, 0.0), (spig_x - 1, hr), (seat_x, hr), (seat_x, seat_r),
                    (L + 1, seat_r), (L + 1, 0.0)], closed=True)
        g0, g1 = P["GROOVE_X"], P["GROOVE_X"] + P["GROOVE_W"]
        p.polyline([(g0, R - P["GROOVE_DEPTH"]), (g0, R + 1), (g1, R + 1),
                    (g1, R - P["GROOVE_DEPTH"])], closed=True)
    else:
        cb_x = L - P["PAD_T"]
        p.polyline([(spig_x - 1, 0.0), (spig_x - 1, hr), (cb_x, hr), (cb_x, 3.0),
                    (L + 1, 3.0), (L + 1, 0.0)], closed=True)
    p.polyline([(a, 3.5), (a, boattail_r(a) - 1.6), (b, boattail_r(b) - 1.6), (b, 3.5)],
               closed=True)
    p.end_sketch("Tail cuts")
    p.revolve("Tail cuts", cut=True)

    p.color(COLORS["Tail"])
    return p.finish(out)


# --------------------------------------------------------------------------
# Assembly: every part is modelled in the same coordinates (x from the tip),
# so each component is placed with an identity transform and fixed.
# --------------------------------------------------------------------------
def build_assembly(sw, out, name, part_paths):
    template = sw.GetUserPreferenceStringValue(swDefaultTemplateAssembly)
    asm = com_call(sw, "NewDocument", template, 0, 0, 0)
    if asm is None:
        raise RuntimeError("Could not create an assembly. Check the default assembly template.")
    mu = com_call(sw, "GetMathUtility")
    identity = com_call(mu, "CreateTransform",
                        darr([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]))
    for path in part_paths:
        comp = com_call(asm, "AddComponent5", path, 0, "", False, "", 0, 0, 0)
        if comp is None:
            raise RuntimeError(f"Could not insert {path}")
        comp.Transform2 = identity
        com_call(comp, "Select4", False, NOTHING, False)
        com_call(asm, "FixComponent")
    com_call(asm, "ClearSelection2", True)
    com_call(asm, "ForceRebuild3", False)
    com_call(asm, "ShowNamedView2", "*Isometric", 7)
    com_call(asm, "ViewZoomtofit2")
    path = str(Path(out) / f"{name}.SLDASM")
    errors = com_call(asm, "SaveAs3", path, swSaveAsCurrentVersion, swSaveAsOptions_Silent)
    if errors:
        raise RuntimeError(f"Saving {path} failed (error code {errors}).")
    print(f"  saved {path}")


def close_previous_outputs(sw):
    """Close torpedo files left open by an earlier run so SaveAs can overwrite them."""
    names = ["Torpedo_NoseCap.SLDPRT", "Torpedo_Forebody.SLDPRT"]
    names += [f"Torpedo_Tail_{v}.SLDPRT" for v in VARIANT]
    names += [f"Torpedo_{v}.SLDASM" for v in VARIANT]
    for n in names:
        try:
            com_call(sw, "CloseDoc", n)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Build the Kraken torpedo in SolidWorks.")
    ap.add_argument("--out", default="solidworks_torpedo", help="folder for the SolidWorks files")
    ap.add_argument("--no-assemblies", action="store_true")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    print("Connecting to SolidWorks...")
    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True
    close_previous_outputs(sw)

    print("Building parts...")
    cap = build_nose_cap(sw, out)
    fore = build_forebody(sw, out)
    tails = {v: build_tail(sw, out, v) for v in VARIANT}

    if not args.no_assemblies:
        print("Building assemblies...")
        for v, tail in tails.items():
            build_assembly(sw, out, f"Torpedo_{v}", [cap, fore, tail])

    print(f"Done. Files in {out}")


if __name__ == "__main__":
    main()
