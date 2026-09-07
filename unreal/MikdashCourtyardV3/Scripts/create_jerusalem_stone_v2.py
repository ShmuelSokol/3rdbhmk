"""Create two UNASSIGNED review materials. Run in the working UE editor only.

No map, actor, mesh, collision, source material or external texture is changed.
An existing namespace is a hard stop: inspect any partial run instead of retrying.
"""
import json
from pathlib import Path

import unreal


ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
DEST = "/Game/MikdashV3/MaterialReview/JerusalemStoneV2"
SPEC = ROOT / "SourceAssets/visual-review/jerusalem-stone-v2-spec.json"

# Dominant-axis planar coordinates: suitable for the bounded axis-aligned pilot,
# not a claim of seamless mapping on arbitrary curved/sloping architectural faces.
PROJECTION = r"""
float3 n = normalize(N);
float3 an = abs(n);
float3 U = an.z >= max(an.x, an.y) ? float3(1,0,0) :
           (an.x >= an.y ? float3(0,1,0) : float3(1,0,0));
float3 V = an.z >= max(an.x, an.y) ? float3(0,1,0) : float3(0,0,1);
float2 q = float2(dot(P,U),dot(P,V));
"""

SURFACE = PROJECTION + r"""
float row = floor(q.y / BlockHeightCm);
float2 cell = float2(floor((q.x + fmod(abs(row),2.0)*BlockWidthCm*0.5)
                          / BlockWidthCm), row);
float h = frac(sin(dot(cell,float2(12.9898,78.233)))*43758.5453);
float h2 = frac(sin(dot(cell,float2(39.346,11.135)))*24634.6345);
float shade = 1.0 + (h-0.5)*BlockVariation;
float3 tint = lerp(float3(0.985,0.990,1.0),float3(1.0,0.986,0.965),h2);
// A broad dressed-face variation and fine grain. Derivative fading removes
// undersampled grain rather than baking a high-frequency screen-space sparkle.
float2 f = q / GrainPeriodCm;
float fade = 1.0-smoothstep(0.12,0.40,max(fwidth(f.x),fwidth(f.y)));
float g = sin(f.x*6.2831853)*sin(f.y*6.2831853)*fade;
float broad = sin(q.x*0.173+sin(q.y*0.137))*sin(q.y*0.119);
float3 color = saturate(Base.rgb*tint*shade*(1.0+broad*0.012+g*0.006));
float rough = clamp(RoughnessBase+(h2-0.5)*0.035+g*0.025,0.0,1.0);
return float4(color,rough);
"""

NORMAL = PROJECTION + r"""
float2 f = q / GrainPeriodCm;
float fade = 1.0-smoothstep(0.12,0.40,max(fwidth(f.x),fwidth(f.y)));
float2 phase = f*6.2831853;
// Analytical gradient of the same fine surface; slope is artistic, not a
// geological measurement. This affects lighting only, never displacement.
float3 grad = U*cos(phase.x)*sin(phase.y) + V*sin(phase.x)*cos(phase.y);
grad -= n*dot(grad,n);
return normalize(n-grad*(NormalSlope*fade));
"""


def run():
    assert Path(unreal.Paths.project_dir()).resolve() == ROOT
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world(), "Stop PIE before authoring a review asset"
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    assert not assets.does_directory_exist(DEST), "Existing pilot: inspect; do not overwrite"
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    result = {"status": "started", "created": [], "assigned": False,
              "shaderCompileAcceptance": "PENDING", "visualAcceptance": "PENDING"}
    edit = unreal.MaterialEditingLibrary

    def node(material, cls, x, y, **properties):
        expression = edit.create_material_expression(material, cls, x, y)
        assert expression, str(cls)
        for key, value in properties.items():
            expression.set_editor_property(key, value)
        return expression

    def wire(source, target, target_pin, output=""):
        assert edit.connect_material_expressions(source, output, target, target_pin), (
            source.get_path_name(), output, target.get_path_name(), target_pin)

    def custom(material, code, inputs, output_type, x, y):
        slots = []
        for name in inputs:
            slot = unreal.CustomInput()
            slot.set_editor_property("input_name", name)
            slots.append(slot)
        expression = node(material, unreal.MaterialExpressionCustom, x, y,
                          inputs=slots, code=code, output_type=output_type,
                          description="Artistic Jerusalem limestone V2; unaccepted pilot")
        for name, source in inputs.items():
            wire(source, expression, name)
        return expression

    try:
        for profile in spec["profiles"]:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                profile["assetName"], DEST, unreal.Material, unreal.MaterialFactoryNew())
            assert isinstance(material, unreal.Material)
            result["created"].append(material.get_path_name())
            material.set_editor_property("tangent_space_normal", False)
            position = node(material, unreal.MaterialExpressionWorldPosition, -1200, -300)
            normal = node(material, unreal.MaterialExpressionVertexNormalWS, -1200, -100)
            inputs = {"P": position, "N": normal}
            base = node(material, unreal.MaterialExpressionVectorParameter, -1200, 100,
                        parameter_name="Base", default_value=unreal.LinearColor(
                            *profile["baseLinearRgb"], 1.0))
            inputs["Base"] = base
            for index, (name, value) in enumerate(profile["parameters"].items()):
                inputs[name] = node(material, unreal.MaterialExpressionScalarParameter,
                                    -1200, 300+index*150,
                                    parameter_name=name, default_value=float(value))
            surface_inputs = {key: value for key, value in inputs.items() if key != "NormalSlope"}
            surface = custom(material, SURFACE, surface_inputs,
                             unreal.CustomMaterialOutputType.CMOT_FLOAT4, -400, -300)
            rgb = node(material, unreal.MaterialExpressionComponentMask, 0, -300,
                       r=True, g=True, b=True, a=False)
            alpha = node(material, unreal.MaterialExpressionComponentMask, 0, -100,
                         r=False, g=False, b=False, a=True)
            wire(surface, rgb, "")
            wire(surface, alpha, "")
            normal_inputs = {key: inputs[key] for key in ("P", "N", "GrainPeriodCm", "NormalSlope")}
            detail_normal = custom(material, NORMAL, normal_inputs,
                                   unreal.CustomMaterialOutputType.CMOT_FLOAT3, -400, 200)
            for expression, prop in (
                (rgb, unreal.MaterialProperty.MP_BASE_COLOR),
                (alpha, unreal.MaterialProperty.MP_ROUGHNESS),
                (detail_normal, unreal.MaterialProperty.MP_NORMAL),
            ):
                assert edit.connect_material_property(expression, "", prop)
            metallic = node(material, unreal.MaterialExpressionConstant, 0, 400, r=0.0)
            assert edit.connect_material_property(metallic, "", unreal.MaterialProperty.MP_METALLIC)
            assert edit.get_material_property_input_node(
                material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET) is None
            assert edit.get_material_property_input_node(
                material, unreal.MaterialProperty.MP_PIXEL_DEPTH_OFFSET) is None
            edit.recompile_material(material)
            assert assets.save_loaded_asset(material, only_if_is_dirty=False)
        result["status"] = "unassigned_material_assets_saved_native_shader_review_pending"
        unreal.log("JERUSALEM_STONE_V2_UNASSIGNED_SAVED: inspect shader log before visual pilot")
    except Exception as error:
        result.update(status="failed_partial_assets_require_inspection", error=str(error))
        raise
    finally:
        spec["nativeRun"] = result
        SPEC.write_text(json.dumps(spec, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    run()
