"""Offline closure, fresh external staging and result validation. Never launches UE."""
import argparse, hashlib, json, math, os, re, shutil, stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = Path('C:/Mikdash/Verification')
LIB = '6100fb9169e3b096abd81f99e5670a60b3bc78b40e56d2c363aa009ccdfac924'
PREVIOUS = '3f4b9a8cf1090f7aff0e0e089ab74353ec40fd5039c21bbccc501af4523954da'

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def load(p):
    require(Path(p).stat().st_size <= 4*1024*1024, 'JSON size budget')
    def pairs(xs):
        result = {}
        for k,v in xs:
            require(k not in result, 'duplicate JSON key')
            result[k] = v
        return result
    return json.loads(Path(p).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def write(p, obj):
    with Path(p).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=2, allow_nan=False); f.write('\n')

def plain(p):
    p = Path(p).absolute()
    for part in [p, *p.parents]:
        if part.exists():
            s = part.lstat()
            require(not (getattr(s, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT), 'reparse path: '+str(part))
    return p

def relpath(root, name):
    require(isinstance(name,str) and '\\' not in name and ':' not in name, 'nonportable relative path')
    require(name and not name.startswith('/') and all(x not in ('','.','..') for x in name.split('/')), 'path escape')
    return plain(Path(root)/name)

def exact_tree(root, pins):
    actual = set()
    require(Path(root).is_dir(), 'missing tree')
    for p in Path(root).rglob('*'):
        plain(p)
        if p.is_file(): actual.add(p.relative_to(root).as_posix())
    require(actual == set(pins), 'unexpected/missing files: '+str(actual ^ set(pins)))
    for n,h in pins.items(): require(sha(relpath(root,n)) == h, 'hash changed: '+n)

def verify(root=ROOT):
    plain(root)
    m = load(root/'manifest.json'); i = load(root/'inputs.json')
    require(m['predecessorManifestSha256']==PREVIOUS, 'predecessor')
    for n,h in m['files'].items(): require(sha(relpath(root,n))==h, 'closure pin: '+n)
    for n,h in m['inputs'].items(): require(sha(plain(n))==h, 'dependency pin: '+n)
    for n,v in i['inputs'].items(): require(sha(plain(n))==v['sha256'], 'project input: '+n)
    require(sha(i['engineExe'])==i['engineExeSha256'], 'engine executable pin')
    project=Path(i['sourceProject'])
    for n,v in {**i['packages'],**i['pluginFiles']}.items():
        p=relpath(project,n)
        require(sha(p)==v['sha256'] and p.stat().st_size==v['bytes'], 'source package/plugin pin: '+n)
        if n in i['packages']:
            for suffix in ('.uexp','.ubulk','.uptnl'):
                require(not p.with_suffix(suffix).exists(), 'unlisted package sidecar')
    require(i['packages'][i['mapFile']]['sha256']==i['mapSha256'], 'map mismatch')
    return m,i

def copy_file(src,dst):
    plain(src); plain(dst); dst.parent.mkdir(parents=True,exist_ok=True)
    with Path(src).open('rb') as a, dst.open('xb') as b: shutil.copyfileobj(a,b,1024*1024)
    require(sha(src)==sha(dst), 'copy changed')

def stage(name):
    require(re.fullmatch('[a-z0-9-]{1,32}',name), 'stage name')
    m,i=verify(); dest=plain(VERIFY/('WalkingCensusRunner09-review-'+name))
    require(not dest.exists(), 'fresh stage only')
    # Explicit reserve; never deletes archives or other files.
    need=sum(v['bytes'] for v in i['packages'].values())+sum(v['bytes'] for v in i['pluginFiles'].values())
    require(shutil.disk_usage(VERIFY).free>=need+2*1024**3, '2GiB staging reserve')
    dest.mkdir()
    for n in [*m['files'],'manifest.json']: copy_file(relpath(ROOT,n),relpath(dest,n))
    e=load(ROOT/'strict-build-result.json')
    lib=next(Path(n) for n,h in e['artifacts'].items() if n.endswith('StrictArithmetic.lib') and h==LIB)
    require(sha(lib)==LIB,'strict library')
    copy_file(lib,dest/'ThirdParty/Win64/StrictArithmetic.lib')
    for n in [*i['packages'],*i['pluginFiles']]: copy_file(relpath(i['sourceProject'],n),relpath(dest/'Payload',n))
    verify(dest)
    write(dest/'stage-receipt.json',{'manifest':sha(ROOT/'manifest.json'),'stage':str(dest),'UEExecuted':False})
    print(dest)

def external():
    require(ROOT.parent==VERIFY and re.fullmatch('WalkingCensusRunner09-review-[a-z0-9-]{1,32}',ROOT.name), 'exact external stage required')
    m,i=verify()
    require(load(ROOT/'stage-receipt.json')['manifest']==sha(ROOT/'manifest.json'),'stage manifest')
    exact_tree(ROOT/'Payload',{n:v['sha256'] for n,v in {**i['packages'],**i['pluginFiles']}.items()})
    require(sha(ROOT/'ThirdParty/Win64/StrictArithmetic.lib')==LIB,'strict library')
    return m,i

def run_path(name):
    require(re.fullmatch('[a-z0-9-]{1,32}',name),'run name')
    return plain(ROOT/'runs'/name)

def prepare(mode,name,build=None):
    m,i=external(); dest=run_path(name)
    require(not dest.exists(),'fresh run only')
    seal=None
    if mode=='Census':
        require(build is not None,'build run required')
        buildroot=run_path(build); seal=load(buildroot/'build-seal.json')
        require(seal['manifest']==sha(ROOT/'manifest.json'),'wrong build source')
        require(seal['receipt']==sha(buildroot/'receipt.json'),'build receipt changed')
        for n,h in seal['files'].items(): require(sha(relpath(buildroot,n))==h,'compiled output changed')
    require(shutil.disk_usage(ROOT).free>=4*1024**3,'4GiB fresh run disk headroom')
    dest.mkdir(parents=True)
    for n in m['files']:
        if n.startswith(('ProbeProject/','ABI/')): copy_file(ROOT/n,dest/n)
    copy_file(ROOT/'ThirdParty/Win64/StrictArithmetic.lib',dest/'ThirdParty/Win64/StrictArithmetic.lib')
    for n in [*i['packages'],*i['pluginFiles']]: copy_file(ROOT/'Payload'/n,dest/'ProbeProject'/n)
    config=dest/'ProbeProject/Config';config.mkdir()
    (config/'DefaultEngine.ini').write_text('[URL]\nGameName=CookedWorldProbe\n[/Script/EngineSettings.GameMapsSettings]\nGameDefaultMap='+i['map']+'\nEditorStartupMap='+i['map']+'\n',encoding='utf-8')
    copy_file(ROOT/'inputs.json',dest/'ProbeProject/CensusInputs.json')
    import uuid
    nonce=uuid.uuid4().hex; prefix='WalkingCensus09_'+nonce
    descriptor={'nonce':nonce,'manifest':sha(ROOT/'manifest.json'),'seal':sha(buildroot/'build-seal.json') if seal else '', 'savePrefix':prefix}
    write(dest/'ProbeProject/CensusRun.json',descriptor)
    if seal:
        for n in seal['files']: copy_file(buildroot/n,dest/n)
    protected={p.relative_to(dest).as_posix():sha(p) for p in dest.rglob('*') if p.is_file()}
    write(dest/'protected.json',protected)
    write(dest/'request.json',{'mode':mode,'manifest':sha(ROOT/'manifest.json'),'run':str(dest),'build':build,'descriptor':descriptor})
    print(dest)

def check_preservation(dest):
    external()
    for n,h in load(dest/'protected.json').items(): require(sha(relpath(dest,n))==h,'staged input changed: '+n)
    i=load(ROOT/'inputs.json')
    exact_tree(dest/'ProbeProject/Content',{n[len('Content/'):]:v['sha256'] for n,v in i['packages'].items()})

def validate_result(result, request, inputs):
    require(result.get('schema')==1 and result.get('status')=='diagnostic_observed','native result failed')
    for k,v in request['descriptor'].items(): require(result.get(k)==v,'result binding: '+k)
    require(result.get('worldReady') is False and result.get('measuredCorrespondenceConditional') is True,'false readiness')
    o=result['observation'];c=o['capture']
    require(o['map']==inputs['map'] and o['residents']==48 and o['scale']==1 and o['idle'] is True,'owner scope')
    idx=o['agentIndex'];require(type(idx) is int and 0<=idx<48,'agent range')
    pose=idx%2;variant=inputs['variants'][pose]
    require(o['pose']==pose and o['instance']==idx//2 and o['profile']==variant['profile'] and o['mesh']==variant['mesh'],'owner mapping')
    require(o['evidence']==inputs['evidence'],'measured evidence')
    require(len(o['origin'])==3 and all(type(v) in (int,float) and math.isfinite(v) for v in o['origin']),'origin')
    require(c['diagnosticOnly'] is True and c['publishedEnumerationExhausted'] is False and c['worldComplete'] is False and c['obstaclesComplete'] is False,'capture claims')
    require(type(c['refusal']) is int and 0<=c['refusal']<=10,'refusal enum')
    require(c['profile']==o['profile'] and c['agent']==str(idx+1) and c['incarnation']=='1','capture owner')
    # Preincrement overflow sentinels are evidence of Budget refusal, not a
    # relaxed enumeration allowance. No other refusal/success may exceed caps.
    overflow=1 if c['refusal']==6 else 0
    for key,cap in [('payloadVisits',64+overflow),('nodeVisits',2048+overflow),('boundsTests',4096+overflow),('sourceFaceTests',4096+overflow),('exhaustedMeshes',32)]:
        require(type(c[key]) is int and 0<=c[key]<=cap,'counter '+key)
    require(type(c['observedEnumerationExhausted']) is bool and type(c['candidateCopyAvailable']) is bool,'capture booleans')
    if c['refusal']:
        require(not c['observedEnumerationExhausted'] and not c['candidateCopyAvailable'],'partial census mislabeled')
    else:
        require(c['observedEnumerationExhausted'] and c['candidateCopyAvailable'],'missing successful copy')
        require(0<=c['candidateVertices']<=256 and 0<=c['candidateFaces']<=128,'copy budgets')
    rows=c['observedShapes'];require(type(rows) is list and len(rows)<=32,'shape budget')
    for row in rows:
        require(isinstance(row['component'],str) and len(row['component'])<=2048 and row['component'],'component identity')
        for key in ('componentUid','instance','shapeOrdinal','blockChannels','overlapChannels'):
            require(isinstance(row[key],str) and re.fullmatch('[0-9]{1,20}',row[key]) is not None and int(row[key])<2**64,'shape identity')
        require(type(row['queryEnabled']) is bool and type(row['classification']) is int and 0<=row['classification']<=5,'shape classification')
        require(type(row['geometryType']) is int and 0<=row['geometryType']<2**32 and type(row['objectChannel']) is int and 0<=row['objectChannel']<32,'shape filter')
    packages=o['loadedProjectPackages'];allowed={v['package'] for v in inputs['packages'].values()}
    require(type(packages) is list and len(packages)==len(set(packages)) and set(packages)<=allowed and inputs['map'] in packages,'loaded project package scope')
    return {'status':'validated_diagnostic_observation','geometryRefusal':c['refusal'],'worldReady':False,'UEExecuted':True}

def validate(name):
    dest=run_path(name);check_preservation(dest)
    result=validate_result(load(dest/'native.json'),load(dest/'request.json'),load(ROOT/'inputs.json'))
    result['nativeSha256']=sha(dest/'native.json');write(dest/'validated-result.json',result)

def seal(name):
    external();dest=run_path(name);check_preservation(dest);r=load(dest/'receipt.json')
    require(r['mode']=='Build' and r['status']=='build_exit_zero' and r['cleanupConfirmed'] is True and r['slotBlocked'] is False and r['sourcePreserved'] is True,'build receipt failed')
    require(r['naturalDrainConfirmed'] is True and r['terminalPoll']['activeProcesses']==0 and r['terminalPoll']['rootExited'] is True and r['terminalPoll']['exitCode']==0,'build terminal')
    require(r['manifest']==sha(ROOT/'manifest.json'),'build manifest')
    files={}
    engine_modules=Path(load(ROOT/'inputs.json')['engineExe']).parent/'UnrealEditor.modules'
    engine_id=load(engine_modules)['BuildId']
    for directory,module in [('ProbeProject/Binaries/Win64','CookedWorldProbe'),('ProbeProject/Plugins/MikdashRuntime/Binaries/Win64','MikdashRuntime')]:
        meta=dest/directory/'UnrealEditor.modules';d=load(meta)
        require(set(d['Modules'])=={module} and d['BuildId']==engine_id,'unexpected module mapping/build ID')
        dll=d['Modules'][module];require(dll=='UnrealEditor-'+module+'.dll','unexpected binary name')
        for n in (directory+'/UnrealEditor.modules',directory+'/'+dll): files[n]=sha(relpath(dest,n))
    write(dest/'build-seal.json',{'manifest':sha(ROOT/'manifest.json'),'receipt':sha(dest/'receipt.json'),'files':files,'UECompiled':True,'worldReady':False})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','stage','prepare','preserve','validate','seal']);p.add_argument('--name');p.add_argument('--mode',choices=['Build','Census']);p.add_argument('--build');a=p.parse_args()
    if a.action=='verify':
        m,i=verify(); print(json.dumps({'files':len(m['files']),'inputs':len(m['inputs']),'packages':len(i['packages']),'pluginFiles':len(i['pluginFiles']),'UEExecuted':False}))
    elif a.action=='stage':stage(a.name)
    elif a.action=='prepare':prepare(a.mode,a.name,a.build)
    elif a.action=='preserve':check_preservation(run_path(a.name))
    elif a.action=='validate':validate(a.name)
    else:seal(a.name)
