"""Isolated smoke review room; explicit build(), then preview_at(seconds).

No main-map edits, engine launches, gameplay binding or historical altar props.
The smoke is saved inactive. preview_at changes only transient preview state;
never save the map after a preview without first deactivating its component.
"""
import hashlib
import json
import math
from pathlib import Path
import unreal as ue

ROOT = '/Game/MikdashV3/MaterialReview/IncenseSmokeReviewV3'
MAP = ROOT + '/L_IncenseSmokeReview'
SYSTEM = '/Game/MikdashV3/MaterialReview/IncenseSmokeV1/NS_FiniteIncenseStudy'
SPEC = Path(ue.Paths.project_dir()) / 'SourceAssets/vessels-review/incense-review-rig-spec.json'
CAMERA = (0.0, -1800.0, 450.0)
ROTATION = dict(pitch=0.0, yaw=90.0, roll=0.0)


def _component():
    world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    if world.get_outermost().get_name() != MAP:
        raise RuntimeError('Only the isolated incense review map may be previewed')
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
    matches = [a for a in actors if a.get_actor_label() == 'REVIEW_FiniteIncense_InactiveByDefault']
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one review smoke actor')
    return matches[0].get_component_by_class(ue.NiagaraComponent)


def preview_at(seconds):
    """Seek one finite sample; editor realtime frames must advance to render it.

    Uses native desired-age mode, no wallclock loop and no actor saves. Root may
    inspect 0/1/3/6/9/12 seconds, then call stop_preview(). This is VFX preview,
    not incense-service choreography or a claim of particle completion.
    """
    if not math.isfinite(seconds) or not 0 <= seconds <= 20:
        raise ValueError('Review age must be finite and within 0..20 seconds')
    comp = _component()
    comp.set_force_solo(True)
    comp.set_age_update_mode(ue.NiagaraAgeUpdateMode.DESIRED_AGE)
    comp.activate(True)
    comp.set_desired_age(float(seconds))
    return {'requested_age_seconds': seconds, 'render_verified': False}


def stop_preview():
    comp = _component()
    comp.deactivate()
    comp.set_editor_property('auto_activate', False)


def build():
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Save or resolve existing dirty work before creating a separate review level')
    if ue.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError('Existing review map preserved; load it instead of rebuilding')
    system = ue.load_asset(SYSTEM)
    cube = ue.load_asset('/Engine/BasicShapes/Cube.Cube')
    if not isinstance(system, ue.NiagaraSystem) or not cube:
        raise RuntimeError('Saved Niagara study and runtime cube must exist before authoring')
    source = json.loads((SPEC.parent / 'incense-smoke-study-spec.json').read_text(encoding='utf-8'))
    execution = source.get('execution', {})
    dimensions = execution.get('design_parameters', {})
    if dimensions.get('ceiling_height_cm') != 900.0:
        raise RuntimeError('This rig matches only the saved 900cm smoke study')
    main_map = Path(ue.Paths.project_dir()) / 'Content/MikdashV3/Maps/Courtyard.umap'
    before = hashlib.sha256(main_map.read_bytes()).hexdigest()
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    old_world = editor.get_editor_world().get_outermost().get_name()
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actor_api = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    report = dict(status='authoring_started', map=MAP, previous_editor_map=old_world,
                  main_map_sha256_before=before, camera_cm=CAMERA, camera_rotation=ROTATION,
                  ceiling_underside_cm=900, smoke_origin_cm=[0, 0, 0],
                  limits=['Artificial open-front room, not Temple architecture',
                          'No collision-aware smoke; matched height only',
                          'No native rendering or lifetime acceptance implied by save/reopen',
                          'Smoke asset saved inactive; activate only for explicit review'])
    def receipt():
        SPEC.parent.mkdir(parents=True, exist_ok=True)
        prior = json.loads(SPEC.read_text(encoding='utf-8')) if SPEC.exists() else {}
        prior['execution'] = report
        SPEC.write_text(json.dumps(prior, indent=2) + '\n', encoding='utf-8')
    receipt()
    try:
        if not levels.new_level(MAP):
            raise RuntimeError('Separate level creation failed')
        tools = ue.AssetToolsHelpers.get_asset_tools()
        materials = []
        for name, value in [('M_ReviewDark', 0.025), ('M_ReviewFloor', 0.08)]:
            if ue.EditorAssetLibrary.does_asset_exist(ROOT + '/' + name):
                raise RuntimeError('Existing review material preserved: ' + name)
            mat = tools.create_asset(name, ROOT, ue.Material, ue.MaterialFactoryNew())
            if not mat:
                raise RuntimeError('Material creation failed')
            mat.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_UNLIT)
            color = ue.MaterialEditingLibrary.create_material_expression(mat, ue.MaterialExpressionConstant3Vector, 0, 0)
            color.set_editor_property('constant', ue.LinearColor(value, value, value, 1.0))
            if not ue.MaterialEditingLibrary.connect_material_property(color, '', ue.MaterialProperty.MP_EMISSIVE_COLOR):
                raise RuntimeError('Review material connection failed')
            ue.MaterialEditingLibrary.recompile_material(mat)
            if not ue.EditorAssetLibrary.save_loaded_asset(mat):
                raise RuntimeError('Review material save failed')
            materials.append(mat)

        def spawn(cls, label, position, rotation=None):
            actor = actor_api.spawn_actor_from_class(cls, ue.Vector(*position), rotation or ue.Rotator(), transient=False)
            if not actor:
                raise RuntimeError('Actor creation failed: ' + label)
            actor.set_actor_label(label)
            return actor

        # Runtime /Engine/BasicShapes geometry, no tutorial or EditorResources.
        boxes = [('Floor', (0, 0, -25), (12, 10, 0.5), 1),
                 ('Ceiling', (0, 0, 925), (12, 10, 0.5), 0),
                 ('Back', (0, 525, 450), (12, 0.5, 9), 0),
                 ('Left', (-625, 0, 450), (0.5, 10, 9), 0),
                 ('Right', (625, 0, 450), (0.5, 10, 9), 0)]
        for name, position, scale, material_index in boxes:
            actor = spawn(ue.StaticMeshActor, 'REVIEW_' + name, position)
            mesh = actor.get_component_by_class(ue.StaticMeshComponent)
            mesh.set_static_mesh(cube)
            mesh.set_material(0, materials[material_index])
            actor.set_actor_scale3d(ue.Vector(*scale))
        # Emissive neutral surfaces and fixed exposure make this reproducible;
        # no unsupported claim about physically realistic sanctuary lighting.
        pp = spawn(ue.PostProcessVolume, 'REVIEW_FixedExposure', (0, 0, 0))
        pp.set_editor_property('unbound', True)
        settings = pp.get_editor_property('settings')
        for key, value in [('override_auto_exposure_method', True),
                           ('auto_exposure_method', ue.AutoExposureMethod.AEM_MANUAL),
                           ('override_auto_exposure_apply_physical_camera_exposure', True),
                           ('auto_exposure_apply_physical_camera_exposure', False),
                           ('override_auto_exposure_bias', True), ('auto_exposure_bias', 0.0)]:
            settings.set_editor_property(key, value)
        pp.set_editor_property('settings', settings)
        camera = spawn(ue.CameraActor, 'REVIEW_FrontCamera_NoHistoricVantageClaim', CAMERA, ue.Rotator(**ROTATION))
        camera.get_component_by_class(ue.CameraComponent).set_field_of_view(60.0)
        smoke = spawn(ue.NiagaraActor, 'REVIEW_FiniteIncense_InactiveByDefault', (0, 0, 0))
        comp = smoke.get_component_by_class(ue.NiagaraComponent)
        comp.set_editor_property('auto_activate', False)
        comp.set_asset(system)
        comp.deactivate()
        editor.set_level_viewport_camera_info(ue.Vector(*CAMERA), ue.Rotator(**ROTATION))
        if not levels.save_current_level() or not levels.load_level(MAP):
            raise RuntimeError('Review level save/reopen failed')
        reopened = _component()
        if reopened.get_editor_property('auto_activate') or reopened.get_asset().get_path_name() != system.get_path_name():
            raise RuntimeError('Reopened smoke assignment or inactive default differs')
        editor.set_level_viewport_camera_info(ue.Vector(*CAMERA), ue.Rotator(**ROTATION))
        after = hashlib.sha256(main_map.read_bytes()).hexdigest()
        if after != before:
            raise RuntimeError('Main map hash changed unexpectedly')
        report.update(status='saved_reopened_inactive_visual_review_pending', main_map_sha256_after=after,
                      main_map_unchanged=True, saved_auto_activate=False)
        receipt()
        return report
    except Exception as error:
        report.update(status='failed_partial_review_assets_preserved', error=str(error))
        receipt()
        raise
