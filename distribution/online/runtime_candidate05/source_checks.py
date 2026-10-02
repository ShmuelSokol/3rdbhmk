"""Native source contracts only; not UE execution or pipe-authentication proof."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parent
C=(R/'PrivateBootstrap.cpp').read_text()
H=(R/'PrivateBootstrap.h').read_text()
M=(R/'PrivateBootstrapModule.cpp').read_text()
class Contracts(unittest.TestCase):
    def test_actual_parser_and_host(self):
        self.assertIn('Receiver03::ParseBootstrap(Body,Out)',C)
        self.assertIn('FHost::AdmitStopped(Provisioning->Identity,Provisioning->Deadline)',C)
    def test_no_activation(self):
        for s in ('StartStreaming(', 'SetConnectionURL(', 'Server->Start(', 'Bootstrap::Start(', 'socket(', 'bind(', 'listen('):self.assertNotIn(s,C+H+M)
    def test_pipe_only_entry(self):
        for s in ('GetStdHandle(STD_INPUT_HANDLE)','FILE_TYPE_PIPE','HANDLE_FLAG_INHERIT','PIPE_TYPE_MESSAGE'):self.assertIn(s,C)
    def test_no_raw_record_public_api(self):
        api=H.split('class FPrivateBootstrap')[1].split('private:')[0]
        self.assertNotIn('Body',api);self.assertNotIn('Key',api)
    def test_complete_eof_before_parse(self):
        self.assertIn('Error==ERROR_BROKEN_PIPE&&Expected>4&&Bytes.Num()==Expected',C)
        body=C.split('void FPrivateBootstrap::AcceptClosedRecord()')[1].split('void FPrivateBootstrap::Tick()')[0]
        self.assertLess(body.index('CloseInput()'),body.index('ValidatePrivateRecord'))
        self.assertLess(body.index('ValidatePrivateRecord'),body.index('FHost::AdmitStopped'))
    def test_partial_oversized_trailing_bounded(self):
        for s in ('ReadEnd=N+5','Size<2||Size>4092','if(Available) Shutdown()', 'Want>4096', 'if(!Fresh(ReadEnd))'):self.assertIn(s,C)
    def test_zero_read_not_eof(self):
        self.assertIn('if(!Ok||Read>Want)',C)
        self.assertNotIn('if(!Read)',C)
    def test_close_handle_quarantine(self):
        self.assertIn('Receiver04::CloseBootstrapInput(Input,InputPoisoned',C)
        self.assertIn('if(Phase==State::Quarantined) return false;',C)
    def test_callback_deadline_recheck(self):
        self.assertIn('if(Stopping||!Admitted||!Fresh(ReadEnd)||!Fresh(Provisioning->Deadline))',C)
        self.assertIn('if(Used||Phase!=State::Empty) return false;',C)
    def test_sensitive_buffers_wiped(self):
        for s in ('SecureZeroMemory(Buffer','Memzero(Body.GetData()','Memzero(Bytes.GetData()','Provisioning.Reset()'):self.assertIn(s,C)
    def test_owned_host_shutdown_only(self):
        self.assertIn('const bool HostClosed=!HostStarted||FHost::Shutdown()',C)
        self.assertLess(C.index('Input=H;'),C.index('GetHandleInformation(H'))
    def test_module_actual_delegates(self):
        for s in ('Bootstrap.Startup()','Bootstrap.Tick()','Bootstrap.Shutdown()','OnBeginFrame.AddLambda','OnEnginePreExit.AddLambda'):self.assertIn(s,M)

if __name__=='__main__':unittest.main()
