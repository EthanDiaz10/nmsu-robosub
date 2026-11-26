"""Roark rectangular-plate checks for BENTO REV-D windows and box walls (uniform pressure).
Roark's Formulas for Stress and Strain, Table 11.4: case 1a (simply supported) and 8a (all edges fixed).
sigma = beta q b^2 / t^2 ; y = alpha q b^4 / (E t^3) ; b = short side.
"""
import numpy as np
Q=0.0215  # MPa: 7 ft pool (21.0 kPa) + margin
# a/b: 1.0 1.2 1.4 1.6 1.8 2.0 inf
ab=np.array([1.0,1.2,1.4,1.6,1.8,2.0,1e3])
ss_beta=np.array([0.2874,0.3762,0.4530,0.5172,0.5688,0.6102,0.7500]); ss_alpha=np.array([0.0444,0.0616,0.0770,0.0906,0.1017,0.1110,0.1421])
fx_beta=np.array([0.3078,0.3834,0.4356,0.4680,0.4872,0.4974,0.5000]); fx_alpha=np.array([0.0138,0.0188,0.0226,0.0251,0.0267,0.0277,0.0284])
def plate(name,a,b,t,E,allow,allow_name):
    r=max(a,b)/min(a,b); b=min(a,b)
    out=[]
    for lab,be,al in [('simply supported',ss_beta,ss_alpha),('fixed edges',fx_beta,fx_alpha)]:
        B=np.interp(r,ab,be); Al=np.interp(r,ab,al)
        s=B*Q*b*b/t/t; y=Al*Q*b**4/(E*t**3)
        out.append((lab,s,y,allow/s))
    print(f'{name}: {a:g} x {b:g} x {t:g} mm span, q = {Q*1000:.1f} kPa')
    for lab,s,y,sf in out: print(f'   {lab:17s} sigma_max {s:6.2f} MPa  deflection {y:6.3f} mm  SF {sf:5.1f} vs {allow_name}')
    return out
res={}
res['window']=plate('Window (acrylic, gasket opening)',122,52,5,3100,10.0,'10 MPa long-term acrylic')
res['side_wall']=plate('Box side wall 6061 (6 mm)',300,150,6,68900,55.0,'55 MPa welded 6061 HAZ fatigue-safe')
res['side_wall_4mm']=plate('Box side wall 6061 if thinned to 4 mm',300,150,4,68900,55.0,'55 MPa')
res['end_wall']=plate('Box end wall 6061 (6 mm)',170,150,6,68900,55.0,'55 MPa')
res['bottom']=plate('Box bottom 6061 (8 mm, no window cut-out)',300,170,8,68900,55.0,'55 MPa')
