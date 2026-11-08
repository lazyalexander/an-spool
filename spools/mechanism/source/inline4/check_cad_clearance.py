"""Independent sampled solid intersections for the first cylinder's moving joints."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parent
doc=App.openDocument(str(ROOT/'engine.FCStd'))
poses=json.loads((ROOT/'poses.json').read_text())
pairs=[('rod_1','crankshaft'),('rod_1','piston_1'),('piston_1','liner_1'),
       ('piston_1','sectioned_head'),('piston_1','intake_1'),('piston_1','exhaust_1'),
       ('intake_1','valve_guides'),('exhaust_1','valve_guides')]
names=set(p for pair in pairs for p in pair)
local={}
for name in names:
    shape=doc.getObject(name).Shape.copy()
    shape.Placement=App.Placement()
    local[name]=shape
maxima={' / '.join(pair):0. for pair in pairs}
failures=[]
for index in range(0,len(poses),12):
    placed={}
    for name in names:
        shape=local[name].copy()
        matrix=App.Matrix(*[v for row in poses[index]['transforms'][name] for v in row])
        shape.Placement=App.Placement(matrix)
        placed[name]=shape
    for a,b in pairs:
        overlap=placed[a].common(placed[b]).Volume
        key=' / '.join((a,b));maxima[key]=max(maxima[key],overlap)
        if overlap>1e-5:
            failures.append({'frame':index+1,'pair':key,'overlap_mm3':overlap})
    print('CAD_SAMPLE',index+1,flush=True)
bad=local['rod_1'].copy()
matrix=App.Matrix(*[v for row in poses[0]['transforms']['rod_1'] for v in row])
matrix.A14+=6
bad.Placement=App.Placement(matrix)
crank=local['crankshaft'].copy()
crank.Placement=App.Placement(App.Matrix(*[v for row in poses[0]['transforms']['crankshaft'] for v in row]))
negative_overlap=bad.common(crank).Volume
assert negative_overlap>1, 'Negative control failed to detect a displaced connecting rod'
report={'passed':not failures,'sample_frames':list(range(1,len(poses)+1,12)),
        'maximum_overlap_mm3':maxima,'failures':failures,
        'negative_control_rod_shift_6mm_overlap_mm3':negative_overlap,
        'inputs_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('engine.FCStd','meshes.json','poses.json')},
        'scope':'First-cylinder critical-pair CAD solid intersections at 16 poses. Other cylinders share component dimensions but are not independently boolean-tested here. Not an exhaustive assembly collision proof.'}
(ROOT/'clearance-check.json').write_text(json.dumps(report,indent=2)+'\n')
App.closeDocument(doc.Name)
if failures:
    raise SystemExit('CAD_CLEARANCE_REJECTED '+str(failures[:3]))
print('CAD_CLEARANCE_PASSED',flush=True)
