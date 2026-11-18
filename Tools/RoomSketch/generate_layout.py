import math,json
from pathlib import Path
P=Path('C:/Users/zhanx/Desktop/Beta Arcade/Beta_Arcade_Team_14/Tools/RoomSketch')
def arc(c,r,a,b,n=12):return [(c[0]+r*math.cos(math.radians(a+(b-a)*i/n)),c[1]+r*math.sin(math.radians(a+(b-a)*i/n))) for i in range(n+1)]
# Clockwise perimeter in drawing coordinates: x right, y up.
poly=[(-1400,-1000),(1000,-1000),(1400,-800),(1400,800)]
poly+=arc((1200,800),200,0,90)[1:]
poly+=[(-600,1000)]
poly+=arc((-600,800),200,90,180)[1:]
poly+=arc((-1000,800),200,0,-90)[1:]
poly+=[(-1400,600),(-1400,-108.578644)]
poly+=arc((-1541.421356,-250),200,45,-45)[1:]
poly+=[(-1400,-1000)]
if poly[0]==poly[-1]:poly.pop()
(P/'layout.json').write_text(json.dumps({'outline':poly,'divider_x':200,'trap_width':400,'trap_y':[(-1000,-670),(-660,-340),(-330,0)]},indent=2))
# Make a thin, untextured grout/foundation under the modular floor. The visible tiles stay original assets.
verts=[(x,-y) for x,y in poly]
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
if sum(verts[i][0]*verts[(i+1)%len(verts)][1]-verts[(i+1)%len(verts)][0]*verts[i][1] for i in range(len(verts)))<0:verts.reverse()
ids=list(range(len(verts)));faces=[]
while len(ids)>3:
 for k,b in enumerate(ids):
  a=ids[k-1];c=ids[(k+1)%len(ids)]
  if cross(verts[a],verts[b],verts[c])<=.00001:continue
  if any(cross(verts[a],verts[b],verts[j])>=-.00001 and cross(verts[b],verts[c],verts[j])>=-.00001 and cross(verts[c],verts[a],verts[j])>=-.00001 for j in ids if j not in [a,b,c]):continue
  faces.append((a,b,c));ids.pop(k);break
 else:raise RuntimeError('Polygon triangulation failed')
faces.append(tuple(ids));n=len(verts)
lines=['o SM_RoomFoundation']
for z in [-35,0]:
 for x,y in verts:lines.append(f'v {x:.6f} {y:.6f} {z:.6f}')
for a,b,c in faces:lines+=['f %d %d %d'%(a+n+1,b+n+1,c+n+1),'f %d %d %d'%(c+1,b+1,a+1)]
for a in range(n):
 b=(a+1)%n;lines+=['f %d %d %d'%(a+1,b+1,b+n+1),'f %d %d %d'%(a+1,b+n+1,a+n+1)]
(P/'SM_RoomFoundation.obj').write_text('\n'.join(lines))
print('LAYOUT_READY',len(poly),len(faces))
