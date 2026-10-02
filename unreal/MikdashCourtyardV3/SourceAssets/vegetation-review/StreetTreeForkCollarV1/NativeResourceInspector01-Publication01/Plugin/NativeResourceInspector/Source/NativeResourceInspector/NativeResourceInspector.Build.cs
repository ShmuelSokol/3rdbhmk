using UnrealBuildTool;

public class NativeResourceInspector : ModuleRules
{
    public NativeResourceInspector(ReadOnlyTargetRules Target) : base(Target)
    {
        if (!Target.bBuildEditor)
            throw new BuildException("NativeResourceInspector is editor-only author source.");
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] { "RHI", "RenderCore" });
    }
}
