// STAGED ONLY: actual Slate hierarchy test; uncompiled, never executed here.
// No fake UE types and no AddWindow/native-window creation.
#include "WindowHierarchy.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOnlineChildWindowRefusal,
    "Mikdash.Online.Candidate04.ChildWindowRefusal",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FOnlineChildWindowRefusal::RunTest(const FString&) {
    using MikdashOnline::RuntimeCandidate04::IsSoleChildlessWindow;
    const TSharedRef<SWindow> Root=SNew(SWindow);
    const TSharedRef<SWindow> Child=SNew(SWindow);
    const TSharedRef<SWindow> Grandchild=SNew(SWindow);
    TArray<TSharedRef<SWindow>> Roots;
    const TSharedPtr<SWindow> Expected=Root;
    TestFalse(TEXT("No root"),IsSoleChildlessWindow(Roots,Expected));
    Roots.Add(Root);
    TestTrue(TEXT("Exact childless root"),IsSoleChildlessWindow(Roots,Expected));
    TestFalse(TEXT("Wrong identity"),IsSoleChildlessWindow(Roots,TSharedPtr<SWindow>(Child)));
    Root->AddChildWindow(Child);
    TestFalse(TEXT("Native-child hierarchy refused"),IsSoleChildlessWindow(Roots,Expected));
    Child->AddChildWindow(Grandchild);
    TestFalse(TEXT("Grandchild subtree refused"),IsSoleChildlessWindow(Roots,Expected));
    Child->SetVisibility(EVisibility::Hidden);
    TestFalse(TEXT("Hidden child still refused"),IsSoleChildlessWindow(Roots,Expected));
    Roots.Add(Grandchild);
    TestFalse(TEXT("Multiple roots refused"),IsSoleChildlessWindow(Roots,Expected));
    return true;
}
#endif
