"""Preserve the approved scene and animate only supplied part transforms."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

config_path, action = sys.argv[sys.argv.index('--') + 1:]
c = json.loads(Path(config_path).read_text())
root = Path(c['run'])
r = c['render']
source = c['inputs']['scene']['path']
poses = json.loads(Path(c['inputs']['poses']['path']).read_text())
meshes = json.loads(Path(c['inputs']['meshes']['path']).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def geometry(obj):
    return ([tuple(v.co) for v in obj.data.vertices], [tuple(p.vertices) for p in obj.data.polygons])


def uv(obj):
    return [[tuple(item.uv) for item in layer.data] for layer in obj.data.uv_layers]


def snapshots():
    return {pid: (geometry(bpy.data.objects[pid]), uv(bpy.data.objects[pid])) for pid in meshes}


def pose_at(frame):
    return poses[(r['start_pose'] + frame - 1) % len(poses)]


def pose_error(frame):
    return max(abs(bpy.data.objects[pid].matrix_world[i][j] - matrix[i][j])
               for pid, matrix in pose_at(frame)['transforms'].items()
               for i in range(4) for j in range(4))


bpy.ops.wm.open_mainfile(filepath=source)
scene = bpy.context.scene
require(scene.camera is not None, 'Missing camera')
baseline = snapshots()
static = {obj.name: obj.matrix_world.copy() for obj in scene.objects if obj.name not in meshes}
camera_scale = scene.camera.data.ortho_scale
source_errors = {}
for pid, data in meshes.items():
    obj = bpy.data.objects[pid]
    require(not obj.modifiers and not obj.constraints and not obj.parent, f'Unsupported transform stack: {pid}')
    require(len(obj.data.vertices) == len(data['vertices']), f'Vertex count differs: {pid}')
    error = max(abs(v.co[k] - data['vertices'][i][k])
                for i, v in enumerate(obj.data.vertices) for k in range(3))
    require(error < r['tolerance'], f'Geometry differs: {pid}')
    source_errors[pid] = error
    vertices = [Vector(v) for v in data['vertices']]
    triangles = [(face[0], face[j], face[j+1]) for face in data['faces'] for j in range(1, len(face)-1)]
    triangles = [f for f in triangles if (vertices[f[1]]-vertices[f[0]]).cross(
        vertices[f[2]]-vertices[f[0]]).length_squared > 1e-20]
    require([tuple(p.vertices) for p in obj.data.polygons] == triangles, f'Topology differs: {pid}')

# Resolve declared images explicitly, so a copied kit does not depend on old absolute paths.
for name, key in c['image_bindings'].items():
    image = bpy.data.images.get(name)
    require(image is not None, f'Missing approved image: {name}')
    image.filepath = c['inputs'][key]['path']
    image.reload()
    require(len(image.pixels) > 0, f'Image failed to load: {name}')

def static_check():
    require(scene.camera.data.ortho_scale == camera_scale, 'Camera scale changed')
    require(all(scene.objects[name].matrix_world == matrix for name, matrix in static.items()),
            'Stationary object or camera moved')
    require(snapshots() == baseline, 'Geometry or UV changed')


errors = []
if action == 'verify':
    bpy.ops.wm.open_mainfile(filepath=str(root / 'editable.blend'))
    scene = bpy.context.scene
    for frame in range(1, r['frames'] + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        error = pose_error(frame)
        require(error < r['tolerance'], f'Saved pose differs at {frame}: {error}')
        static_check()
        errors.append(error)
    require(all(bpy.data.images[name].packed_file for name in c['image_bindings']), 'Images not packed')
else:
    parts = {pid: bpy.data.objects[pid] for pid in meshes}
    for obj in parts.values():
        obj.animation_data_clear()
        obj.rotation_mode = 'QUATERNION'
    scene.render.fps = r['fps']
    scene.frame_start, scene.frame_end = 1, r['frames']
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x, scene.render.resolution_y = r['width'], r['height']
    scene.render.resolution_percentage = 100
    frames = r['preview_frames'] if action == 'preview' else range(1, r['frames'] + 1)
    destination = root / ('preview' if action == 'preview' else 'frames')
    if action != 'check':
        destination.mkdir(exist_ok=True)
    previous = {}
    for frame in frames:
        scene.frame_set(frame)
        for pid, obj in parts.items():
            obj.matrix_world = Matrix(pose_at(frame)['transforms'][pid])
            if pid in previous:
                obj.rotation_quaternion.make_compatible(previous[pid])
            previous[pid] = obj.rotation_quaternion.copy()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                obj.keyframe_insert(data_path=channel, frame=frame)
        bpy.context.view_layer.update()
        error = pose_error(frame)
        require(error < r['tolerance'], f'Pose differs at {frame}: {error}')
        static_check()
        errors.append(error)
        if action != 'check':
            scene.render.filepath = str(destination / f'{frame:04d}.png')
            bpy.ops.render.render(write_still=True)
    if action == 'render':
        for image in bpy.data.images:
            if image.source == 'FILE' and image.has_data:
                image.pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(root / 'editable.blend'))

(root / (action + '-check.json')).write_text(json.dumps({
    'passed': True, 'stage': action, 'frames_checked': len(errors),
    'max_pose_error': max(errors), 'source_vertex_errors': source_errors,
    'source_triangles_verified': True, 'geometry_and_uv_unchanged': True,
    'camera_and_environment_static': True, 'generative_calls': 0,
    'scope': 'Sampled source-model fidelity only. No new collision proof, subframe or temporal-shading certification.'
}, indent=2))
print('KIT_STAGE_PASSED', action, max(errors))
