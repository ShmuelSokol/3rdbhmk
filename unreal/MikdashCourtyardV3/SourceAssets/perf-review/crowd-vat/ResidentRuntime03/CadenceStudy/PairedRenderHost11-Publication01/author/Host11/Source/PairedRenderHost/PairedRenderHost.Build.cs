using UnrealBuildTool;
public class PairedRenderHost : ModuleRules { public PairedRenderHost(ReadOnlyTargetRules Target):base(Target) { PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs; PublicDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine","RenderCore","RHI"}); } }
