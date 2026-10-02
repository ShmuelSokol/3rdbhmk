"""Actual Windows/Job/bootstrap fixture. Never a production ownership policy.

Requires explicit --owned-fixture flag. Fresh bounded roots only; no ACL changes,
network, engine, PID termination, external writes or recursive deletion. Frozen03
is imported unchanged. All failures preserve roots/source snapshots/receipts.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import uuid
from unittest.mock import patch

BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
sys.path.insert(0,str(ROOT))
from session_core import Ownership,SessionError
from adapters.process04.host import LaunchRecipe
from adapters.process04.win32_child import kernel_api,Accounting
from adapters.receiver03_bootstrap import windows_qpc
from runtime_settings03.owned_settings_host import SettingsOwnedProcesses,ExclusiveOwnershipAuthority,ExclusiveAllocation,_probe
from os_fixture04.run_reviewed import Probe,configure

EXPECTED03='5041cbeb6c6785011e8df35763c4819e4e08cde7c16301fb790583bfc3f66079'

def frozen():
    base=ROOT/'runtime_settings03';data=(base/'manifest.json').read_bytes()
    assert hashlib.sha256(data).hexdigest()==EXPECTED03
    for name,h in json.loads(data).items():assert hashlib.sha256((base/name).read_bytes()).hexdigest()==h,name

class FixtureAllocation(ExclusiveAllocation):
    """TEST ONLY: exclusive cooperative ownership of this fresh fixture is declared
    by this test controller, which creates all writers and retains every child.
    This is not an ACL policy or evidence against arbitrary same-account writers.
    No reusable grant file or production registration is created.
    """
    def __init__(self,owner,root,run,w):
        assert root.resolve().is_relative_to((run/'fixture').resolve()) and root.is_dir()
        self.owner=owner;self._root=str(root).replace('\\','/');self.w=w
        self.identity=w.disk_path(root,True)['identity'];self.active=True;self.released=False
    @property
    def root(self):return self._root
    @property
    def slot_count(self):return 2
    def revalidate(self,owner):
        if not self.active or owner!=self.owner or not self.w.owned_root(self.root,self.identity)['ok']:
            raise SessionError('Fixture allocation identity/premise refused')
    def release_after_cleanup(self,owner):
        if owner!=self.owner:raise SessionError('Wrong fixture owner')
        self.active=False;self.released=True

class FixtureAuthority(ExclusiveOwnershipAuthority):
    def __init__(self,allocation):self.allocation=allocation;self.reserves=0
    def reserve(self,owner):
        self.allocation.revalidate(owner)
        self.reserves+=1
        return self.allocation

class NoChannel:
    def __init__(self,*args,**kwargs):pass
    def exchange(self,*args,**kwargs):raise AssertionError('No channel/stream admission in fixture')

class Revoke:
    def __init__(self):self.refuse=False;self.calls=0
    def __call__(self,owner):
        self.calls+=1
        if self.refuse:raise SessionError('Explicit fixture route-cleanup fault')

class QueryFault:
    """Real kernel API passthrough, with explicit negative query fault injection.
    Actual OS query is still performed/recorded; only failure is injected, never
    fabricated successful Job/root/writer cleanup evidence.
    """
    def __init__(self,k):self.k=k;self.fail=True;self.real_active=[]
    def __getattr__(self,name):return getattr(self.k,name)
    def QueryInformationJobObject(self,*args):
        good=self.k.QueryInformationJobObject(*args)
        if good:self.real_active.append(C.cast(args[2],C.POINTER(Accounting)).contents.active)
        return False if self.fail else good

def main():
    if sys.argv[1:]!=['--owned-fixture']:raise RuntimeError('Explicit owned fixture required')
    assert os.name=='nt' and C.sizeof(C.c_void_p)==8
    frozen()
    executable=Path(sys.executable).resolve()
    assert executable.name.lower()=='python.exe'
    run=BASE/'runs'/('lifecycle-'+uuid.uuid4().hex[:10]);run.mkdir(parents=True,exist_ok=False)
    (run/'fixture').mkdir();(run/'source').mkdir()
    for name in ('run_lifecycle.py','child.py'):(run/'source'/name).write_bytes((BASE/name).read_bytes())
    w=_probe();k=kernel_api();configure(k)
    hosts=[];results=[];faults=[];started=time.monotonic();failure=None
    def check(name,good,detail=None):
        results.append({'name':name,'passed':bool(good),'detail':detail})
        if not good:raise AssertionError(name)
        if time.monotonic()-started>25:raise AssertionError('25 second acquisition budget exceeded')
    def until(fn,seconds=2):
        end=time.monotonic()+seconds
        for _ in range(401):
            if fn():return True
            if time.monotonic()>=end:return False
            time.sleep(.005)
        return False
    def rename_attempt(path,suffix):
        destination=path.with_name(path.name+suffix)
        assert path.resolve().is_relative_to((run/'fixture').resolve())
        assert destination.resolve().is_relative_to((run/'fixture').resolve())
        okay=bool(w.k.MoveFileW(str(path),str(destination)))
        return {'renamed':okay,'error':0 if okay else C.get_last_error(),'destination':str(destination)}
    def setup(name,mode,authority=True,sleeper=time.sleep):
        root=run/'fixture'/name
        for sub in ('User/Saved/Config/Windows','User/Saved/SaveGames','User/Temp'):(root/sub).mkdir(parents=True,exist_ok=True)
        owner=Ownership(name,name+'process',name+'stream',name+'save',name+'settings',windows_qpc()+40)
        grant=FixtureAllocation(owner,root,run,w)
        policy=FixtureAuthority(grant) if authority else None
        revoke=Revoke()
        recipe=LaunchRecipe(str(executable),hashlib.sha256(executable.read_bytes()).hexdigest(),str(BASE),
            ('-B',str(BASE/'child.py').replace('\\','/'),mode),os.environ['SystemRoot'],str(root/'User/Temp'),256*1024**2)
        host=SettingsOwnedProcesses(recipe,(19001,),revoke,ownership_authority=policy,
            channel_factory=NoChannel,hint=lambda port,timeout:(root/'User/ready').is_file(),
            sleeper=sleeper,key_factory=lambda:b'F'*32,start_seconds=2,write_seconds=.25,cleanup_seconds=.15)
        hosts.append((host,owner,grant,revoke));host.prepare()
        return host,owner,grant,revoke,root
    def stop(host,owner):return until(lambda:_try_stop(host,owner))

    # Bounded watchdog for unexpectedly stuck test code. Exact retained Job/root
    # handles only; no broad process enumeration or name/PID termination. Hard exit
    # drops kill-on-close Job handles, leaving fixtures quarantined if necessary.
    done=threading.Event()
    def watchdog():
        if done.wait(30):return
        (run/'watchdog.json').write_text('{"status":"deadline_failed","roots_quarantined":true}\n')
        for host,owner,grant,revoke in hosts:
            for r in list(host.settings_records.values()):
                if r.child and r.child.inner.k:
                    child=r.child.inner
                    if child.assigned and child.job:child.k.TerminateJobObject(child.job,0xdead)
                    elif child.root:child.k.TerminateProcess(child.root,0xdead)
        os._exit(9)
    timer=threading.Thread(target=watchdog,daemon=True);timer.start()
    try:
        # All socket usage would be an error; readiness here means fixture-file only.
        with patch('socket.socket',side_effect=AssertionError('Network forbidden')):
            h,o,g,rev,root=setup('missing','hold',False)
            with patch('runtime_settings03.owned_settings_host.WindowsChild.create',side_effect=AssertionError('Unexpected launch')) as created:
                try:h.start(o);refused=False
                except SessionError:refused=True
                check('missing_premise_refuses_before_create',refused and not created.called and not h.settings_records)

            h,o,g,rev,root=setup('replaced','hold')
            moved=rename_attempt(root,'-retired');check('fixture_root_replacement_prepared',moved['renamed'],moved)
            for sub in ('User/Saved/Config/Windows','User/Saved/SaveGames','User/Temp'):(root/sub).mkdir(parents=True)
            with patch('runtime_settings03.owned_settings_host.WindowsChild.create',side_effect=AssertionError('Unexpected launch')) as created:
                try:h.start(o);refused=False
                except SessionError:refused=True
                check('changed_root_identity_refuses_before_create',refused and not created.called and not h.records)

            h,o,g,rev,root=setup('natural','readexit');h.start(o)
            r=h.settings_records[o.process_key];inner=r.child.inner
            check('real_job_assigned_and_private_writer_complete',inner.assigned and inner.bootstrap_done(),{'process_identity':r.child.process_identity})
            rename=rename_attempt(root,'-bad');check('root_rename_refused_while_child_alive',not rename['renamed'] and rename['error'] in (5,32),rename)
            rename=rename_attempt(root/'User/Saved','-bad');check('retained_child_directory_rename_refused',not rename['renamed'],rename)
            check('natural_child_exit_observed',until(lambda:inner.k.WaitForSingleObject(inner.root,0)==0))
            check('real_writer_thread_drained',until(lambda:inner._done.is_set() and not inner._worker.is_alive()))
            code=W.DWORD();k.GetExitCodeProcess(inner.root,C.byref(code))
            check('harmless_child_exit_zero',code.value==0,{'exit_code':code.value})
            rename=rename_attempt(root,'-premature');check('handles_retained_after_exit_before_host_cleanup',bool(r.held.entries) and not g.released and not rename['renamed'],rename)
            check('natural_owned_cleanup_confirmed',stop(h,o) and not h.settings_records and not h.records and g.released)
            check('all_inner_handles_closed_after_cleanup',all(getattr(inner,n) is None for n in ('job','root','thread','reader','writer','null','_worker_handle')))
            rename=rename_attempt(root,'-released');check('root_rename_after_confirmed_release',rename['renamed'],rename)

            h,o,g,rev,root=setup('query','hold');h.start(o)
            r=h.settings_records[o.process_key];inner=r.child.inner;fault=QueryFault(inner.k);faults.append(fault);inner.k=fault
            try:h.stop(o);refused=False
            except SessionError:refused=True
            rename=rename_attempt(root,'-premature')
            check('query_failure_keeps_handles_and_capacity',refused and bool(r.held.entries) and o.process_key in h.records and o.process_key in h.settings_records and not g.released and not rename['renamed'],{'rename':rename,'real_job_active_observations':fault.real_active})
            check('query_failure_still_kills_owned_child_and_drains_writer',inner.k.WaitForSingleObject(inner.root,0)==0 and inner._done.is_set() and not inner._worker.is_alive())
            fault.fail=False
            check('query_recovery_releases_only_after_os_confirmation',stop(h,o) and g.released and not r.held.entries)

            # Saturate real pipe then block original writer on non-reading child.
            # Negative route failure keeps handles observable even after OS cleanup.
            probe=Probe(k,'fill');observations=[];holder={}
            def observe_sleep(seconds):
                if probe.entered.is_set() and not probe.returned.is_set() and time.perf_counter()-probe.entered_at>.02 and not observations:
                    host,owner,root=holder['case'];r=host.settings_records[owner.process_key]
                    observations.append({'handles':len(r.held.entries),'writer_pending':not r.child.inner._done.is_set(),
                                         'rename':rename_attempt(root,'-blocked')})
                time.sleep(seconds)
            h,o,g,rev,root=setup('blocked','ignore',sleeper=observe_sleep);holder['case']=(h,o,root);rev.refuse=True
            with patch('adapters.process04.win32_child.kernel_api',return_value=probe):
                try:h.start(o);refused=False
                except SessionError:refused=True
            r=h.settings_records.get(o.process_key)
            check('real_blocked_writer_observed_with_retained_handles',len(observations)==1 and observations[0]['handles']>0 and observations[0]['writer_pending'] and not observations[0]['rename']['renamed'],observations)
            check('bootstrap_deadline_failure_drains_real_worker',refused and probe.returned.is_set() and probe.error!=0 and r is not None and r.process_disposed and not r.child.inner._worker.is_alive(),{'write_error':probe.error,'cancel_calls':probe.cancel_calls,'job_kills':len(probe.job_kills)})
            rename=rename_attempt(root,'-premature')
            check('revocation_failure_holds_directories_after_worker_drain',bool(r.held.entries) and not g.released and not rename['renamed'],rename)
            rev.refuse=False
            check('revocation_recovery_releases_directory_lease',stop(h,o) and g.released and not r.held.entries)
    except Exception as exc:failure=type(exc).__name__+': '+str(exc)
    finally:
        cleanup=[]
        for fault in faults:fault.fail=False
        for h,o,g,rev in hosts:
            rev.refuse=False
            clean=stop(h,o)
            cleanup.append({'process_key':o.process_key,'confirmed':clean,'base_records':len(h.records),'settings_records':len(h.settings_records)})
            if not clean:failure=failure or 'Owned cleanup unconfirmed'
        try:frozen()
        except Exception as exc:failure=failure or 'Frozen03 changed: '+str(exc)
        receipt={'status':'passed' if failure is None else 'failed','failure':failure,'results':results,'cleanup':cleanup,
                 'elapsed_seconds':time.monotonic()-started,'frozen03_manifest':EXPECTED03,
                 'fixture_premise':'Explicit cooperative test roots/children only; no production ACL policy and no arbitrary same-account writer isolation claim',
                 'fault_injection':'Negative query result after real query; refused route cleanup; real saturated pipe. No successful OS result fabricated.',
                 'unreal':False,'permissions_changed':False,'network':False,'fixtures_retained':True,
                 'source_hashes':{name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in ('child.py','run_lifecycle.py')}}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        done.set();timer.join(timeout=.5)
        print(json.dumps({'receipt':str(run/'receipt.json'),'status':receipt['status'],'cases':len(results),'failure':failure}))
    return 0 if failure is None else 1

def _try_stop(host,owner):
    try:host.stop(owner);return not host.records and not host.settings_records
    except Exception:return False

if __name__=='__main__':raise SystemExit(main())
