"""Integrate pressure + wall-shear forces/moments on patch 'bento' from an OpenFOAM case
(ascii mesh + fields; run `foamFormatConvert -constant` first if the mesh is binary).
Works around the v1912 Ubuntu build whose function objects crash (sha1 digest bug).
Usage: python3 forces_from_fields.py <case> [time] [U] [Aref]
Origin (0,0,0) = vehicle CG (STL was shifted by -CG). Flow +X (vehicle surges -X), Y up, Z lateral.
"""
import numpy as np, re, sys, os, json
RHO=998.2; NU=1.004e-6
case=sys.argv[1]
times=sorted([d for d in os.listdir(case) if re.fullmatch(r'[0-9.]+',d) and d!='0'],key=float)
t=sys.argv[2] if len(sys.argv)>2 and sys.argv[2]!='latest' else times[-1]
Uinf=float(sys.argv[3]) if len(sys.argv)>3 else 0.5; Aref=float(sys.argv[4]) if len(sys.argv)>4 else 0.06453
def body(path):
    s=open(path).read(); return s[s.index('}',s.index('FoamFile'))+1:]
def readlist(s,start=0,dtype=float,vec=False):
    m=re.compile(r'(\d+)\s*\(',re.S).search(s,start)
    n=int(m.group(1)); i=m.end(); j=s.index('\n)',i) if not vec else None
    if vec:
        seg=s[i:]; seg=seg[:seg.index('\n)\n')]
        a=np.array(seg.replace('(',' ').replace(')',' ').split(),dtype=dtype).reshape(n,-1)
    else:
        a=np.array(s[i:j].split(),dtype=dtype)
    assert len(a)==n,(len(a),n); return a
pm=os.path.join(case,'constant/polyMesh')
pts=readlist(body(pm+'/points'),vec=True)
sf=body(pm+'/faces')
m=re.search(r'(\d+)\s*\(',sf); nf=int(m.group(1)); seg=sf[m.end():]; seg=seg[:seg.index('\n)\n')]
own=body(pm+'/owner'); own=readlist(own,dtype=np.int64)
nei=body(pm+'/neighbour'); nei=readlist(nei,dtype=np.int64)
bnd=body(pm+'/boundary'); b=re.search(r'bento\s*\{[^}]*nFaces\s+(\d+);\s*startFace\s+(\d+);',bnd)
nF,sF=int(b.group(1)),int(b.group(2))
# parse faces "4(a b c d)" lines
toks=re.findall(r'(\d+)\(([^)]*)\)',seg); assert len(toks)==nf
ncell=max(own.max(),nei.max())+1
fc=np.zeros((nf,3)); Sf=np.zeros((nf,3))
for k,(n,l) in enumerate(toks):
    P=pts[np.array(l.split(),dtype=np.int64)]
    c=P.mean(0); fc[k]=c
    Sf[k]=0.5*np.cross(P-c,np.roll(P,-1,0)-c).sum(0)
cc=np.zeros((ncell,3)); cnt=np.zeros(ncell)
np.add.at(cc,own,fc); np.add.at(cnt,own,1); np.add.at(cc,nei,fc[:len(nei)]); np.add.at(cnt,nei,1)
cc/=cnt[:,None]
def field(name,vec=False):
    s=body(os.path.join(case,t,name)); i=s.index('internalField')
    return readlist(s,i,vec=vec), s
p,_=field('p'); U,_=field('U',True)
_,snut=field('nut'); i=snut.index('bento'); i=snut.index('value',i)
nutw=readlist(snut,i) if 'nonuniform' in snut[i:i+40] else np.full(nF,float(re.search(r'uniform\s+([-\d.eE+]+)',snut[i:]).group(1)))
fs=slice(sF,sF+nF); o=own[fs]; A=Sf[fs]; magA=np.linalg.norm(A,axis=1); n=A/magA[:,None]; r=fc[fs]
Fp=RHO*(p[o][:,None]*A)
Uc=U[o]; d=np.abs(((cc[o]-r)*n).sum(1)); Ut=Uc-(Uc*n).sum(1)[:,None]*n
Fv=RHO*(NU+nutw)[:,None]*Ut/d[:,None]*magA[:,None]
F=Fp+Fv; M=np.cross(r,F)
q=0.5*RHO*Uinf**2
res=dict(time=t,U=Uinf,Aref=Aref,F_pressure=Fp.sum(0).tolist(),F_viscous=Fv.sum(0).tolist(),F_total=F.sum(0).tolist(),
         M_about_CG=M.sum(0).tolist(),Mz_from_Fx=float((-r[:,1]*F[:,0]).sum()),Mz_from_Fy=float((r[:,0]*F[:,1]).sum()),
         x_cp_lift=float((r[:,0]*F[:,1]).sum()/F[:,1].sum()),Cd=F.sum(0)[0]/(q*Aref),wetted_area=float(magA.sum()))
print(json.dumps(res,indent=1))
json.dump(res,open(os.path.join(case,f'forces_{t}.json'),'w'),indent=1)
