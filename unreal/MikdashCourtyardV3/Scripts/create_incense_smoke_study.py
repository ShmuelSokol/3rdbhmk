"""Author an unplaced finite Niagara study; run explicitly in UE editor Python.

Requires the installed editor-only CascadeToNiagaraConverter module to be loaded.
Does not enable plugins, place actors, activate effects, or claim visual approval.
The ordinary graph modules are engine Niagara content, not converter helpers.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = '/Game/MikdashV3/MaterialReview/IncenseSmokeV1'
REPORT = Path(ue.Paths.project_dir()) / 'SourceAssets/vessels-review/incense-smoke-study-spec.json'
MODULES = {
    'state': '/Niagara/Modules/Emitter/EmitterState.EmitterState',
    'spawn': '/Niagara/Modules/Emitter/SpawnRate.SpawnRate',
    'init': '/Niagara/Modules/Spawn/Initialization/V2/InitializeParticle.InitializeParticle',
    'life': '/Niagara/Modules/Update/Lifetime/ParticleState.ParticleState',
    'solve': '/Niagara/Modules/Solvers/SolveForcesAndVelocity.SolveForcesAndVelocity',
    'position': '/Niagara/DynamicInputs/Transforms/ConvertVectorToPosition.ConvertVectorToPosition',
}
# Exact versions used by the installed UE converter examples. ParticleState
# uses 1.1, while SolveForcesAndVelocity deliberately uses the exposed version.
MODULE_VERSIONS = {'state': [1, 0], 'spawn': [1, 0], 'init': [1, 0],
                   'life': [1, 1], 'solve': None, 'position': None}
ENUMS = {
    'lifecycle': '/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode',
    'loop': '/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions',
    'inactive': '/Niagara/Enums/ENiagaraInactiveMode.ENiagaraInactiveMode',
}


def build(emission_seconds=6.0, rise_seconds=3.0, ceiling_height_cm=900.0,
          spread_seconds=2.0, spread_speed_cm_s=80.0):
    """Numeric defaults are artistic study values, not ritual measurements.

    Finite shaft plus eight delayed radial wisps illustrate ceiling spread.
    No collision/roof detection: ceiling height MUST match a later review rig.
    Scheduler binding and particle compile/runtime verification remain separate.
    """
    values = (emission_seconds, rise_seconds, ceiling_height_cm, spread_seconds, spread_speed_cm_s)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError('All study dimensions and durations must be finite and positive')
    fx = getattr(ue, 'FXConverterUtilitiesLibrary', None)
    if fx is None:
        raise RuntimeError('CascadeToNiagaraConverter authoring API is not loaded; no assets created')
    for path in list(MODULES.values()) + list(ENUMS.values()):
        if not ue.load_asset(path):
            raise RuntimeError('Missing installed Niagara source asset: ' + path)
    for name in ('M_OriginalSoftSmoke', 'NS_FiniteIncenseStudy'):
        if ue.EditorAssetLibrary.does_asset_exist(ROOT + '/' + name):
            raise RuntimeError('Existing study preserved; do not overwrite: ' + name)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    report = dict(status='authoring_started_not_verified', asset_root=ROOT,
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  module_versions=MODULE_VERSIONS,
                  placement='unplaced; no components or activation created',
                  source_ids=['KET-SMOKE-FORM', 'KET-SMOKE-DAILY'],
                  design_parameters=dict(emission_seconds=emission_seconds, rise_seconds=rise_seconds,
                    ceiling_height_cm=ceiling_height_cm, spread_seconds=spread_seconds,
                    spread_speed_cm_s=spread_speed_cm_s),
                  limitations=['Illustrative kinematics, not fluid simulation or confirmed historical dimensions',
                    'No collision or roof detection; only valid in a matched review rig',
                    'No particle compile, visual, package or scheduler-binding acceptance yet',
                    'No external raster assets; analytic original soft sprite material',
                    'Future runtime binding must use one scheduler event and matching lifetime parameters'])
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    source_spec = json.loads(REPORT.read_text(encoding="utf-8"))
    # Archive the previous execution once, before this attempt creates assets.
    # Keep the original design/source metadata and root's execution nesting.
    if 'execution' in source_spec:
        source_spec.setdefault('priorExecutions', []).append(source_spec.pop('execution'))
    def receipt():
        source_spec["execution"] = report
        REPORT.write_text(json.dumps(source_spec, indent=2)+"\n", encoding="utf-8")
    receipt()

    context = None
    try:
        material = tools.create_asset('M_OriginalSoftSmoke', ROOT, ue.Material, ue.MaterialFactoryNew())
        if not material:
            raise RuntimeError('Material factory failed')
        material.set_editor_property('blend_mode', ue.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        ml = ue.MaterialEditingLibrary
        if not ml.set_material_usage(material, ue.MaterialUsage.MATUSAGE_NIAGARA_SPRITES):
            # Return indicates whether usage changed, not compile success.
            pass
        uv = ml.create_material_expression(material, ue.MaterialExpressionTextureCoordinate, -500, 0)
        mask = ml.create_material_expression(material, ue.MaterialExpressionCustom, -250, 0)
        ci = ue.CustomInput()
        ci.set_editor_property('input_name', 'UV')
        mask.set_editor_property('inputs', [ci])
        mask.set_editor_property('output_type', ue.CustomMaterialOutputType.CMOT_FLOAT1)
        mask.set_editor_property('code',
            'float2 p=UV*2-1; float r=dot(p,p); '
            'float grain=0.82+0.10*sin(19*p.x+sin(13*p.y))+0.08*sin(23*p.y); '
            'return pow(saturate(1-r),2.5)*grain*0.12;')
        color = ml.create_material_expression(material, ue.MaterialExpressionConstant3Vector, -250, 180)
        color.set_editor_property('constant', ue.LinearColor(0.46, 0.46, 0.45, 1.0))
        if not ml.connect_material_expressions(uv, '', mask, 'UV'):
            raise RuntimeError('Original material UV connection failed')
        if not ml.connect_material_property(mask, '', ue.MaterialProperty.MP_OPACITY):
            raise RuntimeError('Original material opacity connection failed')
        if not ml.connect_material_property(color, '', ue.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError('Original material color connection failed')
        ml.recompile_material(material)
        system = tools.create_asset('NS_FiniteIncenseStudy', ROOT, ue.NiagaraSystem, ue.NiagaraSystemFactoryNew())
        if not system:
            raise RuntimeError('Niagara system factory failed')
        context = fx.create_system_conversion_context(system)

        def module(emitter, label, key, category):
            version = MODULE_VERSIONS[key]
            asset_data = fx.create_asset_data(MODULES[key])
            args = (ue.CreateScriptContextArgs(asset_data, version) if version is not None
                    else ue.CreateScriptContextArgs(asset_data))
            result = emitter.find_or_add_module_script(label, args, category)
            if not result:
                raise RuntimeError('Module creation failed: ' + label)
            return result

        def setp(script, name, value, optional=False):
            if not script.set_parameter(name, value, optional, optional):
                raise RuntimeError('Niagara input rejected: %s (%s)' % (name, script.get_name()))

        def emitter(name, delay, life, rate, offset, velocity, size):
            e = context.add_empty_emitter(name)
            e.set_local_space(True)
            state = module(e, 'EmitterState', 'state', ue.ScriptExecutionCategory.EMITTER_UPDATE)
            setp(state, 'Life Cycle Mode', fx.create_script_input_enum(ENUMS['lifecycle'], 'Self'))
            setp(state, 'Loop Behavior', fx.create_script_input_enum(ENUMS['loop'], 'Once'))
            setp(state, 'Inactive Response', fx.create_script_input_enum(ENUMS['inactive'], 'Complete (Let Particles Finish then Kill Emitter)'))
            setp(state, 'Loop Duration', fx.create_script_input_float(emission_seconds))
            setp(state, 'Loop Delay', fx.create_script_input_float(delay), True)
            spawn = module(e, 'SpawnRate', 'spawn', ue.ScriptExecutionCategory.EMITTER_UPDATE)
            # Internal input name, NOT its spaced display label. Verified in
            # installed ModuleConversionScripts/CascadeSpawnToNiagaraSpawn.py.
            setp(spawn, 'SpawnRate', fx.create_script_input_float(rate))
            init = module(e, 'InitializeParticle', 'init', ue.ScriptExecutionCategory.PARTICLE_SPAWN)
            setp(init, 'Lifetime', fx.create_script_input_float(life))
            e.set_parameter_directly('Particles.SpriteSize', fx.create_script_input_vec2(ue.Vector2D(size, size)), ue.ScriptExecutionCategory.PARTICLE_SPAWN)
            e.set_parameter_directly('Particles.Velocity', fx.create_script_input_vector(ue.Vector(*velocity)), ue.ScriptExecutionCategory.PARTICLE_SPAWN)
            position = fx.create_script_context(ue.CreateScriptContextArgs(fx.create_asset_data(MODULES['position'])))
            setp(position, 'Input Position', fx.create_script_input_vector(ue.Vector(*offset)))
            e.set_parameter_directly('Particles.Position', fx.create_script_input_dynamic(position, ue.NiagaraScriptInputType.POSITION), ue.ScriptExecutionCategory.PARTICLE_SPAWN)
            life_script = module(e, 'ParticleState', 'life', ue.ScriptExecutionCategory.PARTICLE_UPDATE)
            setp(life_script, 'Kill Particles When Lifetime Has Elapsed', fx.create_script_input_bool(True))
            module(e, 'SolveVelocity', 'solve', ue.ScriptExecutionCategory.PARTICLE_UPDATE)
            renderer = ue.NiagaraSpriteRendererProperties()
            renderer.set_editor_property('material', material)
            e.add_renderer('OriginalSmokeSprites', renderer)

        emitter('FiniteShaft', 0, rise_seconds, 24, (0, 0, 0), (0, 0, ceiling_height_cm/rise_seconds), 32)
        for i in range(8):
            angle = i * math.tau / 8
            emitter('CeilingWisp_%02d' % i, rise_seconds, spread_seconds, 3,
                    (0, 0, ceiling_height_cm-35),
                    (math.cos(angle)*spread_speed_cm_s, math.sin(angle)*spread_speed_cm_s, -12), 65)
        context.finalize()
        for asset in (material, system):
            if not ue.EditorAssetLibrary.save_loaded_asset(asset):
                raise RuntimeError('Asset save failed: ' + asset.get_path_name())
        report.update(status='authored_saved_unplaced_not_compile_or_visual_verified',
                      assets=[material.get_path_name(), system.get_path_name()], emitter_count=9,
                      nominal_visual_end_seconds=emission_seconds+rise_seconds+spread_seconds)
        receipt()
        return system
    except Exception as error:
        report.update(status='authoring_failed_partial_assets_may_exist', error=str(error))
        receipt()
        raise
    finally:
        if context is not None:
            context.cleanup()
