"""Bounded, retained, entirely owned fixtures. No UE, shell, ACL changes or deletion tree.

All created paths, junction targets, hardlink sources/destinations, and rename
destinations are under a fresh runtime_settings02/runs/<uuid>/fixture directory.
Fixtures are retained. Only the explicitly created empty junction itself is removed
with RemoveDirectoryW after tests, to leave no live redirect in the artifact tree.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path
import struct
import time
import uuid
import win32_predicate as w

BASE=Path(__file__).resolve().parent

def main():
    started=time.monotonic()
    run=BASE/'runs'/('windows-'+uuid.uuid4().hex[:12])
    run.mkdir(parents=True,exist_ok=False)
    snapshot=run/'source';snapshot.mkdir()
    for source in (Path(__file__),BASE/'win32_predicate.py'):
        (snapshot/source.name).write_bytes(source.read_bytes())
    fixture=run/'fixture';fixture.mkdir()
    results=[];junctions=[];handles=[]

    def child(rel):
        p=fixture/rel
        # Parents must already be within the resolved fixture; symlink/junction
        # targets never enter this function as destinations for a file write.
        if not p.resolve().is_relative_to(fixture.resolve()):raise RuntimeError('outside owned fixture')
        return p
    def directory(rel):
        p=child(rel);p.mkdir(parents=True,exist_ok=False);return p
    def file(rel):
        p=child(rel);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b'owned-settings-path-fixture\n')
        return p
    def case(name,condition,observed,category='win32'):
        if time.monotonic()-started>30:raise RuntimeError('30 second test budget exceeded')
        results.append({'name':name,'passed':bool(condition),'category':category,'observed':observed})
        if not condition:raise AssertionError(name)
    def move(src,dst):
        # Both names verified inside fixture before each bounded rename.
        for p in (src,dst):
            if not p.resolve().is_relative_to(fixture.resolve()):raise RuntimeError('rename outside fixture')
        if not w.k.MoveFileW(str(src),str(dst)):raise C.WinError(C.get_last_error())
    def junction(name,target):
        link=directory(name)
        if not target.resolve().is_relative_to(fixture.resolve()):raise RuntimeError('external junction target')
        subst=('\\??\\'+str(target)).encode('utf-16-le');printed=str(target).encode('utf-16-le')
        paths=subst+b'\0\0'+printed+b'\0\0'
        data=struct.pack('<IHHHHHH',0xA0000003,8+len(paths),0,0,len(subst),len(subst)+2,len(printed))+paths
        h=w.k.CreateFileW(str(link),0x40000000,7,None,3,w.BACKUP|w.NOFOLLOW,None)
        if h==w.INVALID:raise C.WinError(C.get_last_error())
        try:
            buf=C.create_string_buffer(data);returned=W.DWORD()
            if not w.k.DeviceIoControl(h,0x000900A4,buf,len(data),None,0,C.byref(returned),None):
                raise C.WinError(C.get_last_error())
        finally:w.k.CloseHandle(h)
        junctions.append(link);return link

    failure=None
    try:
        w.verify_frozen()
        root=directory('session-a');saved=directory('session-a/User/Saved/SaveGames')
        leaf=file('session-a/User/Saved/SaveGames/settings.sav')
        r=w.disk_path(root,True);identity=r['identity'];case('regular_root',r['ok'],r)
        r=w.disk_path(leaf,False);case('regular_file',r['ok'],r)
        r=w.disk_path(saved/'missing.sav',False);case('missing_final_file_allowed',r['ok'],r)
        r=w.disk_path(saved/'missing',True);case('missing_directory_refused',not r['ok'],r)
        r=w.disk_path(saved/'absent'/'file.sav',False);case('missing_parent_refused',not r['ok'],r)
        r=w.disk_path(leaf,True);case('file_as_directory_refused',not r['ok'],r)
        r=w.disk_path(saved,False);case('directory_as_file_refused',not r['ok'],r)
        r=w.owned_root(root,identity);case('matching_root_identity',r['ok'],r)
        r=w.owned_root(root,[identity[0],identity[1]^1]);case('wrong_root_identity_refused',not r['ok'],r)

        other=directory('session-b');otherfile=file('session-b/settings.sav')
        link=child('session-a/User/Saved/SaveGames/linked.sav')
        if not w.k.CreateHardLinkW(str(link),str(otherfile),None):raise C.WinError(C.get_last_error())
        r=w.disk_path(link,False);case('hardlink_refused',not r['ok'] and r['reason']=='hardlink',r)
        r=w.disk_path(otherfile,False);case('hardlink_source_also_refused',not r['ok'] and r['reason']=='hardlink',r)

        j=junction('redirect',other)
        r=w.disk_path(j,True);case('junction_root_refused',not r['ok'] and r['reason']=='alias_or_reparse',r)
        r=w.disk_path(j/'settings.sav',False);case('junction_ancestor_refused',not r['ok'],r)
        r=w.disk_path(j,False);case('junction_as_file_refused',not r['ok'],r)

        replacement=directory('replacement');file('replacement/User/Saved/SaveGames/fresh.sav')
        old=child('session-a-retired')
        move(root,old);move(replacement,root)
        r=w.owned_root(root,identity);case('root_replaced_between_checks_refused',not r['ok'],r)

        # Deterministic race: swap a real root after its successful check, then read
        # a descendant. This is a LIMITATION demonstration, not a security pass.
        race=directory('race-root');file('race-root/User/Saved/a.sav')
        race_new=directory('race-new');file('race-new/User/Saved/a.sav')
        before=w.disk_path(race,True)
        move(race,child('race-old'));move(race_new,race)
        descendant=w.disk_path(race/'User/Saved/a.sav',False)
        after=w.owned_root(race,before['identity'])
        case('closed_snapshot_does_not_lock_root',before['ok'] and descendant['ok'] and not after['ok'],
             {'before':before,'descendant':descendant,'fresh_identity_check':after},'race_limitation')

        # Swap inside the actual walker after a real ancestor handle closes.
        walking=directory('walking');file('walking/a.sav')
        walking_new=directory('walking-new');file('walking-new/a.sav')
        triggered=[]
        def swap_after_close(path,last):
            if not triggered and path.casefold()==str(walking).replace('\\','/').casefold():
                move(walking,child('walking-old'));move(walking_new,walking);triggered.append(True)
        r=w.disk_path(walking/'a.sav',False,after_close=swap_after_close)
        case('ancestor_rename_race_needs_ownership_premise',bool(triggered) and r['ok'],r,'race_limitation')

        pinned=directory('pinned');h=w.open_attributes(pinned,share_delete=False);handles.append(h)
        destination=child('pinned-renamed')
        moved=bool(w.k.MoveFileW(str(pinned),str(destination)));error=C.get_last_error()
        still_open=w.inspect_handle(h)
        case('metadata_only_handle_does_not_block_rename',moved and
             still_open['final'].casefold()==str(destination).replace('\\','/').casefold(),
             {'moved':moved,'winerror':error,'handle_readback':still_open},'race_limitation')
        w.k.CloseHandle(handles.pop())
        locked=directory('generic-read-locked')
        h=w.open_attributes(locked,share_delete=False,desired_access=0x80000000);handles.append(h)
        destination=child('generic-read-renamed')
        moved=bool(w.k.MoveFileW(str(locked),str(destination)));error=C.get_last_error()
        case('generic_read_no_delete_handle_blocks_root_rename',not moved and error in (5,32),
             {'moved':moved,'winerror':error},'handle_lease_experiment')
        w.k.CloseHandle(handles.pop());move(locked,destination)
        r=w.disk_path(destination,True);case('rename_after_generic_read_handle_release',r['ok'],r,'handle_lease_experiment')

        late=child('session-b/late.sav');admission=w.disk_path(late,False)
        hardlink_source=child('session-a-retired/User/Saved/SaveGames/settings.sav')
        if not w.k.CreateHardLinkW(str(late),str(hardlink_source),None):
            raise C.WinError(C.get_last_error())
        recheck=w.disk_path(late,False)
        case('missing_leaf_snapshot_cannot_prevent_late_hardlink',admission['ok'] and not recheck['ok'],
             {'before':admission,'after':recheck},'race_limitation')

        contract=w.lex.launch_inputs(str(fixture/'Argument Space'),'settings-a','save-a')
        line='SettingsPathProbe.exe '+contract['exact_suffix']
        actual=w.windows_argv(line)
        case('quoted_userdir_actual_windows_tokenization',actual==['SettingsPathProbe.exe']+contract['tokens'],actual,'windows_arguments')
        case('exact_argument_closure',w.exact_argument_admission(line,contract),True,'windows_arguments')
        variants={
            'duplicate_userdir':line+' -UserDir=C:/other',
            'case_variant_duplicate':line+' -uSeRdIr=C:/other',
            'prefix_userdir':'SettingsPathProbe.exe -UserDir=C:/other '+contract['exact_suffix'],
            'saved_suffix':line+' -saveddirsuffix=other',
            'game_ini_redirect':line+' -GameIni=C:/other/Game.ini',
            'ini_override':line+' -ini:Game:[x]:y=z',
            'unquoted_space':line.replace('"',''),
            'unterminated_quote':line+' "',
            'quote_insertion':line.replace('Argument Space','Argument" Space'),
            'shell_metacharacter':line+' & echo nope',
        }
        for name,bad in variants.items():
            case('argument_refusal_'+name,not w.exact_argument_admission(bad,contract),
                 {'tokens':w.windows_argv(bad)},'windows_arguments')
    except Exception as exc:
        failure=type(exc).__name__+': '+str(exc)
    finally:
        cleanup=[]
        for h in handles:w.k.CloseHandle(h)
        for link in junctions:
            # Never recurse through the junction or remove its target. Exact names
            # come solely from successful junction creation above inside fixture.
            okay=bool(w.k.RemoveDirectoryW(str(link)))
            cleanup.append({'junction':str(link),'removed_link_only':okay,
                            'winerror':0 if okay else C.get_last_error()})
            if not okay:failure=failure or 'junction cleanup failed'
        try:w.verify_frozen()
        except Exception as exc:failure=failure or str(exc)
        receipt={'status':'passed' if failure is None else 'failed','failure':failure,
                 'elapsed_seconds':time.monotonic()-started,'results':results,
                 'fixture':str(fixture),'junction_cleanup':cleanup,'fixtures_retained':True,
                 'permissions_changed':False,'unreal_run':False,'cpp_compiled':False,
                 'coverage':'Real Win32 calls in pinned-source ctypes transcription; not full SettingsOwned runtime proof. Existing four Python tests are separate.',
                 'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),BASE/'win32_predicate.py']},
                 'frozen01_manifest':w.MANIFEST_SHA}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'receipt':str(run/'receipt.json'),'status':receipt['status'],'cases':len(results),'failure':failure}))
    return 0 if failure is None else 1

if __name__=='__main__':raise SystemExit(main())
