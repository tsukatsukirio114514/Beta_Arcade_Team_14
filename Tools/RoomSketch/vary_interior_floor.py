import unreal as u,json,shutil
from pathlib import Path
from datetime import datetime
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);W=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert W.get_editor_world().get_path_name()=='/Game/Levels/L_VisibilityTest.L_VisibilityTest'
assert not L.is_in_play_in_editor()
choices=[(-1100,500,'Middle_Bottom',90),(-900,-100,'Left_Middle',0),(-700,700,'Right_Middle',180),(-700,100,'Middle_Top',90),(-500,-500,'Left_Bottom',180),(-300,500,'Middle_Bottom',0),(-300,-100,'Right_Middle',90),(-100,-700,'Left_Middle',270),(500,-300,'Middle_Top',0),(700,500,'Left_Middle',90),(700,-700,'Right_Middle',270),(900,100,'Right_Top',90),(1100,-300,'Middle_Bottom',180),(1100,700,'Middle_Top',270)]
centers={}
for a in A.get_all_level_actors():
 if isinstance(a,u.StaticMeshActor) and a.get_actor_label()=='Floor Center' and a.static_mesh_component.static_mesh.get_name()=='Center':
  p=a.get_actor_location();centers[(round(p.x),round(p.y))]=a
assert all((x,y) in centers for x,y,_,_ in choices)
materials={k:u.load_asset('/Game/Levels/ART_ASSETS_Support/M_FLOUR_'+k) for k in ['blinn1','blinn2']}
meshes={n:u.load_asset('/Game/Assets/STRUCTURE/MESH/'+n) for _,_,n,_ in choices}
assert all(meshes.values()) and all(materials.values())
root=Path('C:/Users/zhanx/Desktop/Beta Arcade/Beta_Arcade_Team_14')
backup=root.parent/'_backup'/('InteriorFloorVariation_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir(parents=True)
assert L.save_current_level();shutil.copy2(root/'Content/Levels/L_VisibilityTest.umap',backup/'L_VisibilityTest.umap')
changes=[]
with u.ScopedEditorTransaction('Vary a minority of interior floor modules'):
 for i,(x,y,name,yaw) in enumerate(choices,1):
  a=centers[(x,y)];c=a.static_mesh_component
  changes.append(dict(actor=a.get_name(),before_mesh=c.static_mesh.get_path_name(),before_transform=str(a.get_actor_transform()),new_mesh=name,new_yaw=yaw))
  a.modify();c.modify();c.set_static_mesh(meshes[name])
  for j,slot in enumerate(c.static_mesh.static_materials):c.set_material(j,materials[str(slot.material_slot_name)])
  a.set_actor_rotation(u.Rotator(yaw=yaw),False);a.set_actor_label('Floor Interior Variation %02d - %s'%(i,name))
assert L.save_current_level()
(backup/'changes.json').write_text(json.dumps(changes,indent=2))
print('REPLACED',len(choices),'ORIGINAL_INTERIOR',len(centers),'CENTER_REMAINING',len(centers)-len(choices),'BACKUP',str(backup))
W.set_level_viewport_camera_info(u.Vector(-200,1900,2900),u.Rotator(pitch=-65,yaw=-90))
