using UnrealBuildTool;
public class Receiver04CompileEditorTarget : TargetRules
{
    public Receiver04CompileEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("Receiver04Compile");
    }
}
