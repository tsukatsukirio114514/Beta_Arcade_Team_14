#include "BlueprintPorterGraphTools.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/Blueprint.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphSchema_K2.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/StructureEditorUtils.h"
#include "UserDefinedStructure/UserDefinedStructEditorData.h"
#include "K2Node_CallFunction.h"
#include "K2Node_CallArrayFunction.h"
#include "K2Node_MacroInstance.h"
#include "K2Node_MakeArray.h"
#include "K2Node_CallDelegate.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_FunctionResult.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_Self.h"
#include "K2Node_MakeStruct.h"
#include "K2Node_BreakStruct.h"
#include "UObject/UnrealType.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Logging/TokenizedMessage.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/LinkerLoad.h"

void UBlueprintPorterGraphTools::PrepareAssetsForRename(const TArray<UObject*>& Assets)
{
    FlushAsyncLoading();
    TSet<UPackage*> Packages;
    for(UObject* Asset:Assets)if(Asset)
    {
        UPackage* P=Asset->GetOutermost();P->FullyLoad();Packages.Add(P);
        if(auto* BP=Cast<UBlueprint>(Asset))if(BP->GeneratedClass)BP->GeneratedClass->GetDefaultObject();
    }
    FlushAsyncLoading();
    // No deferred CDO imports may remain bound to a package's pre-rename path.
    for(UPackage* P:Packages)ResetLoaders(P);
}

namespace PorterGraph
{
FString S(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, const FString& Default=TEXT(""))
{
    FString V; return O->TryGetStringField(Key,V) ? V : Default;
}
FEdGraphPinType Type(const TSharedPtr<FJsonObject>& O)
{
    FEdGraphPinType T; T.PinCategory=FName(*S(O,TEXT("type"),TEXT("real")));
    if(T.PinCategory==TEXT("real")) T.PinSubCategory=TEXT("double");
    const FString Object=S(O,TEXT("class"));
    if(!Object.IsEmpty()) T.PinSubCategoryObject=LoadObject<UObject>(nullptr,*Object);
    bool bArray=false;O->TryGetBoolField(TEXT("array"),bArray);if(bArray)T.ContainerType=EPinContainerType::Array;
    return T;
}
UEdGraphPin* Pin(UEdGraphNode* N, const FString& Name)
{
    if(!N) return nullptr;
    if(UEdGraphPin* P=N->FindPin(FName(*Name))) return P;
    // User-defined struct pins have GUID suffixes. Specs use friendly names.
    for(UEdGraphPin* P:N->Pins)
        if(P->PinFriendlyName.ToString()==Name || P->PinName.ToString().StartsWith(Name+TEXT("_"))) return P;
    return nullptr;
}
}

FString UBlueprintPorterGraphTools::BuildGraph(UBlueprint* BP,const FString& GraphName,const FString& Json)
{
    using namespace PorterGraph;
    if(!BP) return TEXT("Null Blueprint");
    TSharedPtr<FJsonObject> Spec;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Spec)) return TEXT("Invalid JSON");
    UEdGraph* G=nullptr;
    bool bAppend=false;Spec->TryGetBoolField(TEXT("append"),bAppend);
    for(UEdGraph* Candidate:BP->FunctionGraphs) if(Candidate->GetName()==GraphName) G=Candidate;
    if(bAppend)for(UEdGraph* Candidate:BP->UbergraphPages)if(Candidate->GetName()==GraphName)G=Candidate;
    if(!G)
    {
        G=FBlueprintEditorUtils::CreateNewGraph(BP,FName(*GraphName),UEdGraph::StaticClass(),UEdGraphSchema_K2::StaticClass());
        FBlueprintEditorUtils::AddFunctionGraph(BP,G,false,(UFunction*)nullptr);
    }
    BP->Modify(); G->Modify();
    UK2Node_FunctionEntry* Entry=nullptr;
    TArray<TObjectPtr<UEdGraphNode>> Old=G->Nodes;
    for(UEdGraphNode* N:Old)
    {
        if(bAppend)continue;
        if(auto* E=Cast<UK2Node_FunctionEntry>(N)) {Entry=E; E->BreakAllNodeLinks();}
        else FBlueprintEditorUtils::RemoveNode(BP,N,true);
    }
    if(!Entry&&!bAppend) return TEXT("Function entry missing");
    const UEdGraphSchema_K2* Schema=GetDefault<UEdGraphSchema_K2>();
    const TArray<TSharedPtr<FJsonValue>>* Inputs;
    if(Entry&&Spec->TryGetArrayField(TEXT("inputs"),Inputs)) for(auto V:*Inputs)
    {
        auto O=V->AsObject(); FName Name(*S(O,TEXT("name")));
        if(!Entry->FindPin(Name)) Entry->CreateUserDefinedPin(Name,Type(O),EGPD_Output,false);
    }
    if(Entry){Entry->NodePosX=0;Entry->NodePosY=0;}
    TMap<FString,UEdGraphNode*> Nodes;if(Entry)Nodes.Add(TEXT("entry"),Entry);
    if(bAppend)for(UEdGraphNode* N:G->Nodes)Nodes.Add(N->GetName(),N);
    const TArray<TSharedPtr<FJsonValue>>* NodeSpecs;
    if(!Spec->TryGetArrayField(TEXT("nodes"),NodeSpecs)) return TEXT("nodes missing");
    int32 Index=0;
    for(auto V:*NodeSpecs)
    {
        auto O=V->AsObject(); const FString ID=S(O,TEXT("id")), Kind=S(O,TEXT("kind"));
        UK2Node* N=nullptr;
        if(Kind==TEXT("call"))
        {
            UClass* C=S(O,TEXT("class")).IsEmpty()?BP->SkeletonGeneratedClass.Get():LoadObject<UClass>(nullptr,*S(O,TEXT("class")));
            UFunction* F=C?C->FindFunctionByName(FName(*S(O,TEXT("name")))):nullptr;
            if(!F) return TEXT("Function missing: ")+ID+TEXT(" ")+S(O,TEXT("name"));
            UK2Node_CallFunction* Call=F->HasMetaData(TEXT("ArrayParm"))?(UK2Node_CallFunction*)NewObject<UK2Node_CallArrayFunction>(G):NewObject<UK2Node_CallFunction>(G);Call->SetFromFunction(F);N=Call;
        }
        else if(Kind==TEXT("get")||Kind==TEXT("set"))
        {
            UK2Node_Variable* Var=Kind==TEXT("get")?(UK2Node_Variable*)NewObject<UK2Node_VariableGet>(G):(UK2Node_Variable*)NewObject<UK2Node_VariableSet>(G);
            const FString Class=S(O,TEXT("class"));
            if(Class.IsEmpty()) Var->VariableReference.SetSelfMember(FName(*S(O,TEXT("name"))));
            else Var->VariableReference.SetExternalMember(FName(*S(O,TEXT("name"))),LoadObject<UClass>(nullptr,*Class));
            N=Var;
        }
        else if(Kind==TEXT("branch")) N=NewObject<UK2Node_IfThenElse>(G);
        else if(Kind==TEXT("macro"))
        {
            UEdGraph* Macro=LoadObject<UEdGraph>(nullptr,*S(O,TEXT("path")));
            if(!Macro)return TEXT("Macro not found: ")+ID;
            auto* M=NewObject<UK2Node_MacroInstance>(G);M->SetMacroGraph(Macro);N=M;
        }
        else if(Kind==TEXT("array"))N=NewObject<UK2Node_MakeArray>(G);
        else if(Kind==TEXT("self")) N=NewObject<UK2Node_Self>(G);
        else if(Kind==TEXT("make")||Kind==TEXT("break"))
        {
            UScriptStruct* Struct=LoadObject<UScriptStruct>(nullptr,*S(O,TEXT("class")));
            if(!Struct) return TEXT("Struct missing: ")+ID;
            if(Kind==TEXT("make")){auto* M=NewObject<UK2Node_MakeStruct>(G);M->StructType=Struct;N=M;}
            else {auto* B=NewObject<UK2Node_BreakStruct>(G);B->StructType=Struct;N=B;}
        }
        else if(Kind==TEXT("delegate"))
        {
            auto* D=NewObject<UK2Node_CallDelegate>(G);
            FProperty* Prop=FindFProperty<FProperty>(BP->SkeletonGeneratedClass,FName(*S(O,TEXT("name"))));
            if(!Prop) return TEXT("Delegate missing: ")+ID;
            D->SetFromProperty(Prop,true,BP->SkeletonGeneratedClass);N=D;
        }
        else if(Kind==TEXT("result"))
        {
            auto* R=NewObject<UK2Node_FunctionResult>(G);R->FunctionReference=Entry->FunctionReference;N=R;
        }
        if(!N) return TEXT("Unknown node kind: ")+Kind;
        G->AddNode(N,true,false);N->CreateNewGuid();N->PostPlacedNewNode();N->AllocateDefaultPins();
        if(Kind==TEXT("result"))
        {
            const TArray<TSharedPtr<FJsonValue>>* Outputs;
            if(Spec->TryGetArrayField(TEXT("outputs"),Outputs)) for(auto Output:*Outputs)
            {auto P=Output->AsObject();CastChecked<UK2Node_FunctionResult>(N)->CreateUserDefinedPin(FName(*S(P,TEXT("name"))),Type(P),EGPD_Input,false);}
        }
        N->NodePosX=350*(1+Index%5);N->NodePosY=250*(Index/5);++Index;
        N->NodeComment=S(O,TEXT("comment"));
        Nodes.Add(ID,N);
    }
    for(auto V:*NodeSpecs)
    {
        auto O=V->AsObject();auto* N=Nodes.FindRef(S(O,TEXT("id")));
        const TSharedPtr<FJsonObject>* PinTypes;
        if(O->TryGetObjectField(TEXT("pin_types"),PinTypes))for(auto& Pair:(*PinTypes)->Values)
        {
            auto* P=Pin(N,Pair.Key);if(!P)return TEXT("Typed pin missing: ")+Pair.Key;
            P->PinType=Type(Pair.Value->AsObject());
        }
        const TSharedPtr<FJsonObject>* Defaults;
        if(O->TryGetObjectField(TEXT("defaults"),Defaults)) for(auto& Pair:(*Defaults)->Values)
        {
            auto* P=Pin(N,Pair.Key);if(!P)return TEXT("Default pin missing: ")+S(O,TEXT("id"))+TEXT(".")+Pair.Key;
            const FString Value=Pair.Value->AsString();
            if(P->PinType.PinCategory==UEdGraphSchema_K2::PC_Object||P->PinType.PinCategory==UEdGraphSchema_K2::PC_Class)
                Schema->TrySetDefaultObject(*P,Value==TEXT("None")?nullptr:LoadObject<UObject>(nullptr,*Value));
            else Schema->TrySetDefaultValue(*P,Value);
        }
    }
    const TArray<TSharedPtr<FJsonValue>>* Links;
    if(Spec->TryGetArrayField(TEXT("links"),Links)) for(auto V:*Links)
    {
        const auto& A=V->AsArray();const FString From=A[0]->AsString(),To=A[2]->AsString();
        UEdGraphPin* P=Pin(Nodes.FindRef(From),A[1]->AsString());UEdGraphPin* Q=Pin(Nodes.FindRef(To),A[3]->AsString());
        if(!P||!Q)return TEXT("Link pin missing: ")+From+TEXT(".")+A[1]->AsString()+TEXT(" -> ")+To+TEXT(".")+A[3]->AsString();
        if(!Schema->TryCreateConnection(P,Q))return TEXT("Link rejected: ")+From+TEXT(" -> ")+To;
    }
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);G->NotifyGraphChanged();return TEXT("");
}

UUserDefinedStruct* UBlueprintPorterGraphTools::CreateStructAsset(const FString& Path,const FString& FieldsJson)
{
    if(auto* Existing=LoadObject<UUserDefinedStruct>(nullptr,*(Path+TEXT(".")+FPackageName::GetLongPackageAssetName(Path))))return Existing;
    TArray<TSharedPtr<FJsonValue>> Fields;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(FieldsJson),Fields))return nullptr;
    UPackage* Package=CreatePackage(*Path);
    auto* Struct=FStructureEditorUtils::CreateUserDefinedStruct(Package,FName(*FPackageName::GetLongPackageAssetName(Path)),RF_Public|RF_Standalone);
    TArray<FGuid> Original;
    for(const auto& Desc:FStructureEditorUtils::GetVarDesc(Struct))Original.Add(Desc.VarGuid);
    for(auto Value:Fields)
    {
        auto O=Value->AsObject();if(!FStructureEditorUtils::AddVariable(Struct,PorterGraph::Type(O)))return nullptr;
        FGuid Guid=FStructureEditorUtils::GetVarDesc(Struct).Last().VarGuid;
        FStructureEditorUtils::RenameVariable(Struct,Guid,PorterGraph::S(O,TEXT("name")));
    }
    for(const FGuid& Guid:Original)FStructureEditorUtils::RemoveVariable(Struct,Guid);
    FStructureEditorUtils::CompileStructure(Struct);FAssetRegistryModule::AssetCreated(Struct);Struct->MarkPackageDirty();return Struct;
}
FString UBlueprintPorterGraphTools::StructFields(UUserDefinedStruct* Struct)
{
    TSharedPtr<FJsonObject> O=MakeShared<FJsonObject>();
    if(Struct)for(const auto& D:FStructureEditorUtils::GetVarDesc(Struct))O->SetStringField(D.FriendlyName,D.VarName.ToString());
    FString Json;FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));return Json;
}
FString UBlueprintPorterGraphTools::CompileChecked(UBlueprint* BP)
{
    FCompilerResultsLog Log;FKismetEditorUtilities::CompileBlueprint(BP,EBlueprintCompileOptions::None,&Log);
    FString Result;
    if(Log.NumErrors)for(auto Message:Log.Messages)Result+=Message->ToText().ToString()+TEXT("\n");
    return Result;
}
bool UBlueprintPorterGraphTools::SetComponentObjectDefault(UBlueprint* BP,const FString& Component,const FString& Property,UObject* Value)
{
    if(!BP||!BP->SimpleConstructionScript)return false;
    for(USCS_Node* N:BP->SimpleConstructionScript->GetAllNodes())if(N->GetVariableName()==FName(*Component))
    {
        auto* P=FindFProperty<FObjectPropertyBase>(N->ComponentTemplate->GetClass(),FName(*Property));
        if(!P)return false;N->ComponentTemplate->Modify();P->SetObjectPropertyValue_InContainer(N->ComponentTemplate,Value);
        FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);return true;
    }
    return false;
}
