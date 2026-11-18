import unreal as u,math,random,json
from pathlib import Path
B='/Game/Levels/VisibilityTest_Support'; S='/Game/Assets/STRUCTURE/MESH/'; MAP='/Game/Levels/L_VisibilityTest'
E=u.EditorAssetLibrary; A=u.get_editor_subsystem(u.EditorActorSubsystem); L=u.get_editor_subsystem(u.LevelEditorSubsystem); W=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert not L.is_in_play_in_editor()
assert not E.does_asset_exist(MAP),'Do not replace an existing test map'
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Please preserve dirty maps before creating a new one'
reg=u.AssetRegistryHelpers.get_asset_registry();reg.scan_paths_synchronous([B],True)
camclass=u.load_class(None,B+'/BP_VisibilityCamera.BP_VisibilityCamera_C');assert camclass
assert L.new_level(MAP)
world=W.get_editor_world(); world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Game/Blueprints/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C'))
scale=35.58799252791172
mats={n:u.load_asset(B+'/'+n) for n in ['M_Wall_Reveal','M_Curve_Reveal','M_Backdrop','M_DarkStone','M_Path','M_TestMarker']}
floormat=u.load_asset('/Game/Levels/ART_ASSETS_Support/M_FLOUR_blinn1');cube=u.load_asset('/Engine/BasicShapes/Cube');cylinder=u.load_asset('/Engine/BasicShapes/Cylinder')
def mesh(label,asset,pos,sc=(1,1,1),yaw=0,mat=None,folder='Architecture',coll=True):
 a=A.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos),u.Rotator(yaw=yaw));a.set_actor_label(label);a.set_folder_path(folder)
 c=a.static_mesh_component;c.set_static_mesh(u.load_asset(asset) if isinstance(asset,str) else asset)
 a.set_actor_scale3d(u.Vector(*sc))
 if mat:
  for i in range(max(c.get_num_materials(),1)):c.set_material(i,mat)
 c.set_collision_profile_name('BlockAll' if coll else 'NoCollision')
 return a

def stone(label,asset,pos,yaw=0,mat=None):return mesh(label,S+asset,pos,(scale,scale,scale),yaw,mat or mats['M_Wall_Reveal'])
def block(label,pos,dimensions):
 a=mesh(label,cube,pos,tuple(d/100 for d in dimensions),folder='Collision')
 a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True);return a
mesh('Peripheral Ground',cube,(0,0,-50),(100,100,.6),mat=mats['M_Backdrop'],folder='Backdrop')
mesh('Arena Foundation',cube,(0,0,-8),(25.5,21.5,.3),mat=mats['M_DarkStone'],folder='Architecture')
for x in range(12):
 for y in range(10):
  stone('Floor_%02d_%02d'%(x,y),'Center',(-1100+x*200,-900+y*200,0),mat=floormat).set_folder_path('Architecture/Floor')
for side,y in [('South',-1040),('North',1040)]:
 for i,x in enumerate(range(-1000,1001,400)):stone(side+'_Wall_'+str(i),'Wall_Straight_2G',(x,y,14))
 block(side+'_Boundary',(0,y,200),(2460,90,400))
for side,x in [('West',-1240),('East',1240)]:
 for i,y in enumerate(range(-800,801,400)):stone(side+'_Wall_'+str(i),'Wall_Straight_2G',(x,y,14),90)
 block(side+'_Boundary',(x,0,200),(90,2060,400))
for x in [-1240,1240]:
 for y in [-1040,1040]:stone('Corner_Pier','Pillar_A',(x,y,14))
for i,(x,y) in enumerate([(-380,-320),(340,320),(-620,650)]):
 stone('Occlusion_Pillar_'+str(i),'Pillar_A',(x,y,14));block('Pillar_Collision_'+str(i),(x,y,150),(90,120,280))
stone('Interior_Test_Wall','Wall_Straight_2G',(-420,360,14),90)
block('Interior_Wall_Collision',(-420,360,150),(88,390,280))
stone('Curved_90','Wall_Curved_R2m_91',(650,-560,14),0,mats['M_Curve_Reveal'])
stone('Curved_45','Arc45_Course1_Stone1',(720,390,14),90,mats['M_Curve_Reveal'])
# Broad scenery apron: readable near the room, darker farther out.
rng=random.Random(18)
for i in range(75):
 x=rng.uniform(-3900,3900);y=rng.uniform(-3500,3500)
 if abs(x)<1550 and abs(y)<1350:continue
 dims=(rng.uniform(100,420),rng.uniform(100,340),rng.uniform(40,210))
 a=mesh('Ruin_Block_%02d'%i,cube,(x,y,-20+dims[2]/2),tuple(d/100 for d in dims),rng.uniform(-12,12),mats['M_DarkStone'],'Backdrop/Rubble',False)
for i,(x,y,yaw) in enumerate([(-1900,-1600,0),(-1900,900,90),(1700,1700,0),(2100,-1300,90),(400,2200,0),(-300,-2200,0)]):
 a=stone('Distant_Wall_'+str(i),'Wall_Straight_2G',(x,yaw*0+y,-20),yaw,u.load_asset('/Game/Levels/ART_ASSETS_Support/M_WALL_blinn2'));a.set_folder_path('Backdrop/Ruins')
# Static ring marks where to check visibility of ground beneath a foreground blocker.
for i in range(48):
 t=i*math.tau/48
 mesh('Ground_Ring_%02d'%i,cube,(-250+135*math.cos(t),360+135*math.sin(t),26),(.11,.28,.018),math.degrees(t),mats['M_TestMarker'],'Test Markers',False)
start=A.spawn_actor_from_class(u.PlayerStart,u.Vector(0,0,125));start.set_actor_label('Player Start');start.set_folder_path('Gameplay')
cam=A.spawn_actor_from_class(camclass,u.Vector(0,0,80));cam.set_actor_label('Visibility Camera');cam.set_folder_path('Gameplay')
# Outdoor daylight, with peripheral tone controlled by backdrop materials.
sun=A.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1000),u.Rotator(pitch=-55,yaw=-35));sun.set_actor_label('Sun');sun.set_folder_path('Lighting')
sun.light_component.set_editor_property('intensity',4.0);sun.light_component.set_editor_property('light_color',u.Color(255,238,210,255));sun.light_component.set_editor_property('atmosphere_sun_light',True)
sky=A.spawn_actor_from_class(u.SkyAtmosphere,u.Vector());sky.set_folder_path('Lighting')
sl=A.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,500));sl.set_folder_path('Lighting');sl.light_component.set_editor_property('real_time_capture',True);sl.light_component.set_editor_property('intensity',1.0)
pp=A.spawn_actor_from_class(u.PostProcessVolume,u.Vector());pp.set_folder_path('Lighting');pp.set_editor_property('unbound',True)
settings=pp.get_editor_property('settings');settings.set_editor_property('override_auto_exposure_method',True);settings.set_editor_property('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL);settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',10.0);pp.set_editor_property('settings',settings)
W.set_level_viewport_camera_info(u.Vector(-2400,-2400,2700),u.Rotator(pitch=-39,yaw=45))
assert L.save_current_level()
Path('C:/Users/zhanx/AppData/Local/Temp/visibility-room-20261118/map_result.json').write_text(json.dumps({'map':MAP,'actors':len(A.get_all_level_actors())}),encoding='utf8')
print('VISIBILITY_MAP_SAVED',len(A.get_all_level_actors()))
