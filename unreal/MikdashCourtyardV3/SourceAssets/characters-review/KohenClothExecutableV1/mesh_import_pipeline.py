"""Isolated reviewed mesh import function; provenance in dependency-provenance-v3.json."""
def _mesh_pipeline(ue, skeleton, import_materials=True):
    pipeline = ue.InterchangeGenericAssetsPipeline()
    readback, missing = {}, []

    def apply(owner, key, value, required):
        try:
            owner.set_editor_property(key, value)
            got = owner.get_editor_property(key)
            readback[key] = got.get_path_name() if hasattr(got, 'get_path_name') else str(got)
        except Exception as error:                                   # noqa: BLE001
            readback[key] = 'unavailable: ' + str(error)[:120]
            if required:
                missing.append(key)

    common = pipeline.get_editor_property('common_skeletal_meshes_and_animations_properties')
    apply(common, 'skeleton', skeleton, True)
    apply(common, 'import_only_animations', False, True)
    apply(common, 'use_t0_as_ref_pose', False, False)
    apply(common, 'add_curve_metadata_to_skeleton', False, False)
    try:
        cm = pipeline.get_editor_property('common_meshes_properties')
        apply(cm, 'vertex_color_import_option', ue.InterchangeVertexColorImportOption.IVCIO_REPLACE, False)
    except Exception as error:                                       # noqa: BLE001
        readback['vertex_color_import_option'] = 'unavailable: ' + str(error)[:120]
    mesh = pipeline.get_editor_property('mesh_pipeline')
    apply(mesh, 'import_static_meshes', False, True)
    apply(mesh, 'import_skeletal_meshes', True, True)
    apply(mesh, 'create_physics_asset', False, False)
    apply(mesh, 'import_morph_targets', False, False)
    animation = pipeline.get_editor_property('animation_pipeline')
    apply(animation, 'import_animations', False, True)
    material = pipeline.get_editor_property('material_pipeline')
    apply(material, 'import_materials', import_materials, not import_materials)
    if not import_materials and material.get_editor_property('import_materials'):
        raise RuntimeError('Mesh-only review must not import unused source materials')
    if missing:
        raise RuntimeError('Interchange pipeline would not accept %r; readback %r' % (missing, readback))
    if skeleton.get_name() not in str(readback.get('skeleton', '')):
        raise RuntimeError('common.skeleton did not read back as %s (%r)' % (skeleton.get_name(),
                                                                             readback.get('skeleton')))
    override = ue.InterchangePipelineStackOverride()
    override.add_pipeline(pipeline)
    return override, readback
