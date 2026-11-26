# Nautilus end-cap retainer hooks (option A, rev A)

Eight identical L-hooks keep the hull end caps pressed in. Each hook bolts to the outer face of a 1" T-slot end rail and pushes on the cap with a swivel-pad thumb screw. Nothing touches the acrylic tube.

## Files

| File | What it is |
|---|---|
| `kraken_cap_hook_solidworks.py` | pywin32 script that builds `CapHook_A.SLDPRT` (and, with `--sub`, the assembly on the sub) |
| `cad/CapHook_A.step` | The same hook as a STEP, from the CadQuery check |
| `renders/` | Option A vs B renders on the Nautilus 1 model |
| `nautilus_clamps.glb` | 3D scene used by the viewer |

Run with SolidWorks open:

```
cd C:\Users\ethan\Torpedo\cap_hook
micromamba run -n kraken-torpedo python kraken_cap_hook_solidworks.py --out . --sub "C:\path\to\Nautilus 1.SLDASM"
```

Without `--sub` it builds only the part. With `--sub` it also saves `Nautilus_CapHooks.SLDASM`: your sub as one fixed component plus the 8 hooks, placed from the STEP coordinates. Your sub file is referenced, not edited. Add `--assembly-only` to reuse the part you already built.

## Parts for 8 hooks (3D printed, Home Depot hardware)

| Qty | Part | Notes |
|---|---|---|
| 8 | CapHook_A, printed | PETG, 100% infill, about 84 g each (7/16" thick foot). Print lying on its side so the L is flat on the bed |
| 16 | Foot screw: 1/4"-20 x 3/4" stainless hex bolt (Everbilt 812200, 5-pack, buy 4) or, if your T-slot nuts are M6, M6 x 20 mm pan head (Everbilt 836701, 4-pack, buy 4) | Two per foot, with a 1/4" stainless flat washer under each head. 7/16" foot + washer leaves 1/4" of thread in the T-nut |
| 16 | 1" T-slot nut, 1/4"-20 | Not sold at Home Depot. Use the McMaster self-aligning nuts the frame already uses |
| 8 | 1/4"-20 x 2" stainless hex bolt (or a 1-1/2" stainless thumb screw, see note) | The push screw. Runs through the 6.6 mm hole in the drop leg |
| 16 | 1/4"-20 stainless hex nut | One on each face of the leg, tightened against it, holds the screw where you set it (Everbilt 825801 4-packs, buy 4) |
| 32 | 1/4" stainless flat washer | Under foot screw heads and under the leg nuts (Everbilt 812150 25-pack, buy 2) |
| 8 | 1/4" rubber thread protector (Everbilt 812798, 2-piece, buy 4) | Soft tip on the end of each push screw (required on the 4 front acrylic caps) |

Thumb screw note: the Everbilt 1/4"-20 x 1-1/2" stainless thumb screw reaches the front caps, but at the rear caps it only just touches, with no room for a rubber tip. Use 2" hex bolts at the rear, or everywhere.

For an aluminum hook, run the script with `--aluminum` (5.1 mm hole, tap 1/4"-20; one jam nut is enough).

## Where they go (sub coordinates from the STEP, mm)

All hooks sit on the tube centerline: battery hull X = 105.1, camera hull X = 301.7.

| Hook | Rail | Pad point | Pad radius from cap center | Pad to cap gap |
|---|---|---|---|---|
| Top, rear | Top end rail, Y 0 | Y -52.6 | 69 | 18.1 |
| Bottom, rear | Middle end rail, Y -241.3 (hook flipped) | Y -188.7 | 67 | 18.1 |
| Top, front | Top end rail | Y -52.6 | 69 | 12.6 |
| Bottom, front | Middle end rail (hook flipped) | Y -188.7 | 67 | 12.6 |

The drop leg ends 57 to 59 mm from cap center, about 5 mm outside the penetrator nuts. The STEP has no penetrators or cables, so check the rear caps by hand.

## Install

1. Cap the hull normally.
2. Slide two T-nuts into the rail face slot and bolt the hook foot on, centered on the tube.
3. Run the thumb screw in until the pad touches the cap, then add a quarter turn (about 50 to 100 N). Lock it with the jam nut.
4. Do the opposite hook on the same cap, then the other end of the hull.

To open a hull, back off the two thumb screws on that cap.
