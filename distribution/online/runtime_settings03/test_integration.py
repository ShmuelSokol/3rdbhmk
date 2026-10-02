"""Pure source/control-flow tests. No UE, child, socket, Win32 path calls or policy pass."""
import ast
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from session_core import Ownership,SessionError
from adapters.process04.host import LaunchRecipe,OwnedProcesses
from runtime_settings03.launcher_contract03 import launch_inputs,_lex
from runtime_settings03.owned_settings_host import SettingsOwnedProcesses,ExclusiveOwnershipAuthority,_RootRecord,_arguments

OWNER=Ownership('session','process','stream','save','settings',100)
RECIPE=LaunchRecipe('C:/unlaunched.exe','0'*64,'C:/',('-unattended',),'C:/Windows','C:/Temp')

def root_of_length(n):
    parts=[];left=n-3
    while left>75:
        take=74 if left==76 else 75
        parts.append('a'*take);left-=take+1
    parts.append('b'*left)
    result='C:/'+ '/'.join(parts)
    assert len(result)==n
    return result

class RefusingAuthority(ExclusiveOwnershipAuthority):
    def reserve(self,owner):raise SessionError('No established exclusive premise')

class ClosingObservation:
    """Cleanup-order test double only; never used to admit or launch anything."""
    def __init__(self,events,fail=False):self.events=events;self.fail=fail
    def close_after_process_cleanup(self):
        self.events.append('directories')
        if self.fail:raise SessionError('close pending')

class Integration(unittest.TestCase):
    def host(self,authority=None):
        return SettingsOwnedProcesses(RECIPE,(19001,),lambda o:None,
            ownership_authority=authority,clock=lambda:1,qpc=lambda:1)
    def test_absent_or_boolean_policy_cannot_launch(self):
        for authority in [None,True,False,{'exclusive':True}]:
            with self.subTest(authority=authority),patch('runtime_settings03.owned_settings_host._probe') as probe,\
                 patch('runtime_settings03.owned_settings_host.WindowsChild.create') as create:
                p=self.host(authority)
                with self.assertRaises(SessionError):p.start(OWNER)
                probe.assert_not_called();create.assert_not_called()
                self.assertFalse(p.settings_records)
    def test_refusing_authority_has_no_os_acquisition(self):
        p=self.host(RefusingAuthority());p.verified=True # bypass ONLY executable test setup, no affirmative premise
        with patch('runtime_settings03.owned_settings_host._probe') as probe,\
             patch('runtime_settings03.owned_settings_host.WindowsChild.create') as create:
            with self.assertRaises(SessionError):p.start(OWNER)
            probe.assert_not_called();create.assert_not_called()
            self.assertFalse(p.settings_records)
    def test_unprepared_refuses_before_reserve(self):
        a=RefusingAuthority();p=self.host(a)
        with patch.object(a,'reserve') as reserve:
            with self.assertRaises(SessionError):p.start(OWNER)
            reserve.assert_not_called()
    def test_job_cleanup_failure_retains_directory_lease(self):
        events=[];p=self.host();r=_RootRecord(OWNER);r.held=ClosingObservation(events)
        p.settings_records[OWNER.process_key]=r
        with patch.object(OwnedProcesses,'stop',side_effect=SessionError('Job active')):
            with self.assertRaises(SessionError):p.stop(OWNER)
        self.assertEqual(events,[]);self.assertIs(p.settings_records[OWNER.process_key],r)
    def test_partial_creation_without_disposal_cannot_release(self):
        events=[];p=self.host();r=_RootRecord(OWNER);r.creation_attempted=True
        r.held=ClosingObservation(events);p.settings_records[OWNER.process_key]=r
        with patch.object(OwnedProcesses,'stop',return_value=None):
            with self.assertRaises(SessionError):p.stop(OWNER)
        self.assertEqual(events,[]);self.assertIn(OWNER.process_key,p.settings_records)
    def test_cleanup_order_and_close_failure_quarantine(self):
        for fail in [False,True]:
            events=[];p=self.host();r=_RootRecord(OWNER)
            r.creation_attempted=r.process_disposed=True;r.held=ClosingObservation(events,fail)
            p.settings_records[OWNER.process_key]=r
            with patch.object(OwnedProcesses,'stop',side_effect=lambda o:events.append('job-root-writer-revoke')):
                if fail:
                    with self.assertRaises(SessionError):p.stop(OWNER)
                else:p.stop(OWNER)
            self.assertEqual(events,['job-root-writer-revoke','directories'])
            self.assertEqual(OWNER.process_key in p.settings_records,fail)
    def test_cleanup_reentry_refused(self):
        p=self.host();r=_RootRecord(OWNER);r.cleaning=True;p.settings_records[OWNER.process_key]=r
        with patch.object(OwnedProcesses,'stop') as stop:
            with self.assertRaises(SessionError):p.stop(OWNER)
            stop.assert_not_called()
    def test_p2_historical_230_root(self):
        root=root_of_length(230);old=_lex().launch_inputs(root,'settings','save')
        self.assertEqual(len(old['game_ini']),265)
        self.assertEqual(len(old['game_user_settings_ini']),277)
        with self.assertRaises(ValueError):launch_inputs(root,'settings','save',8)
    def test_long_save_filename_not_only_ini(self):
        root=root_of_length(170)
        old=_lex().launch_inputs(root,'s'*64,'p'*64)
        self.assertLessEqual(len(old['game_user_settings_ini']),240)
        with self.assertRaises(ValueError):launch_inputs(root,'s'*64,'p'*64,64)
    def test_exact_derived_boundary_and_all_actual_slots(self):
        accepted=[]
        for n in range(20,231):
            try:c=launch_inputs(root_of_length(n),'s'*64,'p'*64,64)
            except ValueError:continue
            self.assertEqual(len(c['save_files']),66)
            paths=c['precreate_directories']+c['save_files']+[c['game_ini'],c['game_user_settings_ini']]
            self.assertTrue(all(len(p)<=240 for p in paths));accepted.append((n,c))
        n,c=accepted[-1]
        self.assertEqual(len(c['longest_save_file']),240)
        with self.assertRaises(ValueError):launch_inputs(root_of_length(n+1),'s'*64,'p'*64,64)
        self.assertTrue(c['tokens'][-1].endswith('SlotCount=64'))
    def test_slot_count_and_whitespace_refusal(self):
        for count in [0,65,True,None]:
            with self.assertRaises(ValueError):launch_inputs('C:/Owned/s01','settings','save',count)
        with self.assertRaises(ValueError):launch_inputs('C:/Owned Space/s01','settings','save',8)
    def test_p1_source_delta_is_noncreating_readback(self):
        old=(ROOT/'runtime_settings01/SessionSettingsAdmission.cpp').read_text()
        new=(ROOT/'runtime_settings03/review-overlay/SessionSettingsAdmission.cpp').read_text()
        expected=old.replace('GEngine?GEngine->GetGameUserSettings():nullptr','GEngine?GEngine->GameUserSettings.Get():nullptr')
        expected=expected.replace('if(!Graphics || Graphics->GetClass()', 'if(!IsValid(Graphics) || Graphics->GetClass()')
        self.assertEqual(new,expected)
        self.assertNotIn('GetGameUserSettings()',new)
        self.assertIn('if(!IsValid(Graphics) || Graphics->GetClass()!=UGameUserSettings::StaticClass()',new)
    def test_arguments_reject_hidden_override_before_generation(self):
        # No held OS object needed: rejection must precede dereferencing it.
        for arg in ['-UserDir=C:/other','-GameIni=C:/other','-foo=ok -userdir=bad',
                    '-ExecCmds=anything','-ini:Game:[x]:y=z','-saveddirsuffix=other']:
            with self.assertRaises(SessionError):_arguments((arg,),None,OWNER,8)
    def test_constructor_factory_cannot_bypass_owned_child(self):
        with self.assertRaises(SessionError):SettingsOwnedProcesses(RECIPE,(19001,),lambda o:None,child_factory=lambda:None)

if __name__=='__main__':unittest.main(verbosity=2)
