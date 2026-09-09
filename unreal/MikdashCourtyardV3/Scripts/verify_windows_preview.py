"""Verify ordinary preview ZIPs and extract to a fresh folder; no game launch.
HTTPS mode is publisher verification, not a customer installer. Downloads stream
with size/hash bounds; --manifest-sha256 pins the remotely supplied manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import stat
import urllib.parse
import urllib.request
import zipfile

LIMIT=2*1024**3


def within(path,root):
    try:path.relative_to(root);return True
    except ValueError:return False


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def safe(name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or any(c in name for c in '\\:<>"|?*') or any(ord(c)<32 for c in name) or any(x in ('','..','.') for x in name.split('/')):
        raise ValueError('Unsafe relative path: '+name)
    # Windows aliases, alternate streams and trailing-dot/space normalization.
    for part in p.parts:
        if part.rstrip(' .')!=part or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',part):raise ValueError('Unsafe Windows path')
    return p


def fetch(url,path,expected_bytes,expected_hash):
    if urllib.parse.urlsplit(url).scheme!='https':raise ValueError('Only HTTPS downloads allowed')
    h=hashlib.sha256();count=0
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mikdash-release-verification'}),timeout=60) as incoming,path.open('xb') as output:
        if incoming.status!=200 or urllib.parse.urlsplit(incoming.geturl()).scheme!='https':raise ValueError('Unexpected download response')
        for block in iter(lambda:incoming.read(1024*1024),b''):
            count+=len(block)
            if count>expected_bytes:raise ValueError('Download exceeds declared size')
            h.update(block);output.write(block)
    if count!=expected_bytes or h.hexdigest()!=expected_hash:raise ValueError('Download size/hash differs')


def verify(manifest_location,destination,receipt,original=None,manifest_sha256=None,download_dir=None):
    destination=Path(destination).resolve();receipt=Path(receipt).resolve()
    if destination.exists() or receipt.exists():raise ValueError('Destination and receipt must not exist')
    if within(receipt,destination):raise ValueError('Receipt must be outside extracted payload')
    remote=str(manifest_location).startswith('https://')
    if remote:
        if not re.fullmatch('[0-9a-f]{64}',manifest_sha256 or ''):raise ValueError('Remote verification requires pinned manifest SHA256')
        folder=Path(download_dir).resolve() if download_dir else None
        if folder is None or folder.exists():raise ValueError('Fresh --download-dir required')
        with urllib.request.urlopen(str(manifest_location),timeout=60) as stream:
            if stream.status!=200 or urllib.parse.urlsplit(stream.geturl()).scheme!='https':raise ValueError('Manifest response refused')
            raw=stream.read(4*1024*1024+1)
        if len(raw)>4*1024*1024 or hashlib.sha256(raw).hexdigest()!=manifest_sha256:raise ValueError('Manifest size/hash differs')
    else:
        manifest_path=Path(manifest_location).resolve();folder=manifest_path.parent;raw=manifest_path.read_bytes()
        if manifest_sha256 and hashlib.sha256(raw).hexdigest()!=manifest_sha256:raise ValueError('Manifest hash differs')
    manifest=json.loads(raw)
    if manifest.get('schemaVersion')!=1 or manifest.get('status')!='prepared_crc_and_payload_hashes_verified':raise ValueError('Successful supported manifest required')
    payloads=manifest['payloads'];archives=manifest['archives'];all_names=[]
    if not payloads or not archives or len(archives)>64:raise ValueError('Empty or excessive archive manifest')
    if sum(a['bytes'] for a in archives)>64*1024**3:raise ValueError('Download total exceeds 64 GiB verification bound')
    for row in payloads:
        safe(row['path'])
        if type(row['bytes']) is not int or row['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('Invalid payload size/hash')
    rows={r['path']:r for r in payloads}
    if len(rows)!=len(payloads) or len({n.casefold() for n in rows})!=len(rows):raise ValueError('Duplicate payload paths')
    archive_names=set()
    for a in archives:
        if len(safe(a['name']).parts)!=1 or a['name'].casefold() in archive_names:raise ValueError('Duplicate/unsafe archive filename')
        archive_names.add(a['name'].casefold())
        if type(a['bytes']) is not int or not 0<a['bytes']<LIMIT or not re.fullmatch('[0-9a-f]{64}',a['sha256']):raise ValueError('Invalid archive size/hash')
        all_names.extend(a['payloads'])
    if len(all_names)!=len(set(all_names)) or set(all_names)!=set(rows):raise ValueError('Archive inventory does not exactly partition payloads')
    if remote:
        folder.mkdir(parents=True,exist_ok=False)
        (folder/'manifest.json').write_bytes(raw)
        for a in archives:fetch(urllib.parse.urljoin(str(manifest_location),a['name']),folder/a['name'],a['bytes'],a['sha256'])
    # Preflight all archives before extracting any bytes.
    seen=set()
    for a in archives:
        path=folder/a['name']
        if path.stat().st_size!=a['bytes'] or digest(path)!=a['sha256']:raise ValueError('Archive bytes differ')
        with zipfile.ZipFile(path) as z:
            if set(z.namelist())!=set(a['payloads']) or len(z.infolist())!=len(a['payloads']):raise ValueError('ZIP inventory differs')
            for entry in z.infolist():
                safe(entry.filename)
                if entry.is_dir() or stat.S_ISLNK(entry.external_attr>>16) or entry.filename.casefold() in seen:raise ValueError('ZIP duplicate/link/directory refused')
                seen.add(entry.filename.casefold())
                if entry.file_size!=rows[entry.filename]['bytes']:raise ValueError('ZIP payload size differs')
    destination.mkdir(parents=True,exist_ok=False)
    for a in archives:
        with zipfile.ZipFile(folder/a['name']) as z:
            for entry in z.infolist():
                target=destination/entry.filename;target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256();count=0
                with z.open(entry) as source,target.open('xb') as output:
                    for block in iter(lambda:source.read(1024*1024),b''):
                        count+=len(block)
                        if count>rows[entry.filename]['bytes']:raise ValueError('Decompressed data exceeds declared size')
                        h.update(block);output.write(block)
                if count!=rows[entry.filename]['bytes'] or h.hexdigest()!=rows[entry.filename]['sha256']:raise ValueError('Extracted payload/CRC verification failed')
    matched=0
    if original:
        root=Path(original).resolve()
        if not root.is_dir():raise ValueError('Original package root missing')
        for path in root.rglob('*'):
            if not path.is_file():continue
            rel=path.relative_to(root).as_posix();parts=[p.lower() for p in path.relative_to(root).parts]
            if path.suffix.lower()=='.pdb' or parts[:2]==['mikdashcourtyardv3','saved'] or any(p in ('logs','crashes') for p in parts):continue
            if rel not in rows or digest(path)!=digest(destination/rel):raise ValueError('Original package differs: '+rel)
            matched+=1
        if not matched:raise ValueError('No original files verified')
    result={'status':'passed','manifestSha256':hashlib.sha256(raw).hexdigest(),'payloadFiles':len(rows),
            'archives':archives,'originalFilesMatched':matched,'remoteDownloads':remote,'gameLaunched':False,
            'scope':'Complete ZIP CRC, archive/payload hashes and exact extraction inventory; runtime acceptance separate'}
    receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--destination',required=True,type=Path)
    p.add_argument('--receipt',required=True,type=Path);p.add_argument('--original',type=Path)
    p.add_argument('--manifest-sha256');p.add_argument('--download-dir',type=Path)
    a=p.parse_args();print(json.dumps(verify(a.manifest,a.destination,a.receipt,a.original,a.manifest_sha256,a.download_dir),indent=2))
