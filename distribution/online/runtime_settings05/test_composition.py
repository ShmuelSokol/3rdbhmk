import unittest
from runtime_settings05.compose import overlay,PREFIX
class CompositionTests(unittest.TestCase):
    def test_one_reader_stopped_path(self):
        out=overlay();s=out[PREFIX+'runtime_candidate05/PrivateBootstrap.cpp'].decode()
        self.assertEqual(s.count('::GetStdHandle(STD_INPUT_HANDLE)'),1)
        self.assertEqual(s.count('Settings05::AdmitPrivateV2(Body,Last,*Provisioning)'),1)
        self.assertIn('FHost::AdmitStopped',s)
        self.assertNotIn('Server->Start',s)
        self.assertNotIn('StartStreaming(',s)
        self.assertLess(s.index('Settings05::AdmitPrivateV2'),s.index('FHost::AdmitStopped'))
    def test_all_lifetime_exits_check_lease(self):
        s=overlay()[PREFIX+'runtime_candidate05/PrivateBootstrap.cpp'].decode()
        self.assertEqual(s.count('Settings05::LeaseLive()'),3)
        self.assertIn('const bool LeaseClosed=Settings05::RevokeLease();',s)
        self.assertIn('Phase=LeaseClosed&&InputClosed&&HostClosed?',s)
    def test_v1_validator_retained(self):
        from runtime_settings05.compose import ROOT
        old=(ROOT/'runtime_candidate05/PrivateBootstrap.cpp').read_text()
        new=overlay()[PREFIX+'runtime_candidate05/PrivateBootstrap.cpp'].decode()
        def validator(s):return s[s.index('bool ValidatePrivateRecord('):s.index('bool FPrivateBootstrap::Fresh(')]
        self.assertEqual(validator(old),validator(new))
    def test_no_existing_module_replaced(self):
        out=overlay()
        self.assertEqual(len(out),6)
        self.assertTrue(all('/runtime_settings05/' in n or n.endswith('/PrivateBootstrap.cpp') or
            n.endswith('/SettingsV2Api.cpp') for n in out))
if __name__=='__main__':unittest.main()
