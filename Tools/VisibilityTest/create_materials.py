import unreal as u
B='/Game/Levels/VisibilityTest_Support'
E=u.EditorAssetLibrary; T=u.AssetToolsHelpers.get_asset_tools(); M=u.MaterialEditingLibrary
def st(cls,**kw):
 o=cls();o.set_editor_properties(kw);return o
c=u.load_asset(B+'/MPC_Visibility') or T.create_asset('MPC_Visibility',B,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
c.set_editor_property('vector_parameters',[st(u.CollectionVectorParameter,parameter_name='PlayerPosition',default_value=u.LinearColor(0,0,-10000,1)),st(u.CollectionVectorParameter,parameter_name='CameraPosition',default_value=u.LinearColor(-1000,0,1500,1))])
c.set_editor_property('scalar_parameters',[st(u.CollectionScalarParameter,parameter_name='RevealRadius',default_value=170),st(u.CollectionScalarParameter,parameter_name='RevealEnabled',default_value=0)])
E.save_loaded_asset(c,False)
for source,name in [('M_WALL_blinn2','M_Wall_Reveal'),('M_CURVE_WALL','M_Curve_Reveal')]:
 mat=E.duplicate_asset('/Game/Levels/ART_ASSETS_Support/'+source,B+'/'+name)
 assert mat
 mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
 mat.set_editor_property('two_sided',True)
 custom=M.create_material_expression(mat,u.MaterialExpressionCustom,-300,600)
 custom.set_editor_property('description','Local camera-to-player cutout; visual only, collision remains solid')
 custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
 custom.set_editor_property('inputs',[st(u.CustomInput,input_name=n) for n in ['World','Player','Camera','Radius','Enabled']])
 custom.set_editor_property('code','''float3 ray = Player.xyz - Camera.xyz;
float rayLength = max(length(ray), 1.0);
float3 direction = ray / rayLength;
float along = dot(World - Camera.xyz, direction);
float distanceToRay = length((World - Camera.xyz) - direction * along);
float inFront = step(0.0, along) * step(along, rayLength + 45.0);
float aboveFloor = smoothstep(25.0, 65.0, World.z);
float hole = (1.0 - smoothstep(Radius * 0.78, Radius, distanceToRay)) * inFront * aboveFloor;
return 1.0 - hole * saturate(Enabled);''')
 world=M.create_material_expression(mat,u.MaterialExpressionWorldPosition,-900,500)
 M.connect_material_expressions(world,'',custom,'World')
 for i,(param,pin) in enumerate([('PlayerPosition','Player'),('CameraPosition','Camera'),('RevealRadius','Radius'),('RevealEnabled','Enabled')]):
  n=M.create_material_expression(mat,u.MaterialExpressionCollectionParameter,-900,700+i*170)
  n.set_editor_property('collection',c);n.set_editor_property('parameter_name',param)
  assert M.connect_material_expressions(n,'',custom,pin),param
 assert M.connect_material_property(custom,'',u.MaterialProperty.MP_OPACITY_MASK)
 M.layout_material_expressions(mat);M.recompile_material(mat);E.save_loaded_asset(mat,False)
for name,color,rough in [('M_Backdrop',(0.065,0.085,0.075),.95),('M_DarkStone',(0.13,0.17,0.16),.9),('M_Path',(0.25,0.3,0.27),.9),('M_TestMarker',(0.04,0.5,0.42),.7)]:
 mat=T.create_asset(name,B,u.Material,u.MaterialFactoryNew())
 n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
 n.set_editor_property('constant',u.LinearColor(*color,1));M.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
 r=M.create_material_expression(mat,u.MaterialExpressionConstant);r.set_editor_property('r',rough);M.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
 M.recompile_material(mat);E.save_loaded_asset(mat,False)
print('VISIBILITY_MATERIALS_SAVED')
