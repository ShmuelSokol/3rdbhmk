"""Actual-source and deterministic patch tests. No C++/UE execution."""
from pathlib import Path
import sys
import unittest
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from prepare_patch import build,once
P=(R/'try_talk_replacement.txt').read_text()
ACTION=(R/'ResidentTalkAction.h').read_text()
ADAPTER=(R/'RemoteResidentInteraction.h').read_text()

class InteractionPatchTests(unittest.TestCase):
    def test_exact_export_reproduced(self):
        for name,data in build().items():self.assertEqual((R/'review-overlay'/name).read_bytes(),data)
    def test_anchors_reject_ambiguity(self):
        for text in ('none','x x'):
            with self.assertRaises(ValueError):once(text,'x','replacement')
    def test_preserves_local_blueprint_void(self):
        h=build()['project/Public/MikdashPlayerController.h'].decode()
        self.assertIn('UFUNCTION(BlueprintCallable, Category="Residents") void TalkToNearbyResident();',h)
        self.assertIn('(void)TryTalkToNearbyResident([](){ return true; });',P)
    def test_remote_no_void_inference(self):
        remote=build()['online/native/receiver04/OnlineController.cpp'].decode()
        self.assertIn('ConsumeResidentInteraction(*this,Remote.ToSharedRef(),Fence)',remote)
        self.assertNotIn('return ConsumeInteract(Fence);',remote)
        self.assertNotIn('.TalkToNearbyResident()',ADAPTER)
    def test_scan_precedes_last_branch(self):
        body=P.split('MikdashDialog::TalkOutcome AMikdashPlayerController::TryTalk')[1]
        self.assertLess(body.index('UpdateResidentDialog()'),body.index('if (!LastBranch())'))
        self.assertLess(ACTION.index('if(!FinalCheck())'),ACTION.index('Conversation.PressTalk(Lines)'))
    def test_callback_context_rechecked_before_press(self):
        tail=P.split('if (!LastBranch()) return false;')[1]
        self.assertLess(tail.index('return SameContext() && SameSelection()'),tail.index('SetConversationHold'))
    def test_callback_context_rechecked_after_effect(self):
        tail=P.split('Resident->SetConversationHold')[1]
        self.assertIn('if (!SameContext() || !SameSelection()) return false;',tail)
        self.assertIn('TalkOutcome::Applied:TalkOutcome::Unknown',ACTION)
    def test_last_fence_not_refreshed_after_effect(self):
        self.assertEqual(ADAPTER.count('Service->Consumers().Revalidate(Fence)'),1)
        tail=ADAPTER.split('// Revalidate identity/pause/possession')[1]
        self.assertNotIn('Consumers().Revalidate(',tail)
        self.assertIn('Current.epoch==Fence.epoch',ADAPTER)
    def test_identity_pause_and_possession(self):
        for s in ('GetPawn()!=Pawn.Get()','Pawn->GetController()!=C','C->PlayerInput!=Input.Get()',
                  'C->IsPaused()','C->IsWalkthroughMenuOpen()','C->IsDoveFlightActive()',
                  'Service->BoundContext()==Fence.context','Service->Abort()'):self.assertIn(s,ADAPTER)
    def test_noop_uses_actual_conversation_result(self):
        self.assertIn('if(!Conversation.PressTalk(Lines)) return TalkOutcome::NoOp;',ACTION)
        self.assertNotIn('LineIndex()',ACTION)
    def test_reentrant_attempt_refused(self):
        self.assertIn('if (bTalkAttemptActive || !LastBranch)',P)
        self.assertLess(P.index('TGuardValue<bool> Attempt'),P.index('UpdateResidentDialog()'))
    def test_real_cpp_test_dependencies(self):
        t=(R/'tests/ResidentTalkActionTests.cpp').read_text()
        self.assertIn('#include "../ResidentTalkAction.h"',t)
        self.assertIn('snapshots/native/receiver04/SemanticMailbox.h',t)
        self.assertEqual(t.count('Case([]'),10)
        self.assertNotIn('class Conversation',t)
        self.assertNotIn('class SemanticMailbox',t)

if __name__=='__main__':unittest.main()
