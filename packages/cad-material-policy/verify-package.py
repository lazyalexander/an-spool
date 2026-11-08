"""Compare published client members; npm gzip headers vary across platforms."""
import sys
import tarfile


def payload(path):
    with tarfile.open(path) as archive:
        result = {}
        for entry in archive:
            if not entry.isfile() or entry.name in result:
                raise ValueError(f"Unexpected package member: {entry.name}")
            result[entry.name] = (entry.mode, archive.extractfile(entry).read())
        return result


if payload(sys.argv[1]) != payload(sys.argv[2]):
    raise SystemExit("Published package contents differ from compiled source")
print("All package paths, modes and bytes match")
