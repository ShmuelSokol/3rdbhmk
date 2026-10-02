"""Bounded offline staging. New harness folder only; no Unreal execution."""
import hashlib,json,re,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[5]
PROJECT=BASE/'P'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not PROJECT.exists(),'Fresh staging required'
    receipt=ROOT/'SourceAssets/perf-review/crowd-vat/ResidentStudy13/Cast/Man_Elder/native-20260919T133627785098Z.json'
    source=json.loads(receipt.read_text());v=source['variants'][0]
    allowed=('/Game/MikdashV3/Runtime/CrowdResidentStudy12/Cast/Man_Elder/',
             '/Game/MikdashV3/Runtime/CrowdResidentStudy13/Cast/Man_Elder/',
             '/Game/MikdashV3/Characters/ResidentV4/Textures/')
    seeds=[v['mesh'].split('.')[0]]
    for p in v['materialInstances'].values():
        seeds += [x.split('.')[0] for x in p.values() if isinstance(x,str) and x.startswith('/Game/')]
    seeds += ['/Game/MikdashV3/Characters/ResidentV4/Textures/T_RV4_SlubMottle',
              '/Game/MikdashV3/Characters/ResidentV4/Textures/T_RV4_WeaveN']
    files={};excluded=set();pending=list(seeds);total=0
    while pending:
        package=pending.pop()
        if package in files:continue
        assert len(files)<48,'Closure exceeded bounded package count'
        assert package.startswith(allowed) and '/Source/' not in package,package
        path=ROOT/('Content/'+package[6:]+'.uasset')
        assert path.stat().st_size<128*1024**2
        data=path.read_bytes();total+=len(data);assert total<512*1024**2
        names=set(m.decode('ascii').split('.')[0] for m in re.findall(rb'/Game/[A-Za-z0-9_./]+',data))
        # Conservative string-reference closure, not a hard-dependency claim.
        # Native AssetRegistry hard/soft package dependency gate runs BEFORE loads.
        refs=[]
        for dep in sorted(names):
            depfile=ROOT/('Content/'+dep[6:]+'.uasset')
            if dep.startswith(allowed) and '/Source/' not in dep and depfile.is_file():
                refs.append(dep);pending.append(dep)
            elif dep!=package:excluded.add(dep)
        files[package]={'relative':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'conservativeReferences':refs}
    PROJECT.mkdir()
    for package,row in files.items():
        dst=PROJECT/row['relative'];dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/row['relative'],dst);assert sha(dst)==row['sha256']
    (PROJECT/'AngularVATReview.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','DisableEnginePluginsByDefault':True,
        'Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]},indent=2)+'\n')
    cfg=PROJECT/'Config';cfg.mkdir()
    (cfg/'DefaultEngine.ini').write_text('[/Script/EngineSettings.GameMapsSettings]\nEditorStartupMap=/Engine/Maps/Entry\nGameDefaultMap=/Engine/Maps/Entry\n[/Script/Engine.RendererSettings]\nr.DynamicGlobalIlluminationMethod=0\nr.ReflectionMethod=0\nr.Shadow.Virtual.Enable=0\nr.VelocityOutputPass=1\nr.Velocity.EnableVertexDeformation=1\n')
    frozen=BASE.parent/'AngularVATStudy01/candidate_builder.py'
    shutil.copyfile(frozen,BASE/'candidate_builder.py')
    shutil.copyfile(ROOT/'Scripts/create_crowd_vat_v2.spec.json',BASE/'vat-spec.json')
    shutil.copyfile(ROOT/'Scripts/haram_threshold_png.py',BASE/'png_safe.py')
    cloth=ROOT/'SourceAssets/characters-review/KohenClothExecutableV1'
    proof=json.loads((cloth/'OS-JOB-INTEGRATION.json').read_text())
    expected=proof['actualOS']['helperHash'].lower()
    assert proof['actualOS']['passed'] and sha(cloth/'OwnedChildJob.cs')==expected
    shutil.copyfile(cloth/'OwnedChildJob.cs',BASE/'OwnedChildJob.cs')
    manifest={'mesh':v['mesh'],'slots':v['slots'],'parameters':v['materialInstances'],
        'files':files,'totalBytes':total,'excludedStringReferences':sorted(excluded),
        'closureStatus':'bounded conservative offline closure; native registry validation required before asset loads',
        'receipt':str(receipt.relative_to(ROOT)).replace('\\','/'),'receiptSha256':sha(receipt),
        'frozenBuilderSha256':sha(frozen),'helperSha256':expected,'helperProofSha256':sha(cloth/'OS-JOB-INTEGRATION.json'),
        'noProjectModules':True,'noProjectPlugin':True,'requiresUBT':False,
        'engineOnlyPlugins':['PythonScriptPlugin','EditorScriptingUtilities']}
    (BASE/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'packages':len(files),'bytes':total,'excludedMetadataReferences':len(excluded),'requiresUBT':False}))

if __name__=='__main__':main()
