"""Offline triangle-exact Mount deck cutout; no Unreal scene mutation.

Each affected original tile is replaced in the future map only, using new assets.
Retains the complete original piecewise-linear surface outside the deck polygon.
Run generate() under Python3.12 with FutureMountV1/.tools shapely2.1.2.
Native import is pending; JSON preserves vertex colors and normals, unlike OBJ.
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
BASE=ROOT/'SourceAssets/FutureMountV1'
sys.path.insert(0,str(BASE/'.tools'))
import shapely
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
SOURCE=Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\architecture-review\jerusalem-meshes.json')
TILES=Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\cloud-unreal-v3\context-review\terrain-manifest.json')
OUTPUT=BASE/'terrain-generated'
SOURCE_SHA='cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def f32(value): return struct.unpack('<f',struct.pack('<f',value))[0]
def normalize(vector):
    length=math.sqrt(sum(v*v for v in vector));assert length>.01
    return [v/length for v in vector]
def parts(geometry):
    if geometry.is_empty: return []
    if geometry.geom_type=='Polygon': return [geometry]
    return [part for child in geometry.geoms for part in parts(child)]


def generate():
    assert sha(SOURCE)==SOURCE_SHA
    assert shapely.__version__=='2.1.2'
    source=json.loads(SOURCE.read_text())['meshes'][0]
    tiles=json.loads(TILES.read_text())
    assert tiles['sourceMeshSha256']==SOURCE_SHA and len(tiles['meshes'])==256
    platform=BASE/'mount-platform.mesh.json'
    generation=json.loads((BASE/'mount-platform-generation.json').read_text())
    assert sha(platform)==generation['files'][platform.name]['sha256']
    document=json.loads(platform.read_text())
    # The currently verified platform is one polygon without holes. Refuse a new
    # topology until its ring roles are represented explicitly instead of guessing.
    assert generation['polygonComponents']==1 and generation['interiorHoleCount']==0
    assert len(document['allowedBoundaryRingsXYcm'])==1
    deck=Polygon(document['allowedBoundaryRingsXYcm'][0]);assert deck.is_valid
    position=source['positions'];normal=source['normals'];color=source['vertexColors'];indices=source['indices']
    # Reproduce the retained Blender export's float32 meter storage then native
    # centimeter storage. Native comparison remains required before replacement.
    vertices=[];normals=[];colors=[]
    for index in range(len(position)//3):
        x,y,z=position[3*index:3*index+3]
        vertices.append([f32(f32((x+17.509700315687695)*.5)*100),
            f32(-f32(-(z-.5513496449385334)*.5)*100),f32(f32(y*.5)*100)])
        nx,ny,nz=normal[3*index:3*index+3]
        normals.append(normalize([nx,nz,ny]));colors.append(color[3*index:3*index+3])
    OUTPUT.mkdir(exist_ok=True)
    report=dict(status='offline_clipped_tile_geometry_verified_native_pending',sourceSha256=SOURCE_SHA,
        terrainManifestSha256=sha(TILES),platformSha256=sha(platform),generatorSha256=sha(Path(__file__)),
        operation='Remove terrain only within exact verified platform footprint, including buried terrain. Keep original surface everywhere outside; no rectangle flattening.',
        outputNamespace='/Game/MikdashV3/FutureMountV1/Terrain',map='/Game/MikdashV3/FutureMountV1/L_FutureMount',
        coordinateConvention='UE centimeters east,south,up; anchor baked once; top-facing CCW mathematical winding',
        uvPolicy='Source terrain had no UV channels. JSON colors/normals are authoritative; optional diagnostic OBJ is not a native color-preserving interchange.',
        tiles=[],unaffectedOriginalTiles=[],checks={},limitations=[
        'Offline geometry only. Native import, component replacement, collisions, walking and visual acceptance remain pending.',
        'Only affected tiles may be replaced in the future map. Original shared terrain assets and Courtyard must remain unchanged.',
        'Boundary comes from inferred Mount/platform design with Western Wall/plaza protection; not a surveyed future site.',
        'The cut removes original ground under the deck as well as protrusions; platform collision must be validated before adoption.',
        'Source floats reproduce the original export convention, but native source-mesh coordinate comparison is still required.',
        'Road ribbons, walls, stairs and other objects can protrude separately; they are not edited here.'])
    total_cut=0.;seams={};max_seam=0.
    for tile in tiles['meshes']:
        tids=tile['triangleSourceIndices']
        original_polys=[];kept_polys=[];out_vertices=[];out_normals=[];out_colors=[];out_faces=[];origin_tids=[]
        touched=0;unchanged=0;cut_area=0.;max_weight_error=0.
        bounds=tile['expectedBoundsUnrealCm']
        if not shapely.box(bounds['min'][0],bounds['min'][1],bounds['max'][0],bounds['max'][1]).intersects(deck):
            report['unaffectedOriginalTiles'].append(tile['assetName']);continue
        for tid in tids:
            ids=indices[3*tid:3*tid+3]
            triangle=[vertices[i] for i in ids]
            poly=Polygon([p[:2] for p in triangle]);assert poly.is_valid and poly.area>0
            original_polys.append(poly)
            overlap=poly.intersection(deck).area
            if overlap <= 1e-9:
                unchanged+=1;pieces=[orient(poly,sign=1)]
            else:
                touched+=1;cut_area+=overlap
                remaining=poly.difference(deck)
                pieces=[]
                for polygon in parts(remaining):
                    if polygon.area>1e-8:
                        pieces.extend(orient(t,sign=1) for t in shapely.constrained_delaunay_triangles(polygon).geoms)
                union=shapely.union_all(pieces)
                assert union.symmetric_difference(remaining).area<.01
            a,b,c=triangle
            denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            for piece in pieces:
                assert piece.area>1e-8
                kept_polys.append(piece)
                face=[]
                for x,y in list(piece.exterior.coords)[:3]:
                    exact=next((i for i in range(3) if triangle[i][0]==x and triangle[i][1]==y),None)
                    if exact is not None:
                        point=list(triangle[exact]);n=list(normals[ids[exact]]);rgb=list(colors[ids[exact]])
                    else:
                        w0=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
                        w1=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
                        weights=[w0,w1,1-w0-w1]
                        weight_error=max(0,-min(weights),max(weights)-1);assert weight_error<1e-8
                        max_weight_error=max(max_weight_error,weight_error)
                        point=[x,y,sum(weights[i]*triangle[i][2] for i in range(3))]
                        n=normalize([sum(weights[i]*normals[ids[i]][axis] for i in range(3)) for axis in range(3)])
                        rgb=[sum(weights[i]*colors[ids[i]][axis] for i in range(3)) for axis in range(3)]
                    key=(round(x,6),round(y,6))
                    if key in seams:
                        previous=seams[key]
                        delta=max(abs(point[2]-previous[0]),max(abs(rgb[i]-previous[1][i]) for i in range(3)))
                        max_seam=max(max_seam,delta);assert delta<1e-5
                    else:seams[key]=(point[2],rgb)
                    face.append(len(out_vertices));out_vertices.append(point);out_normals.append(n);out_colors.append(rgb)
                out_faces.append(face);origin_tids.append(tid)
        if not touched:
            report['unaffectedOriginalTiles'].append(tile['assetName']);continue
        original_union=shapely.union_all(original_polys);retained_union=shapely.union_all(kept_polys)
        expected=original_union.difference(deck)
        error=retained_union.symmetric_difference(expected).area
        intrusion=retained_union.intersection(deck).area
        overlap=sum(p.area for p in kept_polys)-retained_union.area
        assert error<.1 and intrusion<.1 and abs(overlap)<.1
        assert abs(cut_area-original_union.intersection(deck).area)<.1
        for face in out_faces:
            a,b,c=[out_vertices[i] for i in face]
            assert (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])>1e-8
        payload=dict(version=1,units='centimeters',axes='east,south,up',anchorAlreadyApplied=True,
            originalAssetName=tile['assetName'],assetName=tile['assetName']+'_FutureMountCut',
            vertices=out_vertices,normals=out_normals,linearVertexColors=out_colors,uvChannels=[],
            triangles=out_faces,triangleSourceIndices=origin_tids,sourceOriginalTriangles=tids,
            material='Reuse original terrain VertexColor RGB material; no material edit')
        path=OUTPUT/(tile['assetName']+'_FutureMountCut.mesh.json')
        path.write_text(json.dumps(payload,separators=(',',':'))+'\n',encoding='utf-8')
        report['tiles'].append(dict(originalAssetName=tile['assetName'],replacementAssetName=payload['assetName'],
            geometryFile=path.name,sha256=sha(path),sourceTriangles=len(tids),untouchedTrianglesCopied=unchanged,
            clippedOrRemovedSourceTriangles=touched,outputTriangles=len(out_faces),removedAreaCm2=cut_area,
            outsideSurfaceSymmetricDifferenceCm2=error,insideDeckTerrainAreaCm2=intrusion,
            triangleOverlapCm2=overlap,maxBarycentricWeightError=max_weight_error))
        total_cut+=cut_area
    assert len(report['tiles'])==4 and len(report['unaffectedOriginalTiles'])==252
    assert abs(total_cut-deck.area)<.1
    report['checks']=dict(removedAreaCm2=total_cut,deckAreaCm2=deck.area,areaErrorCm2=abs(total_cut-deck.area),
        maxSharedVertexHeightCmOrLinearColorError=max_seam,affectedTiles=4,unaffectedTiles=252,
        outsideSourcePiecewiseLinearSurfacePreserved=True,protectedAreasOutsideDeckPreserved=True)
    (OUTPUT/'terrain-cut-manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    result=generate();print(json.dumps(result['checks'],indent=2))
