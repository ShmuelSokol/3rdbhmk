#include "../Plugin/NativeResourceInspector/Source/NativeResourceInspector/Private/ResourceInspectionDecision.h"
#include <cstring>
#include <iostream>

using ResourceInspectionDecision::Facts;
using ResourceInspectionDecision::Decide;
using ResourceInspectionDecision::QualityMatches;

static int Failures = 0;
static void Check(bool ok, const char* name)
{
    if (!ok) { ++Failures; std::cerr << "FAIL " << name << '\n'; }
}
static Facts ReadyFacts()
{
    Facts f;
    f.GameThread = f.Admitted = f.MaterialValid = f.TargetValid = true;
    f.ResourceBefore = f.ResourceAfter = f.IdentityStable = true;
    f.PlatformMatches = f.QualityMatches = true;
    f.Finished = f.MapPresent = f.MapValid = f.MapComplete = true;
    f.HasErrors = false;
    return f;
}
int main()
{
    const char* ready = "READY_REQUESTED_GAME_THREAD_RESOURCE_ONLY";
    Check(std::strcmp(Decide(ReadyFacts()), ready) == 0, "ready");
    struct Gate { bool Facts::* member; bool fault; const char* expected; };
    const Gate gates[] = {
        {&Facts::GameThread, false, "REFUSED_NOT_GAME_THREAD"},
        {&Facts::Admitted, false, "REFUSED_NOT_SUPERVISOR_ADMITTED"},
        {&Facts::MaterialValid, false, "REFUSED_MATERIAL_INVALID"},
        {&Facts::TargetValid, false, "REFUSED_TARGET_UNSUPPORTED"},
        {&Facts::ResourceBefore, false, "PENDING_RESOURCE_ABSENT_BEFORE_WAIT"},
        {&Facts::ResourceAfter, false, "PENDING_RESOURCE_ABSENT_AFTER_WAIT"},
        {&Facts::IdentityStable, false, "REFUSED_IDENTITY_CHANGED"},
        {&Facts::PlatformMatches, false, "REFUSED_PLATFORM_MISMATCH"},
        {&Facts::QualityMatches, false, "REFUSED_QUALITY_MISMATCH"},
        {&Facts::HasErrors, true, "REFUSED_FINAL_COMPILE_ERRORS"},
        {&Facts::Finished, false, "PENDING_COMPILATION_UNFINISHED"},
        {&Facts::MapPresent, false, "PENDING_SHADER_MAP_ABSENT"},
        {&Facts::MapValid, false, "PENDING_SHADER_MAP_NOT_FINALIZED"},
        {&Facts::MapComplete, false, "PENDING_SHADER_MAP_INCOMPLETE"}
    };
    for (const Gate& gate : gates)
    {
        Facts f = ReadyFacts(); f.*(gate.member) = gate.fault;
        Check(std::strcmp(Decide(f), gate.expected) == 0, gate.expected);
    }
    Facts f = ReadyFacts(); f.HasErrors = true; f.Finished = false;
    Check(std::strcmp(Decide(f), "REFUSED_FINAL_COMPILE_ERRORS") == 0, "errors before unfinished");
    f = ReadyFacts(); f.ResourceAfter = false; f.IdentityStable = false;
    Check(std::strcmp(Decide(f), "PENDING_RESOURCE_ABSENT_AFTER_WAIT") == 0, "missing before identity");
    f = ReadyFacts(); f.IdentityStable = false; f.HasErrors = true;
    Check(std::strcmp(Decide(f), "REFUSED_IDENTITY_CHANGED") == 0, "identity before errors");

    unsigned readyCount = 0;
    for (unsigned mask = 0; mask < 16384u; ++mask)
    {
        // Independent truth-table construction; no header parsing or eval.
        f = Facts{};
        f.GameThread = (mask & 1u) != 0;
        f.Admitted = (mask & 2u) != 0;
        f.MaterialValid = (mask & 4u) != 0;
        f.TargetValid = (mask & 8u) != 0;
        f.ResourceBefore = (mask & 16u) != 0;
        f.ResourceAfter = (mask & 32u) != 0;
        f.IdentityStable = (mask & 64u) != 0;
        f.PlatformMatches = (mask & 128u) != 0;
        f.QualityMatches = (mask & 256u) != 0;
        f.HasErrors = (mask & 512u) != 0;
        f.Finished = (mask & 1024u) != 0;
        f.MapPresent = (mask & 2048u) != 0;
        f.MapValid = (mask & 4096u) != 0;
        f.MapComplete = (mask & 8192u) != 0;
        const bool expected = mask == (16383u ^ 512u);
        const bool actual = std::strcmp(Decide(f), ready) == 0;
        Check(actual == expected, "exhaustive readiness iff independent mask oracle");
        if (actual) ++readyCount;
    }
    Check(readyCount == 1u, "one ready assignment");
    Check(QualityMatches(1, 1, 4, false), "exact quality");
    Check(!QualityMatches(1, 4, 4, false), "shared denied");
    Check(QualityMatches(1, 4, 4, true), "shared authorized");
    Check(!QualityMatches(1, 2, 4, true), "other quality denied");
    std::cout << "focused=18 exhaustive=16384 quality=4 readyAssignments="
              << readyCount << " failures=" << Failures << '\n';
    return Failures == 0 ? 0 : 1;
}
