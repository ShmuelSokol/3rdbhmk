"""Create source-only publication metadata. Never reads Compile02 inflight outputs."""
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[5]
OLD=BASE.parent/'AngularVATPublication01';NATIVE=BASE.parent/'AngularVATNative01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=lambda p:p.relative_to(ROOT).as_posix()
def write(name,value):
    (BASE/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
frozen='199bbc388482f58a437b059735815fec0fe63a764e1ad756955c26f437cf600a'
retry='de94eed20f3037a8251f84dea1d4e2b6638a207384509dfd2d231fc6be1ab357'
assert sha(NATIVE/'harness-hashes.json')==frozen
history=json.loads((OLD/'publish-allowlist.json').read_text())
for row in history['entries']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
run=NATIVE/'runs/angular-compile01/compile'
w=json.loads((run/'wrapper.json').read_text())
assert w['status']=='failed' and w['error']=='Owned job private cap'
assert w['cleanupConfirmed'] and w['sourcePreserved'] and not w['slotBlocked']
assert not (run/'native.json').exists()
write('compile01-failure.json',{
    'status':'failed before candidate shader proof; no native.json',
    'historicalManifestSha256':frozen,
    'observed':{k:w[k] for k in ('error','peakPrivateBytes','startFreeCommitBytes','ownedElapsedSeconds','cleanupConfirmed','sourcePreserved','slotBlocked')},
    'localEvidence':{name:{'path':rel(run/name),'sha256':sha(run/name),'publish':False} for name in ('wrapper.json','launch.json','native.log')},
    'startupEvidence':'Local log: DX12/SM5, one local shader worker; missing cached Engine WorldGrid, DeferredDecal, LightFunction and PostProcess SM5 shader maps. No candidate receipt or shader statistics.',
    'diagnosticLimit':'Memory guard termination is established; exact per-allocation cause and savings from batch reduction are not measured. No candidate compiler diagnostic exists.',
    'claims':{'candidateCompiled':False,'pixels':False,'temporalVelocity':False,'productionAcceptance':False},
    'preservation':'Original receipts/logs and Native01 bytes retained. Coordinator relocated malformed fault fixtures and UE Saved unchanged outside SourceAssets; no receipt-parser exemption.'})
engine=Path('C:/Program Files/Epic Games/UE_5.8/Engine')
evidence=[('Source/Runtime/Engine/Private/ShaderCompiler/ShaderCompiler.cpp','831: reads DevOptions.Shaders MaxShaderJobBatchSize'),
 ('Source/Runtime/Engine/Private/ShaderCompiler/ShaderCompilerThreadRunnable.cpp','508 and570: both dispatch paths clamp MaxNumJobs with MaxShaderJobBatchSize; high priority normally one except startup throttling override'),
 ('Config/BaseEngine.ini','2191: default MaxShaderJobBatchSize=10'),
 ('Source/Runtime/RHI/Private/Windows/WindowsDynamicRHI.cpp','625: parses D3D12TargetedShaderFormats')]
write('startup-audit.json',{
 'engineSourceEvidence':[{'path':str(engine/path),'sha256':sha(engine/path),'finding':finding,'publishSource':False} for path,finding in evidence],
 'threshold07':'Retained build/native.log lines969/987 confirm DX12/SM6;1138 confirms one worker. Threshold used the main project with Entry-only study loading, not the tiny isolated Angular project.',
 'thresholdLog':{'sha256':sha(ROOT/'SourceAssets/context-review/HaramThresholdSidesV1/threshold-sides07/build/native.log'),'publish':False},
 'differences':'Angular tiny descriptor omitted Windows target settings, selected SM5 and requested uncached Engine material maps. Shared shader worker settings and GI0/reflection0/VSM0 already matched threshold07.',
 'retryChanges':['Restore threshold07 DX12/SM6 target in external project only','Add -ini:Engine:[DevOptions.Shaders]:MaxShaderJobBatchSize=1'],
 'limits':['Batch1 limits common-job dispatch, not total permutations or engine resident memory; no tenfold savings claim','SM6 alignment does not guarantee identical shader/DDC keys or warm cache','Keep existing DDC, renderer knobs, world/shader features and positive GetStatistics gate; no cache deletion, quality reduction or cap/deadline increase'],
 'unmodifiedGuards':{'startGiB':6,'aggregateOwnedJobGiB':4,'reserveGiB':2,'totalDeadlineSeconds':300,'cleanupSeconds':5},
 'compile02':{'stateAtPublicationPreparation':'launched by coordinator, outcome pending; no inflight receipts inspected','manifestSha256':retry}})
write('publication-plan.json',{
 'status':'Source-only proposal; no publish/commit/native launch by author',
 'supersedes':'Publication01 publication-plan.json and its prepare/test instructions. Retained old files are historical evidence, not current execution guidance.',
 'historicalHazards':['Native01/prepare.py writes P under SourceAssets','Native01/test_offline.ps1 creates deliberate invalid JSON in SourceAssets','Native01/check_and_pin.py expects that old fault directory','Publication01/make_plan.py would recreate obsolete guidance'],
 'onlyCurrentPreparationEntrypoint':'AngularVATPublication02/prepare_external.py',
 'preparationCommand':'& "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" -B "SourceAssets/perf-review/crowd-vat/ResidentRuntime03/CadenceStudy/AngularVATPublication02/prepare_external.py" --project-root "<checkout-root>" --workspace "C:/Mikdash/Verification/<fresh-unique-folder>"',
 'recipe':['Verify exact source allowlist with verify_publication.py; missing prerequisites mean preparation unavailable, not permission to substitute assets',
 'Supply the28 exact original prerequisites in Publication01/prerequisites.json locally with lawful access. No raw asset/engine source redistribution',
 'Run only the external preparation entrypoint. It refuses existing workspace, paths outside Verification, overlap with checkout, changed historical source or changed prerequisites',
 'Copies exact20 historical pins plus manifest into external compile01-source BEFORE derivative edits; then stages19 local asset pairs in external runner/P',
 'External derivative has explicit original-project root for protected hashes/shared sentinel; project, outputs, caches and malformed fault scratch all stay outside the recipe checkout',
 'Runs12 shader-gate and20 wrapper tests offline, then pins the external derivative; no UE/helper OS launch. Snapshot historical prepare.py is never executed',
 'Review generated manifest and exact command before coordinator-only native execution. Fresh fault paths change manifest hash; never impersonate Compile02 de94 receipt',
 'Do not execute old source preparation/testing commands in the active receipt tree. No broad JSON verification exceptions'],
 'offlinePreparationEvidence':{'passedShaderGateCases':12,'passedWrapperCases':20,'stagedPackages':19,'externalManifestSha256':retry,'originalSourcePreserved':True,'nativeLaunchesByAuthor':0},
 'claims':{'sourceAnalyticalProof':True,'compile01':'failed','compile02':'pending coordinator outcome','pixels':False,'productionAcceptance':False},
 'publicationBoundary':'Exact allowlist plus itself only. Historical Native01 and Study01 remain byte-identical. Latest plan controls; no recursive folder copy.',
 'excluded':['P/**','ReviewProject/**','Content/**','Saved/**','Intermediate/**','DDC/**','DerivedDataCache/**','runs/**','fault-tests/**','all raw logs','all Verification workspaces and snapshots','uasset/umap/ubulk/uexp/png/exr/dll/exe/zip','native.lock','__pycache__'],
 'bytePolicy':'Apply publication.gitattributes.fragment exact -text entries; do not normalize frozen source bytes',
 'coordinatorRelocations':['C:/Mikdash/Verification/angular-fault-history-20261002-compile01','C:/Mikdash/Verification/angular-saved-compile01'],
 'freeze':'Compile02 runner de94 remains immutable until terminal; publication preparation does not read or change its inflight outputs'})
names=['prepare_external.py','verify_publication.py','build_publication.py','compile01-failure.json','startup-audit.json','publication-plan.json','publication.gitattributes.fragment']
paths=[ROOT/r['path'] for r in history['entries']]+[OLD/'publish-allowlist.json']+[BASE/n for n in names]
manifest=BASE/'publish-allowlist.json'
(BASE/'publication.gitattributes.fragment').write_text(''.join('"'+rel(p)+'" -text\n' for p in paths+[manifest]),encoding='utf-8')
write('publish-allowlist.json',{'version':2,'type':'source_only_with_sanitized_historical_failure_summary',
 'publishManifestItself':rel(manifest),'currentInstructions':rel(BASE/'publication-plan.json'),
 'entries':[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in paths],
 'excludedByDefault':True,'noRawLogsOrPixels':True,'noProductionClaim':True})
assert sha(NATIVE/'harness-hashes.json')==frozen
print(json.dumps({'sourceFiles':len(paths),'plusManifest':True,'historicalManifestUnchanged':True,'nativeLaunches':0}))
