# an-spool

English · [简体中文](README.zh-CN.md)

Reviewed domain spools: source, knowledge, skills, instructions, domain tests and
immutable client distributions. Runtime instances live under an-agent custody.

## Ownership

- **an-spool** owns domain behavior and its acceptance rules.
- **an-loom** prepares, validates and packages releases.
- **an-agent** owns task authority, scheduling, external harness supervision,
  lifecycle and accepted artifacts.
- **an-shuttle** connects applications, mediates interaction and delivers products.

The catalog introduces no runtime, scheduler or model loop. Release baselines are
**silk**; authorized modified or new runtime work is **kit**. Instructions stay
protected. Labels never grant authority. Credentials, model events, machine
profiles and user artifacts do not belong in this repository.

## Example: CAD → Krita

A saved CAD revision becomes a transparent painting with editable part layers.
CAD is an example of domain packaging, not the catalog's scope.

![Layered CAD painting](https://raw.githubusercontent.com/lazyalexander/an-shuttle/a94485bcb348b28d8ce62cabab321b7739167139/examples/cad-paint/sample/vise.png)

[Spool source and contract](spools/cad-paint/README.md) ·
[Material policy](packages/cad-material-policy/README.md) ·
[Application setup and acceptance](https://github.com/lazyalexander/an-shuttle/blob/main/docs/cad-paint.md)

## Releases and checks

[Catalog identities](catalog.json) describe the immutable renderer release.
The renderer preserves the historical `@an-loom/cad-paint-spool` 0.1.0 identity;
`@an-spool/cad-material-policy` independently versions completion instructions,
appearance-kit planning and historical-material adoption imported by Shuttle.
New source or policy requires a reviewed version; old distributions are not rewritten.

Follow the [renderer distribution checks](spools/cad-paint/DISTRIBUTION.md) and
[policy build/tests](packages/cad-material-policy/README.md). Package reproduction
is distinct from host execution and real application acceptance.
