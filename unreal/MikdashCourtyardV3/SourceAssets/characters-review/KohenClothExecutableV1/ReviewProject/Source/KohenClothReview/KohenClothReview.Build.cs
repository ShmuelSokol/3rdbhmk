using UnrealBuildTool;
public class KohenClothReview : ModuleRules
{
    public KohenClothReview(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.Add("Core");
    }
}
