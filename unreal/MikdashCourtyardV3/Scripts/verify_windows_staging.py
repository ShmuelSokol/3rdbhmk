"""Read-only check of required loose files and native container sizes. Never launch UE."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime,timezone

PROJECT=Path(__file__).resolve().parents[1]
UCAS_LIMIT=1800000000


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def verify(archive_root,receipt,project=PROJECT):
    root=Path(archive_root).resolve();receipt=Path(receipt).resolve();project=Path(project).resolve()
    if receipt.exists():raise ValueError('Receipt must not exist')
    try:receipt.relative_to(root)
    except ValueError:pass
    else:raise ValueError('Receipt must be outside archive')
    report={'status':'started','archiveRoot':str(root),'sourceProject':str(project),
            'scope':'Known loose-file presence/source-byte equality and native container sizes only; no reference, render, launch or runtime acceptance',
            'utc':datetime.now(timezone.utc).isoformat(),'errors':[],'executables':[],'looseFiles':[],'containers':[],
            'ucasLimitBytesInclusive':UCAS_LIMIT}
    try:
        if not root.is_dir():raise ValueError('Windows archive root missing')
        for relative in ('MikdashCourtyardV3.exe','MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe'):
            path=root/relative
            if not path.is_file() or path.stat().st_size==0:
                report['errors'].append('Missing/empty executable: '+relative);continue
            report['executables'].append({'path':relative,'bytes':path.stat().st_size,'sha256':sha(path)})
        for folder in ('Distribution','Localization/Mikdash'):
            source_root=project/'Content'/folder
            sources=sorted(p for p in source_root.rglob('*') if p.is_file()) if source_root.is_dir() else []
            if not sources:report['errors'].append('Source folder missing/empty: '+str(source_root))
            for source in sources:
                relative='MikdashCourtyardV3/Content/'+source.relative_to(project/'Content').as_posix()
                target=root/relative;expected=sha(source)
                row={'path':relative,'sourceSha256':expected,'sourceBytes':source.stat().st_size,'matches':False}
                if target.is_file():
                    row.update(bytes=target.stat().st_size,sha256=sha(target));row['matches']=row['sha256']==expected and row['bytes']==row['sourceBytes']
                if not row['matches']:report['errors'].append('Loose file missing/different: '+relative)
                report['looseFiles'].append(row)
        paks=root/'MikdashCourtyardV3/Content/Paks'
        def is_ucas(path):return bool(re.search(r'\.ucas(?:_s\d+)?$',path.name,re.I))
        containers=sorted(p for p in paks.iterdir() if p.is_file() and (p.suffix.lower() in ('.utoc','.pak') or is_ucas(p))) if paks.is_dir() else []
        for path in containers:
            row={'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}
            report['containers'].append(row)
            if row['bytes']==0:report['errors'].append('Empty native container: '+path.name)
            if is_ucas(path) and row['bytes']>UCAS_LIMIT:report['errors'].append('UCAS partition over limit: '+path.name)
        if not any(p.suffix.lower()=='.utoc' for p in containers):report['errors'].append('No native UTOC found')
        if not any(is_ucas(p) for p in containers):report['errors'].append('No native UCAS found')
        report['status']='passed_known_staging_files' if not report['errors'] else 'failed'
    except Exception as error:
        report['errors'].append(repr(error));report['status']='failed'
    receipt.parent.mkdir(parents=True,exist_ok=True)
    with receipt.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root',required=True,type=Path)
    parser.add_argument('--receipt',required=True,type=Path)
    args=parser.parse_args();result=verify(args.archive_root,args.receipt)
    print(json.dumps({'status':result['status'],'errors':result['errors'],'receipt':str(args.receipt)},indent=2))
    raise SystemExit(0 if result['status']=='passed_known_staging_files' else 1)
