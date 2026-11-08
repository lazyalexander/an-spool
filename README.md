# an-spool

Reviewed domain spool sources and immutable client distributions.

- `spools/cad-paint`: the qualified CAD painting release, domain instructions,
  material policy, renderer, editable appearance kit and independent checks.
- an-loom owns development, validation and packaging. an-agent owns authorization,
  scheduling, execution, lifecycle and accepted artifacts. an-shuttle owns app bridges.

Release baseline files are silk. Runtime modifications and new files acquire the
kit label and remain outside this repository, under an-agent custody. A label
never grants authority. Instructions remain protected during runtime.

The first migration preserves the existing `@an-loom/cad-paint-spool` package
name, v0.1.0 release bytes and runtime/profile identities for compatibility.
Repository ownership does not rewrite historical releases. New code, knowledge
or acceptance changes require a new reviewed release.

Build and verify with Loom and TypeScript 5.9.3; see the package distribution
instructions and `catalog.json`. Private runtime profiles, credentials, model
transcripts, instance stores and user paintings do not belong in this repository.
