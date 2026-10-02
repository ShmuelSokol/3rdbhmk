#pragma once
#include "ResidentDialogState.h"

namespace MikdashDialog {
enum class TalkOutcome { Applied, NoOp, Rejected, Unknown };

// Actual production consumption helper; no UE replacements. The caller scans
// before entry. Nothing callback-capable occurs between FinalCheck and PressTalk.
template<class Guard,class Finish>
TalkOutcome PressTalkGuarded(Conversation& Conversation,std::size_t Lines,
                             Guard FinalCheck,Finish AfterConsumption) {
    if(!FinalCheck()) return TalkOutcome::Rejected;
    if(!Conversation.PressTalk(Lines)) return TalkOutcome::NoOp;
    return AfterConsumption()?TalkOutcome::Applied:TalkOutcome::Unknown;
}
}
