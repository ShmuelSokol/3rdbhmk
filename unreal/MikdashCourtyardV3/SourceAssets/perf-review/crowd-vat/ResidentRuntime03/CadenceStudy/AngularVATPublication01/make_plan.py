"""Build source-only publication manifests OUTSIDE all frozen native inputs.
Never launches, stages assets, reads run output, or changes the two source studies.
"""
import hashlib,json,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[5]
STUDY=BASE.parent/'AngularVATStudy01'
NATIVE=BASE.parent/'AngularVATNative01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=lambda p:str(p.relative_to(ROOT)).replace('\\','/')
def write(name,data):
    (BASE/name).write_text(json.dumps(data,indent=2)+'\n')

def main():
    frozen=json.loads((NATIVE/'harness-hashes.json').read_text())
    assert sha(NATIVE/'harness-hashes.json')=='199bbc388482f58a437b059735815fec0fe63a764e1ad756955c26f437cf600a'
    for p,h in frozen.items():assert sha(NATIVE/p)==h,p
    inputs=json.loads((NATIVE/'inputs.json').read_text())
    generation=json.loads((STUDY/'generation.json').read_text())
    study_names=['candidate_api.txt','candidate_builder.py','controller_adapter.py','coordinator-handoff.json',
        'generate.py','generation.json','source-tests.json','test_source.py']
    native_names=['candidate_builder.py','check_and_pin.py','compile-review.json','harness-hashes.json','inputs.json',
        'native.py','offline-ready.json','owned_ue_shim.ps1','OwnedChildJob.cs','png_safe.py','pose_capture.py',
        'prepare.py','reviewer-delta.json','run_native.ps1','shader-gate-tests.json','support.ps1',
        'test_offline.ps1','test_shader_gate.py','vat-spec.json']
    prereqs={}
    def prerequisite(path,expected,role,kind):
        path=path.replace('\\','/')
        assert path not in prereqs or prereqs[path]['sha256']==expected
        prereqs[path]={'sha256':expected,'role':role,'kind':kind,'publish':False}
        assert sha(ROOT/path)==expected,path
    for path,h in generation['inputs'].items():
        prerequisite(path,h,'Regenerate frozen AngularVATStudy01 graph source','project_source')
    prerequisite('Scripts/create_crowd_vat_v2.spec.json',sha(NATIVE/'vat-spec.json'),'prepare.py spec input','project_source')
    prerequisite('Scripts/haram_threshold_png.py',sha(NATIVE/'png_safe.py'),'prepare.py sanitized export helper input','project_source')
    cloth='SourceAssets/characters-review/KohenClothExecutableV1/'
    prerequisite(cloth+'OwnedChildJob.cs',inputs['helperSha256'],'Exact OS-proven helper; not another Job implementation','project_source')
    prerequisite(cloth+'OS-JOB-INTEGRATION.json',inputs['helperProofSha256'],'Local helper OS provenance consumed by prepare.py; historical paths stay local','local_provenance')
    prerequisite(inputs['receipt'],inputs['receiptSha256'],'Exact Study13 metadata consumed by prepare.py','local_provenance')
    for package,row in inputs['files'].items():
        prerequisite(row['relative'],row['sha256'],'Local package input for staging '+package,'local_asset_never_publish')
        prereqs[row['relative']]['bytes']=row['bytes']
    write('prerequisites.json',{'version':1,'scope':'Presence/pin manifest only; these originals are NOT allowlisted payloads',
        'requirements':prereqs,'requiresLawfulLocalAssetAccess':True,'assetRedistributionAuthorized':False})
    templates=BASE/'source-templates';templates.mkdir(exist_ok=True)
    for source,dest in ((NATIVE/'P/AngularVATReview.uproject',templates/'AngularVATReview.uproject'),
                        (NATIVE/'P/Config/DefaultEngine.ini',templates/'DefaultEngine.ini')):
        shutil.copyfile(source,dest);assert sha(source)==sha(dest)
    write('publication-plan.json',{
        'status':'proposed source-only publication boundary; no publishing, commit, native launch or pinned edits performed',
        'frozenNativeManifestSha256':sha(NATIVE/'harness-hashes.json'),
        'sourceClaims':['4879 frozen generated-graph analytical assertions','12 positive shader-gate control-flow fault cases','20 wrapper filesystem/syntax/source-contract cases'],
        'nativeClaims':{'Compile01':'coordinator-owned run in progress when plan prepared; outcome intentionally not read or asserted','pixels':False,'renderedMotion':False,'temporalVelocity':False,'productionAcceptance':False},
        'existingFinishLine':'Current FINISH-LINE.md already records positive GetStatistics gate and minimal cloth checkout proof; not modified or included wholesale in this task.',
        'payload':'Exact publish-allowlist.json entries plus that manifest itself. Copy nothing else. Disabled pose draft is source only and remains inaccessible through frozen Compile-only entry.',
        'excluded':['AngularVATNative01/P/** (including all 19 Content copies)','AngularVATNative01/ReviewProject/** (failed initial staging)',
            '**/Saved/**','**/Intermediate/**','**/DerivedDataCache/**','**/DDC/**','**/Binaries/**',
            '**/runs/**','**/fault-tests/**','**/*.log','**/*.log.gz','**/*.local-export.png','**/native.lock',
            '**/__pycache__/**','**/*.uasset','**/*.umap','**/*.ubulk','**/*.uexp','**/*.png','**/*.exr','**/*.dll','**/*.exe','**/*.zip'],
        'descriptorPlacement':'Publish two P text descriptors as source-templates in this folder, never in P itself. Frozen prepare requires P absent and recreates matching descriptors.',
        'bytePolicy':'Apply exact allowlist-scoped -text entries from publication.gitattributes.fragment in the publication checkout. Do not normalize CRLF/LF or depend on core.autocrlf. Compare hashes after checkout-index/export.',
        'assetPolicy':'No licensed/unknown-licensed raw package is published. Native staging requires locally supplied originals with the exact pins and lawful access. Absent originals mean nativeEligibility=false; do not borrow another checkout silently.',
        'reproduction':[
            'Export only allowlisted files to the same project-relative paths; preserve byte identity. Add exact -text attributes before committing in the publication tree. No commit is authorized here.',
            'Run verify_plan.py --root <fresh-project-root>. It validates every allowlisted source byte and reports prerequisite availability. Missing prerequisites do not invalidate source publication, but nativeEligibility is false.',
            'For graph regeneration supply all project_source prerequisites from prerequisites.json at matching revisions. Run generate.py only in an independent disposable source checkout, then compare candidate_builder.py with generation.json outputSha256. Never regenerate the live frozen study.',
            'For native staging additionally supply all local_provenance and 19 local_asset_never_publish prerequisites exactly. Require verifier nativeEligibility=true. Use Windows UE5.8 bundled Python with -B. P must not exist.',
            'Run AngularVATNative01/prepare.py in that fresh checkout. It writes only the isolated harness: reconstructs 19 packages, P project/config, helper, spec and source copies. Verify reconstructed inputs.json and P descriptors against published manifest/template hashes. No Unreal is launched.',
            'Run test_source.py, test_shader_gate.py and test_offline.ps1 in the fresh checkout; their generated local scratch/output stays excluded. Historical offline-ready references excluded scratch and is not a substitute for this fresh verification.',
            'Only after fresh offline checks and reviewer approval run check_and_pin.py in that reproduction checkout to create its OWN native-ready manifest. Its random fault-receipt path may change offline-ready/manifest hashes; do not impersonate Compile01 revision or reuse its receipts.',
            'Any engine run remains coordinator-only under unchanged 6/4/2 guards and total deadline. Source publication or prerequisite availability does not authorize launch.'
        ],
        'prepareCommand':'& "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" -B SourceAssets/perf-review/crowd-vat/ResidentRuntime03/CadenceStudy/AngularVATNative01/prepare.py',
        'validationBoundary':'Source verify reads only enumerated allowlist/prerequisite files. Does not recurse the project, inspect running receipt/logs, copy assets, run prepare or start native processes.'})
    payload=[STUDY/n for n in study_names]+[NATIVE/n for n in native_names]
    payload += [BASE/n for n in ('make_plan.py','verify_plan.py','prerequisites.json','publication-plan.json','publication.gitattributes.fragment')]
    payload += [templates/'AngularVATReview.uproject',templates/'DefaultEngine.ini']
    attributes=''.join('/'+rel(p)+' -text\n' for p in payload+[BASE/'publish-allowlist.json'])
    (BASE/'publication.gitattributes.fragment').write_text(attributes)
    write('publish-allowlist.json',{'version':1,'type':'source_only_proposed','publishManifestItself':rel(BASE/'publish-allowlist.json'),
        'entries':[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in payload],
        'excludedByDefault':True,'noNativeEvidenceOrPixels':True})
    for p,h in frozen.items():assert sha(NATIVE/p)==h,p
    print(json.dumps({'sourceFiles':len(payload),'plusAllowlistItself':True,'prerequisites':len(prereqs),
        'localAssetsNotPublished':19,'nativePinnedFilesUnchanged':True,'published':False}))

if __name__=='__main__':main()
