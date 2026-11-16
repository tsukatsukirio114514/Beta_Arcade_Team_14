using UnrealBuildTool;

public class BlueprintPorter : ModuleRules
{
    public BlueprintPorter(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine"
            });

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "BlueprintGraph",
                "Json",
                "AssetRegistry",
                "KismetCompiler",
                "Kismet",
                "UMG",
                "UMGEditor",
                "UnrealEd"
            });
    }
}
