import unreal as u,json,shutil
from pathlib import Path
from datetime import datetime
def compact_room():
    root=Path('C:/Users/zhanx/Desktop/Beta Arcade/Beta_Arcade_Team_14');data=root/'Tools/RoomSketch'
    plan=json.loads((data/'compact_plan.json').read_text())
    A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);W=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert W.get_editor_world().get_path_name()=='/Game/Levels/L_VisibilityTest.L_VisibilityTest'
    assert not L.is_in_play_in_editor()
    actors={a.get_name():a for a in A.get_all_level_actors()}
    assert len(actors)==206,'Room changed after layout audit; re-audit before editing'
    assert all(x in actors for x in plan['delete'])
    backup=root.parent/'_backup'/('RoomCompact_Before_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir(parents=True)
    assert L.save_current_level()
    shutil.copy2(root/'Content/Levels/L_VisibilityTest.umap',backup/'L_VisibilityTest.umap')
    shutil.copy2('C:/Users/zhanx/AppData/Local/Temp/stone-room-sketch/resize_current.json',backup/'actors_before.json')
    shutil.copy2(data/'compact_plan.json',backup/'compact_plan.json')
    path='/Game/Levels/RoomSketch_Support/SM_RoomFoundation_Compact'
    assert not u.EditorAssetLibrary.does_asset_exist(path),'Use a fresh compact support asset name'
    opt=u.FbxImportUI();opt.set_editor_properties(dict(import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH))
    opt.static_mesh_import_data.set_editor_properties(dict(combine_meshes=True,convert_scene=False,convert_scene_unit=False,auto_generate_collision=False))
    task=u.AssetImportTask();task.set_editor_properties(dict(filename=str(data/'SM_RoomFoundation_Compact.obj'),destination_path='/Game/Levels/RoomSketch_Support',destination_name='SM_RoomFoundation_Compact',automated=True,replace_existing=False,save=True,options=opt))
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    foundation=u.load_asset(path);assert foundation
    SC=35.58799252791172
    fm={k:u.load_asset('/Game/Levels/ART_ASSETS_Support/M_FLOUR_'+k) for k in ['blinn1','blinn2']}
    wallmat=u.load_asset('/Game/Levels/ART_ASSETS_Support/M_WALL_blinn2')
    with u.ScopedEditorTransaction('Reduce room footprint by removing interior module bands'):
        for row in plan['move']:
            a=actors[row['id']];a.modify();a.set_actor_location(u.Vector(*row['p']),False,False)
        for row in plan['floors']:
            a=actors[row['id']];a.modify();c=a.static_mesh_component;c.modify()
            c.set_static_mesh(u.load_asset('/Game/Assets/STRUCTURE/MESH/'+row['mesh']))
            a.set_actor_rotation(u.Rotator(pitch=0,yaw=row['yaw'],roll=0),False)
            a.set_actor_label(('Floor Interior Variation - ' if row.get('variation') else 'Floor ')+row['mesh'])
            for i,slot in enumerate(c.static_mesh.static_materials):c.set_material(i,fm[str(slot.material_slot_name)])
        base=next(a for a in actors.values() if a.get_actor_label()=='Room Foundation')
        base.modify();base.static_mesh_component.modify();base.static_mesh_component.set_static_mesh(foundation)
        base.static_mesh_component.set_material(0,u.load_asset('/Game/Levels/RoomSketch_Support/M_Foundation'))
        # Preserve existing OBJ import axis compensation; this is a new support mesh, not a scaled room.
        base.set_actor_scale3d(u.Vector(1,-1,1))
        for row in plan['walls']:
            short=row['length']<270
            name='Wall_Straight_1G' if short else 'Wall_Straight_2G'
            a=A.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*row['p']),u.Rotator(yaw=row['yaw']-90 if short else row['yaw']))
            a.set_actor_label(row['label']);a.set_folder_path('Room/Walls')
            a.set_actor_scale3d(u.Vector(SC,SC*row['length']/200,SC) if short else u.Vector(SC*row['length']/400,SC,SC))
            c=a.static_mesh_component;c.set_static_mesh(u.load_asset('/Game/Assets/STRUCTURE/MESH/'+name));c.set_material(0,wallmat);c.set_collision_profile_name('BlockAll')
        for actor_id in plan['delete']:assert A.destroy_actor(actors[actor_id])
        for a in A.get_all_level_actors():
            if isinstance(a,u.RectLight) and a.get_actor_label().startswith('Bounce - '):
                a.light_component.modify();a.light_component.set_editor_property('attenuation_radius',1200.0)
                a.light_component.set_intensity(150.0 if 'West' in a.get_actor_label() else 200.0)
    A.clear_actor_selection_set()
    W.set_level_viewport_camera_info(u.Vector(x=0,y=1600,z=2400),u.Rotator(pitch=-55,yaw=-90,roll=0))
    L.editor_set_game_view(True);L.editor_invalidate_viewports()
    report={'backup':str(backup),'area_before_m2':plan['area_before_m2'],'area_after_m2':plan['area_after_m2'],'area_ratio':plan['area_ratio'],'actor_count':len(A.get_all_level_actors()),'removed_actor_count':len(plan['delete']),'new_straight_wall_count':len(plan['walls'])}
    (data/'compact_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
compact_room()
compact_capture=u.AutomationLibrary.take_high_res_screenshot(1600,1000,'Room_Compact_Review')
