import unreal as u,math,json,random,shutil
from pathlib import Path
from datetime import datetime
ROOT=Path('C:/Users/zhanx/Desktop/Beta Arcade/Beta_Arcade_Team_14');DATA=ROOT/'Tools/RoomSketch';B='/Game/Levels/RoomSketch_Support';S='/Game/Assets/STRUCTURE/MESH/';SC=35.58799252791172
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);W=u.get_editor_subsystem(u.UnrealEditorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
assert not L.is_in_play_in_editor();w=W.get_editor_world();assert w.get_path_name()=='/Game/Levels/L_VisibilityTest.L_VisibilityTest'
assert all(isinstance(a,(u.Light,u.SkyLight,u.SkyAtmosphere,u.PostProcessVolume)) for a in A.get_all_level_actors()),'Room is not empty; preserve existing work'
backup=ROOT.parent/'_backup'/('RoomSketch_BeforeBuild_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir(parents=True);shutil.copy2(ROOT/'Content/Levels/L_VisibilityTest.umap',backup/'L_VisibilityTest.umap')
poly=json.loads((DATA/'layout.json').read_text())['outline']
def material(name,col,rough=.8,metal=0,unlit=False):
 mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,B,u.Material,u.MaterialFactoryNew());assert mat
 if unlit:mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*col,1));M.connect_material_property(n,'',u.MaterialProperty.MP_EMISSIVE_COLOR if unlit else u.MaterialProperty.MP_BASE_COLOR)
 for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,rough),(u.MaterialProperty.MP_METALLIC,metal)]:
  q=M.create_material_expression(mat,u.MaterialExpressionConstant);q.set_editor_property('r',val);M.connect_material_property(q,'',prop)
 M.recompile_material(mat);E.save_loaded_asset(mat,False);return mat
black=material('M_BlackVoid',(0,0,0),unlit=True);grout=material('M_Foundation',(0.055,.065,.06));iron=material('M_TrapIron',(.12,.13,.12),.55,.75);spike=material('M_TrapSpike',(.32,.33,.28),.3,.8);hot=material('M_WarmLight',(6,1.5,.15),unlit=True);red=material('M_TrapMark',(.3,.045,.01),.7)
wallmat=u.load_asset('/Game/Levels/ART_ASSETS_Support/M_WALL_blinn2');curvemat=u.load_asset('/Game/Levels/ART_ASSETS_Support/M_CURVE_WALL')
floormats={k:u.load_asset('/Game/Levels/ART_ASSETS_Support/M_FLOUR_'+k) for k in ['blinn1','blinn2']}
counts={};placements=[]
def point(x,y,z):return u.Vector(x,-y,z)
def mesh(label,asset,x,y,z,scale=(1,1,1),yaw=0,mat=None,folder='Room',coll=True):
 obj=u.load_asset(asset) if isinstance(asset,str) else asset;assert obj,asset
 a=A.spawn_actor_from_class(u.StaticMeshActor,point(x,y,z),u.Rotator(yaw=-yaw));a.set_actor_label(label);a.set_folder_path(folder);a.set_actor_scale3d(u.Vector(*scale));c=a.static_mesh_component;c.set_static_mesh(obj)
 if mat:
  for i in range(max(c.get_num_materials(),1)):c.set_material(i,mat)
 c.set_collision_profile_name('BlockAll' if coll else 'NoCollision')
 if obj.get_path_name().startswith(S):counts[obj.get_name()]=counts.get(obj.get_name(),0)+1
 return a

def structure(label,name,x,y,z=12,yaw=0,mults=(1,1,1),folder='Room/Walls'):
 return mesh(label,S+name,x,y,z,tuple(SC*v for v in mults),yaw,curvemat if 'Curved' in name or 'Arc45' in name else wallmat,folder)
def line(label,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);ang=math.degrees(math.atan2(dy,dx));num=max(1,round(length/400));seg=length/num
 for i in range(num):
  t=(i+.5)/num
  if seg<270:structure(label+'_%02d'%i,'Wall_Straight_1G',a[0]+dx*t,a[1]+dy*t,yaw=ang+90,mults=(1,seg/200,1))
  else:structure(label+'_%02d'%i,'Wall_Straight_2G',a[0]+dx*t,a[1]+dy*t,yaw=ang,mults=(seg/400,1,1))

def arc(label,center,a,b):
 name='Wall_Curved_R2m_91' if abs(b-a)==90 else 'Arc45_Course1_Stone1'
 cx,cy=(-3.425,-3.425) if 'Curved' in name else (-4.92,-2.42)
 # The asset starts at local angle 0. Convert drawing coordinates to world coordinates.
 worldyaw=-max(a,b);r=math.radians(worldyaw);rx=SC*(cx*math.cos(r)-cy*math.sin(r));ry=SC*(cx*math.sin(r)+cy*math.cos(r))
 x=center[0]-rx;y=center[1]+ry
 return structure(label,name,x,y,yaw=-worldyaw)
def corner(label,joint,worldyaw):
 r=math.radians(worldyaw);rx=90*math.cos(r)-90*math.sin(r);ry=90*math.sin(r)+90*math.cos(r)
 return structure(label,'Wall_Corner',joint[0]-rx,joint[1]+ry,yaw=-worldyaw)
# Matte black beneath and outside the room; no visible horizon or surrounding scenery.
mesh('Black Background','/Engine/BasicShapes/Plane',0,0,-70,(250,250,1),mat=black,folder='Room/Background',coll=False)
mesh('Room Foundation',B+'/SM_RoomFoundation',0,0,-4,mat=grout,folder='Room/Floor')
# Closed perimeter, using both straight lengths, corner pieces, and both curved modules.
corner('Corner Southwest',(-1400,-1000),90)
corner('Corner Northwest Step',(-1400,600),180)
line('South Wall',(-1160,-1000),(1000,-1000))
line('Southeast Chamfer',(1000,-1000),(1400,-800))
line('East Wall',(1400,-800),(1400,800))
arc('Northeast Curve A',(1200,800),0,45);arc('Northeast Curve B',(1200,800),45,90)
line('North Wall',(-600,1000),(1200,1000))
arc('Northwest Upper Curve',(-600,800),90,180)
arc('Northwest Lower Curve',(-1000,800),-90,0)
line('Northwest Ledge',(-1160,600),(-1000,600))
line('West Upper Wall',(-1400,360),(-1400,-108.578644))
arc('West Inset A',(-1541.421356,-250),0,45);arc('West Inset B',(-1541.421356,-250),-45,0)
line('West Lower Wall',(-1400,-391.421356),(-1400,-760))
# Central divider, ending at the continuous three-trap strip.
structure('Divider North','Wall_Straight_2G',200,800,yaw=90)
structure('Divider Middle','Wall_Straight_2G',200,400,yaw=90)
structure('Divider End','Wall_Straight_1G',200,100)
for i,(x,y) in enumerate([(200,990),(200,0),(1000,-1000),(1400,-800),(-1400,600),(-1400,-1000)]):
 structure('Structural Pillar %02d'%i,'Pillar_A',x,y,folder='Room/Pillars')
# Interior floor: regular grid with matching edge/corner modules around perimeter and divider.
def inside(x,y):
 result=False
 for i,p in enumerate(poly):
  q=poly[(i+1)%len(poly)]
  if (p[1]>y)!=(q[1]>y) and x<(q[0]-p[0])*(y-p[1])/(q[1]-p[1])+p[0]:result=not result
 return result

def closest(x,y):
 best=(1e9,None)
 for i,p in enumerate(poly):
  q=poly[(i+1)%len(poly)];dx=q[0]-p[0];dy=q[1]-p[1];t=max(0,min(1,((x-p[0])*dx+(y-p[1])*dy)/(dx*dx+dy*dy)))
  xx=p[0]+t*dx;yy=p[1]+t*dy;dist=math.hypot(x-xx,y-yy)
  if dist<best[0]:best=(dist,(xx,yy))
 return best
rng=random.Random(18)
def floor(name,x,y,yaw=180,mults=(1,1),label=None):
 a=mesh(label or 'Floor '+name,S+name,x,y,0,(SC*mults[0],SC*mults[1],SC),yaw,None,'Room/Floor')
 for i,slot in enumerate(a.static_mesh_component.static_mesh.static_materials):a.static_mesh_component.set_material(i,floormats[str(slot.material_slot_name)])
 placements.append({'asset':name,'x':x,'y':y,'yaw':yaw});return a
for x in range(-1300,1301,200):
 for y in range(-900,901,200):
  if not inside(x,y):continue
  if 0<x<400 and y<0:continue
  if any(not inside(x+dx,y+dy) and closest(x+dx,y+dy)[0]>48 for dx,dy in [(-98,-98),(98,-98),(98,98),(-98,98)]):continue
  edges=[]
  for direction,dx,dy in [('L',-200,0),('R',200,0),('T',0,200),('B',0,-200)]:
   if not inside(x+dx,y+dy) or (0<x+dx<400 and y+dy<0):edges.append(direction)
  # Floors on either side of the divider meet its outer faces with a border.
  if y>=0 and x==100:edges.append('R')
  if y>=0 and x==300:edges.append('L')
  if 'L' in edges and 'T' in edges:name='Left_Top'
  elif 'L' in edges and 'B' in edges:name='Left_Bottom'
  elif 'R' in edges and 'T' in edges:name='Right_Top'
  elif 'R' in edges and 'B' in edges:name='Right_Bottom'
  elif 'L' in edges:name='Left_Middle'
  elif 'R' in edges:name='Right_Middle'
  elif 'T' in edges:name='Middle_Top'
  elif 'B' in edges:name='Middle_Bottom'
  else:name='Center'
  floor(name,x,y,180 if name!='Center' else rng.choice([0,90,180,270]))
# Smaller border pieces follow the curved and diagonal walls, filling the non-grid margins.
for label,center,a,b,inside_sign in [('NE',(1200,800),0,90,-1),('NWupper',(-600,800),90,180,-1),('NWlower',(-1000,800),-90,0,1),('West',(-1541.421356,-250),-45,45,1)]:
 for i in range(3):
  t=math.radians(a+(b-a)*(i+.5)/3);rr=200+inside_sign*85;x=center[0]+rr*math.cos(t);y=center[1]+rr*math.sin(t)
  if inside(x,y):
   # Middle_Top border is native +Y; aim it toward the boundary in world space.
   normal=t+(math.pi if inside_sign==1 else 0);worldyaw=-math.degrees(normal)-90
   floor('Middle_Top',x,y,-worldyaw,(.62,1),label='Curved Floor Border '+label+' '+str(i))
for t in [.25,.7]:
 x=1000+400*t-38;y=-1000+200*t+76
 floor('Middle_Bottom',x,y,153.435,(1,1),label='Chamfer Floor Border')
# Three clearly separate spike-trap placeholders; no damage, animation, or Blueprint logic.
for idx,(lo,hi) in enumerate([(-1000,-670),(-660,-340),(-330,0)],1):
 cy=(lo+hi)/2;length=hi-lo-20;folder='Room/Traps/Trap %d'%idx
 mesh('Trap %d Recess'%idx,'/Engine/BasicShapes/Cube',200,cy,2,(3.74,length/100,.12),mat=black,folder=folder)
 for x in [10,390]:mesh('Trap %d Side Frame'%idx,'/Engine/BasicShapes/Cube',x,cy,13,(.18,length/100,.18),mat=iron,folder=folder)
 for y in [lo+12,hi-12]:mesh('Trap %d End Frame'%idx,'/Engine/BasicShapes/Cube',200,y,13,(4,.18,.18),mat=iron,folder=folder)
 for ix in range(5):
  for iy in range(4):
   xx=55+ix*72;yy=lo+50+iy*(length-70)/3
   mesh('Trap %d Spike %d %d'%(idx,ix,iy),'/Engine/BasicShapes/Cone',xx,yy,27,(.16,.16,.5),mat=spike,folder=folder)
 for x in [23,377]:
  for j in range(3):mesh('Trap %d Warning'%idx,'/Engine/BasicShapes/Cube',x,cy+(j-1)*62,24,(.15,.35,.025),yaw=30,mat=red,folder=folder,coll=False)
# Simple warm wall lamps give the gray stone a focused, torch-lit temple atmosphere.
for i,(x,y) in enumerate([(-1260,450),(-550,850),(1250,650),(1250,-610),(-1220,-850),(750,-860)]):
 mesh('Lamp %02d Mount'%i,'/Engine/BasicShapes/Cylinder',x,y,55,(.42,.42,1.1),mat=iron,folder='Room/Lamps')
 mesh('Lamp %02d Glow'%i,'/Engine/BasicShapes/Sphere',x,y,120,(.28,.28,.36),mat=hot,folder='Room/Lamps',coll=False)
 light=A.spawn_actor_from_class(u.PointLight,point(x,y,165));light.set_actor_label('Warm Lamp %02d'%i);light.set_folder_path('Lighting/Room Lamps');c=light.light_component;c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_properties(dict(intensity=3500.,attenuation_radius=620.,light_color=u.Color(255,165,65,255),source_radius=18.,cast_shadows=True))
for a in A.get_all_level_actors():
 if isinstance(a,u.SkyAtmosphere):
  a.set_actor_hidden_in_game(True)
  for c in a.get_components_by_class(u.SceneComponent):c.set_visibility(False,True)
 if isinstance(a,u.SkyLight):a.light_component.set_editor_property('intensity',.35)
 if isinstance(a,u.DirectionalLight):
  a.light_component.set_mobility(u.ComponentMobility.MOVABLE);a.light_component.set_editor_property('atmosphere_sun_light',False)
  a.light_component.set_editor_property('intensity',3.2 if a.get_actor_label()=='Sun' else 1.5)
 if isinstance(a,u.PostProcessVolume):
  st=a.get_editor_property('settings');st.set_editor_properties(dict(override_auto_exposure_method=True,auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,override_auto_exposure_apply_physical_camera_exposure=True,auto_exposure_apply_physical_camera_exposure=False,override_auto_exposure_bias=True,auto_exposure_bias=0.));a.set_editor_property('settings',st)
W.set_level_viewport_camera_info(u.Vector(0,2900,3400),u.Rotator(pitch=-51,yaw=-90))
assert L.save_current_level()
report={'counts':counts,'floor_placements':placements,'actors':len(A.get_all_level_actors()),'backup':str(backup)}
(DATA/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({'counts':counts,'actors':report['actors']},indent=2))
