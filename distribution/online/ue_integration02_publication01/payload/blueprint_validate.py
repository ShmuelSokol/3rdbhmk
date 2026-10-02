"""EXPLICIT FUTURE UE editor operation. Import does nothing; not run by staging.

Only run(root) in a separately authorized editor opened on prepare_asset_copy's
fresh project. Failure poisons that isolated copy; never repair the active asset.
"""
from pathlib import Path
import hashlib,json

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def guard(root,project,expected_manifest):
    root=Path(root).resolve();project=Path(project).resolve()
    if root.parent.name!='Verification' or not root.name.startswith('ReceiverIntegrationAssets'):
        raise ValueError('Not the designated isolated asset copy')
    for p in (root,*root.rglob('*')):
        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Reparse refused')
    m=json.loads((root/'blueprint-copy.json').read_text())
    if m['purpose']!='isolated-blueprint-validation-only' or Path(m['project']).resolve()!=project or project.parent!=root/'P':
        raise ValueError('Wrong running project')
    if (root/'blueprint-attempt.json').exists():raise ValueError('Fresh unused copy required')
    if sha(root/'allowlist.json')!=expected_manifest or \
       sha(root/'source-stage-allowlist.json')!=m['sourceStageManifestSha256']:raise ValueError('Stage changed')
    for e in json.loads((root/'allowlist.json').read_text())['entries']:
        if sha(root/e['path'])!=e['sha256']:raise ValueError('Reviewed source changed')
    for e in m['assets']:
        p=(root/'P/Content'/e['path']).resolve()
        if root/'P/Content' not in p.parents or sha(p)!=e['sha256']:raise ValueError('Asset changed')
    return root,m

def run(root,expected_manifest):
    import unreal
    root,m=guard(root,unreal.Paths.get_project_file_path(),expected_manifest)
    import importlib.util
    loader=importlib.util.spec_from_file_location('reviewed_dependency_preflight',root/'dependency_preflight.py')
    preflight=importlib.util.module_from_spec(loader);loader.loader.exec_module(preflight)
    dependency_result=preflight.validate(root)
    with (root/'blueprint-attempt.json').open('x') as f:json.dump({'state':'in-progress-or-failed'},f)
    template=unreal.load_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter')
    walker=unreal.load_asset('/Game/MikdashV3/Gameplay/BP_MikdashWalker')
    if not template or not walker:raise RuntimeError('Actual Blueprint dependencies unavailable')
    lib=unreal.BlueprintEditorLibrary
    if template.get_editor_property('parent_class').get_path_name()!='/Script/Engine.Character':
        raise RuntimeError('Unreviewed actual template native parent')
    if walker.get_editor_property('parent_class')!=lib.generated_class(template):
        raise RuntimeError('Actual walker does not inherit pinned template')
    def measures(bp):
        cdo=unreal.get_default_object(lib.generated_class(bp))
        cap=cdo.get_editor_property('capsule_component');move=cdo.get_editor_property('character_movement')
        if not cap or not move:raise RuntimeError('Real native component missing')
        return {'radius':cap.get_unscaled_capsule_radius(),'halfHeight':cap.get_unscaled_capsule_half_height(),
                'step':move.get_editor_property('max_step_height'),'walkSpeed':move.get_editor_property('max_walk_speed')}
    before=measures(walker)
    parent=unreal.load_class(None,'/Script/Receiver04Compile.ReceiverPossessionWalkerBase')
    if not parent:raise RuntimeError('Compiled actual native parent unavailable')
    lib.reparent_blueprint(template,parent)
    if not lib.compile_blueprint(template) or not lib.compile_blueprint(walker):raise RuntimeError('Actual Blueprint compile failed')
    if template.get_editor_property('parent_class')!=parent or walker.get_editor_property('parent_class')!=lib.generated_class(template):
        raise RuntimeError('Parent chain readback failed')
    if measures(walker)!=before:raise RuntimeError('Measured capsule/movement defaults changed')
    cdo=unreal.get_default_object(lib.generated_class(walker))
    if cdo.get_editor_property('character_movement').get_class().get_path_name()!='/Script/Receiver04Compile.Receiver04WalkerMovement':
        raise RuntimeError('Actual movement substitution absent')
    mode=unreal.get_default_object(unreal.load_class(None,'/Script/Receiver04Compile.ReceiverIsolatedGameMode'))
    if mode.get_editor_property('default_pawn_class')!=lib.generated_class(walker) or \
       mode.get_editor_property('player_controller_class').get_path_name()!='/Script/Receiver04Compile.Receiver04Controller':
        raise RuntimeError('Actual GameMode ownership wiring absent')
    dove=unreal.get_default_object(unreal.load_class(None,'/Script/Receiver04Compile.ReceiverPossessionDove'))
    movements=dove.get_components_by_class(unreal.PawnMovementComponent)
    if len(movements)!=1 or movements[0].get_class().get_path_name()!='/Script/Receiver04Compile.Receiver04DoveMovement':
        raise RuntimeError('Actual dove movement substitution absent')
    assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    if not assets.save_loaded_asset(template) or not assets.save_loaded_asset(walker):raise RuntimeError('Isolated save failed')
    # Recheck every untouched input: reparent must not silently save dependencies.
    edited={'FirstPerson/Blueprints/BP_FirstPersonCharacter.uasset','MikdashV3/Gameplay/BP_MikdashWalker.uasset'}
    for e in m['assets']:
        if e['path'] not in edited and sha(root/'P/Content'/e['path'])!=e['sha256']:raise RuntimeError('Unexpected asset write')
    receipt={'status':'isolated-blueprint-readback-only','dimensions':before,'dependencies':dependency_result,
             'edited':{n:sha(root/'P/Content'/n) for n in sorted(edited)},
             'runtimePossessionProven':False,'cameraInputBehaviorProven':False}
    with (root/'blueprint-receipt.json').open('x') as f:json.dump(receipt,f,indent=2)
    return receipt
