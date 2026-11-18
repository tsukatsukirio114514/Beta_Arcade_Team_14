import unreal as u,json,re,uuid
from pathlib import Path
BASE='/Game/Levels/VisibilityTest_Support';OUT=Path('C:/Users/zhanx/AppData/Local/Temp/visibility-room-20261118');GT=u.BlueprintPorterGraphTools;BL=u.BlueprintPorterLibrary;E=u.EditorAssetLibrary
factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.load_class(None,'/Game/Blueprints/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController.BP_ThirdPersonPlayerController_C'))
bp=u.AssetToolsHelpers.get_asset_tools().create_asset('BP_VisibilityController',BASE,u.Blueprint,factory);assert bp
spec=dict(nodes=[
 dict(id='cam',kind='call',name='GetActorOfClass',**{'class':'/Script/Engine.GameplayStatics'},defaults={'ActorClass':BASE+'/BP_VisibilityCamera.BP_VisibilityCamera_C'}),
 dict(id='read',kind='get',name='RevealEnabled',**{'class':BASE+'/BP_VisibilityCamera.BP_VisibilityCamera_C'}),
 dict(id='toggle',kind='call',name='Subtract_DoubleDouble',**{'class':'/Script/Engine.KismetMathLibrary'},defaults={'A':'1.0'}),
 dict(id='write',kind='set',name='RevealEnabled',**{'class':BASE+'/BP_VisibilityCamera.BP_VisibilityCamera_C'})],
 links=[['entry','then','cam','execute'],['cam','then','write','execute'],['cam','ReturnValue','read','self'],['read','RevealEnabled','toggle','B'],['toggle','ReturnValue','write','RevealEnabled'],['cam','ReturnValue','write','self']])
e=GT.build_graph(bp,'ToggleWallReveal',json.dumps(spec));assert not e,e
assert not GT.compile_checked(bp)
s=Path('C:/Users/zhanx/Desktop/Beta Arcade/UE58_Migration/audit57/graphs/BP_ThirdPersonCharacter/EventGraph.bpgraph.txt').read_text(encoding='utf-8-sig')
b=next(b for b in re.findall(r'^Begin Object.*?^End Object',s,re.M|re.S) if 'Class=/Script/BlueprintGraph.K2Node_InputKey ' in b.splitlines()[0])
b=re.sub(r'InputKey=\w+','InputKey=V',b);b=re.sub(r' ExportPath="[^"]+"','',b);b=re.sub(r'LinkedTo=\([^\n]*?\),','',b);b=re.sub(r'NodeGuid=[0-9A-F]+','NodeGuid='+uuid.uuid4().hex.upper(),b)
f=OUT/'key.txt';f.write_text(b,encoding='utf8');assert BL.import_blueprint_graph(bp,'EventGraph',str(f),True)
BL.export_blueprint_graphs(bp,str(OUT/'controller'))
s=(OUT/'controller/EventGraph.bpgraph.txt').read_text(encoding='utf-8-sig');node=re.search(r'Name="([^"]+)"',s)[1]
e=GT.build_graph(bp,'EventGraph',json.dumps(dict(append=True,nodes=[dict(id='toggle',kind='call',name='ToggleWallReveal')],links=[[node,'Pressed','toggle','execute']])));assert not e,e
assert not GT.compile_checked(bp);assert E.save_loaded_asset(bp,False)
factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.load_class(None,'/Game/Blueprints/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C'))
gm=u.AssetToolsHelpers.get_asset_tools().create_asset('BP_VisibilityGameMode',BASE,u.Blueprint,factory);assert gm
u.get_default_object(gm.generated_class()).set_editor_property('player_controller_class',bp.generated_class());assert not GT.compile_checked(gm);assert E.save_loaded_asset(gm,False)
print('VISIBILITY_CONTROLLER_AND_MODE_SAVED')
