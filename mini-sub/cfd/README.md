# BENTO REV-D: CFD drag and pitch moment (OpenFOAM)

Steady RANS (simpleFoam, k-omega SST, wall functions) on the full REV-D vehicle: structure, electronics bay, latches, lead plate and 6 T200s,
with thrusters not spinning. Water at 20 °C (rho 998.2, nu 1.004e-6).

| Speed | Drag | Cd (A = 0.0645 m²) | Vertical force | Pitch moment about CG |
|---|---|---|---|---|
| 0.25 m/s | 1.70 N | 0.84 | 0.3 N down | 0.04 N·m nose-down |
| 0.5 m/s | 6.8 N | 0.85 | 1.2 N down | 0.16 N·m nose-down |
| 1.0 m/s | 27.1 N | 0.84 | 5.1 N down | 0.57 N·m nose-down |

Renders are in `results/renders/`.

## Pipeline
1. **Geometry**: export `05_TOP-ASSY_REV-D_T200_full-vehicle.step` from SolidWorks, then
   `python step_to_stl.py <step> bento.stl`. This uses cadquery-ocp, drops fasteners smaller than 1.5 cm³ or 40 mm, shifts the CG to the origin and converts mm to m.
   The ready-made STL is in `case/constant/triSurface/bento.stl.gz` (`gunzip` it first).
2. **Mesh**: `blockMesh`, `decomposePar`, `mpirun -np 4 snappyHexMesh -parallel -overwrite`, then `reconstructParMesh -constant`.
   This gives about 1.7 M cells, surface refinement level 3 to 4 (about 3 mm cells on the body), and a wake box to 1.3 m downstream.
3. **Solve**: `./run_case.sh <U> <name> [iters]`. It copies the case, sets the inlet and turbulence, and runs simpleFoam on 4 cores (about 40 min for 800 iterations).
4. **Forces**: `foamFormatConvert -constant -noZero -latestTime`, then `python3 forces_from_fields.py <name> latest <U>`.
   The Ubuntu `openfoam` package (v1912) crashes in every function object (`sha1` digest error), so forces are integrated from the written fields instead:
   pressure × face area, plus wall shear from the wall-function nut.
5. **Pictures**: `xvfb-run -a pvbatch render_cfd.py <name> <U> <prefix>`.

Coordinates: +X is the flow direction (the vehicle moves toward -X, the window end), +Y is up, and +Z is lateral. A positive Mz is nose-down.

## Caveats
* Viscous drag is under-predicted (about 0.2 N at 1 m/s). The inlet turbulence is low and many wall faces have y+ < 11, so the boundary layer is close to laminar.
  A flat-plate estimate adds about 0.5 N at 0.5 m/s. The pressure drag (more than 95 % of the total) dominates either way.
* Thrusters are modelled as stationary solid ducts. Real prop wash changes the wake behind the horizontal thrusters.
* No free surface, and no pool walls or floor.
