using UnrealBuildTool;
public class CookedWorldProbeEditorTarget : TargetRules
{
 public CookedWorldProbeEditorTarget(TargetInfo Target) : base(Target)
 {
  Type = TargetType.Editor;
  DefaultBuildSettings = BuildSettingsVersion.V7;
  IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
  ExtraModuleNames.Add("CookedWorldProbe");
 }
}
