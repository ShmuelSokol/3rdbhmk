#pragma once

// Engine-independent educational state. No method certifies real-world entry,
// personal purity, or the unresolved sacred boundaries of the Yechezkel model.
namespace MikdashPreparation
{
enum class Mode { Exploration, Learning };
enum class Stage { Inactive, Recall, ModestPreparation, Reflection };
enum class Scenario { PreparedPilgrim, CorpseProcessPending, AwaitingDayCompletion, OfferingPending, UnknownHistory };
enum class Answer { AllClear, CheckRemainingRequirements, SeekReview };
enum class Decision { Allow, Deny, NeedsReview };
enum class Fact { Unknown, No, Yes };
enum class Role { Unknown, Pilgrim, Kohen, KohenGadol };
enum class Action { PreparationLesson, EnterSacredZone, PerformService };

struct Facts
{
    Role AvatarRole = Role::Unknown;
    Fact HistoryKnown = Fact::Unknown;
    Fact CorpseProcessRequired = Fact::Unknown;
    Fact CorpseProcessComplete = Fact::Unknown;
    Fact PurificationImmersionRequired = Fact::Unknown;
    Fact PurificationImmersionComplete = Fact::Unknown;
    Fact DayCompletionRequired = Fact::Unknown;
    Fact DayComplete = Fact::Unknown;
    Fact OfferingRequired = Fact::Unknown;
    Fact OfferingComplete = Fact::Unknown;
    Fact ServiceQualified = Fact::Unknown;
    Fact ServiceAssigned = Fact::Unknown;
    Fact ServicePreparationComplete = Fact::Unknown;
    Fact HandsAndFeetSanctified = Fact::Unknown;
    Fact ServiceGarmentsReady = Fact::Unknown;
    // This educational action is deliberately not PurificationImmersionComplete.
    bool ModestLessonCompleted = false;
};

struct Request
{
    Action IntendedAction = Action::PreparationLesson;
    // These facts must come from reviewed authored content, never a quiz score.
    Fact ZoneMappingReviewed = Fact::Unknown;
    Fact RoleAndTaskPermitted = Fact::Unknown;
};

struct DecisionResult
{
    Decision Value;
    const char* Explanation;
    const char* Source;
};

struct Card
{
    const char* Title;
    const char* FictionalHistory;
    const char* Question;
    const char* Hint;
    const char* Source;
    Answer CorrectAnswer;
};

inline const char* AnswerLabel(Answer Choice)
{
    switch (Choice)
    {
    case Answer::AllClear: return "The immersion scene alone permits entry everywhere.";
    case Answer::CheckRemainingRequirements: return "Check the remaining requirements, role, task and zone.";
    case Answer::SeekReview: return "The information is incomplete; ask for review.";
    }
    return "Unknown answer";
}

inline Card GetScenarioCard(Scenario Selected)
{
    switch (Selected)
    {
    case Scenario::PreparedPilgrim:
        return {"A prepared fictional pilgrim",
            "This story supplies a completed purification history. You are a visitor, not an assigned kohen.",
            "Does completing the preparation scene permit every sacred activity?",
            "Preparation, role, purpose and sacred zone are separate questions.",
            "Kelim 1:8-9 | https://www.sefaria.org/Mishnah_Kelim.1.8-9", Answer::CheckRemainingRequirements};
    case Scenario::CorpseProcessPending:
        return {"An unfinished purification process",
            "This fictional avatar still has an unfinished corpse-purification process.",
            "Will a single immersion scene complete every requirement?",
            "Bamidbar describes several stages; immersion does not erase outstanding stages.",
            "Bamidbar 19:11-19 | https://www.sefaria.org/Numbers.19.11-19", Answer::CheckRemainingRequirements};
    case Scenario::AwaitingDayCompletion:
        return {"Immersed, with a stage still pending",
            "In this authored example, the required immersion is complete but the required day transition is not.",
            "Can another immersion replace the pending day transition?",
            "Immersion and completion of the day are distinct facts.",
            "Biat HaMikdash 3:6,14 | https://www.chabad.org/library/article_cdo/aid/1008244/jewish/Biat-Hamikdash-Chapter-3.htm",
            Answer::CheckRemainingRequirements};
    case Scenario::OfferingPending:
        return {"A required offering remains",
            "This fictional mechusar-kippurim example has completed immersion and the day transition; its required offering remains.",
            "Does the completed day transition erase the outstanding offering?",
            "An outstanding required offering is not completed by waiting or another immersion scene.",
            "Biat HaMikdash 3:6-7 | https://www.chabad.org/library/article_cdo/aid/1008244/jewish/Biat-Hamikdash-Chapter-3.htm",
            Answer::CheckRemainingRequirements};
    case Scenario::UnknownHistory:
        break;
    }
    return {"An incomplete fictional history",
        "The story has not supplied enough information about this avatar. No personal information is requested.",
        "What should happen when a required fact is unknown?",
        "Missing information is not permission. Choose review rather than guessing.",
        "Design safeguard; source distinctions: Kelim 1:8-9 | https://www.sefaria.org/Mishnah_Kelim.1.8-9",
        Answer::SeekReview};
}

inline Fact RequirementSatisfied(Fact Required, Fact Complete)
{
    if (Required == Fact::No) return Fact::Yes;
    if (Required != Fact::Yes) return Fact::Unknown;
    return Complete;
}

inline const char* DescribePreparation(const Facts& State)
{
    if (State.HistoryKnown != Fact::Yes)
        return "Fictional history incomplete: seek review. No personal information is needed.";
    if (RequirementSatisfied(State.CorpseProcessRequired, State.CorpseProcessComplete) == Fact::No)
        return "The authored corpse-purification process is unfinished. An immersion scene cannot complete it.";
    if (RequirementSatisfied(State.PurificationImmersionRequired, State.PurificationImmersionComplete) == Fact::No)
        return "A required purification immersion remains unfinished in the authored history.";
    if (RequirementSatisfied(State.DayCompletionRequired, State.DayComplete) == Fact::No)
        return "The authored required day transition remains pending.";
    if (RequirementSatisfied(State.OfferingRequired, State.OfferingComplete) == Fact::No)
        return "The authored required offering remains pending.";
    const Fact Requirements[] = {
        RequirementSatisfied(State.CorpseProcessRequired, State.CorpseProcessComplete),
        RequirementSatisfied(State.PurificationImmersionRequired, State.PurificationImmersionComplete),
        RequirementSatisfied(State.DayCompletionRequired, State.DayComplete),
        RequirementSatisfied(State.OfferingRequired, State.OfferingComplete) };
    for (Fact Item : Requirements)
        if (Item != Fact::Yes) return "A preparation requirement is unknown: seek review.";
    return "The story supplies completed preparation. Role, task and reviewed sacred-zone rules still matter.";
}

// This is a conservative learning prerequisite check, NOT a zone-by-zone
// halachic permission table. Some earlier-Temple outer zones admit statuses
// excluded from deeper ones. Their Yechezkel mapping is not supplied here.
inline DecisionResult EvaluateFacts(const Facts& State, const Request& Query)
{
    const char* Source = "Kelim 1:8-9; Biat HaMikdash 3:3-7; research/halacha-and-service.md";
    if (Query.IntendedAction == Action::PreparationLesson)
        return {Decision::Allow, "The fictional learning lesson may be viewed; this grants no sacred entry.", Source};
    if (Query.IntendedAction != Action::EnterSacredZone && Query.IntendedAction != Action::PerformService)
        return {Decision::NeedsReview, "The requested action is not modeled.", Source};
    // No supplied zone-specific rule set: fail closed even if a caller sets
    // ZoneMappingReviewed=Yes. This prevents turning a generic purity checklist
    // into an invented sacred-zone authorization table.
    if (Query.ZoneMappingReviewed != Fact::Yes)
        return {Decision::NeedsReview, "The sacred-zone mapping needs review; this lesson does not authorize entry.", Source};
    if (Query.RoleAndTaskPermitted == Fact::No)
        return {Decision::Deny, "The authored role and task do not permit this action.", Source};
    if (Query.RoleAndTaskPermitted != Fact::Yes || State.HistoryKnown != Fact::Yes || State.AvatarRole == Role::Unknown)
        return {Decision::NeedsReview, "Required role, task or fictional-history information is incomplete.", Source};
    if (Query.IntendedAction == Action::PerformService)
    {
        if (State.AvatarRole == Role::Pilgrim || State.ServiceQualified == Fact::No || State.ServiceAssigned == Fact::No)
            return {Decision::Deny, "This avatar is not qualified and assigned for this service.", Source};
        const Fact ServiceFacts[] = { State.ServiceQualified, State.ServiceAssigned,
            State.ServicePreparationComplete, State.HandsAndFeetSanctified, State.ServiceGarmentsReady };
        for (Fact Item : ServiceFacts)
        {
            if (Item == Fact::No) return {Decision::Deny, "A modeled service prerequisite remains incomplete.", Source};
            if (Item != Fact::Yes) return {Decision::NeedsReview, "A service prerequisite is unknown.", Source};
        }
    }
    return {Decision::NeedsReview, "A reviewed zone-specific rule set is still required; generic preparation never grants entry.", Source};
}

class Journey
{
public:
    void Start(Scenario Selected)
    {
        CurrentScenario = Selected;
        CurrentMode = Mode::Learning;
        CurrentStage = Stage::Recall;
        Avatar = Facts{};
        Feedback = "This lesson concerns an authored fictional avatar, not your personal status.";
        CorrectionCount = 0;
        if (Selected == Scenario::UnknownHistory) return;
        if (Selected != Scenario::PreparedPilgrim && Selected != Scenario::CorpseProcessPending
            && Selected != Scenario::AwaitingDayCompletion && Selected != Scenario::OfferingPending)
        {
            CurrentScenario = Scenario::UnknownHistory;
            return;
        }
        Avatar.AvatarRole = Role::Pilgrim;
        Avatar.HistoryKnown = Fact::Yes;
        Avatar.CorpseProcessRequired = Fact::No;
        Avatar.PurificationImmersionRequired = Fact::Yes;
        Avatar.PurificationImmersionComplete = Fact::Yes;
        Avatar.DayCompletionRequired = Fact::Yes;
        Avatar.DayComplete = Fact::Yes;
        Avatar.OfferingRequired = Fact::No;
        Avatar.ServiceQualified = Fact::No;
        Avatar.ServiceAssigned = Fact::No;
        if (Selected == Scenario::CorpseProcessPending)
        {
            Avatar.CorpseProcessRequired = Fact::Yes;
            Avatar.CorpseProcessComplete = Fact::No;
            Avatar.PurificationImmersionComplete = Fact::No;
            Avatar.DayComplete = Fact::No;
        }
        else if (Selected == Scenario::AwaitingDayCompletion) Avatar.DayComplete = Fact::No;
        else if (Selected == Scenario::OfferingPending)
        {
            Avatar.OfferingRequired = Fact::Yes;
            Avatar.OfferingComplete = Fact::No;
        }
    }

    bool SubmitAnswer(Answer Selected)
    {
        if (CurrentMode != Mode::Learning || CurrentStage != Stage::Recall) return false;
        if (Selected != GetCard().CorrectAnswer)
        {
            ++CorrectionCount;
            Feedback = GetCard().Hint;
            return false;
        }
        if (CurrentScenario == Scenario::UnknownHistory)
        {
            CurrentStage = Stage::Reflection;
            Feedback = "Correct: seek review. No purification status has been invented or changed.";
        }
        else
        {
            CurrentStage = Stage::ModestPreparation;
            Feedback = "Continue with an offscreen preparation lesson. No body or changing scene is shown.";
        }
        return true;
    }

    // UI can show an opaque door or neutral fade, or let the user skip it.
    // Completion marks learning only; it cannot change purification facts.
    bool CompleteModestPreparation()
    {
        if (CurrentMode != Mode::Learning || CurrentStage != Stage::ModestPreparation) return false;
        Avatar.ModestLessonCompleted = true;
        CurrentStage = Stage::Reflection;
        Feedback = "Lesson completed. Review the remaining requirements; this does not grant sacred-zone access.";
        return true;
    }

    void ReturnToExploration()
    {
        CurrentMode = Mode::Exploration;
        CurrentStage = Stage::Inactive;
        Feedback = "Exploration is an educational viewing mode, not a statement of ritual permission.";
    }

    Mode GetMode() const { return CurrentMode; }
    Stage GetStage() const { return CurrentStage; }
    Scenario GetScenario() const { return CurrentScenario; }
    const Facts& GetFacts() const { return Avatar; }
    Card GetCard() const { return GetScenarioCard(CurrentScenario); }
    const char* GetFeedback() const { return Feedback; }
    const char* GetPreparationSummary() const { return DescribePreparation(Avatar); }
    unsigned GetCorrectionCount() const { return CorrectionCount; }
    DecisionResult Evaluate(const Request& Query) const { return EvaluateFacts(Avatar, Query); }

private:
    Mode CurrentMode = Mode::Exploration;
    Stage CurrentStage = Stage::Inactive;
    Scenario CurrentScenario = Scenario::UnknownHistory;
    Facts Avatar;
    unsigned CorrectionCount = 0;
    const char* Feedback = "Choose an authored fictional learning scenario or explore.";
};
}
