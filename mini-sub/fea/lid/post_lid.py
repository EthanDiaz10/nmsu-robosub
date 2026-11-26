"""Post-process lid FEA: parse CalculiX .frd (DISP, STRESS), write .vtu, summarise gasket squeeze + lid stress."""
import numpy as np, meshio, json, sys, re
def read_frd(fn):
    res={}; cur=None; ids=[]; vals=[]
    for line in open(fn):
        if line.startswith(' -4'):
            cur=line.split()[1]; ids=[]; vals=[]
        elif cur and line.startswith(' -1'):
            ids.append(int(line[3:13])); s=line[13:].rstrip('\n')
            vals.append([float(s[i:i+12]) for i in range(0,len(s),12) if s[i:i+12].strip()])
        elif cur and line.startswith(' -3'):
            res[cur]=(np.array(ids),np.array(vals)); cur=None
    return res
def read_inp(fn):
    nodes={}; cells={}; mode=None; es=None
    for line in open(fn):
        if line.startswith('*'):
            u=line.upper(); mode=None
            if u.startswith('*NODE') and 'FILE' not in u and 'PRINT' not in u: mode='n'
            elif u.startswith('*ELEMENT'): mode='e'; es=re.search(r'ELSET=(\w+)',u).group(1); cells[es]=[]
            continue
        if mode=='n': p=line.split(','); nodes[int(p[0])]=[float(x) for x in p[1:4]]
        elif mode=='e': p=[int(x) for x in line.strip().strip(',').split(',')]; cells[es].append(p[1:])
    return nodes,cells
case=sys.argv[1]; Y1=1047.13; T0=3.0; sq0=0.0
nodes,cells=read_inp(case+'.inp'); r=read_frd(case+'.frd')
nid=np.array(sorted(nodes)); pos={n:i for i,n in enumerate(nid)}; X=np.array([nodes[n] for n in nid])
di,dv=r['DISP']; U=np.zeros((len(nid),3)); U[[pos[i] for i in di]]=dv[:,:3]
si,sv=r['STRESS']; S=np.zeros((len(nid),6)); S[[pos[i] for i in si]]=sv[:,:6]
sx,sy,sz,txy,tyz,tzx=S.T
vm=np.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)+3*(txy**2+tyz**2+tzx**2))
lidc=np.array([[pos[k] for k in c] for c in cells['LID']]); gc=np.array([[pos[k] for k in c] for c in cells['GSK']])
lidn=np.unique(lidc); 
# nodal stress at a shared lid/gasket node is averaged with soft gasket -> use lid-only max excluding interface
vm_lid=vm[lidn]; X_l=X[lidn]
gt=np.load('gtop_tags.npy'); gi=np.array([pos[t] for t in gt])
dy=-U[gi,1]                                    # downward motion of gasket top = extra compression (mm)
squeeze=(dy)/T0*100                            # % of free 3 mm height produced by this load case
out=dict(case=case,max_disp_mm=float(np.abs(U[lidn]).max()),lid_center_sag_mm=float(-U[lidn,1].max()*0+(-U[lidn,1]).max()),
 lid_max_vm_MPa=float(vm_lid.max()),lid_vm_99pct_MPa=float(np.percentile(vm_lid,99.9)),
 gasket_squeeze_pct=dict(min=float(squeeze.min()),mean=float(squeeze.mean()),max=float(squeeze.max())),
 gasket_unloaded_fraction=float((squeeze<0).mean()))
print(json.dumps(out,indent=1)); json.dump(out,open(case+'_summary.json','w'),indent=1)
np.save(case+'_squeeze.npy',np.c_[X[gi],squeeze])
m=meshio.Mesh(X,[('tetra10',lidc[:,[0,1,2,3,4,5,6,7,8,9]]),('tetra10',gc)],
  point_data={'U':U,'vonMises':vm,'S':S},cell_data={'part':[np.ones(len(lidc)),2*np.ones(len(gc))]})
m.write(case+'.vtu')
