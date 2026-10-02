using UnrealBuildTool;
using System.IO;
using System.Security.Cryptography;
public class MeasuredStrict : ModuleRules
{
 public MeasuredStrict(ReadOnlyTargetRules Target) : base(Target)
 {
  Type = ModuleType.External;
  if(Target.Platform != UnrealTargetPlatform.Win64 || Target.Architecture != UnrealArch.X64 ||
     Target.WindowsPlatform.Compiler != WindowsCompiler.VisualStudio2022 || Target.Configuration != UnrealTargetConfiguration.Development)
   throw new BuildException("Only reviewed MSVC Win64 Development closure is supported");
  string Root = Path.GetFullPath(Path.Combine(ModuleDirectory,"../../.."));
  string Library = Path.Combine(Root,"ThirdParty/Win64/StrictArithmetic.lib");
  if(!File.Exists(Library))throw new BuildException("Pinned strict library must be explicitly staged first");
  string Actual = System.Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Library))).ToLowerInvariant();
  if(Actual != "6100fb9169e3b096abd81f99e5670a60b3bc78b40e56d2c363aa009ccdfac924")throw new BuildException("Strict library artifact pin mismatch");
  PublicIncludePaths.Add(Path.Combine(Root,"ABI"));
  PublicAdditionalLibraries.Add(Library);
 }
}
