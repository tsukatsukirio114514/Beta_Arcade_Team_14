#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BlueprintPorterLibrary.generated.h"

class UBlueprint;
class UWidgetBlueprint;
class UUserWidget;
class UAnimMontage;
class UAnimNotifyState;

/**
 * Editor-only helpers for moving Blueprint graph nodes through Unreal's text
 * clipboard format. Reflected functions are also available to Unreal Python.
 */
UCLASS()
class BLUEPRINTPORTER_API UBlueprintPorterLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /**
     * Exports every graph in UbergraphPages, FunctionGraphs, MacroGraphs and
     * DelegateSignatureGraphs to a separate UTF-8 text file.
     *
     * Files are named <GraphName>.bpgraph.txt (with a numeric suffix only when
     * sanitized graph names collide). Returns false if any file cannot be saved.
     */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool ExportBlueprintGraphs(UBlueprint* Blueprint, const FString& OutputDirectory);

    /**
     * Imports nodes from a graph text file into the named existing graph.
     * When bClearExisting is true, validation happens first and the existing
     * nodes are removed only after the input has been accepted.
     */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool ImportBlueprintGraph(
        UBlueprint* Blueprint,
        const FString& GraphName,
        const FString& FilePath,
        bool bClearExisting = true);

    /** Returns the names of all supported graphs in deterministic order. */
    UFUNCTION(BlueprintPure, Category = "Blueprint Porter")
    static TArray<FString> ListBlueprintGraphs(UBlueprint* Blueprint);

    /** Returns Blueprint-declared member variable names (excluding inherited properties). */
    UFUNCTION(BlueprintPure, Category = "Blueprint Porter")
    static TArray<FString> ListBlueprintVariables(UBlueprint* Blueprint);

    /** Adds a native override graph using a function signature from SignatureClass. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool AddOverrideFunctionGraph(
        UBlueprint* Blueprint,
        const FString& FunctionName,
        UClass* SignatureClass);

    /** Restores a Widget variable GUID so imported variable nodes keep their links. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool SetWidgetVariableGuid(
        UWidgetBlueprint* Blueprint,
        const FString& VariableName,
        const FString& GuidDigits);

    /** Reconstructs every node against the target engine's schemas and classes. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool RefreshBlueprintNodes(UBlueprint* Blueprint);

    /** Rebinds self-context variable nodes by name in the target Blueprint. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static int32 RepairSelfVariableReferences(UBlueprint* Blueprint);

    /** Restores the native parent signature on an imported override graph. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool RebindOverrideFunction(
        UBlueprint* Blueprint,
        const FString& FunctionName,
        UClass* SignatureClass);

    /** Exports the complete root widget hierarchy using Unreal's clipboard text format. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool ExportWidgetTree(UWidgetBlueprint* Blueprint, const FString& FilePath);

    /** Replaces the target Widget Blueprint tree with a previously exported hierarchy. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool ImportWidgetTree(
        UWidgetBlueprint* Blueprint,
        const FString& FilePath,
        bool bClearExisting = true);

    /** Writes a compact description of every SCS component template. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool ExportBlueprintComponents(UBlueprint* Blueprint, const FString& FilePath);

    /** Adds a non-scene ActorComponent node to a Blueprint SCS. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool AddActorComponentNode(
        UBlueprint* Blueprint,
        UClass* ComponentClass,
        const FString& VariableName);

    /** Adds and configures a WidgetComponent node in a Blueprint SCS. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool AddWidgetComponentNode(
        UBlueprint* Blueprint,
        const FString& VariableName,
        const FString& ParentVariableName,
        TSubclassOf<UUserWidget> WidgetClass,
        FVector RelativeLocation,
        FRotator RelativeRotation,
        FVector2D DrawSize,
        bool bDrawAtDesiredSize);

    /** Adds one Blueprint AnimNotifyState event to a montage if absent. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool AddMontageNotifyState(
        UAnimMontage* Montage,
        TSubclassOf<UAnimNotifyState> NotifyStateClass,
        float StartTime,
        float Duration,
        int32 TrackIndex);

    /** Writes montage notify classes, timing and tracks for cross-version comparison. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool ExportMontageNotifies(UAnimMontage* Montage, const FString& FilePath);

    /** Restores the authored name of an imported custom event identified by node GUID. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool RenameCustomEventByGuid(
        UBlueprint* Blueprint,
        const FString& NodeGuidDigits,
        const FString& NewName);

    /** Sets the bool return pin default on a Blueprint function result node. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool SetFunctionBoolReturnDefault(
        UBlueprint* Blueprint,
        const FString& FunctionName,
        bool Value);

    /** Connects an explicit MakeLiteralBool node to a function result for stable cross-version behavior. */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Porter")
    static bool ConnectFunctionBoolReturnLiteral(
        UBlueprint* Blueprint,
        const FString& FunctionName,
        bool Value);
};
