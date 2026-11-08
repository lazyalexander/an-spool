"""Check actual union material inside both pin joints, without exemptions."""
import importlib.util
from pathlib import Path
import unittest
import json
import numpy as np
from mechflow.steam_engine import SteamEngineProvider
from mechflow import mesh as prim
from mechflow.types import Mesh

spec = importlib.util.spec_from_file_location(
    "joint_quality", Path(__file__).resolve().parent / "support/quality.py")
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


def intrusions(mesh, length):
    solids = quality.components(mesh)
    hits = []
    for center, radius in ((0., 4.2), (-length, 4.)):
        for y in (-6., 0., 6.):
            for fraction in (0., .5, .9):
                for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                    point = np.array([center + radius*fraction*np.cos(angle),
                                      y, radius*fraction*np.sin(angle)])
                    if quality.interior_component(point, solids) is not None:
                        hits.append(point.tolist())
    return hits


class JointMaterialTests(unittest.TestCase):
    def test_exported_rod_leaves_both_pin_volumes_empty(self):
        path = Path(__file__).resolve().parents[1] / 'delivery/meshes.json'
        if not path.exists():
            self.skipTest('Delivery has not been built yet')
        payload = json.loads(path.read_text())['rod']
        mesh = Mesh(np.asarray(payload['vertices']), np.asarray(payload['faces']))
        self.assertEqual(intrusions(mesh, SteamEngineProvider().rod_length), [])

    def test_complete_rod_leaves_both_pin_volumes_empty(self):
        provider = SteamEngineProvider()
        self.assertEqual(intrusions(provider._meshes['rod'][2], provider.rod_length), [])
        # These local bounds apply throughout the rigid joint's whole cycle.
        self.assertGreater(-provider.shank_start, provider.big_end_bore)
        self.assertLess(-provider.shank_start, provider.big_end_outer)
        self.assertGreater(provider.shank_end + provider.rod_length, provider.small_end_bore)
        self.assertLess(provider.shank_end + provider.rod_length, provider.small_end_outer)

    def test_old_capsule_refilling_each_bore_is_rejected(self):
        provider = SteamEngineProvider()
        rod = provider._meshes['rod'][2]
        for center in (0., -provider.rod_length):
            with self.subTest(center=center):
                mutated = prim.combine(rod, prim.capsule((center, -2., 0.),
                                                        (center, 2., 0.), 2.))
                self.assertTrue(intrusions(mutated, provider.rod_length))
