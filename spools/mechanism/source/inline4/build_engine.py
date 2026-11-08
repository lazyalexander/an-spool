"""Editable FreeCAD inline-four cutaway with checked prescribed kinematics.

An educational assembly, not a production engine or thermodynamic simulation.
All dimensions are millimetres. The crank and cam axes run along Y.
"""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import MeshPart

ROOT=Path(__file__).resolve().parent
PI=math.pi
R,L,CZ=30.,100.,65.
YS=(-135.,-45.,45.,135.)
FIRE=(0.,3*PI,PI,2*PI)  # 1-3-4-2, measured from cylinder 1 firing TDC.
HEAD,CAMZ,BASE,LIFT=225.,292.,30.,6.
FRAMES=192
V=App.Vector

def save(name,data):
    (ROOT/name).write_text(json.dumps(data,indent=2)+'\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def box(x,y,z,dx,dy,dz):
    return Part.makeBox(dx,dy,dz,V(x,y,z))

def cyl(radius,length,point=(0,0,0),axis=(0,0,1)):
    return Part.makeCylinder(radius,length,V(*point),V(*axis))

def union(*items):
    return items[0].multiFuse(list(items[1:])).removeSplitter() if len(items)>1 else items[0]

def tube_y(x,z,y0,y1,outer,inner):
    return cyl(outer,y1-y0,(x,y0,z),(0,1,0)).cut(cyl(inner,y1-y0,(x,y0,z),(0,1,0)))

def tube_z(radius,inner,z,length):
    return cyl(radius,length,(0,0,z)).cut(cyl(inner,length,(0,0,z)))

def move(shape,x=0,y=0,z=0):
    result=shape.copy(); result.translate(V(x,y,z)); return result

def mat(x=0,y=0,z=0,angle=0):
    co,si=math.cos(angle),math.sin(angle)
    return [[co,0,si,x],[0,1,0,y],[-si,0,co,z],[0,0,0,1]]

def valve_lift(q,kind):
    # 240 crank-degree opening windows; small overlap at gas-exchange TDC.
    start=(.75 if kind=='exhaust' else 23/12)*PI
    width=4*PI/3
    t=(q-start)%(4*PI)
    if t>=width:
        return 0.,0.,0.
    a=2*PI*t/width
    return (LIFT*(1-math.cos(a))/2,
            LIFT*PI/width*math.sin(a),
            2*LIFT*PI*PI/(width*width)*math.cos(a))

def cam_outline(offset,kind):
    points=[]
    convex=[]
    for i in range(720):
        a=2*PI*i/720
        lift,d1,d2=valve_lift(2*(a+PI/2)-offset,kind)
        h,dh=BASE+lift,2*d1
        points.append((h*math.cos(a)-dh*math.sin(a),h*math.sin(a)+dh*math.cos(a)))
        convex.append(h+4*d2)
    assert min(convex)>0, 'Flat-follower cam envelope would undercut'
    return points,min(convex)

def extrude_profile(points,y0,width):
    wire=Part.makePolygon([V(x,y0,z) for x,z in points]+[V(points[0][0],y0,points[0][1])])
    return Part.Face(wire).extrude(V(0,width,0))

parts={}; materials={}; static={}; cam_profiles={}
def add(name,shape,material='steel',placement=None):
    assert shape.isValid() and not shape.isNull(), name
    parts[name]=shape
    materials[name]=material
    if placement is not None:
        static[name]=placement

add('display_base',box(-70,-245,0,140,490,15),'iron',mat())

# Rear half of the block and liner shells are intentional display sections.
block=box(0,-190,120,40,380,105)
for y in YS:
    block=block.cut(cyl(29.3,110,(0,y,118)))
add('sectioned_block',block,'iron',mat())
for i,y in enumerate(YS):
    liner=move(tube_z(29,25.6,120,105),y=y)
    liner=liner.cut(box(-35,y-35,115,35,70,115))
    add(f'liner_{i+1}',liner,'steel',mat())

# Journals leave the rod planes open; no shaft runs through a rod sweep.
crank=[]
limits=[-225]+[v for y in YS for v in (y-10,y+10)]+[230]
for lo,hi in zip(limits[::2],limits[1::2]):
    crank.append(cyl(8,hi-lo,(0,lo,0),(0,1,0)))
for i,y in enumerate(YS):
    sign=1 if i in (0,3) else -1
    pinz=sign*R
    crank.append(cyl(6,22,(0,y-11,pinz),(0,1,0)))
    for yy in (y-17,y+10):
        web=union(cyl(11,7,(0,yy,0),(0,1,0)),
                  cyl(10,7,(0,yy,pinz),(0,1,0)),
                  box(-9,yy,min(0,pinz),18,7,abs(pinz)),
                  cyl(17,7,(0,yy,-sign*14),(0,1,0)))
        crank.append(web)
add('crankshaft',union(*crank),'red')
add('flywheel',tube_y(0,0,204,215,45,8.2),'brass')
add('crank_pulley',tube_y(0,0,-219,-211,11.25,8.2),'steel')

bearings=[]
for y in (-180,-90,0,90,180):
    boss=tube_y(0,CZ,y-5,y+5,13,8.4)
    bearings += [boss,box(-9,y-5,15,18,10,CZ-27)]
add('main_bearings',union(*bearings),'iron',mat())

piston=cyl(25,35,(0,0,-15)).cut(cyl(21.5,30,(0,0,-15)))
piston=union(piston,cyl(4,48,(0,-24,0),(0,1,0)))
for zz in (11,16):
    piston=piston.cut(tube_z(26,24.1,zz,1.4))
rings=union(*(tube_z(25.2,24.15,zz+.2,1) for zz in (11,16)))
rod=union(tube_y(0,0,-6,6,12,6.3),tube_y(0,L,-5,5,8,4.3),box(-5,-4,9,10,8,L-16))
# Reopen both bores after union to exclude bridge intrusions.
rod=rod.cut(cyl(6.3,14,(0,-7,0),(0,1,0))).cut(cyl(4.3,14,(0,-7,L),(0,1,0)))
for i,y in enumerate(YS):
    add(f'piston_{i+1}',piston,'steel')
    add(f'rings_{i+1}',rings,'brass')
    add(f'rod_{i+1}',rod,'steel')

# Eight vertical valves with flat followers. Ideal return force is not drawn.
valve=union(cyl(6,2),cyl(2,34,(0,0,2)),box(-14,-5,34,28,10,3))
cam=[cyl(5,450,(0,-225,0),(0,1,0))]
curvatures=[]
for i,y in enumerate(YS):
    for kind,dy in (('intake',-12),('exhaust',12)):
        name=f'{kind}_{i+1}'
        add(name,valve,'steel' if kind=='intake' else 'red')
        outline,curvature=cam_outline(FIRE[i],kind)
        cam_profiles[name]=outline
        curvatures.append(curvature)
        cam.append(extrude_profile(outline,y+dy-4,8))
    plug=union(cyl(3,17,(12,y,230)),cyl(4,5,(12,y,242)))
    add(f'spark_plug_{i+1}',plug,'brass',mat())
add('camshaft',union(*cam),'brass')
add('cam_pulley',tube_y(0,0,-219,-211,23.25,5.2),'brass')

head=box(0,-190,225,34,380,9)
for y in YS:
    for dy in (-12,12):
        head=head.cut(cyl(6.4,12,(0,y+dy,224)))
add('sectioned_head',head,'iron',mat())
guides=[]
for y in YS:
    for dy in (-12,12):
        guide=move(tube_z(5,2.4,244,7),y=y+dy)
        guides.append(guide)
    guides.append(box(4,y-19,245,30,38,5))
add('valve_guides',union(*guides),'iron',mat())
cam_support=[]
for y in (-180,-90,0,90,180):
    cam_support += [tube_y(0,CAMZ,y-4,y+4,8,5.3),
                    box(31,y-4,234,7,8,72),box(0,y-4,299,38,8,7)]
add('cam_bearings',union(*cam_support),'iron',mat())

# Uniform open timing belt: its occupied shape is invariant while circulating.
d=CAMZ-CZ; small,big=12.,24.; beta=math.asin((big-small)/d)
path=[]
for i in range(181):
    a=-beta+(PI+2*beta)*i/180
    path.append((big*math.cos(a),CAMZ+big*math.sin(a)))
for i in range(181):
    a=PI+beta+(PI-2*beta)*i/180
    path.append((small*math.cos(a),CZ+small*math.sin(a)))
outer=[];inner=[]
for i,(x,z) in enumerate(path):
    p=path[(i-1)%len(path)];n=path[(i+1)%len(path)]
    tx,tz=n[0]-p[0],n[1]-p[1];length=math.hypot(tx,tz)
    nx,nz=tz/length,-tx/length
    outer.append((x+.75*nx,z+.75*nz));inner.append((x-.75*nx,z-.75*nz))
def face_xz(points):
    return Part.Face(Part.makePolygon([V(x,-217,z) for x,z in points]+[V(points[0][0],-217,points[0][1])]))
belt=face_xz(outer).cut(face_xz(inner)).extrude(V(0,4,0))
add('timing_belt',belt,'iron',mat())

def frame(theta):
    transforms=dict(static); cylinders=[]
    transforms['crankshaft']=mat(z=CZ,angle=theta)
    transforms['flywheel']=mat(z=CZ,angle=theta)
    transforms['crank_pulley']=mat(z=CZ,angle=theta)
    transforms['camshaft']=mat(z=CAMZ,angle=theta/2)
    transforms['cam_pulley']=mat(z=CAMZ,angle=theta/2)
    for i,y in enumerate(YS):
        a=theta-FIRE[i]
        x=R*math.sin(a); z=CZ+R*math.cos(a)
        pz=z+math.sqrt(L*L-x*x)
        transforms[f'piston_{i+1}']=mat(y=y,z=pz)
        transforms[f'rings_{i+1}']=mat(y=y,z=pz)
        transforms[f'rod_{i+1}']=mat(x,y,z,math.atan2(-x,pz-z))
        q=a%(4*PI)
        lifts={}
        for kind,dy in (('intake',-12),('exhaust',12)):
            lift=valve_lift(q,kind)[0]
            lifts[kind]=lift
            transforms[f'{kind}_{i+1}']=mat(y=y+dy,z=HEAD-lift)
        cylinders.append({'phase':q,'stroke':('power','exhaust','intake','compression')[min(3,int(q/PI))],
                          'pin_z':pz,'valve_lifts':lifts})
    return {'phase':theta/(4*PI),'transforms':transforms,'cylinders':cylinders}

# Admission tests are numeric and independent of drawing/material choices.
max_closure=0.;min_valve_gap=float('inf');max_cam_gap=0.;max_contact_x=0.
for step in range(1441):
    theta=4*PI*step/1440
    f=frame(theta)
    for i,y in enumerate(YS):
        rod_m=f['transforms'][f'rod_{i+1}']
        small=[rod_m[k][2]*L+rod_m[k][3] for k in range(3)]
        desired=[0,y,f['cylinders'][i]['pin_z']]
        max_closure=max(max_closure,max(abs(a-b) for a,b in zip(small,desired)))
        for kind in ('intake','exhaust'):
            lift=f['cylinders'][i]['valve_lifts'][kind]
            min_valve_gap=min(min_valve_gap,HEAD-lift-(desired[2]+20))
            co,si=math.cos(theta/2),math.sin(theta/2)
            rotated=[(co*x+si*z,-si*x+co*z) for x,z in cam_profiles[f'{kind}_{i+1}']]
            contact=min(rotated,key=lambda p:p[1])
            gap=CAMZ+contact[1]-(HEAD+37-lift)
            max_cam_gap=max(max_cam_gap,abs(gap))
            max_contact_x=max(max_contact_x,abs(contact[0]))
assert max_closure<1e-9
assert min_valve_gap>3
assert max_cam_gap<.01 and max_contact_x<14
# Negative control: an incorrectly half-speed crank-to-cam mapping loses contact.
bad_gap=0
for step in range(144):
    theta=4*PI*step/144
    lift=valve_lift(theta,'intake')[0]
    co,si=math.cos(theta),math.sin(theta)
    low=min(-si*x+co*z for x,z in cam_profiles['intake_1'])
    bad_gap=max(bad_gap,abs(CAMZ+low-(HEAD+37-lift)))
assert bad_gap>1

print('KINEMATICS_PASSED',max_closure,min_valve_gap,max_cam_gap,flush=True)
meshes={};topology={}
for name,shape in parts.items():
    tess=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.18,AngularDeflection=.22,Relative=False)
    vertices,faces=tess.Topology
    meshes[name]={'vertices':[list(v) for v in vertices],'faces':[list(f) for f in faces]}
    counts=Counter(tuple(sorted((f[j],f[(j+1)%3]))) for f in faces for j in range(3))
    topology[name]={'vertices':len(vertices),'triangles':len(faces),'closed_edges':all(n==2 for n in counts.values()),'brep_valid':shape.isValid()}
    assert topology[name]['closed_edges'], name
    print('TESSELLATED',name,len(faces),flush=True)
poses=[frame(4*PI*i/FRAMES) for i in range(FRAMES)]
save('meshes.json',meshes);save('poses.json',poses);save('materials.json',materials)
doc=App.newDocument('InlineFourCutaway')
objects=[]
for name,shape in parts.items():
    obj=doc.addObject('PartDesign::Feature',name)
    obj.Shape=shape
    m=poses[0]['transforms'][name]
    matrix=App.Matrix(*[v for row in m for v in row])
    obj.Placement=App.Placement(matrix)
    objects.append(obj)
doc.recompute();doc.saveAs(str(ROOT/'engine.FCStd'))
Part.export(objects,str(ROOT/'engine.step'))
App.closeDocument(doc.Name)
save('report.json',{'schema':'mechanical-film.inline4-report/v1','passed':True,
    'delivery_sha256':{name:sha(ROOT/name) for name in ('meshes.json','poses.json')},
    'cad_sha256':{'engine.step':sha(ROOT/'engine.step'),'engine.FCStd':sha(ROOT/'engine.FCStd')},
    'generator_sha256':sha(Path(__file__)),
    'part_count':len(parts),'frames':FRAMES,'topology':topology,
    'checks':{'samples':1441,'rod_closure_max_mm':max_closure,'minimum_piston_valve_axial_gap_mm':min_valve_gap,
              'maximum_cam_follower_gap_mm':max_cam_gap,'maximum_cam_contact_x_mm':max_contact_x,
              'minimum_cam_support_curvature_mm':min(curvatures),'wrong_cam_ratio_gap_mm':bad_gap,
              'piston_to_liner_radial_clearance_mm':.4,'big_end_bore_clearance_mm':.3,
              'small_end_bore_clearance_mm':.3,'rod_to_web_axial_clearance_mm':4,
              'timing_pitch_radius_ratio':2},
    'cycle':{'firing_order':[1,3,4,2],'crank_turns':2,'cam_turns':1,'seconds':8},
    'limitations':['Educational original CAD assembly, not a manufacturer engine design.',
                   'Front housing and liners are deliberately sectioned; springs and fluid systems are omitted.',
                   'Prescribed motion and selected clearance checks; no whole-assembly continuous collision or load proof.',
                   'Uniform belt circulation is visually invariant; pulley pitch radii enforce the speed ratio.',
                   'Tessellation normals and CAD feature history are not reconstructed from another manufacturer design.'],
    'references':['https://www.briggsandstratton.com/en-us/support/videos/4-stroke-theory']})
print('ENGINE_READY',len(parts),flush=True)
