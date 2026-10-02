"""Actual installed-source insertion regressions; NOT UE execution or compilation.

Run with --plugin <installed PixelStreaming2 directory>. No engine output written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plugin_recipe as recipe

PLUGIN = None

def body(text, signature):
    start = text.index('{', text.index(signature))
    level = 1
    end = start + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start + 1:end - 1]

class PluginRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = recipe.build(PLUGIN)
        cls.h = cls.out[recipe.PREFIX+'Private/EpicRtcStreamer.h'].decode()
        cls.cpp = cls.out[recipe.PREFIX+'Private/EpicRtcStreamer.cpp'].decode()
        cls.own = cls.out[recipe.PREFIX+'Private/MikdashOwnedRtc.cpp'].decode()

    def test_installed_inputs_still_exact(self):
        for path, sha in json.loads((recipe.ROOT/'plugin-pins.json').read_text()).items():
            self.assertEqual(hashlib.sha256((PLUGIN/path).read_bytes()).hexdigest(), sha)

    def test_factory_stock_body_preserved_except_passive_origin_tracking(self):
        # Compare the real generated function to the pinned stock function after
        # removing ONLY our known tracking statements/type refinement. Any new
        # early return, ID policy, start/stop or other factory behavior fails.
        signature = 'FRTCStreamerFactory::CreateNewStreamer('
        stock = (PLUGIN/(recipe.PREFIX+'Private/EpicRtcStreamer.cpp')).read_text(encoding='utf-8-sig')
        actual = body(self.cpp, signature)
        actual = actual.replace('Created.RemoveAll([](const TWeakPtr<FEpicRtcStreamer>& Weak){return !Weak.IsValid();});', '')
        actual = actual.replace('Created.Add(NewStreamer);', '')
        actual = actual.replace('TSharedPtr<FEpicRtcStreamer> NewStreamer', 'TSharedPtr<IPixelStreaming2Streamer> NewStreamer')
        self.assertEqual(''.join(actual.split()), ''.join(body(stock, signature).split()))

    def test_recreation_tracks_exact_live_instances_not_id_slots(self):
        self.assertIn('TArray<TWeakPtr<FEpicRtcStreamer>> Created;', self.h)
        find = body(self.h, 'FindCreated(')
        self.assertIn('Exact.Get()==S.Get()', find)
        self.assertNotIn('GetId', find)
        self.assertNotIn('Created.Find', find)
        self.assertNotIn('Created.Contains', self.cpp)
        self.assertNotIn('Created.Num', self.cpp)

    def test_null_scope_short_circuits_before_dereference(self):
        predicate = ''.join(body(self.h, 'MikdashMatchesScope(').split())
        self.assertEqual(predicate, 'returnScope&&OwnedConference.IsValid()&&OwnedConference.Get()==Scope&&EpicRtcConference==OwnedConference->GetConference();')

    def test_scope_live_caller_checks_installed_exact_identity(self):
        self.assertIn('(Installed&&!S->MikdashMatchesScope(this))', body(self.own, 'FMikdashOwnedConference::Live('))

    def test_cap_is_exclusively_owned_admission(self):
        attach = body(self.own, 'bool MikdashAttachOwnedRtc(')
        self.assertLess(attach.index('!Exact.IsValid()'), attach.index('OwnedAdoptionAttempts>=64'))
        self.assertLess(attach.index('OwnedAdoptionAttempts>=64'), attach.index('++OwnedAdoptionAttempts'))
        self.assertNotIn('OwnedAdoptionAttempts', self.cpp)
        self.assertNotIn('OwnedAdoptionAttempts', self.h)

    def test_teardown_snapshots_only_owned_before_callbacks(self):
        revoke = body(self.h, 'void RevokeOwned(')
        self.assertLess(revoke.index('OwnedClosing=true'), revoke.index('for(const auto& Weak:Created)'))
        self.assertIn('S.IsValid()&&S->MikdashIsOwned()', revoke)
        self.assertIn('for(const auto& S:Owned)S->MikdashRevoke();', revoke)
        self.assertEqual(revoke.count('MikdashRevoke()'), 1)
        self.assertIn('if(OwnedClosing||!S.IsValid())return {};', body(self.h, 'FindCreated('))

    def test_owned_paths_do_not_broadcast_to_foreign_streamers(self):
        for prohibited in ('ForEachStreamer', 'GetSharedTickableTasks', 'StopAll', 'StartAll'):
            self.assertNotIn(prohibited, self.own)
        self.assertIn('Installed&&S.IsValid()&&S->MikdashMatchesScope(this))S->StopStreaming();', self.own)
        module = self.out[recipe.PREFIX+'Private/PixelStreaming2RTCModule.cpp'].decode()
        shutdown = body(module, 'FPixelStreaming2RTCModule::ShutdownModule(')
        self.assertLess(shutdown.index('StreamerFactory->RevokeOwned()'), shutdown.index('StreamerFactory.Reset()'))
        create=body(module,'bool FPixelStreaming2RTCModule::MikdashCreateConference(')
        self.assertLess(create.index('GetConference('),create.index('CreateConference('))
        self.assertIn('if(Result!=EpicRtcErrorCode::Ok){Out=nullptr;return false;}',create)
        self.assertIn('Current.GetReference()==Conference.GetReference())Platform->ReleaseConference',self.own)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plugin', type=Path, required=True)
    args = parser.parse_args()
    PLUGIN = args.plugin
    unittest.main(argv=[sys.argv[0]], verbosity=2)
