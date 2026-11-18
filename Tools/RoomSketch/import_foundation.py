import unreal as u
B='/Game/Levels/RoomSketch_Support'
opt=u.FbxImportUI();opt.set_editor_properties(dict(import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH))
opt.static_mesh_import_data.set_editor_properties(dict(combine_meshes=True,convert_scene=False,convert_scene_unit=False,auto_generate_collision=False))
t=u.AssetImportTask();t.set_editor_properties(dict(filename='C:/Users/zhanx/Desktop/Beta Arcade/Beta_Arcade_Team_14/Tools/RoomSketch/SM_RoomFoundation.obj',destination_path=B,destination_name='SM_RoomFoundation',automated=True,replace_existing=False,save=True,options=opt))
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
print('IMPORTED',t.imported_object_paths)
for p in t.imported_object_paths:
 a=u.load_asset(p)
 if isinstance(a,u.StaticMesh):print('BOUNDS',a.get_bounding_box())
