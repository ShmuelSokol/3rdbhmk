"""Offline complete-clip coverage, saved-texture and sampled-pose normal checks."""
from pathlib import Path
import argparse,gzip,hashlib,json
import numpy as np
from compare_resident_vat_pose import png16

def run(folder):
    folder=Path(folder)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    reports=[(p,json.loads(p.read_text())) for p in folder.glob('native-*.json')]
    build_path,build=next((p,r) for p,r in reports if r['status']=='built-needs-fresh-readback-and-render')
    fresh_path,fresh=next((p,r) for p,r in reports if r['status']=='verified-fresh-candidate-not-rendered')
    assert build['protectedUnchanged'] and fresh['protectedUnchanged'] and fresh['buildReceipt']==build_path.name
    output=folder/'complete-normal-textures.json';assert not output.exists()
    root=Path(__file__).resolve().parents[1]
    for name,h in build['assets'].items():assert sha(root/name)==h
    source_receipt=root/build['sourceStudy']
    assert sha(source_receipt)==build['sourceStudySha256']
    old_folder=source_receipt.parent
    assert old_folder.name==folder.name
    audit=next(r for p in old_folder.glob('normals-*.json') if (r:=json.loads(p.read_text())).get('status')=='audited-reference-normals')
    static_file=next(old_folder/n for n in audit['files'] if n.endswith('-static.json.gz'))
    assert sha(static_file)==audit['files'][static_file.name]
    with gzip.open(static_file,'rt',encoding='utf-8') as stream:rows=json.load(stream)['rows']
    old_layout=audit['walkBake']
    xy=np.floor(np.array([r[4] for r in rows])*np.array([old_layout['width'],old_layout['height']])).astype(int)
    assert len(set(map(tuple,xy)))==build['correspondence']['uniqueRows']
    results={};walk=None
    for clip in ('walk','idle'):
        layout=build['variants'][0][clip+'Bake'];info=build['normalClips'][clip]
        source_file=folder/info['sourcePNG'];assert sha(source_file)==build['files'][source_file.name]
        saved_file=next(folder/n for n in fresh['files'] if n.endswith('-'+clip+'.png'));assert sha(saved_file)==fresh['files'][saved_file.name]
        source=png16(source_file);saved=png16(saved_file)
        assert np.array_equal(source,saved),'Saved native normal texture pixels changed'
        assert source.shape==(layout['height'],layout['width'],4)
        assert layout['width']==old_layout['width'] and layout['rowsPerFrame']==old_layout['rowsPerFrame']
        assert layout['height']==layout['frames']*layout['rowsPerFrame']
        assert [f['frame'] for f in info['frames']]==list(range(layout['frames']))
        encoded=np.rint(source*65535).astype('>u2');max_unit_error=0.
        for frame,f in enumerate(info['frames']):
            block=encoded[frame*layout['rowsPerFrame']:(frame+1)*layout['rowsPerFrame']]
            assert hashlib.sha256(block.tobytes()).hexdigest()==f['rgba16BigEndianSha256']
            assert f['writtenTexels']==len(rows) and f['timeSeconds']==frame/layout['sampleRateHz']
            values=source[frame*layout['rowsPerFrame']+xy[:,1],xy[:,0],:3]*2.-1.
            error=float(np.max(np.abs(np.linalg.norm(values,axis=1)-1.)))
            assert error<3e-5;max_unit_error=max(max_unit_error,error)
        assert not np.any(encoded[:,:,3])
        results[clip]=dict(frames=layout['frames'],texelsPerFrame=len(rows),savedPixelsExact=True,allFrameHashesVerified=True,maximumUnitLengthError=max_unit_error)
        if clip=='walk':walk=source
    pose_path=next(p for p in old_folder.glob('posed-normals-*.json') if json.loads(p.read_text()).get('status')=='exported-posed-normals')
    pose=json.loads(pose_path.read_text());samples=[]
    for frame in pose['poses']:
        p=old_folder/frame['file'];assert sha(p)==pose['files'][p.name]
        with gzip.open(p,'rt',encoding='utf-8') as stream:posed=json.load(stream)['rows']
        uv=np.array([r[2] for r in posed]);pixels=np.floor(uv*np.array([old_layout['width'],old_layout['height']])).astype(int)
        expected=np.array([r[4] for r in posed]);expected/=np.linalg.norm(expected,axis=1)[:,None]
        desired=np.rint((expected+1.)*.5*65535).astype(int)
        actual=np.rint(walk[frame['frame']*old_layout['rowsPerFrame']+pixels[:,1],pixels[:,0],:3]*65535).astype(int)
        difference=int(np.max(np.abs(desired-actual)))
        decoded=actual.astype(float)/65535.*2.-1.;decoded/=np.linalg.norm(decoded,axis=1)[:,None]
        angles=np.degrees(np.arccos(np.clip(np.sum(decoded*expected,axis=1),-1,1)))
        # Separate pose evaluations need not yield bit-identical first-frame
        # normals. Bound direction error explicitly; saved PNG pixels above
        # still require exact equality with the complete bake.
        maximum_angle=float(np.max(angles));assert maximum_angle<.02
        samples.append(dict(frame=frame['frame'],comparedRows=len(posed),maximumUnsigned16Difference=difference,maximumNormalAngleDegrees=maximum_angle,maximumAllowedDegrees=.02))
    report=dict(status='verified-complete-normal-textures',scope='Complete72 walk/192 idle frame coverage and exact saved texture readback; four independent walk pose exports. Not idle GPU/transition or runtime acceptance.',build=build_path.name,buildSha256=sha(build_path),fresh=fresh_path.name,freshSha256=sha(fresh_path),clips=results,independentWalkPoseComparisons=samples)
    output.write_text(json.dumps(report,indent=2)+'\n');print(report)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder');run(parser.parse_args().folder)
