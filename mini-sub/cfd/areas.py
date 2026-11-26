import numpy as np, sys
d=open(sys.argv[1] if len(sys.argv)>1 else 'bento.stl','rb').read()
n=np.frombuffer(d[80:84],np.uint32)[0]
rec=np.frombuffer(d[84:84+n*50],dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))
V=rec['v'].astype(float)
from PIL import Image, ImageDraw
def area(i,j,res=0.001):
    P=V[:,:,[i,j]]
    mn=P.reshape(-1,2).min(0); mx=P.reshape(-1,2).max(0)
    W,H=((mx-mn)/res).astype(int)+2
    im=Image.new('1',(W,H),0); dr=ImageDraw.Draw(im)
    for t in ((P-mn)/res):
        dr.polygon([tuple(p) for p in t],fill=1)
    return np.array(im).sum()*res*res
print('x-dir (yz) A=',area(1,2)); print('y-dir (xz) A=',area(0,2)); print('z-dir (xy) A=',area(0,1))
