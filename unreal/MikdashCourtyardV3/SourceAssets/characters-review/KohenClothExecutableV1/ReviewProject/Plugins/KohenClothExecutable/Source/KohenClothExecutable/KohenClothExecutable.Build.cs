using UnrealBuildTool;
public class KohenClothExecutable : ModuleRules
{
    public KohenClothExecutable(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] {
            "UnrealEd", "Json", "Chaos", "ChaosCloth", "ChaosClothAsset", "ChaosClothAssetEngine",
            "ClothingSystemRuntimeCommon", "ClothingSystemRuntimeInterface", "RenderCore", "RHI"
        });
        SetupModulePhysicsSupport(Target);
    }
}
