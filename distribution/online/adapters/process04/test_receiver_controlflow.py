"""Checks actual C++ branch/order wiring, alongside staged native seam tests.

These inspect production source, not a parallel lifecycle model. They do not
claim C++ compilation/execution; LifecycleRegressionTests.cpp exercises the real
helpers/Authority when the coordinator later runs native automation.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]/'native/receiver04'


def source(name):
    text=(ROOT/name).read_text()
    return re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)


def body(name, signature):
    text=source(name); start=text.index('{',text.index(signature)); depth=1; end=start+1
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    return text[start+1:end-1]


class ReceiverControlFlowTests(unittest.TestCase):
    def test_native_read_classifier_has_exact_ue_branch_order(self):
        code=body('StreamRead.h','StreamRead ReadStream(')
        false=code.index('if(!Peer.Recv(Buffer,Want,Read))return StreamRead::Closed;')
        wait=code.index('if(Read==0)return StreamRead::Wait;')
        self.assertLess(false,wait)
        self.assertNotIn('GetLastError',code)

    def test_idle_maintenance_precedes_every_receiver_early_return(self):
        code=body('Receiver.cpp','void Receiver::Tick()')
        self.assertLess(code.index('Service.Maintain();'),code.index('return;'))
        self.assertLess(code.index('Service.IsClosed()'),code.index('if(!Peer)return;'))
        self.assertRegex(code,r'if\(Stopping\|\|Now<0\|\|Service.IsClosed\(\)\)\{Shutdown\(\);return;\}')

    def test_maintenance_aborts_without_a_pending_reply(self):
        code=body('Authority.cpp','void Authority::Maintain()')
        self.assertIn('const double N=Now();',code)
        self.assertIn('if(Closed||N<0||N>=Deadline||(Awaiting&&N>=ReplyUntil))Abort();',code)
        self.assertNotIn('if(!Awaiting)',code)

    def test_failed_pipe_close_retains_identity_and_cannot_retry(self):
        code=body('BootstrapGuards.h','bool CloseBootstrapInput(')
        guard=code.index('if(Poisoned)return false;')
        close=code.index('if(!CloseHandle(Input)){Poisoned=true;return false;}')
        clear=code.index('Input=nullptr;return true;')
        self.assertLess(guard,close); self.assertLess(close,clear)
        caller=body('Bootstrap.cpp','bool Bootstrap::CloseInput()')
        self.assertIn('CloseBootstrapInput(Input,InputPoisoned,',caller)
        self.assertIn('if(!Closed)Stopping=true;',caller)
        self.assertNotIn('Input=nullptr',caller)

    def test_shutdown_pipe_failure_does_not_skip_independent_cleanup(self):
        code=body('Bootstrap.cpp','bool Bootstrap::Shutdown()')
        fail=code.index('if(!InputClosed||!ServerClosed||!StreamClosed)return false;')
        for step in ('CloseInput();','Service->Abort();','Streamer->StopStreaming();','Server->Shutdown();'):
            self.assertLess(code.index(step),fail)
        self.assertLess(fail,code.index('return true;'))

    def test_complete_bootstrap_frame_cannot_ignore_close_failure(self):
        code=body('Bootstrap.cpp','void Bootstrap::Poll()')
        close=code.index('if(!CloseInput()){Shutdown();return;}')
        self.assertLess(close,code.index('SettingsProof(Config.Identity)'))

    def test_after_settings_guard_precedes_all_configure_and_pawn_access(self):
        code=body('Bootstrap.cpp','void Bootstrap::Poll()')
        after=code[code.index('if(!SettingsProof(Config.Identity)){Shutdown();return;}'):]
        gate=after.index('if(!BootstrapTargetsValid(')
        failure=after.index('{Shutdown();return;}',gate)
        for unsafe in ('Controller->ConfigureRemote','Controller->GetPawn()'):
            self.assertLess(failure,after.index(unsafe))

    def test_target_weak_validity_precedes_pointer_dereference(self):
        code=body('BootstrapGuards.h','bool BootstrapTargetsValid(')
        early=code.index('if(!Controller.IsValid()||!Pawn.IsValid()||!Input.IsValid()||!Streamer.IsValid())return false;')
        self.assertLess(early,code.index('Controller->GetPawn()'))
        for check in ('Controller->GetPawn()!=Pawn.Get()', 'Pawn->GetController()!=Controller.Get()',
                      'Controller->PlayerInput!=Input.Get()', '!Controller->GetWorld()',
                      '!Controller->IsLocalController()', 'Streamer->IsStreaming()'):
            self.assertIn(check,code)
        self.assertIn('Fresh>=0&&Fresh<Deadline',code)


if __name__=='__main__':unittest.main()
