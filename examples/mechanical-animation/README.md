# Mechanical animation teaching chain

Three source releases generate checked geometry, bind approved appearance inputs, and render a complete film with an editable Blender scene. Each stage uses the existing operator-reviewed workspace backend. Downstream stages bind formally accepted artifact revisions. See [release identities](../../teaching-releases.json).

```sh
python3 examples/mechanical-animation/qualify.py --host HOST_BINARY --evidence NEW_DIRECTORY --fixtures SELECTED_FIXTURES --python-runtime PYTHON_BINARY --python-site NUMPY_SITE steam inline4
```

Select the installed host, Python with NumPy, FreeCAD, Blender 5.2.3 and FFmpeg. The script uses standard macOS application locations and Homebrew runtime roots. Fixtures contain steam-inputs and inline4-inputs folders with config.json, scene.blend, atlas.png and background.png. These are operator-selected inputs with recorded hashes. The evidence directory must be new. Unknown outcomes are retained for reconciliation.

The operator explicitly selects macos-agx-metal-v1 for rendering, with two IOKit classes and two Mach services. The default has no graphics access. Rendering selects a bounded 900-second deadline. Network and external writes remain denied. This is reviewed workspace execution with trusted local tools.

[Portable acceptance](acceptance.json) records two completed cases, reopened scenes and decoded-frame equality. The source material atlas and backdrop are retained approved AI images. No new image-generation calls were made. Native grants and raw machine records remain private. The [native macOS teaching application](product/README.md) supplies ordinary native envelopes and a browser entry over the original daemon. Its real runtime qualification and the Krita GUI round-trip retain separate acceptance scope.

The host owns execution, cancellation and accepted artifact custody. The spool bodies own geometry, appearance and rendering. Temporary frames are removed after successful verification and export. Formal products survive later workspace collection.
