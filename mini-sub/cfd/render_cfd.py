# pvbatch render_cfd.py <case_dir> <U> <outprefix>
import sys
from paraview.simple import *
case,U,out=sys.argv[1],float(sys.argv[2]),sys.argv[3]
q=0.5*U*U   # kinematic p -> Cp = p/(0.5 U^2)
r=OpenFOAMReader(FileName=case+'/case.foam'); r.MeshRegions=['internalMesh','patch/bento']; r.CellArrays=['p','U']
r.UpdatePipelineInformation(); r.UpdatePipeline(max(r.TimestepValues))
body=ExtractBlock(Input=r); body.Selectors=['/Root/boundary/bento'] if hasattr(body,'Selectors') else None
try: body.BlockIndices=[2]
except Exception: pass
vol=ExtractBlock(Input=r)
try: vol.BlockIndices=[1]
except Exception: vol.Selectors=['/Root/internalMesh']
c2p=CellDatatoPointData(Input=body)
cp=Calculator(Input=c2p,ResultArrayName='Cp',Function=f'p/{q}')
vc2p=CellDatatoPointData(Input=vol)
view=GetActiveViewOrCreate('RenderView'); view.ViewSize=[2400,1500]; view.OrientationAxesVisibility=0
view.Background=[1,1,1]
try: view.UseColorPaletteForBackground=0
except Exception: pass
d=Show(cp,view); ColorBy(d,('POINTS','Cp')); lut=GetColorTransferFunction('Cp'); lut.ApplyPreset('Cool to Warm',True); lut.RescaleTransferFunction(-1.2,1.0)
bar=GetScalarBar(lut,view); bar.Title='Pressure coefficient Cp'; bar.ComponentTitle=''; bar.TitleColor=[0,0,0]; bar.LabelColor=[0,0,0]; bar.WindowLocation='Any Location'; bar.Orientation='Horizontal'; bar.Position=[0.3,0.05]; bar.ScalarBarLength=0.4
# streamlines from a rake upstream
st=StreamTracer(Input=vc2p,SeedType='Point Cloud'); st.Vectors=['POINTS','U']
st.SeedType.Center=[-0.45,0.0,0.0]; st.SeedType.Radius=0.17; st.SeedType.NumberOfPoints=500; st.MaximumStreamlineLength=2.5
tube=Tube(Input=st); tube.Radius=0.0015
ds=Show(tube,view); ColorBy(ds,('POINTS','U','Magnitude')); ul=GetColorTransferFunction('U'); ul.ApplyPreset('Viridis (matplotlib)',True); ul.RescaleTransferFunction(0,1.3*U)
ub=GetScalarBar(ul,view); ub.Title='Velocity (m/s)'; ub.ComponentTitle=''; ub.TitleColor=[0,0,0]; ub.LabelColor=[0,0,0]; ub.WindowLocation='Any Location'; ub.Orientation='Horizontal'; ub.Position=[0.3,0.9]; ub.ScalarBarLength=0.4
cam=view.GetActiveCamera(); view.CameraFocalPoint=[0.15,0,0]; view.CameraPosition=[-0.75,0.55,0.95]; view.CameraViewUp=[0,1,0]; view.CameraViewAngle=30
SaveScreenshot(out+'_streamlines.png',view,ImageResolution=[2400,1500])
Hide(tube,view); ub.Visibility=0
view.CameraPosition=[-0.7,0.35,-0.75]; view.CameraFocalPoint=[0,0,0]
SaveScreenshot(out+'_surface_cp.png',view,ImageResolution=[2400,1500])
# side slice z=0 velocity magnitude
sl=Slice(Input=vc2p); sl.SliceType.Normal=[0,0,1]; sl.SliceType.Origin=[0,0,0]
dsl=Show(sl,view); ColorBy(dsl,('POINTS','U','Magnitude')); ul.RescaleTransferFunction(0,1.3*U); ub.Visibility=1; ub.Position=[0.3,0.06]
Hide(cp,view); bar.Visibility=0
d2=Show(cp,view); ColorBy(d2,None); d2.DiffuseColor=[0.25,0.25,0.28]
view.CameraFocalPoint=[0.45,0,0]; view.CameraPosition=[0.45,0,2.6]; view.CameraViewUp=[0,1,0]; view.CameraParallelProjection=1; view.CameraParallelScale=0.42
SaveScreenshot(out+'_side_velocity.png',view,ImageResolution=[2600,1300])
