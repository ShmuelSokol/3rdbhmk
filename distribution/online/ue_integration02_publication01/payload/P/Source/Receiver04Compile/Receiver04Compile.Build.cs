using UnrealBuildTool;
public class Receiver04Compile : ModuleRules
{
    public Receiver04Compile(ReadOnlyTargetRules Target) : base(Target)
    {
        if (Target.Platform != UnrealTargetPlatform.Win64)
            throw new BuildException("Receiver04 compile review is Win64 only");
        PCHUsage = PCHUsageMode.NoPCHs;
        bUseUnity = false;
        PrivateDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "InputCore", "ApplicationCore",
            "InputDevice", "Slate", "SlateCore", "Json", "Sockets", "PlatformFeatures",
            "MikdashRuntime", "PixelStreaming2", "PixelStreaming2Core", "PixelStreaming2Input"
        });
        PublicSystemLibraries.Add("bcrypt.lib");
        RuntimeDependencies.Add("$(ProjectDir)/SourceAssets/tour-review/tour-stops.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/SourceAssets/tour-review/codex-entries.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/SourceAssets/localization-review/strings.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/Localization/Mikdash/strings.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/Distribution/People/people.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/SourceAssets/third-party/third-party-manifest.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/SourceAssets/third-party/soundscape-v2-audio-manifest.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/SourceAssets/third-party/ATTRIBUTION-additions.txt", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/SourceAssets/third-party/ATTRIBUTION-soundscape-v2.txt", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/MikdashV3/Fonts/NotoSansHebrew-Regular.ttf", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/MikdashV3/Fonts/NotoSansHebrew-Bold.ttf", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/MikdashV3/Fonts/NotoSansHebrew-OFL.txt", StagedFileType.NonUFS);
    }
}
