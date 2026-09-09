"""Prepare ordinary ZIPs from an already verified Windows package; never cook/upload."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

PROJECT=Path(__file__).resolve().parents[1]
LIMIT=2*1024**3
LICENSES={
 'CREDITS.txt':'Content/Distribution/CREDITS.txt',
 'ThirdPartyNotices/ATTRIBUTION-additions.txt':'SourceAssets/third-party/ATTRIBUTION-additions.txt',
 'ThirdPartyNotices/Aron-CC-BY-SA-LICENSE.txt':'SourceAssets/third-party/aron-ark-box-davidgra11-thingiverse/LICENSE.txt',
 'ThirdPartyNotices/Menorah-CC-BY-LICENSE.txt':'SourceAssets/third-party/menorah-titus-dahan-meir-printables/LICENSE.txt',
}


def within(path,root):
    try:path.relative_to(root);return True
    except ValueError:return False


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def prepare(archive_root,output_dir,version,project=PROJECT):
    root=Path(archive_root).resolve();out=Path(output_dir).resolve();project=Path(project).resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',version):raise ValueError('Unsafe version')
    if not root.is_dir() or out.exists():raise ValueError('Windows archive root must exist; output must not exist')
    if within(out,root):raise ValueError('Output cannot be inside archive root')
    if not (root/'MikdashCourtyardV3.exe').is_file() or not (root/'MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe').is_file():
        raise ValueError('Windows package root with bootstrap and child executable required')
    payload={};excluded=[]
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('Symlink/reparse source refused: '+str(path))
        if not path.is_file():continue
        relative=path.relative_to(root).as_posix();parts=[p.lower() for p in path.relative_to(root).parts]
        if path.suffix.lower()=='.pdb' or parts[:2]==['mikdashcourtyardv3','saved'] or any(p in ('logs','crashes') for p in parts):
            excluded.append(relative);continue
        if not within(path.resolve(),root):raise ValueError('Source escapes root')
        payload[relative]=path
    for relative,source in LICENSES.items():
        source=project/source
        if not source.is_file():raise ValueError('Required license missing: '+str(source))
        if relative in payload and digest(payload[relative])!=digest(source):raise ValueError('Existing root notice differs: '+relative)
        payload[relative]=source
    folded=[name.casefold() for name in payload]
    if len(set(folded))!=len(folded):raise ValueError('Case-insensitive payload collision')
    data=sorted(name for name in payload if re.search(r'\.ucas(?:_s\d+)?$',name,re.I))
    if not data:raise ValueError('No native UCAS files found')
    groups=[('App',[name for name in sorted(payload) if name not in data])]+[(f'Data{i:02d}',[name]) for i,name in enumerate(data,1)]
    rows={name:{'path':name,'bytes':path.stat().st_size,'sha256':digest(path)} for name,path in payload.items()}
    out.mkdir(parents=True,exist_ok=False)
    report={'schemaVersion':1,'status':'preparing','version':version,'payloads':list(rows.values()),'archives':[],
            'excluded':excluded,'archiveRoot':str(root),'maxArchiveBytesExclusive':LIMIT,
            'scope':'Ordinary native-file ZIPs; no joining/install executable; packaged runtime acceptance separate'}
    manifest=out/'manifest.json'
    try:
        for label,names in groups:
            name=f'Mikdash-{version}-{label}.zip';target=out/name
            with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
                for relative in names:z.write(payload[relative],relative)
            if target.stat().st_size>=LIMIT:raise ValueError('Archive exceeds exclusive 2 GiB bound: '+name)
            with zipfile.ZipFile(target) as z:
                if z.testzip() is not None:raise ValueError('CRC failure: '+name)
                for relative in names:
                    h=hashlib.sha256()
                    with z.open(relative) as stream:
                        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
                    if h.hexdigest()!=rows[relative]['sha256']:raise ValueError('Payload changed during preparation')
            report['archives'].append({'name':name,'bytes':target.stat().st_size,'sha256':digest(target),'payloads':names})
        report['status']='prepared_crc_and_payload_hashes_verified'
        (out/'SHA256SUMS.txt').write_text(''.join(a['sha256']+'  '+a['name']+'\n' for a in report['archives']),encoding='utf-8')
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc);raise
    finally:manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root',required=True,type=Path,help='New build Windows folder')
    parser.add_argument('--output-dir',required=True,type=Path,help='Must not exist')
    parser.add_argument('--version',required=True)
    args=parser.parse_args()
    print(prepare(args.archive_root,args.output_dir,args.version))
