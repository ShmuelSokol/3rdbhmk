"""Read-only evidence extraction to new sanitized receipt; no historical edits/native work."""
import hashlib,json,re
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[5]
RUNNER=Path('C:/Mikdash/Verification/angular-native02-20261002/runner')
RUN=RUNNER/'runs/angular-compile02/compile'
THRESH=ROOT/'SourceAssets/context-review/HaramThresholdSidesV1/threshold-sides07/build'
ENGINE=Path('C:/Program Files/Epic Games/UE_5.8/Engine')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pin='de94eed20f3037a8251f84dea1d4e2b6638a207384509dfd2d231fc6be1ab357'
assert sha(RUNNER/'harness-hashes.json')==pin
pins=json.loads((RUNNER/'harness-hashes.json').read_text())
for name,digest in pins.items():assert sha(RUNNER/name)==digest,name
w=json.loads((RUN/'wrapper.json').read_text())
assert w['status']=='failed' and w['error']=='Total deadline: reserve cleanup5s plus poll margin'
assert w['cleanupConfirmed'] and w['sourcePreserved'] and not w['slotBlocked']
assert not (RUN/'native.json').exists()
logs={name:path.read_text(errors='replace') for name,path in [('compile02',RUN/'native.log'),('threshold07',THRESH/'native.log')]}
def cvars(text):
    return dict(re.findall(r'Set CVar \[\[([^:\]]+):([^\]]+)\]\]',text))
cv={name:cvars(text) for name,text in logs.items()}
differences={key:{name:values.get(key,'not logged; unknown effective value') for name,values in cv.items()}
             for key in sorted(set(cv['compile02'])|set(cv['threshold07']))
             if cv['compile02'].get(key)!=cv['threshold07'].get(key)}
material_keys=re.findall(r'Missing cached shadermap for (\S+).*?DDC key hash: ([a-f0-9]+)',logs['compile02'])
source_specs=[
 ('Source/Runtime/Engine/Private/ShaderCompiler/ShaderCompilerJobCache.cpp','159-177 excludes non-cook commandlets unless forceAllowShaderCompilerJobCache;185 selects material-map cache as inverse for this mode;2251-2267 gates per-job DDC Put'),
 ('Source/Runtime/Engine/Private/ShaderCompiler/ShaderCompiler.cpp','2336-2350 saves persistent material map after no incomplete materials;5632-5650 computes global key and optional dump'),
 ('Source/Runtime/Engine/Private/ShaderCompiler/ShaderCompilerEditor.cpp','174-215 global key includes format/version, shared shader key, dependencies and environment modifications;546-578 global map save expects completeness'),
 ('Source/Runtime/RenderCore/Private/Shader.cpp','1802-1814 VelocityOutputPass1 adds GV; other values add VOP/value to shared shader key'),
 ('Source/Runtime/Renderer/Private/VelocityRendering.cpp','29-37 default VelocityOutputPass0; comment states changing causes full shader recompile'),
 ('Source/Runtime/Engine/Private/Materials/MaterialShader.cpp','269/438 shared shader key feeds material keys;2220-2235 material cache write and verbose full-key logging')]
evidence=[{'path':str(ENGINE/path),'sha256':sha(ENGINE/path),'finding':finding,'publishSource':False} for path,finding in source_specs]
receipt={
 'scope':'Sanitized terminal addendum to published771712b32; historical Publication02 and runner untouched',
 'manifestSha256':pin,'verifiedHistoricalPins':len(pins),
 'wrapper':{k:w[k] for k in ('status','error','ownedElapsedSeconds','peakPrivateBytes','startFreeCommitBytes','cleanupConfirmed','sourcePreserved','slotBlocked')},
 'rawEvidenceNeverPublish':{str(p):sha(p) for p in (RUN/'wrapper.json',RUN/'launch.json',RUN/'native.log',THRESH/'native.log')},
 'observed':{'shaderPlatform':'Both logs DX12/SM6','workerCount':'Both logs one local worker',
 'candidateReceiptPresent':False,'pythonScriptStartLogged':False,'candidateShaderStats':None,
 'termination':'Total deadline, not owned memory cap','peakGiB':w['peakPrivateBytes']/1024**3,
 'lastLoggedWork':'Four missing Engine default material SM6 maps; completion/progress of individual jobs not logged',
 'materialKeys':dict(material_keys)},
 'exactCommandComparison':{
 'compile02Arguments':w['arguments'],
 'threshold07Command':next(line.split('Command Line: ',1)[1].strip() for line in logs['threshold07'].splitlines() if 'LogInit: Command Line: ' in line),
 'shared':'commandlet rendering/offscreen, one worker settings999/999, SCW pressure False, GI0/reflection0/VSM0, async concurrency1, no p4',
 'different':'Threshold main project and GeometryScripting enabled versus isolated tiny plugin allowlist; batch1 explicit only Compile02. Entry positional argument in threshold does not prove load; its Python explicitly loaded Entry.'},
 'loggedCvarDifferences':differences,
 'configEvidence':{'compile02DefaultEngineSha256':sha(RUNNER/'P/Config/DefaultEngine.ini'),
 'currentMainDefaultEngineSha256':sha(ROOT/'Config/DefaultEngine.ini'),
 'historicalLimitation':'Threshold07 snapshot has five script/audit files, no full effective configuration snapshot. Current main config is corroboration, not exact historical proof. Absence of a SetCVar line is not an effective-value readback.',
 'velocity':'Compile02 explicitly/logged1. Threshold command/config has no override; UE default0 is source-confirmed, but threshold effective0 is an inference, not a native readback.'},
 'globalKeys':{'threshold07':None,'compile02':None,
 'reason':'Neither retained log records exact global keys. WorldGrid756381bdeed6c3be2bd70e80f14d692db7880066 is a MATERIAL key, not a global shader key. Cannot honestly reconstruct exact global-key equality from SM6 alone.'},
 'cacheProgress':{'perJobDDC':'Disabled by source for these non-cook commandlet commands; neither contains forceAllowShaderCompilerJobCache. In-process job reuse does not imply cross-process persisted progress.',
 'wholeMaps':'Completed persistent material/global maps can be saved independently of completion of the entire startup. No evidence establishes which maps were saved here.',
 'rerunConclusion':'Do not assume a third identical deadline-limited run resumes individual completed jobs. Do not claim every completed map was lost either.',
 'forceFlagCaution':'Flag changes IsMaterialMapDDCEnabled/ODSC policy too; not a cache-only switch. Needs separate source review against positive representative shader proof.'},
 'sourceEvidence':evidence,
 'nextReadOnlyWork':['Determine historical effective velocity/config from an authoritative saved artifact if available, without loading maps',
 'Audit whether compile-only graph proof requires VelocityOutputPass1 at all; temporal render is deferred. Do not silently change it in historical runner',
 'If exact historical keys remain unavailable, document that limit; any future diagnostic run must be separately reviewed with explicit key/progress instrumentation, same guards and fresh outputs'],
 'noRetryProposedOrLaunched':True,'claims':{'shaderCompiled':False,'renderedPixels':False,'temporalVelocity':False,'productionAcceptance':False}}
target=BASE/'terminal-startup-audit.json'
assert not target.exists(),'Never overwrite terminal audit'
target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
manifest=BASE/'publish-addendum.json'
manifest.write_text(json.dumps({'additiveTo':'Publication02 source checkpoint771712b32','publishManifestItself':str(manifest.relative_to(ROOT)).replace('\\','/'),
 'entries':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p)} for p in (Path(__file__),target)],
 'rawLogsExcluded':True,'historicalPayloadUnchanged':True},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'historicalPinsVerified':len(pins),'sourceAddendumFiles':3,'outcome':'deadline, no candidate proof','loggedCvarDifferences':len(differences),'noNativeLaunch':True}))
