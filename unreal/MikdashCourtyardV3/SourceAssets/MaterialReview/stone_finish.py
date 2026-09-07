"""Optional UE5.7 editor material AUTHORING only. Import does nothing.
Call create_finish explicitly after color/finish review; never assigns materials.
No source mesh, existing asset, actor, map, wood/metal/altar/trim edits.
"""
from pathlib import Path
import math
import re

PRESETS = {
    "vertical": {"BlockWidthCm": 100.0, "CourseHeightCm": 50.0,
                 "JointWidthCm": .45, "RunningBond": .5, "RoughnessBase": .80},
    "paving": {"BlockWidthCm": 60.0, "CourseHeightCm": 60.0,
               "JointWidthCm": .30, "RunningBond": 0.0, "RoughnessBase": .73},
}
SHARED = {"BlockVariation": .035, "MicroScaleCm": .65,
          "MicroNormalStrength": .014, "MicroRoughness": .018,
          "GridOffsetUCm": 0.0, "GridOffsetVCm": 0.0}
DEST = "/Game/MikdashV3/MaterialReview"


def create_finish(kind, stone_rgb_linear, mortar_rgb_linear, suffix="Review01"):
    """Create ONE new unassigned review material, refusing an existing name.

    Colors are explicit LINEAR RGB from the separate approved color review.
    Scalar defaults are artistic sampling parameters, not canonical masonry sizes.
    kind is 'vertical' or 'paving'. Source meshes are never enumerated or matched.
    A failed authoring attempt may leave only its new partial review asset; inspect
    it and choose a new suffix rather than overwriting it automatically.
    """
    import unreal
    if kind not in PRESETS:
        raise ValueError("Choose vertical or paving")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,40}", suffix):
        raise ValueError("Use a short asset-safe suffix")
    for color in (stone_rgb_linear, mortar_rgb_linear):
        if len(color) != 3 or any(not math.isfinite(v) or v < 0 or v > 1 for v in color):
            raise ValueError("Explicit finite linear RGB triples in [0,1] required")
    name = "M_StoneFinish_" + kind.capitalize() + "_" + suffix
    path = DEST + "/" + name
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    if assets.does_asset_exist(path) or unreal.load_asset(path):
        raise FileExistsError("Refusing existing asset: " + path)
    shader = Path(__file__).with_name("stone_finish.hlsl").read_text()
    # Mode is a compile-time literal; each material runs only its own projection.
    shader = shader.replace("__PAVING__", "1" if kind == "paving" else "0")
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    if not mat:
        raise RuntimeError("Could not create " + path)
    mat.set_editor_property("tangent_space_normal", False)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("two_sided", False)
    edit = unreal.MaterialEditingLibrary

    def node(cls, x=-650, y=0, **props):
        n = edit.create_material_expression(mat, cls, x, y)
        if not n:
            raise RuntimeError("Expression creation failed: " + str(cls))
        for key, value in props.items():
            n.set_editor_property(key, value)
        return n

    def wire(a, b, input_name, output_name=""):
        if not edit.connect_material_expressions(a, output_name, b, input_name):
            raise RuntimeError("Connection failed: " + input_name)

    def output(n, pin, prop):
        if not edit.connect_material_property(n, pin, prop):
            raise RuntimeError("Output connection failed: " + str(prop))

    position = node(unreal.MaterialExpressionWorldPosition)
    flat = node(unreal.MaterialExpressionConstant3Vector, y=100,
                constant=unreal.LinearColor(0, 0, 1, 1))
    normal = node(unreal.MaterialExpressionTransform, x=-400, y=100,
                  transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                  transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(flat, normal, "")  # Geometric tangent-basis normal, no PixelNormal feedback.
    inputs = {"P": position, "N": normal}
    for index, (label, color) in enumerate((("StoneTint", stone_rgb_linear),
                                           ("MortarTint", mortar_rgb_linear))):
        inputs[label] = node(unreal.MaterialExpressionVectorParameter, y=220+index*90,
                             parameter_name=label, group="Reviewed linear colors",
                             default_value=unreal.LinearColor(*color, 1))
    for index, (label, value) in enumerate({**PRESETS[kind], **SHARED}.items()):
        inputs[label] = node(unreal.MaterialExpressionScalarParameter, y=440+index*70,
                             parameter_name=label, group=kind.capitalize()+" finish assumptions",
                             default_value=float(value))
    custom_inputs = []
    for label in inputs:
        entry = unreal.CustomInput()
        entry.set_editor_property("input_name", label)
        custom_inputs.append(entry)
    custom_outputs = []
    for label, output_type in (("WorldNormal", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
                               ("SurfaceRoughness", unreal.CustomMaterialOutputType.CMOT_FLOAT1)):
        entry = unreal.CustomOutput()
        entry.set_editor_property("output_name", label)
        entry.set_editor_property("output_type", output_type)
        custom_outputs.append(entry)
    finish = node(unreal.MaterialExpressionCustom, x=100, y=0,
                  description="Optional stone finish: artistic dimensions; no geometry movement",
                  inputs=custom_inputs, additional_outputs=custom_outputs,
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, code=shader)
    for label, expression in inputs.items():
        wire(expression, finish, label)
    output(finish, "", unreal.MaterialProperty.MP_BASE_COLOR)
    output(finish, "WorldNormal", unreal.MaterialProperty.MP_NORMAL)
    output(finish, "SurfaceRoughness", unreal.MaterialProperty.MP_ROUGHNESS)
    zero = node(unreal.MaterialExpressionConstant, x=100, y=200, r=0.0)
    specular = node(unreal.MaterialExpressionConstant, x=100, y=290, r=.3)
    output(zero, "", unreal.MaterialProperty.MP_METALLIC)
    output(specular, "", unreal.MaterialProperty.MP_SPECULAR)
    # No displacement/WPO/PDO, decal, opacity or extra geometry connections.
    edit.layout_material_expressions(mat)
    edit.recompile_material(mat)  # Schedules compilation; NOT a visual/compile pass.
    if not assets.save_loaded_asset(mat):
        raise RuntimeError("Could not save new review material: " + path)
    unreal.log("CREATED, UNASSIGNED, UNAPPROVED: " + path)
    return {"asset": path, "assigned": False, "visualApproval": False,
            "shaderCompileStatus": "requested; inspect Material Editor errors/stats",
            "kind": kind, "artisticParameterDefaults": {**PRESETS[kind], **SHARED}}
