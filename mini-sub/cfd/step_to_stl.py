import sys
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.gp import gp_Trsf, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
r=STEPControl_Reader(); r.ReadFile(sys.argv[1]); r.TransferRoots(); s=r.OneShape()
b=BRep_Builder(); c=TopoDS_Compound(); b.MakeCompound(c)
ex=TopExp_Explorer(s,TopAbs_SOLID); n=k=0
while ex.More():
    so=ex.Current(); g=GProp_GProps(); BRepGProp.VolumeProperties_s(so,g)
    bb=Bnd_Box(); BRepBndLib.Add_s(so,bb,False); d=bb.CornerMax().Distance(bb.CornerMin())
    n+=1
    if abs(g.Mass())>1500 or d>40: b.Add(c,so); k+=1   # drop small fasteners (<1.5 cm3 and <40 mm)
    ex.Next()
print('solids',n,'kept',k)
cg=[float(v) for v in sys.argv[3:6]]
t=gp_Trsf(); t.SetTranslation(gp_Vec(-cg[0],-cg[1],-cg[2])); s=BRepBuilderAPI_Transform(c,t,True).Shape()
t2=gp_Trsf(); t2.SetScaleFactor(0.001); s=BRepBuilderAPI_Transform(s,t2,True).Shape()
BRepMesh_IncrementalMesh(s,0.0004,False,0.4,True)
w=StlAPI_Writer(); w.ASCIIMode=False; w.Write(s,sys.argv[2]); print('ok')
