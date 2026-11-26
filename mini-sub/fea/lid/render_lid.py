# pvbatch render_lid.py <case.vtu> <out.png> <title>
import sys
from paraview.simple import *
r=XMLUnstructuredGridReader(FileName=[sys.argv[1]])
lid=Threshold(Input=r); lid.Scalars=['CELLS','part']
try: lid.LowerThreshold=0.5; lid.UpperThreshold=1.5
except Exception: lid.ThresholdRange=[0.5,1.5]
gsk=Threshold(Input=r); gsk.Scalars=['CELLS','part']
try: gsk.LowerThreshold=1.5; gsk.UpperThreshold=2.5
except Exception: gsk.ThresholdRange=[1.5,2.5]
wl=WarpByVector(Input=lid,Vectors=['POINTS','U'],ScaleFactor=60)
wg=WarpByVector(Input=gsk,Vectors=['POINTS','U'],ScaleFactor=60)
v=GetActiveViewOrCreate('RenderView'); v.ViewSize=[2400,1500]; v.Background=[1,1,1]; v.OrientationAxesVisibility=0
try: v.UseColorPaletteForBackground=0
except Exception: pass
d=Show(wl,v); ColorBy(d,('POINTS','vonMises')); l=GetColorTransferFunction('vonMises'); l.ApplyPreset('Turbo',True); l.RescaleTransferFunction(0,30)
b=GetScalarBar(l,v); b.Title='von Mises stress (MPa), deflection x60'; b.ComponentTitle=''; b.TitleColor=[0,0,0]; b.LabelColor=[0,0,0]; b.WindowLocation='Any Location'; b.Orientation='Horizontal'; b.Position=[0.3,0.05]; b.ScalarBarLength=0.4
t=Text(Text=sys.argv[3]); td=Show(t,v); td.Color=[0,0,0]; td.FontSize=22; td.WindowLocation='Upper Center'
v.CameraFocalPoint=[753,1040,1397]; v.CameraPosition=[753-250,1040-330,1397-420]; v.CameraViewUp=[0,1,0]
ResetCamera(); v.CameraPosition=[753-260,1040-300,1397-440]; v.CameraFocalPoint=[753,1046,1397]
GetActiveCamera().Dolly(1.25)
SaveScreenshot(sys.argv[2],v,ImageResolution=[2400,1500])

# gasket squeeze map (top-down)
for x in list(GetSources().values()):
    Hide(x,v)
sq=Calculator(Input=gsk,ResultArrayName='squeeze',Function='-U_Y/3*100')
ds=Show(sq,v); ColorBy(ds,('POINTS','squeeze')); L=GetColorTransferFunction('squeeze'); L.ApplyPreset('Viridis (matplotlib)',True); import os; L.RescaleTransferFunction(0,float(os.environ.get('SQMAX',15)))
b.Visibility=0
bs=GetScalarBar(L,v); bs.Title='Gasket squeeze added by this load case (% of 3 mm)'; bs.ComponentTitle=''; bs.TitleColor=[0,0,0]; bs.LabelColor=[0,0,0]; bs.WindowLocation='Any Location'; bs.Orientation='Horizontal'; bs.Position=[0.3,0.05]; bs.ScalarBarLength=0.4
td=Show(t,v); t.Text=sys.argv[3]+' : gasket squeeze, top view (front/window end at left)'
v.CameraFocalPoint=[751,1046,1397]; v.CameraPosition=[751,1600,1397]; v.CameraViewUp=[0,0,-1]; v.CameraParallelProjection=1; v.CameraParallelScale=110
SaveScreenshot(sys.argv[2].replace('.png','_gasket.png'),v,ImageResolution=[2400,1500])
