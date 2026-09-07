#include "PreparationJourney.h"
#include <cstdlib>
#include <iostream>
#include <cstring>

using namespace MikdashPreparation;

// Unlike assert(), this remains active in release/NDEBUG test builds.
void Check(bool Condition, const char* Message)
{
    if (!Condition) { std::cerr << Message << '\n'; std::exit(1); }
}

int main()
{
    Journey Lesson;
    Check(Lesson.GetMode() == Mode::Exploration, "startup must not impersonate ritual preparation");
    Check(!Lesson.CompleteModestPreparation(), "out-of-order completion rejected");
    Request Entry;
    Entry.IntendedAction = Action::EnterSacredZone;
    Check(Lesson.Evaluate(Entry).Value == Decision::NeedsReview, "unknown zone must need review");

    const Scenario Known[] = {Scenario::PreparedPilgrim, Scenario::CorpseProcessPending,
        Scenario::AwaitingDayCompletion, Scenario::OfferingPending};
    for (Scenario Example : Known)
    {
        Lesson.Start(Example);
        Check(!Lesson.CompleteModestPreparation(), "cannot bypass recall");
        Check(!Lesson.SubmitAnswer(Answer::AllClear), "universal immersion answer rejected");
        Check(Lesson.GetStage() == Stage::Recall && Lesson.GetCorrectionCount() == 1, "correction is retryable");
        Check(Lesson.SubmitAnswer(Answer::CheckRemainingRequirements), "meaningful recall accepted");
        const Facts Before = Lesson.GetFacts();
        Check(!Lesson.SubmitAnswer(Answer::CheckRemainingRequirements), "double answer cannot advance twice");
        Check(Lesson.CompleteModestPreparation(), "modest lesson completes");
        const Facts After = Lesson.GetFacts();
        Check(After.ModestLessonCompleted, "record learning completion");
        Check(Before.CorpseProcessComplete == After.CorpseProcessComplete
            && Before.PurificationImmersionComplete == After.PurificationImmersionComplete
            && Before.DayComplete == After.DayComplete && Before.OfferingComplete == After.OfferingComplete,
            "a visual lesson must not mutate purification facts");
        Check(!Lesson.CompleteModestPreparation(), "replay completion rejected");
        Check(Lesson.Evaluate(Entry).Value == Decision::NeedsReview, "quiz mastery never grants entry");
        if (Example == Scenario::CorpseProcessPending)
            Check(std::strstr(Lesson.GetPreparationSummary(), "corpse-purification") != nullptr, "corpse requirement stays visible");
        if (Example == Scenario::AwaitingDayCompletion)
            Check(std::strstr(Lesson.GetPreparationSummary(), "day transition") != nullptr, "waiting stage stays visible");
        if (Example == Scenario::OfferingPending)
            Check(std::strstr(Lesson.GetPreparationSummary(), "offering") != nullptr, "offering stays visible");
        Lesson.ReturnToExploration();
        Check(Lesson.GetFacts().OfferingComplete == After.OfferingComplete, "mode switch does not reset purity");
        Check(!Lesson.SubmitAnswer(Answer::AllClear), "exploration cannot advance lesson");
    }

    Lesson.Start(Scenario::UnknownHistory);
    Check(!Lesson.SubmitAnswer(Answer::CheckRemainingRequirements), "unknown history needs review, not guessing");
    Check(Lesson.SubmitAnswer(Answer::SeekReview), "review is correct learning outcome");
    Check(Lesson.GetStage() == Stage::Reflection && !Lesson.GetFacts().ModestLessonCompleted,
        "unknown scenario cannot silently fabricate immersion");
    Check(Lesson.GetFacts().HistoryKnown == Fact::Unknown, "learning answer does not manufacture history");
    Lesson.Start(static_cast<Scenario>(99));
    Check(Lesson.GetScenario() == Scenario::UnknownHistory, "invalid scenario fails to review");

    Check(RequirementSatisfied(Fact::Yes, Fact::No) == Fact::No, "outstanding requirement persists");
    Check(RequirementSatisfied(Fact::No, Fact::Unknown) == Fact::Yes, "not-required differs from incomplete");
    Check(RequirementSatisfied(Fact::Unknown, Fact::Yes) == Fact::Unknown, "unknown requirement cannot pass");

    Facts Priest;
    Priest.HistoryKnown = Fact::Yes;
    Priest.AvatarRole = Role::Kohen;
    Priest.ServiceQualified = Priest.ServiceAssigned = Priest.ServicePreparationComplete = Fact::Yes;
    Priest.ServiceGarmentsReady = Fact::Yes;
    Priest.HandsAndFeetSanctified = Fact::No;
    Request Service;
    Service.IntendedAction = Action::PerformService;
    Service.ZoneMappingReviewed = Service.RoleAndTaskPermitted = Fact::Yes;
    Check(EvaluateFacts(Priest, Service).Value == Decision::Deny, "immersion cannot substitute for hands and feet");
    Priest.HandsAndFeetSanctified = Fact::Unknown;
    Check(EvaluateFacts(Priest, Service).Value == Decision::NeedsReview, "unknown service prerequisite fails closed");
    Priest.HandsAndFeetSanctified = Fact::Yes;
    Check(EvaluateFacts(Priest, Service).Value == Decision::NeedsReview, "generic facts are not a zone rule set");
    Priest.AvatarRole = Role::Pilgrim;
    Check(EvaluateFacts(Priest, Service).Value == Decision::Deny, "visitor cannot gain priest service by toggling flags");
    Service.RoleAndTaskPermitted = Fact::No;
    Check(EvaluateFacts(Priest, Service).Value == Decision::Deny, "task restriction is not bypassed");
    Request ViewLesson;
    Check(EvaluateFacts(Facts{}, ViewLesson).Value == Decision::Allow, "learning remains available without personal data");
    ViewLesson.IntendedAction = static_cast<Action>(99);
    Check(EvaluateFacts(Facts{}, ViewLesson).Value == Decision::NeedsReview, "unknown action never grants permission");
    std::cout << "PreparationJourney: all semantic checks passed\n";
}
