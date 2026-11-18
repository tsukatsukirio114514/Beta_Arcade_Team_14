import unreal as u,json,re,uuid
from pathlib import Path
OUT=Path('C:/Users/zhanx/AppData/Local/Temp/visibility-room-20261118')
BASE='/Game/Levels/VisibilityTest_Support'
GT=u.BlueprintPorterGraphTools; BL=u.BlueprintPorterLibrary; EL=u.EditorAssetLibrary
MATH='/Script/Engine.KismetMathLibrary'; ACT='/Script/Engine.Actor'; GS='/Script/Engine.GameplayStatics'; ML='/Script/Engine.KismetMaterialLibrary'
P=BASE+'/BP_VisibilityCamera'
factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.load_class(None,'/Game/Blueprints/PlayerMechanics/BP_ActiveCamera.BP_ActiveCamera_C'))
bp=u.load_asset(P) if EL.does_asset_exist(P) else u.AssetToolsHelpers.get_asset_tools().create_asset('BP_VisibilityCamera',BASE,u.Blueprint,factory)
def checked():
 e=GT.compile_checked(bp);assert not e,e
for n,v in [('LimitX',600.),('LimitY',450.),('FollowSpeed',5.),('RevealRadius',170.),('RevealEnabled',1.),('CameraHeight',1450.),('CameraOffsetX',-1015.)]:
 if n not in BL.list_blueprint_variables(bp):assert u.BlueprintEditorLibrary.add_member_variable(bp,n,u.BlueprintEditorLibrary.get_basic_type_by_name('real'))
 u.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp,n,True)
 checked();u.get_default_object(bp.generated_class()).set_editor_property(n,v)
class G:
 def __init__(self,name,append=False):self.name=name;self.s=dict(nodes=[],links=[],append=append)
 def node(self,kind,name=None,parent=None,**defaults):
  i='n'+str(len(self.s['nodes']));n=dict(id=i,kind=kind)
  if name:n['name']=name
  if parent:n['class']=parent
  if defaults:n['defaults']={k:str(v) for k,v in defaults.items()}
  self.s['nodes'].append(n);return i
 def call(self,name,parent=None,**defaults):return self.node('call',name,parent,**defaults)
 def link(self,a,p,b,q):self.s['links'].append([a,p,b,q])
 def chain(self,*ns):
  for a,b in zip(ns,ns[1:]):self.link(a,'then',b,'execute')
 def get(self,n):return self.node('get',n),n
 def math(self,n,a=None,b=None,**kw):
  i=self.call(n,MATH,**kw)
  if a:self.link(*a,i,'A')
  if b:self.link(*b,i,'B')
  return i,'ReturnValue'
 def finish(self):
  (OUT/(self.name+'.json')).write_text(json.dumps(self.s,indent=2),encoding='utf8')
  e=GT.build_graph(bp,self.name,json.dumps(self.s));assert not e,self.name+': '+e
  checked()
g=G('UpdateVisibilityCamera');g.s['inputs']=[dict(name='DeltaTime',type='real')]
player=g.call('GetPlayerCharacter',GS,PlayerIndex='0')
valid=g.call('IsValid','/Script/Engine.KismetSystemLibrary');g.link(player,'ReturnValue',valid,'Object')
branch=g.node('branch');g.link(valid,'ReturnValue',branch,'Condition');g.chain('entry',branch)
pos=g.call('K2_GetActorLocation',ACT);g.link(player,'ReturnValue',pos,'self')
split=g.call('BreakVector',MATH);g.link(pos,'ReturnValue',split,'InVec')
target=g.call('MakeVector',MATH,Z='80.0')
for axis,limit in [('X','LimitX'),('Y','LimitY')]:
 clamp=g.call('FClamp',MATH);g.link(split,axis,clamp,'Value');g.link(*g.get(limit),clamp,'Max')
 minus=g.math('Multiply_DoubleDouble',g.get(limit),B='-1.0');g.link(*minus,clamp,'Min');g.link(clamp,'ReturnValue',target,axis)
current=g.call('K2_GetActorLocation',ACT)
interp=g.call('VInterpTo',MATH);g.link(current,'ReturnValue',interp,'Current');g.link(target,'ReturnValue',interp,'Target');g.link('entry','DeltaTime',interp,'DeltaTime');g.link(*g.get('FollowSpeed'),interp,'InterpSpeed')
move=g.call('K2_SetActorLocation',ACT,bSweep='false',bTeleport='true');g.link(interp,'ReturnValue',move,'NewLocation');g.link(branch,'then',move,'execute')
rotate=g.call('K2_SetActorRotation',ACT,NewRotation='0,0,0',bTeleportPhysics='true');g.chain(move,rotate)
cam=g.get('Camera')
offset=g.call('MakeVector',MATH);g.link(*g.get('CameraOffsetX'),offset,'X');g.link(*g.get('CameraHeight'),offset,'Z')
worldpos=g.math('Add_VectorVector',(current,'ReturnValue'),(offset,'ReturnValue'))
place=g.call('K2_SetWorldLocation','/Script/Engine.SceneComponent',bSweep='false',bTeleport='true');g.link(*cam,place,'self');g.link(*worldpos,place,'NewLocation')
orient=g.call('K2_SetWorldRotation','/Script/Engine.SceneComponent',NewRotation='-55,0,0',bSweep='false',bTeleport='true');g.link(*cam,orient,'self');g.chain(rotate,place,orient)
fov=g.call('SetFieldOfView','/Script/Engine.CameraComponent',InFieldOfView='60.0');g.link(*cam,fov,'self');g.chain(orient,fov)
pc=g.call('GetPlayerController',GS,PlayerIndex='0');view=g.call('SetViewTargetWithBlend','/Script/Engine.PlayerController',BlendTime='0.0');g.link(pc,'ReturnValue',view,'self');selfn=g.node('self');g.link(selfn,'self',view,'NewViewTarget');g.chain(fov,view)
last=view
for name,vec in [('PlayerPosition',(pos,'ReturnValue')),('CameraPosition',worldpos)]:
 color=g.call('Conv_VectorToLinearColor',MATH);g.link(*vec,color,'InVec')
 setp=g.call('SetVectorParameterValue',ML,Collection=BASE+'/MPC_Visibility.MPC_Visibility',ParameterName=name)
 g.link(color,'ReturnValue',setp,'ParameterValue');g.chain(last,setp);last=setp
for name in ['RevealRadius','RevealEnabled']:
 setp=g.call('SetScalarParameterValue',ML,Collection=BASE+'/MPC_Visibility.MPC_Visibility',ParameterName=name)
 g.link(*g.get(name),setp,'ParameterValue');g.chain(last,setp);last=setp
g.finish()
# Native Tick event override: do not invoke the parent camera's unrestricted follow/zoom.
s=(OUT/'BP_ActiveCamera/EventGraph.bpgraph.txt').read_text(encoding='utf-8-sig')
block=next(b for b in re.findall(r'^Begin Object.*?^End Object',s,re.M|re.S) if 'MemberName="ReceiveTick"' in b)
block=re.sub(r' ExportPath="[^"]+"','',block)
block=re.sub(r'LinkedTo=\([^\n]*?\),','',block)
block=re.sub(r'NodeGuid=[0-9A-F]+','NodeGuid='+uuid.uuid4().hex.upper(),block)
f=OUT/'tick_event.txt';f.write_text(block,encoding='utf8')
assert BL.import_blueprint_graph(bp,'EventGraph',str(f),True)
BL.export_blueprint_graphs(bp,str(OUT/'newcamera'))
s=(OUT/'newcamera/EventGraph.bpgraph.txt').read_text(encoding='utf-8-sig');event=re.search(r'Name="([^"]+)"',s)[1]
g=G('EventGraph',True);c=g.call('UpdateVisibilityCamera');g.link(event,'then',c,'execute');g.link(event,'DeltaSeconds',c,'DeltaTime');g.finish()
assert EL.save_loaded_asset(bp,False)
(OUT/'blueprint_result.json').write_text(json.dumps({'success':True,'asset':P}),encoding='utf8')
print('VISIBILITY_CAMERA_COMPILED_AND_SAVED')
