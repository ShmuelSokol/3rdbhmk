"""Source contract checks ONLY. These do not compile or execute native code."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).parent
ENGINE=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/Media/PixelStreaming2/Source')


class NativeSourceContract(unittest.TestCase):
    def test_every_installed_input_entry_overridden(self):
        api=(ENGINE/'PixelStreaming2Input/Public/IPixelStreaming2InputHandler.h').read_text()
        gate=(ROOT/'OnlineInputGate.h').read_text()
        names=re.findall(r'virtual\s+[^;\n]+?\b(\w+)\s*\([^;\n]*?=\s*0;',api)
        self.assertEqual(len(names),43)
        for name in names:
            self.assertRegex(gate,r'\b'+name+r'\([^\n]*override')

    def test_gate_unconditionally_discards_every_datachannel_id_and_console(self):
        gate=(ROOT/'OnlineInputGate.h').read_text()
        self.assertRegex(gate,r'void OnMessage\([^\n]*override\s*\{\s*\}')
        self.assertRegex(gate,r'bool Exec\([^\n]*\{ return false; \}')
        for name in ['RegisterMessageHandler','SetCommandHandler','SetElevatedCheck']:
            self.assertRegex(gate,name+r'\([^\n]*override\s*\{\s*\}')
        self.assertNotIn('->OnMessage',gate)
        self.assertNotIn('->Tick',gate)
        self.assertIn('!Original.IsValid()',gate)
        self.assertIn('!To.IsValid() || !From.IsValid()',gate)
        self.assertIn('Streamer->IsStreaming()',gate)

    def test_keyframe_initial_settings_and_latency_handled_before_input_gate(self):
        source=(ENGINE/'PixelStreaming2RTC/Private/EpicRtcStreamer.cpp').read_text()
        method=source.split('void FEpicRtcStreamer::OnDataTrackMessage(')[1].split('void FEpicRtcStreamer::OnDataTrackError(')[0]
        gate=method.index('InputHandler->OnMessage')
        for case in ['IFrameRequest','RequestInitialSettings','LatencyTest','TestEcho']:
            self.assertLess(method.index('EPixelStreaming2ToStreamerMessage::'+case),gate)
        rtc=(ENGINE/'PixelStreaming2RTC/Private/RTCInputHandler.cpp').read_text()
        self.assertIn('RequestQualityControl has been removed',rtc)

    def test_native_ack_follows_sink_and_deadline_check(self):
        bridge=(ROOT/'SessionBridge.h').read_text()
        self.assertLess(bridge.index('fresh<deadline'),bridge.index('applied=sink.Apply'))
        self.assertLess(bridge.index('applied=sink.Apply'),bridge.index('a.status="applied"'))
        self.assertIn('p.owner==owner',bridge)
        self.assertIn('p.connection_id==connection',bridge)
        self.assertIn('p.sequence<=sequence',bridge)
        self.assertIn('inputUntil=fresh+2',bridge)
        self.assertNotIn('ConsoleCommand',(ROOT/'ControllerSink.h').read_text())

    def test_controller_requires_owned_playerinput_and_observed_delivery(self):
        sink=(ROOT/'ControllerSink.h').read_text()
        self.assertIn('OwnedInput.IsValid()',sink)
        self.assertIn('Controller->PlayerInput==OwnedInput.Get()',sink)
        self.assertIn('if(!Available())return Delivery::Rejected',sink)
        self.assertIn('After->SampleCountAccumulator!=Samples+1',sink)
        key=sink.split('bool Key(int Index,bool Down)')[1].split('public:')[0]
        self.assertLess(key.index('Delivery::Rejected)return false'),key.index('Held[Index]=Down'))
        self.assertIn('if(!bReleased)return false',sink)
        self.assertIn('*State=FKeyState()',sink)
        engine=ENGINE.parents[3]/'Source/Runtime/Engine/Private/UserInterface/PlayerInput.cpp'
        # Installed UPlayerInput records a pressed key before returning whether an
        # action binding handled it; false must not reject successful polling input.
        source=engine.read_text()
        start=source.index('bool UPlayerInput::InputKey(const FInputKeyEventArgs& Params)')
        method=source[start:source.index('bool UPlayerInput::InputTouch(',start)]
        self.assertLess(method.index('KeyState.SampleCountAccumulator++'),method.index('return IsKeyHandledByAction'))
        self.assertIn('Exchange(KeyState->EventCounts[EventIndex], KeyState->EventAccumulator[EventIndex])',source)
        self.assertIn('return (KeyState->EventCounts[IE_Pressed].Num() > 0)',source)
        self.assertNotIn('return Release()',sink.split('if(Action=="move")')[1].split('else if(Action=="look")')[0])

if __name__=='__main__':unittest.main()
