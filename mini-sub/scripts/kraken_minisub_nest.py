import rectpack, itertools
IN=25.4
# (name, w, h, qty)  mm, all 8 mm (5/16") plate
parts=[("Bottom (window cutout)",316,166,1),("Side wall",316,140,2),("End wall (1 w/ window)",150,140,2),
       ("Outer U-flange",323,196,1),("O-ring flange",300,150,1),("Battery partition",150,140,1),
       ("Lid",316,166,1),("Window flange",176,106,2),("Window extender strip",354,20,2)]
GAP=6; EDGE=6
def pack(W,H,plist):
    rs=[]
    for n,w,h,q in plist:
        for i in range(q): rs.append((w+GAP,h+GAP,n))
    best=None
    for algo in [rectpack.MaxRectsBssf,rectpack.MaxRectsBaf,rectpack.MaxRectsBl,rectpack.GuillotineBssfSas,rectpack.SkylineMwf]:
        p=rectpack.newPacker(rotation=True,pack_algo=algo,sort_algo=rectpack.SORT_AREA)
        for r in rs: p.add_rect(*r)
        p.add_bin(W-2*EDGE+GAP,H-2*EDGE+GAP,count=20)
        p.pack()
        n=len(p); 
        if len(p.rect_list())!=len(rs): continue
        if best is None or n<best[0]: best=(n,p)
    return best
area=sum(w*h*q for _,w,h,q in parts); print("part bbox area mm2",area, "in2 %.0f"%(area/IN**2))
nested=[x for x in parts if x[0] not in ("O-ring flange",)]  # O-ring flange cut from inside the U-flange dropout
for label,plist in [("all separate",parts),("O-ring flange nested in U-flange",nested)]:
    print("==",label)
    for W,H in [(12,24),(24,24),(24,36),(24,48),(48,48)]:
        b=pack(W*IN,H*IN,plist)
        if b: print(f"  {W}x{H} in: {b[0]} sheet(s), sheet area {b[0]*W*H} in2, util {area/(b[0]*W*H*IN*IN)*100:.0f}%")
        else: print(f"  {W}x{H}: no fit")
