using UnrealBuildTool;
public class Receiver04CompileGameTarget : TargetRules
{
    public Receiver04CompileGameTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("Receiver04Compile");
    }
}
