"""Configuration-driven mechanical film production; Python standard library only."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def load(path):
    path = Path(path).resolve()
    c = json.loads(path.read_text())
    require(c['schema'] == 'mechanical-film-kit/v1', 'Unsupported configuration schema')
    for name, item in c['inputs'].items():
        item['path'] = str((path.parent / item['path']).resolve())
        require(digest(item['path']) == item['sha256'], f'Input hash mismatch: {name}')
    report = json.loads(Path(c['inputs']['report']['path']).read_text())
    require(report.get('passed') is True, 'Mechanical source report rejected')
    for name in ('meshes', 'poses'):
        require(report['delivery_sha256'][name + '.json'] == c['inputs'][name]['sha256'],
                f'Report does not certify this {name} input')
    poses = json.loads(Path(c['inputs']['poses']['path']).read_text())
    meshes = json.loads(Path(c['inputs']['meshes']['path']).read_text())
    require(poses and all(set(p['transforms']) == set(meshes) for p in poses), 'Part IDs differ')
    r, e = c['render'], c['export']
    for key in ('frames', 'fps', 'width', 'height'):
        require(type(r[key]) is int and r[key] > 0, f'Invalid render {key}')
    require(r['frames'] <= len(poses) and 0 <= r['start_pose'] < len(poses), 'Invalid pose range')
    require(r['width'] % 2 == 0 and r['height'] % 2 == 0, 'H264 requires even dimensions')
    require(r['preview_frames'] and all(1 <= f <= r['frames'] for f in r['preview_frames']), 'Invalid preview frames')
    require(0 < r['tolerance'] <= 0.0001, 'Tolerance exceeds source fidelity contract')
    require(type(e['fps']) is int and e['fps'] >= r['fps'] and e['fps'] % r['fps'] == 0,
            'Export fps must be an integer multiple of source fps (frame holds only)')
    require(type(e['crf']) is int and 0 <= e['crf'] <= 51, 'Invalid CRF')
    # Encoding settings do not invalidate expensive renders.
    identity = {k: c[k] for k in ('inputs', 'image_bindings', 'render')}
    identity['worker_sha256'] = digest(HERE / 'blender_worker.py')
    identity['blender_version'] = subprocess.check_output([c['tools']['blender'], '--version'], text=True).splitlines()[0]
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    output = (path.parent / c['output']).resolve()
    require(not any(Path(i['path']).is_relative_to(output) for i in c['inputs'].values()), 'Output contains source inputs')
    run = output / key
    run.mkdir(parents=True, exist_ok=True)
    c['run'] = str(run)
    c['identity'] = identity
    write(run / 'resolved-config.json', c)
    return c, run


def manifest(run, paths):
    return {str(p.relative_to(run)): digest(p) for p in paths}


def verified(run):
    receipt = json.loads((run / 'render-receipt.json').read_text())
    require(receipt['passed'] is True, 'Render not accepted')
    for name, expected in receipt['artifacts'].items():
        require(digest(run / name) == expected, f'Stale or modified render artifact: {name}')
    return receipt


def worker(c, run, action):
    receipt = run / (action + '-check.json')
    receipt.unlink(missing_ok=True)
    with (run / (action + '.log')).open('w') as log:
        subprocess.run([c['tools']['blender'], '--background', '--python-exit-code', '1',
                        '--python', str(HERE / 'blender_worker.py'), '--',
                        str(run / 'resolved-config.json'), action], stdout=log, stderr=subprocess.STDOUT, check=True)
    require(receipt.exists() and json.loads(receipt.read_text()).get('passed') is True,
            f'{action} did not produce a passing receipt; inspect {action}.log')


def render(c, run):
    if (run / 'render-receipt.json').exists():
        verified(run)
        print('Verified render cache reused', flush=True)
        return
    worker(c, run, 'render')
    worker(c, run, 'verify')
    paths = [run / 'frames' / f'{i:04d}.png' for i in range(1, c['render']['frames'] + 1)]
    paths += [run / 'editable.blend', run / 'render-check.json', run / 'verify-check.json']
    write(run / 'render-receipt.json', {'passed': True, 'identity': c['identity'], 'artifacts': manifest(run, paths)})


def export(c, run):
    verified(run)
    e, r = c['export'], c['render']
    key = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()[:12]
    target = run / ('export-' + key)
    target.mkdir(exist_ok=True)
    receipt_path = target / 'receipt.json'
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text())
        require(old['passed'] is True, 'Invalid export receipt')
        for name, value in old['artifacts'].items():
            require(digest(run / name) == value, f'Export modified: {name}')
        print(f'Verified export cache reused: {target}', flush=True)
        return
    outputs = [('film.mp4', ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(e['crf']),
                              '-pix_fmt', 'yuv420p', '-movflags', '+faststart'])]
    if e['prores']:
        outputs.append(('edit-master.mov', ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le']))
    probes = {}
    for name, codec in outputs:
        destination = target / name
        temporary = target / ('partial-' + name)
        subprocess.run([c['tools']['ffmpeg'], '-hide_banner', '-loglevel', 'error', '-y',
                        '-framerate', str(r['fps']), '-i', str(run / 'frames/%04d.png'),
                        '-vf', f"fps={e['fps']}", '-frames:v', str(r['frames'] * e['fps'] // r['fps']),
                        *codec, str(temporary)], check=True)
        probe = json.loads(subprocess.check_output([c['tools']['ffprobe'], '-v', 'error',
            '-select_streams', 'v:0', '-show_streams', '-of', 'json', str(temporary)], text=True))['streams'][0]
        require((probe['width'], probe['height']) == (r['width'], r['height']), 'Wrong video size')
        require(int(probe['nb_frames']) == r['frames'] * e['fps'] // r['fps'], 'Wrong video frame count')
        require(abs(float(probe['duration']) - r['frames'] / r['fps']) < 0.001, 'Wrong video duration')
        temporary.replace(destination)
        probes[name] = probe
    write(receipt_path, {'passed': True, 'settings': e, 'streams': probes,
                        'artifacts': manifest(run, [target / name for name, _ in outputs]),
                        'render_receipt_sha256': digest(run / 'render-receipt.json'),
                        'interpolation': 'Frame holds only; no optical flow or generative interpolation'})
    print(f'Exported: {target}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'preview', 'render', 'export', 'run'))
    parser.add_argument('--config', type=Path, default=HERE / 'config.json')
    args = parser.parse_args()
    c, run = load(args.config)
    print(f'Run: {run}', flush=True)
    try:
        if args.action in ('check', 'run'):
            worker(c, run, 'check')
        if args.action == 'preview':
            worker(c, run, 'preview')
        if args.action in ('render', 'run'):
            render(c, run)
        if args.action in ('export', 'run'):
            export(c, run)
    except Exception as error:
        write(run / 'last-failure.json', {'stage': args.action, 'error': str(error)})
        raise


if __name__ == '__main__':
    main()
