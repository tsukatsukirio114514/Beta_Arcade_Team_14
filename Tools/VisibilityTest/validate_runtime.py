import unreal as u,time,json,traceback
from pathlib import Path
root=Path('C:/Users/zhanx/AppData/Local/Temp/visibility-room-20261118')
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();p=u.GameplayStatics.get_player_character(w,0)
cam=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,'/Game/Levels/VisibilityTest_Support/BP_VisibilityCamera.BP_VisibilityCamera_C'))[0]
cases=[('wall_hidden',(-250,360),1),('wall_solid',(-250,360),0),('pillar_hidden',(-240,-320),1),('corner_NE',(1110,900),1),('corner_NW',(-1110,900),1),('corner_SE',(1110,-900),1),('corner_SW',(-1110,-900),1)]
state={'i':-1,'phase':'next','when':0.,'rows':[]}
def next_case():
 state['i']+=1
 if state['i']>=len(cases):return False
 name,xy,on=cases[state['i']];p.character_movement.stop_movement_immediately();p.set_actor_location(u.Vector(xy[0],xy[1],120),False,True);cam.set_editor_property('RevealEnabled',float(on));state['when']=time.monotonic();state['phase']='settle';return True

def tick(dt):
 try:
  if state['phase']=='next':
   if next_case():return
   # Collision uses the player capsule sweep, including while visual cutout is enabled.
   cam.set_editor_property('RevealEnabled',1.)
   p.set_actor_location(u.Vector(0,0,120),False,True)
   p.set_actor_location(u.Vector(-1800,0,120),True,False)
   pos=p.get_actor_location();state['boundary_collision']=dict(x=pos.x,y=pos.y,passed=pos.x>-1200)
   p.set_actor_location(u.Vector(0,0,120),False,True)
   state['complete']=True;(root/'runtime_validation.json').write_text(json.dumps({k:v for k,v in state.items() if k!="handle"},indent=2),encoding='utf8');u.unregister_slate_post_tick_callback(state['handle']);return
  if state['phase']=='settle' and time.monotonic()-state['when']>3.5:
   name,xy,on=cases[state['i']];cp=cam.get_actor_location();pp=p.get_actor_location();cc=cam.get_component_by_class(u.CameraComponent)
   row={'case':name,'player':[pp.x,pp.y,pp.z],'camera_target':[cp.x,cp.y,cp.z],'clamped':abs(cp.x)<=600.05 and abs(cp.y)<=450.05,'reveal':u.MaterialLibrary.get_scalar_parameter_value(w,u.load_asset('/Game/Levels/VisibilityTest_Support/MPC_Visibility'),'RevealEnabled'),'view_rotation':str(cc.get_world_rotation())}
   state['rows'].append(row);u.AutomationLibrary.take_high_res_screenshot(1280,720,'Visibility_'+name)
   state['phase']='capture';state['when']=time.monotonic();(root/'runtime_progress.json').write_text(json.dumps({k:v for k,v in state.items() if k!="handle"},indent=2),encoding='utf8');return
  if state['phase']=='capture' and time.monotonic()-state['when']>2.0:state['phase']='next'
 except Exception:
  state['error']=traceback.format_exc();(root/'runtime_validation.json').write_text(json.dumps({k:v for k,v in state.items() if k!="handle"},indent=2),encoding='utf8');u.unregister_slate_post_tick_callback(state['handle'])
state['handle']=u.register_slate_post_tick_callback(tick)
print('RUNTIME_CHECKS_STARTED')
