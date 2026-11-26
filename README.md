# NMSU Kraken Submersibles: RoboSub tools

Scripts, analysis and results for the 2026-27 RoboSub vehicles. SolidWorks files stay in OneDrive; this repo holds
what drives and analyzes them.

| Folder | What's in it |
|---|---|
| `mini-sub/` | BENTO (competition mini sub): SolidWorks survey/export scripts, analysis scripts, results |
| `torpedo/` | Torpedo rev A: cadquery model + SolidWorks (pywin32) builder, shared body with spring/pneumatic tails |
| `bulkhead-retainer/` | Nautilus 1 end-cap hook retainer (SolidWorks builder) |

## Running the SolidWorks scripts
Windows + SolidWorks + a micromamba env with pywin32:

    micromamba create -n kraken-torpedo -f torpedo/environment.yml
    micromamba run -n kraken-torpedo python mini-sub/scripts/kraken_bento_survey.py --cad "C:\Users\ethan\OneDrive\Desktop\BENTO_REV-C"

Analysis scripts in `*/analysis/` only need Python 3 + numpy and run anywhere.
