# Executive Summary — P2.5.0.4 OWN TOP_BAR Engineering Crop Rendering

- MODEL_VERSION: `10.6.3`
- Decision: **READY_FOR_P2.5.1**
- Determinism: `PASS`
- Unit tests: `0/0`
- Regression unchanged: `True`
- Claude: NONE

## Root Cause

OWN TOP_BAR LWPOLYLINEs on -STR-BEAM use BYLAYER ACI color 7 (white). ezdxf MatplotlibBackend draws them as white strokes on a white PNG background, so they are present in the draw pass but invisible. The diagnostic overlay redraws the same coordinates in magenta, which is why overlay showed OWN while engineering crop did not.

## Answers

1. B97A OWN packaged+rendered? packaged=`OWN::B97A::1247FFF` rendered=`True` distinguishable=`True`
2. B98A OWN packaged+rendered? packaged=`OWN::B98A::1247FFE` rendered=`True` distinguishable=`True`
3. Actual DXF geometry used? YES (points from handles 1247FFF/1247FFE)
4. Synthetic geometry? NO
5–8. Annotations/leaders: B97A `4-Y25`/`LDR::E83C245B`; B98A `4-Y25`/`LDR::1812F192`
9–12. Rejected excluded / not extreme: B97A extreme=`False` B98A extreme=`False`
13. Crop dims: B97A={'w_mm': 5410.138447962701, 'h_mm': 3219.220000002533} B98A={'w_mm': 3585.400000002235, 'h_mm': 3048.940000001341}
14. Determinism: `PASS`
15. Vision-ready / P2.5.1: **READY_FOR_P2.5.1**
