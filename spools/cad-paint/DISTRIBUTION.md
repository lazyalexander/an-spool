# CAD painting distribution

The first an-spool migration preserves the qualified v0.1.0 payload from an-loom,
including release digest `1a380dff33ca0fc569d306e6de67af505544bb4185d7db086f600b9bc63ee4a1`.
The historical npm name `@an-loom/cad-paint-spool` remains a compatibility identity.
The domain source now belongs here; Loom remains the packaging tool.

Use Python 3.12+, npm, TypeScript 5.9.3 and an explicitly selected Loom CLI:

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 -B -m unittest discover -s tests -v
python3 pack-client.py --loom /absolute/an-loom --tsc node_modules/.bin/tsc --output releases --check
```

The check independently rebuilds the Loom archive and npm payload and compares
all distributed members with the retained release. Consumer migrations must pin
an immutable distribution and its integrity. Source edits require a new version;
never replace a retained release in place.
