"""
Kraken Submersibles - mini sub (BENTO rev C) analysis survey
=============================================================

Opens STRUCTURE-ASSY_BENTO_REV-C.SLDASM read-only with your SolidWorks and writes
everything the hydro/structural analysis needs into <cad>\\analysis_export:

    STRUCTURE-ASSY_BENTO_REV-C.STEP   whole assembly, positioned (for buoyancy / CB / drag geometry)
    parts\\<part>.STEP                 one STEP per unique part
    survey.json                       assembly mass, volume, center of mass, inertia, bounding box;
                                      every component instance with its file, material, density,
                                      mass, volume, own center of mass, bounding box and 4x4 transform
                                      (thrusters included, so the thrust axes can be worked out)

Nothing in the CAD folder is changed: files are opened read-only and exported as copies.

Run (same micromamba env as the rev B export script):
    micromamba run -n kraken-torpedo python "C:\\Users\\ethan\\OneDrive\\Desktop\\BENTO_REV-C\\kraken_bento_survey.py"
Options:
    --asm OTHER.SLDASM     survey a different assembly in the folder (e.g. TOP-ASSY_BENTO_REV-C.SLDASM)
    --no-step              skip the STEP exports (json only, much faster)
"""

import argparse
import json
import traceback
from pathlib import Path

import pythoncom
import win32com.client

HERE = Path(__file__).resolve().parent
DEFAULT_ASM = "STRUCTURE-ASSY_BENTO_REV-C.SLDASM"

swDocPART, swDocASSEMBLY = 1, 2
swOpenDocOptions_Silent, swOpenDocOptions_ReadOnly = 1, 2
swSaveAsCurrentVersion, swSaveAsOptions_Silent, swSaveAsOptions_Copy = 0, 1, 2


def get(obj, name, *args):
    """Call an API member whether pywin32 exposes it as a method or a property."""
    v = getattr(obj, name)
    if args:
        return v(*args)
    if callable(v) and not isinstance(v, win32com.client.CDispatch):
        return v()
    return v


def byref_int():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def open_doc(sw, path, doc_type):
    err, warn = byref_int(), byref_int()
    model = sw.OpenDoc6(str(path), doc_type,
                        swOpenDocOptions_Silent | swOpenDocOptions_ReadOnly, "", err, warn)
    if model is None:
        raise RuntimeError(f"OpenDoc6 failed for {path} (error {err.value})")
    return model


def export_step(model, out_path):
    return model.SaveAs3(str(out_path), swSaveAsCurrentVersion,
                         swSaveAsOptions_Silent | swSaveAsOptions_Copy) == 0


def r(v, n=6):
    return None if v is None else round(float(v), n)


def mass_props(model):
    mp = get(model.Extension, "CreateMassProperty")
    try:
        mp.UseSystemUnits = True          # kg, m, m^3
    except Exception:
        pass
    out = {
        "mass_kg": r(mp.Mass),
        "volume_cm3": r(mp.Volume * 1e6, 3),
        "surface_area_cm2": r(mp.SurfaceArea * 1e4, 2),
        "center_of_mass_mm": [r(c * 1000, 3) for c in mp.CenterOfMass],
    }
    try:
        out["density_kg_m3"] = r(mp.Density, 1)
    except Exception:
        pass
    try:   # principal moments + axes at the CoM
        out["principal_moments_kg_m2"] = [r(x, 8) for x in mp.PrincipleMomentsOfInertia]
        out["principal_axes"] = [r(x, 6) for x in mp.PrincipleAxesOfInertia(0)] + \
                                [r(x, 6) for x in mp.PrincipleAxesOfInertia(1)] + \
                                [r(x, 6) for x in mp.PrincipleAxesOfInertia(2)]
    except Exception:
        pass
    try:   # inertia tensor about the CoM, output-coordinate aligned (0 = at CoM)
        out["inertia_at_com_kg_m2"] = [r(x, 8) for x in mp.GetMomentOfInertia(0)]
    except Exception:
        pass
    return out


def material_of(doc):
    try:
        return doc.MaterialIdName           # "db|name|id"; empty when none assigned
    except Exception:
        return None


def comp_record(comp):
    rec = {"name": comp.Name2, "file": Path(get(comp, "GetPathName")).name}
    try:
        rec["suppressed"] = bool(get(comp, "IsSuppressed"))
    except Exception:
        pass
    try:
        rec["transform"] = [r(x, 9) for x in comp.Transform2.ArrayData]   # 9 rot, 3 trans (m), scale, ...
    except Exception:
        pass
    try:
        b = list(comp.GetBox(False, False))
        rec["box_mm"] = [r(x * 1000, 3) for x in b]      # xmin ymin zmin xmax ymax zmax, assembly frame
    except Exception:
        pass
    try:
        doc = get(comp, "GetModelDoc2")
        if doc is not None and rec["file"].lower().endswith(".sldprt"):
            rec["material"] = material_of(doc)
    except Exception:
        pass
    try:   # this instance's mass properties in assembly coordinates
        mp = comp.GetModelDoc2().Extension.CreateMassProperty()
        rec["mass_kg"] = r(mp.Mass)
        rec["volume_cm3"] = r(mp.Volume * 1e6, 3)
        rec["density_kg_m3"] = r(mp.Density, 1)
        c = list(mp.CenterOfMass)                      # part frame, m
        t = list(comp.Transform2.ArrayData)
        R, T = t[:9], t[9:12]
        w = [R[0] * c[0] + R[3] * c[1] + R[6] * c[2] + T[0],
             R[1] * c[0] + R[4] * c[1] + R[7] * c[2] + T[1],
             R[2] * c[0] + R[5] * c[1] + R[8] * c[2] + T[2]]
        rec["center_of_mass_mm"] = [r(x * 1000, 3) for x in w]
    except Exception as e:
        rec["mass_error"] = str(e)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cad", default=str(HERE))
    ap.add_argument("--asm", default=DEFAULT_ASM)
    ap.add_argument("--out", default=None, help="default: <cad>\\analysis_export")
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()

    cad = Path(a.cad)
    out = Path(a.out) if a.out else cad / "analysis_export"
    (out / "parts").mkdir(parents=True, exist_ok=True)

    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True

    asm_path = cad / a.asm
    print("opening", asm_path)
    model = open_doc(sw, asm_path, swDocASSEMBLY)
    survey = {"assembly": asm_path.name}
    try:
        try:
            model.ResolveAllLightWeightComponents(False)
        except Exception:
            pass
        try:
            get(model, "ForceRebuild3", False)
        except Exception:
            pass
        try:
            survey["config"] = get(model.ConfigurationManager, "ActiveConfiguration").Name
        except Exception:
            pass
        try:
            survey["units"] = "mm, kg (SolidWorks system units converted)"
            survey["mass"] = mass_props(model)
        except Exception as e:
            survey["mass_error"] = str(e)
        try:
            b = list(get(model, "GetBox", 0))
            survey["box_mm"] = [r(x * 1000, 3) for x in b]
        except Exception as e:
            survey["box_error"] = str(e)

        comps = get(model, "GetComponents", False) or []
        print(f"{len(comps)} components")
        survey["components"] = []
        for c in comps:
            try:
                survey["components"].append(comp_record(c))
            except Exception as e:
                survey["components"].append({"name": str(c.Name2), "error": str(e)})

        if not a.no_step:
            print("exporting assembly STEP ...")
            survey["asm_step_ok"] = export_step(model, out / (asm_path.stem + ".STEP"))
    finally:
        (out / "survey.json").write_text(json.dumps(survey, indent=2))

    if not a.no_step:
        done = set()
        for rec in survey.get("components", []):
            f = rec.get("file", "")
            if not f.lower().endswith(".sldprt") or f in done:
                continue
            done.add(f)
            print("part STEP", f)
            try:
                pm = open_doc(sw, cad / f, swDocPART)
                try:
                    export_step(pm, out / "parts" / (Path(f).stem + ".STEP"))
                finally:
                    sw.CloseDoc(get(pm, "GetTitle"))
            except Exception:
                traceback.print_exc()

    try:
        sw.CloseDoc(get(model, "GetTitle"))
    except Exception:
        pass
    m = survey.get("mass", {})
    print(f"\nDone -> {out}\n  mass {m.get('mass_kg')} kg, CoM {m.get('center_of_mass_mm')} mm, "
          f"box {survey.get('box_mm')}")


if __name__ == "__main__":
    main()
