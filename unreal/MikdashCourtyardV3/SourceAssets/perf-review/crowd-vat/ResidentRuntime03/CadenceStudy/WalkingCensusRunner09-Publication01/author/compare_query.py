"""Exact Fraction audit of actual ABI-emitted query boxes against pinned profiles."""
import csv,json,math,re,sys,hashlib
from fractions import Fraction as Q
from pathlib import Path
root=Path(__file__).resolve().parent
profiles=[]
for line in (root/'MeasuredProfiles.h').read_text().splitlines():
    if re.match(r'\s*\{"(?:Man_Elder|Woman_Young)"',line):
        profiles.append([float(x.strip()) for x in line.strip().strip('{},').split(',')[1:]])
rows=list(csv.reader(Path(sys.argv[1]).open()));assert len(rows)==len(profiles)==6
checks=0
for row in rows:
    i=int(row[0]);scale,radius,minz,maxz=profiles[i];values=list(map(float,row[1:]))
    assert values[:3]==[radius,minz,maxz];checks+=1
    rad=math.ceil(radius);origin=list(map(Q,[10000.1,-43000.96,.5]))
    expected=[(origin[0]+Q(1,10)-rad,origin[0]+Q(201,10)+rad),
              (origin[1]-rad,origin[1]+rad),(origin[2]+Q(minz),origin[2]+Q(maxz))]
    for j,(lo,hi) in enumerate(expected):
        actualLo,actualHi=map(Q,values[3+2*j:5+2*j])
        assert actualLo<=lo<=hi<=actualHi,(i,j);checks+=1
print(json.dumps({'checks':checks,'failures':0,'profiles':6,
 'csvSha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()},indent=2))
