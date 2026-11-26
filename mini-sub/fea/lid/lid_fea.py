"""BENTO REV-D lid + lid gasket FEA (gmsh -> CalculiX).
Units: mm, N, MPa. Assembly frame, Y up.
Cases: (1) latches only, 8 x F_LATCH down at the keeper pads (dry, at surface)
       (2) latches + 21.5 kPa external water pressure on the lid top (7 ft pool + margin)
Gasket: 8 mm wide EPDM band modelled as a 2.4 mm solid (its 20%-squeezed CAD height),
bonded to the lid underside, bottom fixed on the gasket flange (treated rigid).
"""
import gmsh, numpy as np, json, subprocess, sys, os
G=os.environ.get('GEOM','analysis_results/geometry').rstrip('/')+'/'   # REV-D export folder: STEP files + notes.json
notes=json.load(open(G+'notes.json'))
F_LATCH=float(os.environ.get('F_LATCH',111.2))  # McMaster 4432N117 rated 25 lb; Q=0.0215
E_AL,NU_AL=68900.,0.33; E_GSK=float(os.environ.get('E_GSK',5.0))
Y0,Y1=1044.73,1047.13   # gasket bottom / lid underside
gasket=notes['lid_gasket']; ob=gasket['outer_bbox_mm']; ib=gasket['inner_opening_bbox_mm']
gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
v=gmsh.model.occ.importShapes(G+'02_LID-STACK_REV-D_asm-position.step')
lid=[t for d,t in v if abs(gmsh.model.occ.getMass(d,t)-265513)<500][0]
gmsh.model.occ.remove([(d,t) for d,t in v if t!=lid],recursive=True)
o=gmsh.model.occ.addBox(ob[0],Y0,ob[2],ob[3]-ob[0],Y1-Y0,ob[5]-ob[2])
i=gmsh.model.occ.addBox(ib[0],Y0,ib[2],ib[3]-ib[0],Y1-Y0,ib[5]-ib[2])
gk,_=gmsh.model.occ.cut([(3,o)],[(3,i)])
out,_=gmsh.model.occ.fragment([(3,lid)],gk); gmsh.model.occ.synchronize()
vols=[t for d,t in gmsh.model.getEntities(3)]
gvol=[t for t in vols if gmsh.model.getBoundingBox(3,t)[4]<Y1+0.01]; lvol=[t for t in vols if t not in gvol]
gmsh.model.addPhysicalGroup(3,lvol,1); gmsh.model.addPhysicalGroup(3,gvol,2)
gmsh.option.setNumber("Mesh.MeshSizeMax",float(os.environ.get('H',3.0)))
gmsh.option.setNumber("Mesh.ElementOrder",2); gmsh.option.setNumber("Mesh.HighOrderOptimize",0)
gmsh.model.mesh.field.add("Box",1)
for k,val in dict(VIn=1.6,VOut=3.0,XMin=ob[0]-1,XMax=ob[3]+1,YMin=Y0-1,YMax=Y1+0.5,ZMin=ob[2]-1,ZMax=ob[5]+1).items():
    gmsh.model.mesh.field.setNumber(1,k,val)
gmsh.model.mesh.field.setAsBackgroundMesh(1)
gmsh.model.mesh.generate(3)
tags,xyz,_=gmsh.model.mesh.getNodes(); X=xyz.reshape(-1,3); idx={t:k for k,t in enumerate(tags)}
els={}
for pg,name in [(1,'LID'),(2,'GSK')]:
    E=[]
    for t in gmsh.model.getEntitiesForPhysicalGroup(3,pg):
        et,etags,en=gmsh.model.mesh.getElements(3,t)
        for a,b,c in zip(et,etags,en):
            if a==11: E.append((b,c.reshape(-1,10)))
    els[name]=E
# surface loads: pressure on lid faces with outward normal +Y (top of plate + pad tops)
up_tris=[]; pad_tris=[]
pads=[p['pad_xz'] for p in notes['latch_keeper_pads_on_lid']]
for d,t in gmsh.model.getBoundary([(3,x) for x in lvol],oriented=False):
    bb=gmsh.model.getBoundingBox(2,t)
    if abs(bb[1]-bb[4])>1e-3: continue          # not horizontal
    if bb[1]<Y1+0.01: continue                     # underside
    et,etags,en=gmsh.model.mesh.getElements(2,t)
    tri=en[0].reshape(-1,6); up_tris.append(tri)
up=np.vstack(up_tris)
F=np.zeros((len(tags),3))
def tri_area(n):
    p=X[[idx[k] for k in n[:3]]]; return 0.5*np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))
padload=np.zeros(len(tags))
cent=lambda n: X[[idx[k] for k in n[:3]]].mean(0)
tri_info=[(n,tri_area(n),cent(n)) for n in up]
ytop=max(c[1] for _,_,c in tri_info)
for pid,p in enumerate(pads):
    sel=[(n,a) for n,a,c in tri_info if c[1]>ytop-0.05 and p[0]<=c[0]<=p[2] and p[1]<=c[2]<=p[3]]
    A=sum(a for _,a in sel)
    for n,a in sel:
        for k in n[3:]: padload[idx[k]]+=F_LATCH*a/A/3
Fp=np.zeros(len(tags))
for n,a,c in tri_info:
    for k in n[3:]: Fp[idx[k]]+=Q*a/3
print('pressure resultant N',Fp.sum(),' latch resultant N',padload.sum())
fix=[t for t,x in zip(tags,X) if abs(x[1]-Y0)<1e-6]
gtop=np.array([t for t,x in zip(tags,X) if abs(x[1]-Y1)<1e-6 and ob[0]-0.01<=x[0]<=ob[3]+0.01 and ob[2]-0.01<=x[2]<=ob[5]+0.01 and not(ib[0]+0.01<x[0]<ib[3]-0.01 and ib[2]+0.01<x[2]<ib[5]-0.01)])
gmsh.finalize()
def write(case,loads):
    f=open(case+'.inp','w')
    f.write('*NODE\n'); [f.write(f'{int(t)},{x[0]:.6f},{x[1]:.6f},{x[2]:.6f}\n') for t,x in zip(tags,X)]
    for name,E in els.items():
        f.write(f'*ELEMENT,TYPE=C3D10,ELSET={name}\n')
        for et,con in E:
            for e,c in zip(et,con):
                c=c[[0,1,2,3,4,5,6,7,9,8]]  # gmsh->ccx tet10 midside order
                f.write(f'{int(e)},'+','.join(str(int(k)) for k in c)+'\n')
    def nset(n,l):
        f.write(f'*NSET,NSET={n}\n'); [f.write(f'{int(k)},\n') for k in l]
    nset('FIX',fix); nset('GTOP',gtop)
    f.write(f'*MATERIAL,NAME=AL6061\n*ELASTIC\n{E_AL},{NU_AL}\n*MATERIAL,NAME=EPDM\n*ELASTIC\n{E_GSK},0.0\n')
    f.write('*SOLID SECTION,ELSET=LID,MATERIAL=AL6061\n*SOLID SECTION,ELSET=GSK,MATERIAL=EPDM\n')
    f.write('*BOUNDARY\nFIX,1,3\n*STEP\n*STATIC\n*CLOAD\n')
    tot=sum(loads)
    for t,val in zip(tags,tot):
        if val!=0: f.write(f'{int(t)},2,{-val:.8e}\n')
    f.write('*NODE FILE\nU\n*EL FILE\nS\n*NODE PRINT,NSET=GTOP\nU\n*NODE PRINT,NSET=FIX,TOTALS=ONLY\nRF\n*END STEP\n'); f.close()
np.save('gtop_xyz.npy',np.array([X[idx[t]] for t in gtop])); np.save('gtop_tags.npy',gtop)
write('case1_latch',[padload]); write('case2_latch_pressure',[padload,Fp]); write('case3_pressure_only',[Fp])
print('nodes',len(tags),'gasket-top nodes',len(gtop))
