using UnrealBuildTool;

public class MikdashRuntime : ModuleRules
{
    public MikdashRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "InputCore",
            "UMG"                       // front end, HUD, tour and codex widgets, built in C++
        });

        PrivateDependencyModuleNames.AddRange(new[] {
            "Slate", "SlateCore", "NavigationSystem",
            "RenderCore",               // photo mode high-resolution capture
            "MovieScene",               // cinematic intro playback
            "MovieSceneTracks",
            "LevelSequence",
            "AudioMixer",               // layered soundscape
            "Json",                     // third-party attribution manifests for the credits
            "Projects"                  // plugin and content path lookups at run time
        });
    }
}
