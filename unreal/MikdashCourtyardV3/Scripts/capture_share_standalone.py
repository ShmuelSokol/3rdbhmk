"""Render the saved preview through standalone Unreal; preserve maps and source saves."""
import json, subprocess, time, struct
from pathlib import Path
from render_share_video import ROOT, MAP, maps, saves, sha

def run():
    output=ROOT.parent/'ShareVideo-20260909-V4'
    if output.exists(): raise RuntimeError('Fresh output required')
    inventory=subprocess.run(['powershell','-NoProfile','-Command',
        'Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'],capture_output=True,text=True)
    if inventory.stdout.strip(): raise RuntimeError('Unreal already running')
    sequence=ROOT/'Content/MikdashV3/ShareVideo_20260909_V2/SEQ_ShareCurrent.uasset'
    if not sequence.is_file(): raise RuntimeError('Saved sequence absent')
    output.mkdir(); frames=output/'Frames'; frames.mkdir()
    report={'status':'starting','mapsBefore':maps(),'savesBefore':saves(),'sequenceSha256':sha(sequence),'errors':[]}
    receipt=output/'standalone-receipt.json'
    def write(): receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    command=[r'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe',
        str(ROOT/'MikdashCourtyardV3.uproject'),MAP+'?game=/Script/Engine.GameModeBase','-game',
        '-MovieSceneCaptureType=/Script/MovieSceneTools.AutomatedLevelSequenceCapture',
        '-LevelSequence=/Game/MikdashV3/ShareVideo_20260909_V2/SEQ_ShareCurrent.SEQ_ShareCurrent',
        '-MovieFolder='+str(frames),'-MovieName=frame_{frame}','-MovieFormat=PNG',
        '-MovieFrameRate=24','-MovieStartFrame=0','-MovieEndFrame=960','-HandleFrames=0','-MovieOverwriteExisting=False','-MovieRelativeFrames=True',
        '-MovieWarmUpFrames=24','-MovieDelayBeforeWarmUp=5','-MovieDelayBeforeShotWarmUp=3',
        '-MovieEngineScalabilityMode=False','-MovieCinematicMode=True','-WriteEditDecisionList=False','-WriteFinalCutProXML=False','-UseBurnIn=False','-RenderOffscreen',
        '-ResX=1280','-ResY=720','-Windowed','-ForceRes','-NoSplash','-NoScreenMessages','-unattended','-nosound',
        '-ExecCmds=r.ScreenPercentage 100,r.SecondaryScreenPercentage.GameViewport 100,r.DynamicRes.OperationMode 0',
        '-abslog='+str(output/'Unreal.log'),
        '-ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=AstraProbe_ShareVideoV3,'
        '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=AstraProbe_ShareVideoV3_Settings,'
        '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False,'
        '[/Script/MikdashRuntime.MikdashFrontEnd]:bEnabled=False,[/Script/MikdashRuntime.MikdashCinematics]:bEnabled=False']
    report['command']=command;write()
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    process=subprocess.Popen(command,startupinfo=startup)
    report['pid']=process.pid;report['status']='rendering';write()
    try:
        report['exitCode']=process.wait(timeout=1800)
        files=sorted(frames.glob('*.png'));report['frameCount']=len(files)
        bad=[]
        for p in files:
            with p.open('rb') as f: h=f.read(24)
            if len(h)!=24 or h[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',h[16:24])!=(1280,720): bad.append(p.name)
        report['badHeaders']=bad
        report['status']='frames_complete_visual_review_pending' if report['exitCode']==0 and len(files)==960 and not bad else 'failed'
    except subprocess.TimeoutExpired:
        process.terminate();process.wait(timeout=30)
        report['errors'].append('Owned capture exceeded 1800s watchdog');report['status']='failed'
    finally:
        report['mapsUnchanged']=maps()==report['mapsBefore'];report['originalSavesUnchanged']=saves()==report['savesBefore']
        if not report['mapsUnchanged'] or not report['originalSavesUnchanged']:report['status']='failed'
        write()
    print(json.dumps({k:v for k,v in report.items() if k not in ('mapsBefore','savesBefore','command')},indent=2))

if __name__=='__main__':run()
