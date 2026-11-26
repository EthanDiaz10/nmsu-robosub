"""
Kraken Submersibles - mini sub (BENTO rev B) material export
=============================================================

Opens every part and assembly in the BENTO_REV-B CAD folder with the
SolidWorks you already have, and writes:

    export\\<part>.STEP          one STEP per part  (geometry for the cut list)
    export\\<assembly>.STEP      one STEP per assembly (part positions -> weld seams)
    export\\parts.json           material, mass, volume, bounding box,
                                 sheet-metal thickness / flat-pattern size
    export\\bom.json             how many of each part each assembly uses

Nothing in your CAD folder is changed: parts are opened, read, exported as
copies, and closed without saving.

Requirements: Windows, SolidWorks, pywin32 (same micromamba env as the
torpedo scripts).

Run
---
    micromamba run -n kraken-torpedo python "C:\\Users\\ethan\\Robo-Sub\\kraken_minisub_export.py"
    micromamba run -n kraken-torpedo python kraken_minisub_export.py --cad "C:\\other\\folder"
    ... --no-step      # only parts.json / bom.json, skip STEP export
"""

import argparse
import json
import traceback
from pathlib import Path

import pythoncom
import win32com.client

# default: the BENTO folder sitting next to this script, wherever you put it
DEFAULT_CAD = str(Path(__file__).resolve().parent / "BENTO_REV-B CAD Files")

swDocPART, swDocASSEMBLY = 1, 2
swOpenDocOptions_Silent, swOpenDocOptions_ReadOnly = 1, 2
swSaveAsCurrentVersion, swSaveAsOptions_Silent, swSaveAsOptions_Copy = 0, 1, 2


def get(obj, name, *args):
    """Call a SolidWorks API member whether pywin32 exposes it as a method or a
    property (dynamic dispatch evaluates no-argument methods like GetTitle on
    attribute access, so calling the result fails with 'str' not callable)."""
    v = getattr(obj, name)
    if args:
        return v(*args)
    if callable(v) and not isinstance(v, win32com.client.CDispatch):
        return v()
    return v


def close(sw, model):
    try:
        sw.CloseDoc(get(model, "GetTitle"))
    except Exception:
        traceback.print_exc()


def byref_int():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def open_doc(sw, path, doc_type):
    err, warn = byref_int(), byref_int()
    model = sw.OpenDoc6(str(path), doc_type,
                        swOpenDocOptions_Silent | swOpenDocOptions_ReadOnly,
                        "", err, warn)
    if model is None:
        raise RuntimeError(f"OpenDoc6 failed (error {err.value})")
    return model


def export_step(model, out_path):
    # SaveAs3(name, version, options) -> 0 on success; Copy keeps the doc as-is
    rc = model.SaveAs3(str(out_path), swSaveAsCurrentVersion,
                       swSaveAsOptions_Silent | swSaveAsOptions_Copy)
    return rc == 0


def box_mm(model):
    try:
        b = list(get(model, "GetPartBox", True))
        lo, hi = b[:3], b[3:]
        return sorted([round((h - l) * 1000, 3) for l, h in zip(lo, hi)], reverse=True)
    except Exception:
        return None


def iter_features(model):
    f = get(model, "FirstFeature")
    while f is not None:
        yield f
        f = get(f, "GetNextFeature")


def sheet_metal_info(model):
    info = {}
    for f in iter_features(model):
        t = get(f, "GetTypeName2")
        if t == "SheetMetal" and "thickness_mm" not in info:
            try:
                d = get(f, "GetDefinition")
                info["thickness_mm"] = round(d.Thickness * 1000, 4)
                info["bend_radius_mm"] = round(d.BendRadius * 1000, 4)
            except Exception:
                pass
        if t == "FlatPattern":
            info["flat_feature"] = f.Name
            try:
                was_suppressed = get(f, "IsSuppressed")
                f.SetSuppression2(1, 2, None)   # unsuppress, all configs
                get(model, "EditRebuild3")
                info["flat_box_mm"] = box_mm(model)
                if was_suppressed:
                    f.SetSuppression2(0, 2, None)
                    get(model, "EditRebuild3")
            except Exception as e:
                info["flat_error"] = str(e)
    return info


def part_record(sw, path, out_dir, do_step):
    rec = {"file": path.name}
    model = open_doc(sw, path, swDocPART)
    try:
        try:
            rec["material"] = model.MaterialIdName   # "db|name|id"
        except Exception:
            rec["material"] = None
        try:
            mp = get(model.Extension, "CreateMassProperty")
            rec["mass_kg"] = round(mp.Mass, 5)
            rec["volume_cm3"] = round(mp.Volume * 1e6, 3)
            rec["surface_area_cm2"] = round(mp.SurfaceArea * 1e4, 3)
            rec["density_kg_m3"] = round(mp.Density, 1)
        except Exception as e:
            rec["mass_error"] = str(e)
        rec["box_mm"] = box_mm(model)
        rec["config"] = get(model.ConfigurationManager, "ActiveConfiguration").Name
        rec["sheet_metal"] = sheet_metal_info(model)
        if do_step:
            rec["step_ok"] = export_step(model, out_dir / (path.stem + ".STEP"))
    finally:
        close(sw, model)
    return rec


def assembly_record(sw, path, out_dir, do_step):
    model = open_doc(sw, path, swDocASSEMBLY)
    counts = {}
    try:
        try:
            model.ResolveAllLightWeightComponents(False)
        except Exception:
            pass
        comps = get(model, "GetComponents", False) or []   # all levels
        for c in comps:
            if get(c, "IsSuppressed"):
                continue
            p = get(c, "GetPathName")
            if p.lower().endswith(".sldprt"):
                n = Path(p).name
                counts[n] = counts.get(n, 0) + 1
        step_ok = export_step(model, out_dir / (path.stem + ".STEP")) if do_step else None
    finally:
        close(sw, model)
    return {"file": path.name, "parts": counts, "step_ok": step_ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cad", default=DEFAULT_CAD)
    ap.add_argument("--out", default=None, help="default: <cad>\\export")
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()

    cad = Path(a.cad)
    out = Path(a.out) if a.out else cad / "export"
    out.mkdir(parents=True, exist_ok=True)
    do_step = not a.no_step

    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True

    files = sorted(p for p in cad.iterdir() if not p.name.startswith("~$"))
    parts, boms = [], []
    for p in files:
        ext = p.suffix.lower()
        try:
            if ext == ".sldprt":
                print("part ", p.name)
                parts.append(part_record(sw, p, out, do_step))
            elif ext == ".sldasm":
                print("asm  ", p.name)
                boms.append(assembly_record(sw, p, out, do_step))
        except Exception as e:
            traceback.print_exc()
            (parts if ext == ".sldprt" else boms).append({"file": p.name, "error": str(e)})

    (out / "parts.json").write_text(json.dumps(parts, indent=2))
    (out / "bom.json").write_text(json.dumps(boms, indent=2))
    print(f"\nWrote {len(parts)} parts, {len(boms)} assemblies to {out}")


if __name__ == "__main__":
    main()
