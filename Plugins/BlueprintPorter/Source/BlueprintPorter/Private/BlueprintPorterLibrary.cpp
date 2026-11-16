#include "BlueprintPorterLibrary.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraphUtilities.h"
#include "Engine/Blueprint.h"
#include "EdGraphSchema_K2.h"
#include "WidgetBlueprint.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Widget.h"
#include "Components/SceneComponent.h"
#include "Components/WidgetComponent.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "HAL/FileManager.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_FunctionResult.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Variable.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "WidgetBlueprintEditorUtils.h"

DEFINE_LOG_CATEGORY_STATIC(LogBlueprintPorter, Log, All);

namespace BlueprintPorter
{
void AddGraphsUnique(const TArray<TObjectPtr<UEdGraph>>& Source, TArray<UEdGraph*>& Destination)
{
    for (UEdGraph* Graph : Source)
    {
        if (IsValid(Graph))
        {
            Destination.AddUnique(Graph);
        }
    }
}

TArray<UEdGraph*> GatherGraphs(UBlueprint* Blueprint)
{
    TArray<UEdGraph*> Graphs;
    if (!IsValid(Blueprint))
    {
        return Graphs;
    }

    AddGraphsUnique(Blueprint->UbergraphPages, Graphs);
    AddGraphsUnique(Blueprint->FunctionGraphs, Graphs);
    AddGraphsUnique(Blueprint->MacroGraphs, Graphs);
    AddGraphsUnique(Blueprint->DelegateSignatureGraphs, Graphs);
    return Graphs;
}

UEdGraph* FindGraph(UBlueprint* Blueprint, const FString& GraphName)
{
    for (UEdGraph* Graph : GatherGraphs(Blueprint))
    {
        if (Graph->GetName().Equals(GraphName, ESearchCase::CaseSensitive))
        {
            return Graph;
        }
    }

    return nullptr;
}

void ClearGraph(UBlueprint* Blueprint, UEdGraph* Graph)
{
    // Work on a copy because RemoveNode mutates Graph->Nodes.
    const TArray<TObjectPtr<UEdGraphNode>> ExistingNodes = Graph->Nodes;
    for (UEdGraphNode* Node : ExistingNodes)
    {
        if (IsValid(Node))
        {
            FBlueprintEditorUtils::RemoveNode(Blueprint, Node, true);
        }
    }
}
} // namespace BlueprintPorter

bool UBlueprintPorterLibrary::ExportBlueprintGraphs(
    UBlueprint* Blueprint,
    const FString& OutputDirectory)
{
    if (!IsValid(Blueprint))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Export failed: Blueprint is null or invalid."));
        return false;
    }

    if (OutputDirectory.TrimStartAndEnd().IsEmpty())
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Export failed for '%s': output directory is empty."), *Blueprint->GetPathName());
        return false;
    }

    const FString AbsoluteOutputDirectory = FPaths::ConvertRelativePathToFull(OutputDirectory);
    if (!IFileManager::Get().MakeDirectory(*AbsoluteOutputDirectory, true)
        && !IFileManager::Get().DirectoryExists(*AbsoluteOutputDirectory))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Export failed: could not create directory '%s'."), *AbsoluteOutputDirectory);
        return false;
    }

    const TArray<UEdGraph*> Graphs = BlueprintPorter::GatherGraphs(Blueprint);
    TSet<FString> UsedFilenames;
    bool bAllSaved = true;

    for (UEdGraph* Graph : Graphs)
    {
        TSet<UObject*> NodesToExport;
        for (UEdGraphNode* Node : Graph->Nodes)
        {
            if (IsValid(Node))
            {
                NodesToExport.Add(Node);
            }
        }

        FString ExportedText;
        FEdGraphUtilities::ExportNodesToText(MoveTemp(NodesToExport), ExportedText);

        FString FilenameStem = FPaths::MakeValidFileName(Graph->GetName());
        if (FilenameStem.IsEmpty())
        {
            FilenameStem = TEXT("Graph");
        }

        FString Filename = FilenameStem + TEXT(".bpgraph.txt");
        int32 CollisionIndex = 2;
        while (UsedFilenames.Contains(Filename))
        {
            Filename = FString::Printf(TEXT("%s_%d.bpgraph.txt"), *FilenameStem, CollisionIndex++);
        }
        UsedFilenames.Add(Filename);

        const FString OutputPath = FPaths::Combine(AbsoluteOutputDirectory, Filename);
        if (!FFileHelper::SaveStringToFile(
                ExportedText,
                *OutputPath,
                FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
        {
            UE_LOG(LogBlueprintPorter, Error, TEXT("Could not save graph '%s' to '%s'."), *Graph->GetName(), *OutputPath);
            bAllSaved = false;
        }
        else
        {
            UE_LOG(LogBlueprintPorter, Log, TEXT("Exported graph '%s' (%d nodes) to '%s'."), *Graph->GetName(), Graph->Nodes.Num(), *OutputPath);
        }
    }

    UE_LOG(
        LogBlueprintPorter,
        Log,
        TEXT("Exported %d graph(s) from '%s'."),
        Graphs.Num(),
        *Blueprint->GetPathName());
    return bAllSaved;
}

bool UBlueprintPorterLibrary::ImportBlueprintGraph(
    UBlueprint* Blueprint,
    const FString& GraphName,
    const FString& FilePath,
    bool bClearExisting)
{
    if (!IsValid(Blueprint))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Import failed: Blueprint is null or invalid."));
        return false;
    }

    UEdGraph* Graph = BlueprintPorter::FindGraph(Blueprint, GraphName);
    if (!IsValid(Graph))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Import failed: graph '%s' was not found in '%s'."), *GraphName, *Blueprint->GetPathName());
        return false;
    }

    const FString AbsoluteFilePath = FPaths::ConvertRelativePathToFull(FilePath);
    FString TextToImport;
    if (!FFileHelper::LoadFileToString(TextToImport, *AbsoluteFilePath))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Import failed: could not read '%s'."), *AbsoluteFilePath);
        return false;
    }

    const bool bInputIsEmpty = TextToImport.TrimStartAndEnd().IsEmpty();
    if (!bInputIsEmpty && !FEdGraphUtilities::CanImportNodesFromText(Graph, TextToImport))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Import failed: '%s' does not contain nodes accepted by graph '%s'."), *AbsoluteFilePath, *GraphName);
        return false;
    }

    Blueprint->Modify();
    Graph->Modify();

    if (bClearExisting)
    {
        BlueprintPorter::ClearGraph(Blueprint, Graph);
    }

    TSet<UEdGraphNode*> ImportedNodes;
    if (!bInputIsEmpty)
    {
        FEdGraphUtilities::ImportNodesFromText(Graph, TextToImport, ImportedNodes);
    }

    Graph->NotifyGraphChanged();
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);

    UE_LOG(
        LogBlueprintPorter,
        Log,
        TEXT("Imported %d node(s) from '%s' into graph '%s' of '%s'."),
        ImportedNodes.Num(),
        *AbsoluteFilePath,
        *GraphName,
        *Blueprint->GetPathName());
    return true;
}

TArray<FString> UBlueprintPorterLibrary::ListBlueprintGraphs(UBlueprint* Blueprint)
{
    TArray<FString> GraphNames;
    for (UEdGraph* Graph : BlueprintPorter::GatherGraphs(Blueprint))
    {
        GraphNames.Add(Graph->GetName());
    }
    return GraphNames;
}

TArray<FString> UBlueprintPorterLibrary::ListBlueprintVariables(UBlueprint* Blueprint)
{
    TArray<FString> VariableNames;
    if (!IsValid(Blueprint))
    {
        return VariableNames;
    }

    for (const FBPVariableDescription& Variable : Blueprint->NewVariables)
    {
        VariableNames.Add(Variable.VarName.ToString());
    }
    return VariableNames;
}

bool UBlueprintPorterLibrary::AddOverrideFunctionGraph(
    UBlueprint* Blueprint,
    const FString& FunctionName,
    UClass* SignatureClass)
{
    if (!IsValid(Blueprint) || !IsValid(SignatureClass) || FunctionName.IsEmpty())
    {
        return false;
    }

    if (BlueprintPorter::FindGraph(Blueprint, FunctionName))
    {
        return true;
    }

    if (!SignatureClass->FindFunctionByName(FName(*FunctionName)))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Override signature '%s' was not found on '%s'."), *FunctionName, *SignatureClass->GetPathName());
        return false;
    }

    Blueprint->Modify();
    UEdGraph* NewGraph = FBlueprintEditorUtils::CreateNewGraph(
        Blueprint,
        FName(*FunctionName),
        UEdGraph::StaticClass(),
        UEdGraphSchema_K2::StaticClass());
    if (!IsValid(NewGraph))
    {
        return false;
    }

    FBlueprintEditorUtils::AddFunctionGraph(Blueprint, NewGraph, false, SignatureClass);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return BlueprintPorter::FindGraph(Blueprint, FunctionName) != nullptr;
}

bool UBlueprintPorterLibrary::SetWidgetVariableGuid(
    UWidgetBlueprint* Blueprint,
    const FString& VariableName,
    const FString& GuidDigits)
{
    if (!IsValid(Blueprint) || !IsValid(Blueprint->WidgetTree) || VariableName.IsEmpty())
    {
        return false;
    }

    const FName VariableFName(*VariableName);
    if (!IsValid(Blueprint->WidgetTree->FindWidget(VariableFName)))
    {
        return false;
    }

    FGuid ParsedGuid;
    if (!FGuid::ParseExact(GuidDigits, EGuidFormats::Digits, ParsedGuid))
    {
        return false;
    }

    Blueprint->Modify();
    Blueprint->WidgetVariableNameToGuidMap.Add(VariableFName, ParsedGuid);
    return true;
}

bool UBlueprintPorterLibrary::RefreshBlueprintNodes(UBlueprint* Blueprint)
{
    if (!IsValid(Blueprint))
    {
        return false;
    }
    FBlueprintEditorUtils::RefreshAllNodes(Blueprint);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

int32 UBlueprintPorterLibrary::RepairSelfVariableReferences(UBlueprint* Blueprint)
{
    if (!IsValid(Blueprint))
    {
        return 0;
    }

    int32 RepairedCount = 0;
    Blueprint->Modify();
    for (UEdGraph* Graph : BlueprintPorter::GatherGraphs(Blueprint))
    {
        for (UEdGraphNode* Node : Graph->Nodes)
        {
            UK2Node_Variable* VariableNode = Cast<UK2Node_Variable>(Node);
            if (!IsValid(VariableNode) || !VariableNode->VariableReference.IsSelfContext())
            {
                continue;
            }

            const FName VariableName = VariableNode->VariableReference.GetMemberName();
            if (VariableName.IsNone())
            {
                continue;
            }

            VariableNode->Modify();
            // Cross-version clipboard data can carry a GUID that is valid only
            // in the source Blueprint. Resolve against the target by name.
            VariableNode->VariableReference.SetDirect(VariableName, FGuid(), nullptr, true);
            VariableNode->ReconstructNode();
            ++RepairedCount;
        }
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    UE_LOG(LogBlueprintPorter, Log, TEXT("Rebound %d self variable node(s) in '%s'."), RepairedCount, *Blueprint->GetPathName());
    return RepairedCount;
}

bool UBlueprintPorterLibrary::RebindOverrideFunction(
    UBlueprint* Blueprint,
    const FString& FunctionName,
    UClass* SignatureClass)
{
    if (!IsValid(Blueprint) || !IsValid(SignatureClass) || FunctionName.IsEmpty())
    {
        return false;
    }

    const FName FunctionFName(*FunctionName);
    if (!SignatureClass->FindFunctionByName(FunctionFName))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Override signature '%s' was not found on '%s'."), *FunctionName, *SignatureClass->GetPathName());
        return false;
    }

    UEdGraph* Graph = BlueprintPorter::FindGraph(Blueprint, FunctionName);
    if (!IsValid(Graph))
    {
        return false;
    }

    int32 TerminatorCount = 0;
    Blueprint->Modify();
    Graph->Modify();
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (UK2Node_FunctionEntry* Entry = Cast<UK2Node_FunctionEntry>(Node))
        {
            Entry->Modify();
            Entry->FunctionReference.SetExternalMember(FunctionFName, SignatureClass);
            Entry->ReconstructNode();
            ++TerminatorCount;
        }
        else if (UK2Node_FunctionResult* Result = Cast<UK2Node_FunctionResult>(Node))
        {
            Result->Modify();
            Result->FunctionReference.SetExternalMember(FunctionFName, SignatureClass);
            Result->ReconstructNode();
            ++TerminatorCount;
        }
    }

    Graph->NotifyGraphChanged();
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    UE_LOG(LogBlueprintPorter, Log, TEXT("Rebound %d override terminator(s) for '%s' in '%s'."), TerminatorCount, *FunctionName, *Blueprint->GetPathName());
    return TerminatorCount > 0;
}

bool UBlueprintPorterLibrary::ExportWidgetTree(
    UWidgetBlueprint* Blueprint,
    const FString& FilePath)
{
    if (!IsValid(Blueprint) || !IsValid(Blueprint->WidgetTree)
        || !IsValid(Blueprint->WidgetTree->RootWidget))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Widget export failed: Blueprint has no valid root widget."));
        return false;
    }

    TArray<UWidget*> Roots;
    Blueprint->WidgetTree->GetAllWidgets(Roots);
    FString ExportedText;
    FWidgetBlueprintEditorUtils::ExportWidgetsToText(Roots, ExportedText);

    const FString AbsoluteFilePath = FPaths::ConvertRelativePathToFull(FilePath);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(AbsoluteFilePath), true);
    if (!FFileHelper::SaveStringToFile(
            ExportedText,
            *AbsoluteFilePath,
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Widget export failed: could not save '%s'."), *AbsoluteFilePath);
        return false;
    }

    UE_LOG(LogBlueprintPorter, Log, TEXT("Exported widget tree from '%s' to '%s'."), *Blueprint->GetPathName(), *AbsoluteFilePath);
    return true;
}

bool UBlueprintPorterLibrary::ImportWidgetTree(
    UWidgetBlueprint* Blueprint,
    const FString& FilePath,
    bool bClearExisting)
{
    if (!IsValid(Blueprint) || !IsValid(Blueprint->WidgetTree))
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Widget import failed: invalid Widget Blueprint."));
        return false;
    }

    const FString AbsoluteFilePath = FPaths::ConvertRelativePathToFull(FilePath);
    FString TextToImport;
    if (!FFileHelper::LoadFileToString(TextToImport, *AbsoluteFilePath)
        || TextToImport.TrimStartAndEnd().IsEmpty())
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Widget import failed: could not read '%s'."), *AbsoluteFilePath);
        return false;
    }

    Blueprint->Modify();
    Blueprint->WidgetTree->Modify();
    if (bClearExisting && IsValid(Blueprint->WidgetTree->RootWidget))
    {
        TArray<UWidget*> ExistingWidgets;
        Blueprint->WidgetTree->GetAllWidgets(ExistingWidgets);
        for (UWidget* ExistingWidget : ExistingWidgets)
        {
            if (IsValid(ExistingWidget))
            {
                Blueprint->OnVariableRemoved(ExistingWidget->GetFName());
            }
        }
        TSet<UWidget*> ExistingRoot;
        ExistingRoot.Add(Blueprint->WidgetTree->RootWidget);
        FWidgetBlueprintEditorUtils::DeleteWidgets(
            Blueprint,
            ExistingRoot,
            FWidgetBlueprintEditorUtils::EDeleteWidgetWarningType::DeleteSilently);
    }

    TSet<UWidget*> ImportedWidgets;
    TMap<FName, UWidgetSlotPair*> ExtraSlotData;
    FWidgetBlueprintEditorUtils::ImportWidgetsFromText(
        Blueprint,
        TextToImport,
        ImportedWidgets,
        ExtraSlotData);

    TArray<UWidget*> ImportedRoots;
    for (UWidget* Widget : ImportedWidgets)
    {
        if (IsValid(Widget))
        {
            Widget->bIsVariable = true;
            Blueprint->OnVariableAdded(Widget->GetFName());
            if (Widget->GetParent() == nullptr)
            {
                ImportedRoots.Add(Widget);
            }
        }
    }

    if (ImportedRoots.Num() != 1)
    {
        UE_LOG(LogBlueprintPorter, Error, TEXT("Widget import failed: expected one root widget, found %d."), ImportedRoots.Num());
        return false;
    }

    Blueprint->WidgetTree->RootWidget = ImportedRoots[0];
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    UE_LOG(LogBlueprintPorter, Log, TEXT("Imported %d widget(s) into '%s'."), ImportedWidgets.Num(), *Blueprint->GetPathName());
    return true;
}

bool UBlueprintPorterLibrary::ExportBlueprintComponents(UBlueprint* Blueprint, const FString& FilePath)
{
    if (!IsValid(Blueprint) || !IsValid(Blueprint->SimpleConstructionScript))
    {
        return false;
    }

    TMap<const USCS_Node*, FString> ParentNames;
    for (USCS_Node* Parent : Blueprint->SimpleConstructionScript->GetAllNodes())
    {
        if (!IsValid(Parent))
        {
            continue;
        }
        for (USCS_Node* Child : Parent->GetChildNodes())
        {
            ParentNames.Add(Child, Parent->GetVariableName().ToString());
        }
    }

    TArray<FString> Lines;
    for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
    {
        if (!IsValid(Node) || !IsValid(Node->ComponentTemplate))
        {
            continue;
        }

        FString Line = FString::Printf(
            TEXT("name=%s\tclass=%s\tparent=%s"),
            *Node->GetVariableName().ToString(),
            *Node->ComponentTemplate->GetClass()->GetPathName(),
            *ParentNames.FindRef(Node));

        if (const USceneComponent* Scene = Cast<USceneComponent>(Node->ComponentTemplate))
        {
            Line += FString::Printf(
                TEXT("\tlocation=%s\trotation=%s\tscale=%s"),
                *Scene->GetRelativeLocation().ToString(),
                *Scene->GetRelativeRotation().ToString(),
                *Scene->GetRelativeScale3D().ToString());
        }
        if (const UWidgetComponent* Widget = Cast<UWidgetComponent>(Node->ComponentTemplate))
        {
            Line += FString::Printf(
                TEXT("\twidget_class=%s\tdraw_size=%s\tdraw_desired=%s\tspace=%d\tpivot=%s"),
                Widget->GetWidgetClass() ? *Widget->GetWidgetClass()->GetPathName() : TEXT("None"),
                *Widget->GetDrawSize().ToString(),
                Widget->GetDrawAtDesiredSize() ? TEXT("true") : TEXT("false"),
                static_cast<int32>(Widget->GetWidgetSpace()),
                *Widget->GetPivot().ToString());
        }
        Lines.Add(Line);
    }

    return FFileHelper::SaveStringArrayToFile(
        Lines,
        *FPaths::ConvertRelativePathToFull(FilePath),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

bool UBlueprintPorterLibrary::AddActorComponentNode(
    UBlueprint* Blueprint,
    UClass* ComponentClass,
    const FString& VariableName)
{
    if (!IsValid(Blueprint) || !IsValid(Blueprint->SimpleConstructionScript)
        || !IsValid(ComponentClass) || !ComponentClass->IsChildOf(UActorComponent::StaticClass())
        || VariableName.IsEmpty())
    {
        return false;
    }

    if (Blueprint->SimpleConstructionScript->FindSCSNode(FName(*VariableName)))
    {
        return true;
    }

    Blueprint->Modify();
    USCS_Node* Node = Blueprint->SimpleConstructionScript->CreateNode(ComponentClass, FName(*VariableName));
    Blueprint->SimpleConstructionScript->AddNode(Node);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return IsValid(Node);
}

bool UBlueprintPorterLibrary::AddWidgetComponentNode(
    UBlueprint* Blueprint,
    const FString& VariableName,
    const FString& ParentVariableName,
    TSubclassOf<UUserWidget> WidgetClass,
    FVector RelativeLocation,
    FRotator RelativeRotation,
    FVector2D DrawSize,
    bool bDrawAtDesiredSize)
{
    if (!IsValid(Blueprint) || !IsValid(Blueprint->SimpleConstructionScript)
        || VariableName.IsEmpty() || !WidgetClass)
    {
        return false;
    }

    USCS_Node* Node = Blueprint->SimpleConstructionScript->FindSCSNode(FName(*VariableName));
    if (!IsValid(Node))
    {
        Blueprint->Modify();
        Node = Blueprint->SimpleConstructionScript->CreateNode(UWidgetComponent::StaticClass(), FName(*VariableName));
        if (USCS_Node* Parent = Blueprint->SimpleConstructionScript->FindSCSNode(FName(*ParentVariableName)))
        {
            Parent->AddChildNode(Node);
        }
        else
        {
            Blueprint->SimpleConstructionScript->AddNode(Node);
        }
    }

    UWidgetComponent* Widget = Cast<UWidgetComponent>(Node->ComponentTemplate);
    if (!IsValid(Widget))
    {
        return false;
    }
    Widget->Modify();
    Widget->SetWidgetClass(WidgetClass);
    Widget->SetRelativeLocation(RelativeLocation);
    Widget->SetRelativeRotation(RelativeRotation);
    Widget->SetDrawSize(FIntPoint(FMath::RoundToInt(DrawSize.X), FMath::RoundToInt(DrawSize.Y)));
    Widget->SetDrawAtDesiredSize(bDrawAtDesiredSize);
    Widget->SetWidgetSpace(EWidgetSpace::Screen);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool UBlueprintPorterLibrary::AddMontageNotifyState(
    UAnimMontage* Montage,
    TSubclassOf<UAnimNotifyState> NotifyStateClass,
    float StartTime,
    float Duration,
    int32 TrackIndex)
{
    if (!IsValid(Montage) || !NotifyStateClass || Duration <= 0.0f)
    {
        return false;
    }

    for (const FAnimNotifyEvent& Existing : Montage->Notifies)
    {
        if (Existing.NotifyStateClass
            && Existing.NotifyStateClass->GetClass() == NotifyStateClass
            && FMath::IsNearlyEqual(Existing.GetTime(), StartTime, KINDA_SMALL_NUMBER)
            && FMath::IsNearlyEqual(Existing.GetDuration(), Duration, KINDA_SMALL_NUMBER))
        {
            return true;
        }
    }

    Montage->Modify();
    FAnimNotifyEvent& Event = Montage->Notifies.AddDefaulted_GetRef();
    Event.NotifyStateClass = NewObject<UAnimNotifyState>(
        Montage,
        NotifyStateClass,
        NAME_None,
        RF_Transactional);
    Event.NotifyName = Event.NotifyStateClass->GetFName();
    Event.TrackIndex = TrackIndex;
    Event.Link(Montage, StartTime, 0);
    Event.SetDuration(Duration);
    Event.Guid = FGuid::NewGuid();
    Event.TriggerTimeOffset = GetTriggerTimeOffsetForType(Montage->CalculateOffsetForNotify(StartTime));
    Event.EndTriggerTimeOffset = GetTriggerTimeOffsetForType(Montage->CalculateOffsetForNotify(StartTime + Duration));
    Montage->SortNotifies();
    Montage->RefreshCacheData();
    Montage->MarkPackageDirty();
    return true;
}

bool UBlueprintPorterLibrary::ExportMontageNotifies(UAnimMontage* Montage, const FString& FilePath)
{
    if (!IsValid(Montage) || FilePath.IsEmpty())
    {
        return false;
    }

    TArray<FString> Lines;
    for (const FAnimNotifyEvent& Event : Montage->Notifies)
    {
        FString ClassPath = TEXT("None");
        FString Kind = TEXT("Named");
        if (Event.NotifyStateClass)
        {
            Kind = TEXT("State");
            ClassPath = Event.NotifyStateClass->GetClass()->GetPathName();
        }
        else if (Event.Notify)
        {
            Kind = TEXT("Notify");
            ClassPath = Event.Notify->GetClass()->GetPathName();
        }

        Lines.Add(FString::Printf(
            TEXT("kind=%s\tclass=%s\tname=%s\tstart=%.6f\tduration=%.6f\ttrack=%d"),
            *Kind,
            *ClassPath,
            *Event.NotifyName.ToString(),
            Event.GetTime(),
            Event.GetDuration(),
            Event.TrackIndex));
    }

    Lines.Add(FString::Printf(TEXT("montage\tlength=%.6f"), Montage->GetPlayLength()));
    for (const FSlotAnimationTrack& Slot : Montage->SlotAnimTracks)
    {
        Lines.Add(FString::Printf(
            TEXT("slot\tname=%s\tsegments=%d"),
            *Slot.SlotName.ToString(),
            Slot.AnimTrack.AnimSegments.Num()));
        for (int32 Index = 0; Index < Slot.AnimTrack.AnimSegments.Num(); ++Index)
        {
            const FAnimSegment& Segment = Slot.AnimTrack.AnimSegments[Index];
            const UAnimSequenceBase* Reference = Segment.GetAnimReference();
            Lines.Add(FString::Printf(
                TEXT("segment\tslot=%s\tindex=%d\tasset=%s\tstart=%.6f\tanim_start=%.6f\tanim_end=%.6f\trate=%.6f\tloops=%d"),
                *Slot.SlotName.ToString(),
                Index,
                Reference ? *Reference->GetPathName() : TEXT("None"),
                Segment.StartPos,
                Segment.AnimStartTime,
                Segment.AnimEndTime,
                Segment.AnimPlayRate,
                Segment.LoopingCount));
        }
    }
    for (const FCompositeSection& Section : Montage->CompositeSections)
    {
        Lines.Add(FString::Printf(
            TEXT("section\tname=%s\tstart=%.6f\tnext=%s"),
            *Section.SectionName.ToString(),
            Section.GetTime(),
            *Section.NextSectionName.ToString()));
    }
    Lines.Sort();

    return FFileHelper::SaveStringArrayToFile(
        Lines,
        *FPaths::ConvertRelativePathToFull(FilePath),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

bool UBlueprintPorterLibrary::RenameCustomEventByGuid(
    UBlueprint* Blueprint,
    const FString& NodeGuidDigits,
    const FString& NewName)
{
    if (!IsValid(Blueprint) || NewName.IsEmpty())
    {
        return false;
    }

    FGuid NodeGuid;
    if (!FGuid::ParseExact(NodeGuidDigits, EGuidFormats::Digits, NodeGuid))
    {
        return false;
    }

    for (UEdGraph* Graph : BlueprintPorter::GatherGraphs(Blueprint))
    {
        for (UEdGraphNode* Node : Graph->Nodes)
        {
            UK2Node_CustomEvent* CustomEvent = Cast<UK2Node_CustomEvent>(Node);
            if (CustomEvent && CustomEvent->NodeGuid == NodeGuid)
            {
                CustomEvent->Modify();
                CustomEvent->OnRenameNode(NewName);
                FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
                return true;
            }
        }
    }
    return false;
}

bool UBlueprintPorterLibrary::SetFunctionBoolReturnDefault(
    UBlueprint* Blueprint,
    const FString& FunctionName,
    bool Value)
{
    if (!IsValid(Blueprint))
    {
        return false;
    }

    UEdGraph* Graph = BlueprintPorter::FindGraph(Blueprint, FunctionName);
    if (!IsValid(Graph))
    {
        return false;
    }

    const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        UK2Node_FunctionResult* Result = Cast<UK2Node_FunctionResult>(Node);
        if (!Result)
        {
            continue;
        }

        if (UEdGraphPin* ReturnPin = Result->FindPin(TEXT("ReturnValue"), EGPD_Input))
        {
            Result->Modify();
            Schema->TrySetDefaultValue(*ReturnPin, Value ? TEXT("true") : TEXT("false"));
            FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
            return true;
        }
    }
    return false;
}

bool UBlueprintPorterLibrary::ConnectFunctionBoolReturnLiteral(
    UBlueprint* Blueprint,
    const FString& FunctionName,
    bool Value)
{
    if (!IsValid(Blueprint))
    {
        return false;
    }

    UEdGraph* Graph = BlueprintPorter::FindGraph(Blueprint, FunctionName);
    if (!IsValid(Graph))
    {
        return false;
    }

    UK2Node_FunctionResult* Result = nullptr;
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        Result = Cast<UK2Node_FunctionResult>(Node);
        if (Result)
        {
            break;
        }
    }
    if (!Result)
    {
        return false;
    }

    UEdGraphPin* ReturnPin = Result->FindPin(TEXT("ReturnValue"), EGPD_Input);
    const UFunction* LiteralFunction = UKismetSystemLibrary::StaticClass()->FindFunctionByName(TEXT("MakeLiteralBool"));
    if (!ReturnPin || !LiteralFunction)
    {
        return false;
    }

    UK2Node_CallFunction* LiteralNode = nullptr;
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        UK2Node_CallFunction* Candidate = Cast<UK2Node_CallFunction>(Node);
        if (Candidate && Candidate->FunctionReference.GetMemberName() == TEXT("MakeLiteralBool"))
        {
            LiteralNode = Candidate;
            break;
        }
    }

    if (!LiteralNode)
    {
        Graph->Modify();
        LiteralNode = NewObject<UK2Node_CallFunction>(Graph);
        LiteralNode->SetFlags(RF_Transactional);
        LiteralNode->SetFromFunction(LiteralFunction);
        LiteralNode->CreateNewGuid();
        LiteralNode->NodePosX = Result->NodePosX - 240;
        LiteralNode->NodePosY = Result->NodePosY + 80;
        Graph->AddNode(LiteralNode, true, false);
        LiteralNode->PostPlacedNewNode();
        LiteralNode->AllocateDefaultPins();
    }

    UEdGraphPin* ValuePin = LiteralNode->FindPin(TEXT("Value"), EGPD_Input);
    UEdGraphPin* LiteralReturnPin = LiteralNode->FindPin(TEXT("ReturnValue"), EGPD_Output);
    if (!ValuePin || !LiteralReturnPin)
    {
        return false;
    }

    const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
    LiteralNode->Modify();
    Result->Modify();
    Schema->TrySetDefaultValue(*ValuePin, Value ? TEXT("true") : TEXT("false"));
    ReturnPin->BreakAllPinLinks();
    if (!Schema->TryCreateConnection(LiteralReturnPin, ReturnPin))
    {
        return false;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}
