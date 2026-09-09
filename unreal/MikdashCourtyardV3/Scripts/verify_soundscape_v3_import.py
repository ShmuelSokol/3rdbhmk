"""Fresh-process read-only SoundscapeV3 verification; never imports/saves/adopts.
Native switch -SoundscapeV3Verify=<absolute successful import receipt>.
Offline --selftest validates receipt rejection logic only. No listening acceptance.
"""
import json
import math
import os
from pathlib import Path
import shlex
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from release_surface_soft import sha,inventory,check_hashes
from release_soundscape_v2 import IMPORT_ONLY_STATUS,load_spec,SPEC_PATH,SOURCE_TABLE,encode_value,values_match,_protected_hashes
NAMESPACE='/Game/MikdashV3/Runtime/Audio/SoundscapeV3'


def validate_receipt(receipt,pid):
    switches=receipt.get('switches',{})
    if receipt.get('status')!=IMPORT_ONLY_STATUS or receipt.get('errors') or receipt.get('mapSaved') or receipt.get('mapBytesChanged'):
        raise RuntimeError('Successful untouched-map import-only receipt required')
    if not switches.get('importOnly') or not switches.get('runtimeActor') or switches.get('dryRun') or switches.get('ambientFallback'):
        raise RuntimeError('Wrong import mode')
    if receipt.get('protectedUnchanged') is not True:
        raise RuntimeError('Import preservation not verified')
    process=receipt.get('zombieEditorCheckAtStart',{})
    processes=process.get('processes',[])
    old_pid=processes[0].get('pid') if len(processes)==1 else None
    if process.get('checked') is not True or process.get('otherEditors') or type(old_pid) is not int or old_pid<=0 or old_pid==pid:
        raise RuntimeError('Fresh distinct native process required')
    rows=receipt.get('savedAssetReadback',[])
    paths=[r.get('path','') for r in rows]
    if not rows or len(set(paths))!=len(paths) or any(not p.startswith(NAMESPACE+'/') for p in paths):
        raise RuntimeError('Missing/duplicate/out-of-namespace saved assets')
    if set(paths)!=set(receipt.get('createdAssetPaths',[])):
        raise RuntimeError('Saved asset list differs from created assets')
    waves=receipt.get('assets',{}).get('waves',[])
    if not waves or any(w.get('looping') is not False or w.get('path') not in paths for w in waves):
        raise RuntimeError('Invalid runtime waves')
    return rows,waves


def run(source):
    import unreal as u
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=ROOT/'SourceAssets/soundscape-review'/('v3-fresh-verify-'+stamp+'.json')
    report={'status':'started','pid':os.getpid(),'errors':[],'auditioned':False,
            'scope':'Numeric asset persistence only; no map adoption, listening or runtime audio acceptance'}
    protected={}
    def write():
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    write()
    try:
        source=Path(source).resolve(strict=True)
        original=json.loads(source.read_text(encoding='utf-8-sig'))
        rows,waves=validate_receipt(original,os.getpid())
        report['sourceReceipt']=str(source);report['sourceReceiptSha256']=sha(source)
        inventory()
        if Path(u.Paths.project_dir()).resolve()!=ROOT: raise RuntimeError('Wrong project')
        ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        def clean():
            if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('PIE or dirty packages')
        clean()
        spec=load_spec()
        mapfile=(ROOT/spec['targetMapFile']).resolve()
        if original.get('map')!=spec['targetMap'] or Path(original.get('mapFile','')).resolve()!=mapfile:
            raise RuntimeError('Import target map identity differs')
        if not original.get('mapSha256Before') or original['mapSha256Before']!=original.get('mapSha256After') or sha(mapfile)!=original['mapSha256Before']:
            raise RuntimeError('Target map changed during or since import')
        if spec['namespace']['root']!=NAMESPACE or sha(SPEC_PATH)!=original['specSha256']:
            raise RuntimeError('Import spec or namespace changed')
        if _protected_hashes(spec)!=original['protectedSha256Before']:
            raise RuntimeError('Protected maps/audio changed since import')
        protected={str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file()}
        report['protectedContentCount']=len(protected)
        loaded={}
        for row in rows:
            package=row['path'].split('.')[0]
            path=ROOT/'Content'/(package[6:]+'.uasset')
            if sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:
                raise RuntimeError('Saved asset bytes differ '+package)
            asset=u.load_asset(package)
            if asset is None or asset.get_path_name()!=row['path']:
                raise RuntimeError('Fresh asset load identity differs '+package)
            loaded[row['path']]=asset
        table={entry['key']:entry for entry in SOURCE_TABLE}
        if {w['key'] for w in waves}!=set(table) or len(waves)!=len(table):
            raise RuntimeError('Wave/source inventory differs')
        report['waves']=[]
        for wave in waves:
            key=wave['key'];entry=table[key]
            if wave['file']!=entry['file']: raise RuntimeError('Source filename differs')
            source_file=ROOT/spec['sourceFolder']/entry['file']
            if sha(source_file)!=wave['sourceSha256']: raise RuntimeError('Source bytes changed '+key)
            asset=loaded[wave['path']]
            if not isinstance(asset,u.SoundWave) or asset.get_editor_property('looping'):
                raise RuntimeError('Runtime wave wrong type/looping '+key)
            duration=float(asset.get_editor_property('duration'))
            expected_duration=float(wave['durationSeconds'])
            if not math.isfinite(expected_duration) or expected_duration<=0:
                raise RuntimeError('Invalid receipt duration '+key)
            if not math.isfinite(duration) or duration<=0 or abs(duration-expected_duration)>max(.00001,.000001*duration):
                raise RuntimeError('Fresh duration differs '+key)
            changes=[c for c in original['changes'] if c.get('target')=='wave:'+key and c.get('applied')]
            for change in changes:
                actual=encode_value(u,asset.get_editor_property(change['resolvedName']))
                if not values_match(actual,change['after'],spec['verification']['floatRelativeTolerance']):
                    raise RuntimeError('Wave configuration differs '+key+'.'+change['resolvedName'])
            report['waves'].append({'key':key,'durationSeconds':duration,'looping':False,'sourceSha256':wave['sourceSha256'],'propertiesChecked':len(changes)})
        clean()
        report['status']='fresh_assets_verified_UNAUDITIONED'
    except Exception as error:
        report['status']='failed';report['errors'].append(repr(error));raise
    finally:
        report['protectedDifferences']=check_hashes(protected)
        current={str(p) for p in (ROOT/'Content').rglob('*') if p.is_file()} if protected else set()
        report['unexpectedContentFiles']=sorted(current-set(protected))
        if report['protectedDifferences'] or report['unexpectedContentFiles']: report['status']='failed_preservation'
        write()
    if report['status'].startswith('failed'): raise RuntimeError(report['status'])
    return report


if __name__=='__main__':
    if '--selftest' in sys.argv:
        for bad in ({},{'status':'failed'},{'status':IMPORT_ONLY_STATUS}):
            try: validate_receipt(bad,123)
            except RuntimeError: pass
            else: raise AssertionError('Invalid receipt accepted')
        print('3 invalid receipt rejection checks passed; no native verification')
    else:
        import unreal as u
        command=u.SystemLibrary.get_command_line()
        tokens=shlex.split(command,posix=False)
        value=next((t.split('=',1)[1].strip('"') for t in tokens if t.lower().startswith('-soundscapev3verify=')),None)
        try:
            if not value: raise RuntimeError('Explicit -SoundscapeV3Verify receipt required')
            run(value)
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower(): u.SystemLibrary.quit_editor()
