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

## Releases and checks

[Catalog identities](catalog.json) describe the immutable renderer release.
The renderer preserves the historical `@an-loom/cad-paint-spool` 0.1.0 identity;
`@an-spool/cad-material-policy` independently versions completion instructions,
appearance-kit planning and historical-material adoption imported by Shuttle.
New source or policy requires a reviewed version; old distributions are not rewritten.

Follow the [renderer distribution checks](spools/cad-paint/DISTRIBUTION.md) and
[policy build/tests](packages/cad-material-policy/README.md). Package reproduction
is distinct from host execution and real application acceptance.

## Cases · mechanical animation

### Ink and painted steam-engine comparison

| Ink animation | Painted version · 6 s |
| --- | --- |
| ![Ink animation](https://raw.githubusercontent.com/lazyalexander/an-agent/d94f574197d8a7f56d30ca78d9cad8d81039d65d/assets/demos/mechanical-ink.gif) | ![Painted steam engine](https://raw.githubusercontent.com/lazyalexander/an-agent/d94f574197d8a7f56d30ca78d9cad8d81039d65d/assets/demos/painted-steam-engine.gif) |

The future animation spool owns geometry, prescribed motion, appearance instructions and domain checks. The currently published catalog contains the CAD painting packages; animation packaging remains pending.
[Teaching workflow and reproduction evidence](https://github.com/lazyalexander/an-agent/blob/d94f574197d8a7f56d30ca78d9cad8d81039d65d/doc/cases.md).

### Supplementary case · inline-four engine

<img src="https://raw.githubusercontent.com/lazyalexander/an-agent/d94f574197d8a7f56d30ca78d9cad8d81039d65d/assets/demos/painted-inline-four.gif" alt="Inline-four engine" width="420">

Forty CAD parts reuse the painted workflow over an eight-second cycle. Both
painted GIFs loop at 720 × 405 and 12 fps. Media and teaching notes reference a
fixed an-agent revision.

## Example: CAD → Krita

A saved CAD revision becomes a transparent painting with editable part layers.
CAD is an example of domain packaging, not the catalog's scope.

![Layered CAD painting](https://raw.githubusercontent.com/lazyalexander/an-shuttle/a94485bcb348b28d8ce62cabab321b7739167139/examples/cad-paint/sample/vise.png)

[Spool source and contract](spools/cad-paint/README.md) ·
[Material policy](packages/cad-material-policy/README.md) ·
[Application setup and acceptance](https://github.com/lazyalexander/an-shuttle/blob/main/docs/cad-paint.md)

Kit labels files modified or created by an agent. Unchanged copies retain their silk baseline label. Modification history, current baseline match, trust and retention decisions remain separate records. Paths and legacy slot names do not define this label.

The [mechanical teaching chain](examples/mechanical-animation/README.md) runs the three source releases through the existing host. See [teaching release identities](teaching-releases.json).
