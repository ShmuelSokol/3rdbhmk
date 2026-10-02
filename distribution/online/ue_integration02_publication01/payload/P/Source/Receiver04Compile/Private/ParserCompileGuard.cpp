#include "CoreMinimal.h"
#include "runtime_candidate05/PrivateBootstrap.h"
#include <type_traits>

// Fail compilation instead of allowing an empty automation-test object to pass.
#if !WITH_DEV_AUTOMATION_TESTS
#error Candidate05 real parser assertions require WITH_DEV_AUTOMATION_TESTS
#endif
static_assert(std::is_same_v<
    decltype(&MikdashOnline::RuntimeCandidate05::ValidatePrivateRecord),
    bool (*)(const TArray<uint8>&,double,MikdashOnline::Receiver03::Bootstrap&)>);
// No startup hook, test execution, listener, process, fixture or engine launch.
