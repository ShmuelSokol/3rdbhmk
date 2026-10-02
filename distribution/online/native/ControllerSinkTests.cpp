// STAGED UE automation source. Not compiled, registered, or executed in this slice.
// Add to a future explicitly approved native test module; no Build.cs change here.
#if WITH_DEV_AUTOMATION_TESTS
#include "ControllerSink.h"
#include "Engine/World.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOnlineControllerSinkDeliveryTest,
    "Mikdash.Online.ControllerSink.DeliveryAndRelease",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FOnlineControllerSinkDeliveryTest::RunTest(const FString& Parameters)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if(!TestNotNull(TEXT("Test world"),World))return false;
    APlayerController* Controller=World->SpawnActor<APlayerController>();
    if(!TestNotNull(TEXT("Test controller"),Controller)){World->DestroyWorld(false);return false;}
    Controller->PlayerInput=nullptr;
    MikdashOnline::ControllerSink Uninitialized(Controller);
    TestFalse(TEXT("No PlayerInput: input refused"),Uninitialized.Apply("move",1,0));
    TestFalse(TEXT("No PlayerInput: release cannot ACK"),Uninitialized.Release());

    UPlayerInput* Input=NewObject<UPlayerInput>(Controller);
    Controller->PlayerInput=Input;
    MikdashOnline::ControllerSink Sink(Controller);
    TestTrue(TEXT("Recorded unbound WASD accepted for polling"),Sink.Apply("move",1,0));
    TestNotNull(TEXT("D sample recorded"),Input->GetKeyState(EKeys::D));
    TestTrue(TEXT("Analog recorded despite false consumption result"),Sink.Apply("look",.1,.2));
    Controller->PlayerInput=nullptr;
    TestFalse(TEXT("Rejected release is not acknowledged"),Sink.Release());
    Controller->PlayerInput=Input;
    TestTrue(TEXT("Held state retained: release can retry"),Sink.Release());
    const FKeyState* State=Input->GetKeyState(EKeys::D);
    TestTrue(TEXT("No down or queued movement survives release"),State && !State->bDown &&
        State->SampleCountAccumulator==0 && State->RawValueAccumulator.IsZero() &&
        State->EventAccumulator[IE_Pressed].IsEmpty());
    TestTrue(TEXT("Double cleanup is idempotent"),Sink.Release());
    TestTrue(TEXT("Same-frame E press/release recorded"),Sink.Apply("interact",0,0));
    TestTrue(TEXT("Move-zero does not erase E pulse"),Sink.Apply("move",0,0));
    const TArray<UInputComponent*> EmptyStack;
    Input->ProcessInputStack(EmptyStack,1.f/60.f,false);
    TestTrue(TEXT("Project AnyKey polling observes same-frame pulse"),Controller->WasInputKeyJustPressed(EKeys::AnyKey));
    TestTrue(TEXT("E polling observes press even after same-frame release"),Controller->WasInputKeyJustPressed(EKeys::E));
    TestFalse(TEXT("Pulse does not leave E down"),Controller->IsInputKeyDown(EKeys::E));
    World->DestroyWorld(false);
    return true;
}
#endif
