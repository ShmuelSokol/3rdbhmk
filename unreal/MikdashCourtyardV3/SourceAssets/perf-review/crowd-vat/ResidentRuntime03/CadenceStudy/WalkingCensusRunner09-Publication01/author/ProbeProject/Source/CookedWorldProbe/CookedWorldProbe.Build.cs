using UnrealBuildTool;
public class CookedWorldProbe : ModuleRules
{
 public CookedWorldProbe(ReadOnlyTargetRules Target) : base(Target)
 {
  PCHUsage = PCHUsageMode.NoPCHs;
  bUseUnity = false;
  CppStandard = CppStandardVersion.Cpp20;
  bEnableExceptions = true;
  FPSemantics = FPSemanticsMode.Precise; // Capture module only; not claimed to be strict.
  PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "MeasuredStrict", "PhysicsCore", "Chaos" });
  PrivateDependencyModuleNames.AddRange(new[] {"Json", "MikdashRuntime"});

 }
}
