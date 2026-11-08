# mechanical-film

Render an accepted appearance bundle through Blender and FFmpeg.

## Entry

```sh
python source/run.py APPEARANCE_ZIP
```

The bundle must use flat paths. Source geometry, UVs and supplied poses are checked, all frames are rendered, and the saved packed scene is reopened and verified. Final outputs are film.mp4, editable.blend and report.json. Frame caches are removed after verification and export to fit the existing workspace acceptance budget.

## Host integration

The teaching chain runs this entry through the existing reviewed workspace backend. The operator selects runtime dependencies, approves the bound execution plan and separately accepts outputs after confirmed termination. Downstream stages consume fixed artifact revisions. Packaging supplies selected bytes and creates no execution grant.

Release files are immutable silk baselines. Files modified or created by an agent carry kit provenance. Unchanged copies retain silk labels. Modification history, current baseline match, trust, acceptance and retention decisions remain separate records. Legacy paths do not define labels. Instructions remain protected under the host authorization contract.
