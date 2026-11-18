import unreal as u,math,json,shutil
from pathlib import Path
from datetime import datetime
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);W=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert W.get_editor_world().get_path_name()=='/Game/Levels/L_VisibilityTest.L_VisibilityTest'
assert not L.is_in_play_in_editor()
root=Path('C:/Users/zhanx/Desktop/Beta Arcade/Beta_Arcade_Team_14')
backup=root.parent/'_backup'/('WallFloorAlignment_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir(parents=True)
assert L.save_current_level();shutil.copy2(root/'Content/Levels/L_VisibilityTest.umap',backup/'L_VisibilityTest.umap')
actors=A.get_all_level_actors();bylabel={a.get_actor_label():a for a in actors};records=[]
def adjust(a,p=None,s=None):
 old=a.get_actor_transform();records.append({'actor':a.get_name(),'label':a.get_actor_label(),'before':str(old)})
 if p is not None:a.set_actor_location(u.Vector(*p),False,False)
 if s is not None:a.set_actor_scale3d(u.Vector(*s))
 records[-1]['after']=str(a.get_actor_transform())
def shift(label,dx=0,dy=0):
 a=bylabel[label];p=a.get_actor_location();adjust(a,[p.x+dx,p.y+dy,p.z])
for i in range(4):shift('North Wall_%02d'%i,dy=-40)
for i in range(4):shift('East Wall_%02d'%i,dx=40)
shift('Corner Northwest Step',dy=-40)
shift('Northwest Ledge_00',dy=-40)
# Increase/decrease arc radii about their actual construction centers; preserve wall height.
for label,cx,cy,factor in [('Northeast Curve A',1200,-800,1.2),('Northeast Curve B',1200,-800,1.2),('Northwest Upper Curve',-600,-800,1.2),('Northwest Lower Curve',-1000,-800,.8)]:
 a=bylabel[label];p=a.get_actor_location();s=a.get_actor_scale3d();adjust(a,[cx+(p.x-cx)*factor,cy+(p.y-cy)*factor,p.z],[s.x*factor,s.y*factor,s.z])
# Extend the west straight spans to meet the user's relocated corner pieces.
for label,dy,length in [('West Upper Wall_00',-20,468.578644),('West Lower Wall_00',20,368.578644)]:
 a=bylabel[label];p=a.get_actor_location();s=a.get_actor_scale3d();adjust(a,[p.x,p.y+dy,p.z],[s.x*(length+40)/length,s.y,s.z])
# Join the south reference wall to the shifted east perimeter.
a=bylabel['Southeast Chamfer_00'];p=a.get_actor_location();s=a.get_actor_scale3d()
start=(1000,1040);end=(1440,824.72136);dx=end[0]-start[0];dy=end[1]-start[1]
adjust(a,[(start[0]+end[0])/2,(start[1]+end[1])/2,p.z],[s.x*math.hypot(dx,dy)/math.hypot(400,200),s.y,s.z]);a.set_actor_rotation(u.Rotator(yaw=math.degrees(math.atan2(dy,dx))),False)
a=bylabel['East Wall_00'];p=a.get_actor_location();s=a.get_actor_scale3d();adjust(a,[p.x,p.y+12.36068,p.z],[s.x*424.72136/400,s.y,s.z])
shift('Structural Pillar 00',dy=-40)
shift('Structural Pillar 02',dy=40)
shift('Structural Pillar 03',dx=40,dy=24.72136)
shift('Structural Pillar 04',dx=-50,dy=-40)
# Shorten the floor cells next to the divider, keeping their far seam fixed.
for a in actors:
 if str(a.get_folder_path())!='Room/Floor' or not a.get_actor_label().startswith('Floor '):continue
 p=a.get_actor_location();s=a.get_actor_scale3d()
 if p.y<0 and abs(p.x-100)<.01:adjust(a,[p.x-22.5,p.y,p.z],[s.x*.775,s.y,s.z])
 if p.y<0 and abs(p.x-300)<.01:adjust(a,[p.x+22.5,p.y,p.z],[s.x*.775,s.y,s.z])
# Reveal the curved floor edging instead of burying it below the inner wall face.
for prefix,center in [('Curved Floor Border NE ',(1200,-800)),('Curved Floor Border NWupper ',(-600,-800))]:
 for i in range(3):
  a=bylabel[prefix+str(i)];p=a.get_actor_location();d=math.hypot(p.x-center[0],p.y-center[1]);r=d-30
  adjust(a,[center[0]+(p.x-center[0])*r/d,center[1]+(p.y-center[1])*r/d,p.z])
# Correct the chamfer edging tangent; its previous rotation crossed the wall.
for a in actors:
 if a.get_actor_label()=='Chamfer Floor Border':
  a.set_actor_rotation(u.Rotator(yaw=153.9344),False)
assert L.save_current_level()
(backup/'changes.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print('BACKUP',str(backup));print('ADJUSTED',len(records))
W.set_level_viewport_camera_info(u.Vector(0,2350,3000),u.Rotator(pitch=-55,yaw=-90))
