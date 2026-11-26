# BENTO REV-D: lid, gasket, window and wall stress

## Lid + lid gasket (gmsh + CalculiX, `lid/`)
* `GEOM=<folder with the REV-D STEP exports> python3 lid_fea.py` meshes the 10 mm machined lid (4 mm plate + 6 mm keeper pads) from
  `02_LID-STACK_REV-D_asm-position.step`. It adds the 8 mm × 3 mm EPDM gasket band (modelled at its 2.4 mm CAD-squeezed height, E = 5 MPa
  compression modulus, bonded to the lid, base fixed) and writes 3 CalculiX decks with about 360 k nodes of C3D10 elements.
* `ccx -i <case>`, then `python3 post_lid.py <case>` gives a summary json and a .vtu. `pvbatch render_lid.py <case>.vtu out.png "title"` makes the pictures.
* Loads: the latch force on the 8 keeper pads (`F_LATCH`, default 111.2 N, the 25 lb McMaster 4432N117 rating) and 21.5 kPa water pressure on the top (7 ft + margin).

| Case | Lid peak von Mises | Lid sag | Gasket squeeze added (min / mean / max) |
|---|---|---|---|
| Latched at the surface, 8 × 111 N | 7.9 MPa | 0.1 mm | 0.6 / 2.0 / 2.6 % |
| 7 ft + latches, 8 × 111 N | 23.8 MPa | 0.5 mm | 0.4 / 4.8 / 7.3 % |
| (sensitivity) surface, 8 × 400 N | 28.3 MPa | 0.4 mm | 2.3 / 7.3 / 9.5 % |

The lid has a large margin (6061-T6 yield 276 MPa). **The gasket does not get enough squeeze:** a solid 8 mm EPDM band needs about 7 kN for 20 % squeeze,
while 8 latches give 0.9 kN. The corners (furthest from the latches) are the weakest point.
Recommendation: a closed-cell sponge EPDM or neoprene gasket (about 20 to 40 × softer), or an O-ring cord in a groove.

## Windows and walls (Roark hand calcs, `plates/plate_checks.py`)
See `results/plate_checks.txt`. Acrylic windows (5 mm, 52 × 122 mm open span): 1.2 to 1.4 MPa, SF 7 or more against 10 MPa long-term.
Box side walls at 6 mm: 7 to 8 MPa, SF 7 or more against 55 MPa welded-6061. At 4 mm: 15 to 18 MPa, SF 3 or more.
