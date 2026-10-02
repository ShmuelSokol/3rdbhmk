"""Offline preflight gate checks. No Unreal, subprocesses, or file writes."""
import ast
import copy
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from haram_threshold_study_common import validate_preflight_record, require


def main():
    wrapper_source = Path(__file__).with_name('run_haram_threshold_study.ps1').read_text(encoding='utf-8')
    ini_args = re.findall(r'-ini:Engine:([^\s\x27]+)', wrapper_source)
    require(len(ini_args) == 6 and all(',' not in arg for arg in ini_args), 'Expected six separate INI overrides')
    expected_ini = {
        '[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=999',
        '[DevOptions.Shaders]:NumUnusedShaderCompilingThreadsDuringGame=999',
        '[DevOptions.Shaders]:bForceUseSCWMemoryPressureLimits=False',
        '[/Script/Engine.RendererSettings]:r.DynamicGlobalIlluminationMethod=0',
        '[/Script/Engine.RendererSettings]:r.ReflectionMethod=0',
        '[/Script/Engine.RendererSettings]:r.Shadow.Virtual.Enable=0'}
    require(set(ini_args) == expected_ini, 'INI section/key/value drift')
    now = datetime.now(timezone.utc)
    revision, inputs = {'script': 'hash'}, {'source': 'inputhash'}
    record = dict(status='preflight-passed', revisionHashes=revision, protectedBefore=inputs,
                  protectedAfter=inputs, completedUtc=now.isoformat(), sourceTriangleCount=180,
                  entryNoPIE={'world':'/Engine/Maps/Entry', 'gameWorld':None},
                  queries=dict(collisionEnabled=True, castShadow=True, collisionNumeric=1,
                               shadowNumeric=1, auditedFunctions=5))
    wrapper = dict(status='preflight-passed', exitCode=0, nativeReceiptSha256='receipt')
    def validate(r, w):
        validate_preflight_record(r, w, 'receipt', revision, inputs, now)
    validate(record, wrapper)
    cases = [('status','failed'), ('revisionHashes',{}), ('protectedAfter',{}),
             ('completedUtc',(now-timedelta(seconds=3601)).isoformat()),
             ('completedUtc',(now+timedelta(seconds=1)).isoformat()),
             ('entryNoPIE',{'world':'/Engine/Maps/Entry','gameWorld':'PIE'}),
             ('sourceTriangleCount',179), ('queries',dict(record['queries'],collisionEnabled=False)),
             ('queries',dict(record['queries'],castShadow=1)),
             ('queries',dict(record['queries'],shadowNumeric=0))]
    for key, value in cases:
        r = copy.deepcopy(record)
        r[key] = value
        try:
            validate(r, wrapper)
        except RuntimeError:
            continue
        raise RuntimeError('Accepted invalid native field '+key)
    for key, value in [('status','failed'),('exitCode',1),('nativeReceiptSha256','tampered')]:
        try:
            validate(record, dict(wrapper, **{key:value}))
        except RuntimeError:
            continue
        raise RuntimeError('Accepted invalid wrapper '+key)
    tree = ast.parse(Path(__file__).with_name('study_haram_threshold_sides.py').read_text())
    cdo = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AuditedMeshQueries')
    calls = {n.func.attr for n in ast.walk(cdo) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
             and isinstance(n.func.value,ast.Attribute) and n.func.value.attr=='_cdo'}
    require(calls == {'get_path_name','get_lod_build_settings','get_simple_collision_count',
                     'get_convex_collision_count','is_section_collision_enabled','is_section_cast_shadow_enabled'},
            'CDO allowlist changed')
    preflight = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='preflight')
    called = {n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(preflight)
              if isinstance(n,ast.Call) and isinstance(n.func,(ast.Attribute,ast.Name))}
    require(not called & {'create_candidate','duplicate_asset','save_loaded_asset','spawn_actor_from_class',
                         'capture_scene','set_editor_property','load_map'}, 'Preflight mutation introduced')
    require(not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='quit_editor'
                    for n in ast.walk(tree)), 'Commandlet must return normally')
    loads = [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='load_map']
    require(len(loads)==1 and len(loads[0].args)==1 and isinstance(loads[0].args[0],ast.Constant)
            and loads[0].args[0].value=='/Engine/Maps/Entry', 'Only the hardcoded Entry load is permitted')
    from types import SimpleNamespace
    from study_haram_threshold_sides import initialize_entry_world, validate_isolated_files, probe_build_api, attributed_counter, mapping_render_profile
    profile={'r.DynamicGlobalIlluminationMethod':0,'r.ReflectionMethod':0,'r.Shadow.Virtual.Enable':0,'r.Nanite':1}
    def profile_ue(values):
        return SimpleNamespace(SystemLibrary=SimpleNamespace(get_console_variable_int_value=values.__getitem__))
    require(mapping_render_profile(profile_ue(profile))['cvars']==profile, 'Valid render profile rejected')
    for key in profile:
        wrong=dict(profile);wrong[key]=1-profile[key]
        try:
            mapping_render_profile(profile_ue(wrong))
        except RuntimeError:
            continue
        raise RuntimeError('Render profile drift accepted: '+key)
    corners = [dict(positions=[[0,0,0],[1,0,0],[0,1,0]], materialId=0,
                    attrs={'normal':[[0,0,1]]*3,'uv0':[[0,0],[1,0],[0,1]],'color':[[1,1,1,1]]*3})]
    reordered = copy.deepcopy(corners)
    reordered[0]['positions'] = reordered[0]['positions'][1:] + reordered[0]['positions'][:1]
    for key,value in reordered[0]['attrs'].items(): reordered[0]['attrs'][key] = value[1:] + value[:1]
    reordered[0]['materialId'] = 1
    require(attributed_counter(corners) == attributed_counter(reordered), 'Cyclic/section reorder rejected')
    for key in ('normal','uv0','color'):
        changed=copy.deepcopy(corners)
        changed[0]['attrs'][key][0][0] += 0.25
        require(attributed_counter(corners) != attributed_counter(changed), 'Corner attribute change missed: '+key)
    candidate = 'isolated/candidate.uasset'
    for files,save,verify,status,saved,expected in [
        ([],True,False,'failed',False,True),
        ([candidate],True,False,'failed',False,True),
        ([],True,False,'captured-review-pending',False,False),
        ([],True,False,'failed',True,False),
        ([],False,True,'failed',False,False),
        ([candidate],True,False,'captured-review-pending',True,True),
        ([candidate],False,True,'captured-review-pending',False,True),
        ([],False,False,'captured-review-pending',False,True),
        ([candidate],False,False,'failed',False,False),
        (['foreign.uasset'],True,False,'failed',False,False),
        ([candidate,'foreign.uasset'],True,False,'captured-review-pending',True,False)]:
        try:
            validate_isolated_files(files,candidate,save,verify,status,saved)
            passed=True
        except RuntimeError:
            passed=False
        require(passed == expected, 'Isolated-file lifecycle regression')
    # Fail early on missing reflection or enabled SCC, before asset tools/mesh reads.
    for source_control in (None, SimpleNamespace(is_enabled=None), SimpleNamespace(is_enabled=lambda:True)):
        ue = SimpleNamespace(StaticMaterial=lambda:None, TriangleID=lambda:None, SourceControl=source_control)
        try:
            probe_build_api(ue, None)
        except RuntimeError:
            continue
        raise RuntimeError('Invalid SourceControl accepted')
    class World:
        def __init__(self, name): self.name=name
        def get_outermost(self): return self
        def get_name(self): return self.name
        def get_path_name(self): return self.name+'.World'
    def world_case(initial, game=None, fail=False):
        state = dict(world=World(initial), calls=[])
        editor = SimpleNamespace(get_editor_world=lambda:state['world'], get_game_world=lambda:game)
        def load(path):
            state['calls'].append(path)
            if fail: return None
            state['world']=World(path)
            return state['world']
        ue = SimpleNamespace(UnrealEditorSubsystem=object(), get_editor_subsystem=lambda _:editor,
                             EditorLoadingAndSavingUtils=SimpleNamespace(load_map=load), log=lambda _:None)
        report={}
        try:
            initialize_entry_world(ue, report)
            passed=True
        except RuntimeError:
            passed=False
        return passed,state,report
    passed,state,report=world_case('/Engine/Transient')
    require(passed and state['calls']==['/Engine/Maps/Entry'] and report['initialWorld']['package']=='/Engine/Transient'
            and report['entryLoadReturn']['package']=='/Engine/Maps/Entry', 'Transient-to-Entry proof failed')
    for initial,game in [('/Game/Forbidden',None),('/Engine/Transient',World('PIE'))]:
        passed,state,_=world_case(initial,game)
        require(not passed and not state['calls'], 'Unsafe startup world allowed')
    passed,_,report=world_case('/Engine/Transient',fail=True)
    require(not passed and report['entryLoadReturn'] is None, 'Null load return accepted')
    print('PASS: receipt gates; CDO allowlist; literal-only Entry load; startup-world cases; no quit_editor; 11 isolated-file lifecycle cases; SourceControl reflection guards')


if __name__ == '__main__':
    main()
