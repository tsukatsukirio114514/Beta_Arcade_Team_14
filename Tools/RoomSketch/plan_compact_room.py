"""Remove interior module bands; retain stone/module height and curved perimeter radii."""
import json, math
from pathlib import Path
ROOT=Path(__file__).parent
data=json.loads(Path('C:/Users/zhanx/AppData/Local/Temp/stone-room-sketch/resize_current.json').read_text())
def fx(x):
    if x<=-600:return x+400
    if x<=0:return -200
    if x<=400:return x-200
    if x<=600:return 200
    return x-400
def fy(y):
    if y<=-600:return y+300
    if y<=-200:return -300
    if y<=400:return y-100
    if y<=600:return 300
    return y-300
def removed(x,y):return (-600<x<0) or (400<x<600) or (-600<y<-200) or (400<y<600)
plan={'delete':[],'move':[],'walls':[],'floors':[],'keep':[]}
def move(row,x,y):plan['move'].append({'id':row['id'],'p':[x,y,row['p'][2]]})
for row in data:
    label=row['label'];folder=row['folder'];x,y,z=row['p']
    if folder=='Room/Walls':
        if label.startswith(('South Wall','North Wall','East Wall','West Upper Wall','West Lower Wall','Divider ')):
            plan['delete'].append(row['id'])
        elif label.startswith(('Corner Southwest','Southeast Chamfer')):move(row,x+(400 if x<0 else -400),y-300)
        elif label.startswith(('Corner Northwest','Northwest','Northeast')):move(row,x+(400 if x<0 else -400),y+300)
        elif label.startswith('West Inset'):move(row,x+400,y-100)
        else:raise RuntimeError(label)
    elif folder=='Room/Pillars':
        nx,ny=fx(x),fy(y)
        if label=='Structural Pillar 01':ny=-300
        move(row,nx,ny)
    elif folder=='Room/Floor':
        if label=='Room Foundation':continue
        if label.startswith('Fire Trap '):move(row,0,y-300)
        elif label.startswith('Curved Floor Border'):
            if ' NE ' in label:move(row,x-400,y+300)
            elif ' NW' in label:move(row,x+400,y+300)
            elif ' West ' in label:move(row,x+400,y-100)
            else:raise RuntimeError(label)
        elif label.startswith('Inset Floor Fill'):move(row,x+400,y-100)
        elif label=='Chamfer Floor Border':move(row,x-400,y-300)
        elif label.startswith('Floor '):
            nx,ny=fx(x),fy(y)
            if removed(x,y) or (abs(nx)<200 and ny>=-300):plan['delete'].append(row['id'])
            else:
                move(row,nx,ny)
                plan['floors'].append({'id':row['id'],'x':nx,'y':ny,'original_mesh':row['mesh'].split('.')[-1],'original_yaw':row['r'][1],'label':label})
        else:raise RuntimeError(label)
    elif folder.startswith('Room/Traps/Fire Trap '):move(row,x-200,y-300)
    elif folder.startswith('Room/Props/Barrels/'):
        # Preserve clusters and sizes; translate each cluster with its adjoining perimeter.
        if x<-1000:move(row,x+400,y+(300 if y<0 else -300))
        elif x>900:move(row,x-400,y+(300 if y<0 else -100))
        else:move(row,fx(x),fy(y))
    elif row['class']=='PlayerStart':move(row,-500,100)
    elif label=='Bounce - West Stone':move(row,-700,0)
    elif label=='Bounce - East Stone':move(row,650,-250)
    else:plan['keep'].append(row['id'])
# Rebuild straight spans from full 400 cm or 200 cm modules, plus at most one fitted end piece.
def wall_span(label,p,q):
    dx=q[0]-p[0];dy=q[1]-p[1];length=math.hypot(dx,dy);yaw=math.degrees(math.atan2(dy,dx))
    sections=[];remaining=length
    while remaining>450:sections.append(400);remaining-=400
    if remaining>280 and remaining<350:sections.append(remaining)
    elif remaining>450:raise AssertionError(remaining)
    else:sections.append(remaining)
    offset=0
    for i,size in enumerate(sections):
        t=(offset+size/2)/length
        plan['walls'].append({'label':label+'_%02d'%i,'p':[p[0]+dx*t,p[1]+dy*t,12],'length':size,'yaw':yaw})
        offset+=size
wall_span('South Wall',(-810,740),(600,740))
wall_span('North Wall',(-200,-740),(800,-740))
wall_span('East Wall',(1040,524.72136),(1040,-500))
wall_span('West Upper Wall',(-1050,-100),(-1050,8.578644))
wall_span('West Lower Wall',(-1050,291.421356),(-1050,500))
wall_span('Divider North',(0,-700),(0,-300))
# Re-evaluate the straight perimeter floor borders after removing rows/columns.
def grid_x(x):return -100 if -150<x<0 else 100 if 0<x<150 else round(x)
occupied={(grid_x(f['x']),round(f['y'])) for f in plan['floors']}
for f in plan['floors']:
    x=grid_x(f['x']);y=round(f['y']);edges=[]
    for tag,dx,dy in [('L',-200,0),('R',200,0),('T',0,-200),('B',0,200)]:
        if (x+dx,y+dy) not in occupied:edges.append(tag)
    if y<-300 and x==-100:edges.append('R')
    if y<-300 and x==100:edges.append('L')
    if 'L' in edges and 'T' in edges:name='Left_Top'
    elif 'L' in edges and 'B' in edges:name='Left_Bottom'
    elif 'R' in edges and 'T' in edges:name='Right_Top'
    elif 'R' in edges and 'B' in edges:name='Right_Bottom'
    elif 'L' in edges:name='Left_Middle'
    elif 'R' in edges:name='Right_Middle'
    elif 'T' in edges:name='Middle_Top'
    elif 'B' in edges:name='Middle_Bottom'
    else:name='Center'
    f['mesh']=name;f['yaw']=180 if name!='Center' else f['original_yaw']
# A small minority of true interior cells use variations; the majority remain center tiles.
interior=[f for f in plan['floors'] if f['mesh']=='Center']
interior.sort(key=lambda f:(f['x']*37+f['y']*17)%997)
for i,f in enumerate(interior[:max(1,round(len(interior)*.2))]):
    f['mesh']=['Middle_Top','Right_Middle','Left_Middle','Middle_Bottom'][i%4]
    f['yaw']=[90,0,270,180][i%4];f['variation']=True
poly0=json.loads((ROOT/'layout.json').read_text())['outline']
poly=[]
for x,y in poly0:
    q=(fx(x),fy(-y))
    if not poly or q!=poly[-1]:poly.append(q)
def area(p):return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2)
plan['outline_world']=poly
plan['area_before_m2']=area(poly0)/10000
plan['area_after_m2']=area(poly)/10000
plan['area_ratio']=area(poly)/area(poly0)
# Ear clipping for a dedicated support foundation; keep the old support asset intact.
vertices=list(poly)
if sum(vertices[i][0]*vertices[(i+1)%len(vertices)][1]-vertices[(i+1)%len(vertices)][0]*vertices[i][1] for i in range(len(vertices)))<0:vertices.reverse()
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
ids=list(range(len(vertices)));faces=[]
while len(ids)>3:
    for k,b in enumerate(ids):
        a=ids[k-1];c=ids[(k+1)%len(ids)]
        if cross(vertices[a],vertices[b],vertices[c])<=.00001:continue
        if any(cross(vertices[a],vertices[b],vertices[j])>=-.00001 and cross(vertices[b],vertices[c],vertices[j])>=-.00001 and cross(vertices[c],vertices[a],vertices[j])>=-.00001 for j in ids if j not in [a,b,c]):continue
        faces.append((a,b,c));ids.pop(k);break
    else:raise RuntimeError('Foundation triangulation failed')
faces.append(tuple(ids));n=len(vertices);lines=['o SM_RoomFoundation_Compact']
for z in [-35,0]:
    for x,y in vertices:lines.append(f'v {x:.6f} {y:.6f} {z:.6f}')
for a,b,c in faces:lines+=['f %d %d %d'%(a+n+1,b+n+1,c+n+1),'f %d %d %d'%(c+1,b+1,a+1)]
for a in range(n):
    b=(a+1)%n;lines+=['f %d %d %d'%(a+1,b+1,b+n+1),'f %d %d %d'%(a+1,b+n+1,a+n+1)]
(ROOT/'SM_RoomFoundation_Compact.obj').write_text('\n'.join(lines))
(ROOT/'compact_plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps({k:len(plan[k]) for k in ['delete','move','walls','floors']}))
print('AREA_M2',plan['area_before_m2'],plan['area_after_m2'],'RATIO',plan['area_ratio'])
