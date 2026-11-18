import unreal as u,math,re,json,shutil
from pathlib import Path
from datetime import datetime
A=u.get_editor_subsystem(u.EditorActorSubsystem);W=u.get_editor_subsystem(u.UnrealEditorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);world=W.get_editor_world()
assert world.get_path_name()=='/Game/Levels/L_VisibilityTest.L_VisibilityTest' and not L.is_in_play_in_editor()
assert not any(a.get_actor_label().startswith('Room Barrel ') for a in A.get_all_level_actors())
mesh=u.load_asset('/Game/Assets/PROPS/MESH/BARRELS');mat=u.load_asset('/Game/Assets/PROPS/MAT/M_BARRELS');assert mesh and mat
places=[(-1230,820,18,1.0,'Southwest'),(-1090,845,-28,.94,'Southwest'),(-1180,685,67,1.03,'Southwest'),(1120,-830,12,1.0,'Northeast'),(1250,-680,-43,.92,'Northeast'),(-1150,-430,31,1.0,'Northwest'),(1240,270,81,1.0,'East'),(1250,405,-14,.96,'East')]
root=Path('C:/Users/zhanx/Desktop/Beta Arcade/Beta_Arcade_Team_14');backup=root.parent/'_backup'/('RoomBarrels_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir(parents=True)
assert L.save_current_level();shutil.copy2(root/'Content/Levels/L_VisibilityTest.umap',backup/'L_VisibilityTest.umap')
created=[];report=[]
with u.ScopedEditorTransaction('Dress room with eight wooden barrels'):
 for i,(x,y,yaw,scale,group) in enumerate(places,1):
  heights=[]
  for dx,dy in [(0,0),(-28,0),(28,0),(0,-28),(0,28)]:
   hit=u.SystemLibrary.line_trace_single(world,u.Vector(x+dx,y+dy,180),u.Vector(x+dx,y+dy,-30),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,created,u.DrawDebugTrace.NONE)
   assert hit,'No ground for barrel '+str(i)
   txt=hit.export_text();assert 'bBlockingHit=True' in txt
   z=float(re.search(r'ImpactPoint=\(X=[^,]+,Y=[^,]+,Z=([^\)]+)',txt).group(1));assert -5<z<45,z;heights.append(z)
  z=sorted(heights)[3]-.8
  a=A.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,y,z),u.Rotator(yaw=yaw));c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_material(0,mat);c.set_collision_profile_name('BlockAll');a.set_actor_scale3d(u.Vector(scale,scale,scale));a.set_actor_label('Room Barrel %02d'%i);a.set_folder_path('Room/Props/Barrels/'+group)
  created.append(a);report.append({'name':a.get_name(),'location':[x,y,z],'yaw':yaw,'scale':scale,'group':group})
assert L.save_current_level();(backup/'placed_barrels.json').write_text(json.dumps(report,indent=2))
print('PLACED',len(created),'SAVED',True,'BACKUP',str(backup))
W.set_level_viewport_camera_info(u.Vector(0,2700,3300),u.Rotator(pitch=-55,yaw=-90))
