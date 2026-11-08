> Example-only: this directory teaches client use and supports acceptance tests. It is not an installed product component or a second host. The historical `product/` path is retained for existing scripts.

# Teaching and test example

This local application loads three ordinary native Python spools into the existing macOS user daemon. The browser submits reviewed operations, and opens the original read-only observation console. The daemon retains its existing FIFO queue, finite supervisors, task grants, lifecycle and artifact custody. This application has no worker loop, retry policy, model client or credential store.

## Prepare and run

Use an-agent with native operator auxiliary inputs, accepted-revision submission and explicit Metal runtime support; use Shuttle with `packages/krita/dist/accepted.js`. Build both once. Python 3.12 needs NumPy and Pillow in a selected, link-free site directory. FreeCAD, Blender and FFmpeg must already be installed. The fixtures are the approved per-case `config.json`, `scene.blend`, `atlas.png` and `background.png` documented in the [case](../README.md); nothing is downloaded or installed.

```sh
python3 product.py prepare --root NEW_PRIVATE_ROOT --host HOST_BINARY \
  --python PYTHON_BINARY --site SITE_PACKAGES --stdlib PYTHON_STDLIB \
  --fixtures SELECTED_FIXTURES --node NODE_BINARY --shuttle SHUTTLE_ACCEPTED_JS
HOST_BINARY daemon serve NEW_PRIVATE_ROOT/service
# In another terminal:
python3 product.py serve NEW_PRIVATE_ROOT
```

Run from this directory or select the script by its path. Open the URL in the private `application-endpoint.json`. The prepared `agent.plist` can instead be installed with the existing user launchd workflow. Preparation does not install or start services. Root must be new and remains private. Two cases use separate instances of the same three release bodies, allowing different approved fixtures without changing release code.

`pack.py NEW_DIRECTORY` produces reproducible native envelopes from the exact indexed Loom releases. It verifies their distribution hashes, extracts their entry code directly from verified archives and records origin identities. The OpenRaster helper comes from the pinned published CAD client archive. The film envelope adds a first-frame OpenRaster reference using the existing CAD OpenRaster packer; it never claims editable mechanical part layers. Loom's immutable source archives are unchanged. Native silk/kit labels follow original host provenance rules.

## Product operations

Choose **Run**, review the selected phase and authority, then confirm. The application obtains a finite, non-delegable grant for that exact instance/run/input/deadline and submits through `tasks.sock`. The grant credential exists only in that call's memory. A subsequent **Accept artifacts** action obtains its own narrowed acceptance grant and invokes original custody validation. The next stage selects the accepted upstream revision, not a copied path or latest output. Changed plans require a fresh preview.

Pause, resume, unload and cancel use the original lifecycle operations. Cancel also revokes the run grant through the daemon. Unknown outcomes cannot be retried or reclaimed by this application. A confirmed failed run remains visible in the original console; a developer must explicitly select a new run name after fixing the cause. No stage advances without explicit review and acceptance.

After film acceptance, **Send to Krita** checks the selected accepted ORA revision and invokes Shuttle's existing `openInKrita` bridge. The operation never opens an arbitrary output file. The reference is one animation frame; the full editable animation remains in `editable.blend`. GUI painting and native KRA save/reopen have the [separate existing acceptance scope](https://github.com/lazyalexander/an-shuttle/blob/main/docs/mechanical-krita-gui.md).

The teaching controls have a separate local token. They require exact loopback Host, same-origin POST and bounded bodies. The original daemon observation token remains read-only. Raw grants and local paths are absent from public acceptance summaries. No provider request, cloud resource or automatic remote process is introduced.

## Acceptance

The native host fixture `native_daemon_inputs.py` checks operator selections, changed auxiliary input refusal, missing graphics refusal and revision-bound queued handoff. Run the host's existing `native_task_permissions.py` to preserve attenuation, cancellation, revocation and retained custody guarantees. The actual product qualification must additionally run steam and inline-four from this browser entry through all three accepted stages and invoke the existing Shuttle bridge. Package reproduction and fixtures alone do not establish that result.

After completing both cases, run `python3 qualify.py --root PRIVATE_ROOT --output LOCAL_SUMMARY.json` to check application transport refusals, original grants, all six accepted phases and exact upstream revision claims. The summary is private until its operator paths and records are reviewed for publication.

[Portable product acceptance](acceptance.json) records both cases through all six native phases, original task grants and revision claims, exact decoded-frame parity (144 steam / 192 inline-four), reproducible envelopes and refusal of unaccepted Shuttle output. Both native Krita windows were observed after the application handoff, with the correct 1920×1080 reference and film-reference layer. This product run qualifies opening the accepted reference; historical paint/KRA save/reopen evidence retains its separate scope.

This integration requires an-agent `f740188` (or its merged descendant) and Shuttle `34facba` (or its merged descendant). Merge the host support first, then Shuttle, then this application; Loom's matching platform note is documentation only. All ordinary development targets remain their repository's current development authority.

The product page defaults to English. Its language button retains the Simplified Chinese companion using the same controller and records; changing language does not submit an operation or change permissions. The original observation workbench also defaults to English.

Client protocol and the optional local page transport live under `examples/support/`; both remain test/example support. This file contains domain setup and sequencing only. Downstream submissions use `{catalog, revision}` with a `run-artifact` grant. Blob filenames and revision-directory layouts are resolved only inside the host.
