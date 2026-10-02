#include "WalkingQuery.h"
#include "Physics/PhysicsFiltering.h"
#include "Misc/AutomationTest.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWalkingFilter08Test,"Measured.WalkingFilter08.ChannelPair",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWalkingFilter08Test::RunTest(const FString&){
 using namespace CookedWorldPort;
 // Installed5.8 builder constructors accept scene=nullptr and do not dereference it.
 // Actual Engine/Chaos implementations are linked; no duplicated response algorithm.
 auto Shape=[](ECollisionResponse Pawn,ECollisionResponse Visibility,bool Complex=false){
  FCollisionResponseContainer R;R.SetAllChannels(ECR_Ignore);
  R.SetResponse(ECC_Pawn,Pawn);R.SetResponse(ECC_Visibility,Visibility);
  FPhysicsFilterBuilder B(nullptr);B.SetCollisionChannelIndex(ECC_WorldStatic).SetResponses(R)
   .SetFlags(Chaos::EFilterFlags::SimpleCollision,!Complex).SetFlags(Chaos::EFilterFlags::ComplexCollision,Complex);
  return B.BuildShapeFilterData();
 };
 auto Query=[](ECollisionChannel C,ECollisionResponse Static){
  FCollisionResponseContainer R;R.SetAllChannels(ECR_Block);R.SetResponse(ECC_WorldStatic,Static);
  FPhysicsTraceQueryFilterBuilder B(nullptr);B.SetCollisionChannelIndex(C).SetResponses(R)
   .SetFlags(Chaos::EFilterFlags::SimpleCollision,true);
  return B.Build();
 };
 const auto Pawn=Query(ECC_Pawn,ECR_Block),Visibility=Query(ECC_Visibility,ECR_Block);
 const auto Kotel=Shape(ECR_Block,ECR_Ignore);
 int Checks=0;
 auto Check=[&](const TCHAR* N,EWalkingShape Actual,EWalkingShape Expected){++Checks;TestTrue(N,Actual==Expected);};
 Check(TEXT("Kotel Pawn block survives Visibility ignore"),ClassifyWalkingShape(true,false,Pawn,Kotel),EWalkingShape::Blocking);
 Check(TEXT("Visibility would miss Kotel"),ClassifyWalkingShape(true,false,Visibility,Kotel),EWalkingShape::NonBlockingResponse);
 Check(TEXT("Visibility-only face is not physical Pawn support"),ClassifyWalkingShape(true,false,Pawn,Shape(ECR_Ignore,ECR_Block)),EWalkingShape::NonBlockingResponse);
 Check(TEXT("Querier ignore participates"),ClassifyWalkingShape(true,false,Query(ECC_Pawn,ECR_Ignore),Kotel),EWalkingShape::NonBlockingResponse);
 Check(TEXT("Querier overlap is not blocking"),ClassifyWalkingShape(true,false,Query(ECC_Pawn,ECR_Overlap),Kotel),EWalkingShape::NonBlockingResponse);
 Check(TEXT("Target overlap is not blocking"),ClassifyWalkingShape(true,false,Pawn,Shape(ECR_Overlap,ECR_Block)),EWalkingShape::NonBlockingResponse);
 Check(TEXT("Query disabled excludes before geometry"),ClassifyWalkingShape(false,false,Pawn,Kotel),EWalkingShape::QueryDisabled);
 Check(TEXT("Simple movement excludes complex-only query shape"),ClassifyWalkingShape(true,false,Pawn,Shape(ECR_Block,ECR_Ignore,true)),EWalkingShape::OtherComplexity);
 Check(TEXT("Exact body flag excludes"),ClassifyWalkingShape(true,true,Pawn,Kotel),EWalkingShape::ExactOwnBody);
 // Invalid data never becomes an exclusion, even if the requested self flag is true.
 Check(TEXT("Unknown filter refuses"),ClassifyWalkingShape(true,true,{},{}),EWalkingShape::Unknown);
 FCollisionResponseContainer All;All.SetAllChannels(ECR_Block);
 FPhysicsFilterBuilder Player(nullptr);Player.SetCollisionChannelIndex(ECC_Pawn).SetResponses(All)
  .SetFlags(Chaos::EFilterFlags::SimpleCollision,true);
 Check(TEXT("Unrelated player blocks VAT Pawn query with no self exclusion"),ClassifyWalkingShape(true,false,Pawn,Player.BuildShapeFilterData()),EWalkingShape::Blocking);
 FPhysicsObjectQueryFilterBuilder Objects(nullptr);Objects.SetObjectTypes(uint64(1)<<ECC_WorldStatic);
 Check(TEXT("Object query cannot replace walking pair"),ClassifyWalkingShape(true,false,Objects.Build(),Kotel),EWalkingShape::Unknown);
 AddInfo(FString::Printf(TEXT("WalkingFilter08 actual engine helper checks=%d; no world or owner-binding runtime proof"),Checks));
 return !HasAnyErrors();
}
#endif
