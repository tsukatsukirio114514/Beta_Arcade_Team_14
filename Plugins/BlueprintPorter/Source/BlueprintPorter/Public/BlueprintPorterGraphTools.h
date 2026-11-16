#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BlueprintPorterGraphTools.generated.h"
class UBlueprint;
class UUserDefinedStruct;

/** Editor-only construction tools. Generated combat assets need no runtime plugin. */
UCLASS()
class BLUEPRINTPORTER_API UBlueprintPorterGraphTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Blueprint Porter")
    static void PrepareAssetsForRename(const TArray<UObject*>& Assets);
    UFUNCTION(BlueprintCallable, Category="Blueprint Porter")
    static FString BuildGraph(UBlueprint* Blueprint, const FString& GraphName, const FString& Json);
    UFUNCTION(BlueprintCallable, Category="Blueprint Porter")
    static UUserDefinedStruct* CreateStructAsset(const FString& PackagePath, const FString& FieldsJson);
    UFUNCTION(BlueprintCallable, Category="Blueprint Porter")
    static FString StructFields(UUserDefinedStruct* Struct);
    UFUNCTION(BlueprintCallable, Category="Blueprint Porter")
    static FString CompileChecked(UBlueprint* Blueprint);
    UFUNCTION(BlueprintCallable, Category="Blueprint Porter")
    static bool SetComponentObjectDefault(UBlueprint* Blueprint, const FString& ComponentName, const FString& PropertyName, UObject* Value);
};
