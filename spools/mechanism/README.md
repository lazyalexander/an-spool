# mechanism

Generate mechanical geometry and checked prescribed poses.

## Entry

```sh
python source/run.py LOOM_SOURCE_ARCHIVE steam
```

The case selector accepts steam or inline4. The steam case requires NumPy. The inline-four case uses the selected FreeCAD installation. geometry.zip carries meshes, poses and their source report; report.json records the domain checks.

## Host integration

The teaching chain runs this entry through the existing reviewed workspace backend. The operator selects runtime dependencies, approves the bound execution plan and separately accepts outputs after confirmed termination. Downstream stages consume fixed artifact revisions. Packaging supplies selected bytes and creates no execution grant.

Release files are immutable silk baselines. Files modified or created by an agent carry kit provenance. Unchanged copies retain silk labels. Modification history, current baseline match, trust, acceptance and retention decisions remain separate records. Legacy paths do not define labels. Instructions remain protected under the host authorization contract.

## Domain checks

From `source/production-mechanics-v2`, run `PYTHONPATH=src python -B tools/build_delivery.py`, then `PYTHONPATH=src python -B -m unittest discover -s tests -v`. The packaged v1 modules are immutable comparison fixtures. The joint-quality helper is an exact snapshot from the original mechanical miniapp, retained under tests/support for self-contained rejection tests. Its historical kit wording does not assign runtime provenance. Version 0.1.1 adds these test dependencies without changing the runtime generator.
