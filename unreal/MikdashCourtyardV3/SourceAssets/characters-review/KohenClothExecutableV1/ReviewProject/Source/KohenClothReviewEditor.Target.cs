using UnrealBuildTool;
public class KohenClothReviewEditorTarget : TargetRules
{
    public KohenClothReviewEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("KohenClothReview");
    }
}
