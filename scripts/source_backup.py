#!/usr/bin/env python3
"""Private source-only PostgreSQL backup; optional isolated restore verification."""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from reconcile import TABLES

PG = ["docker", "compose", "exec", "-T", "postgres"]


def pg(program, *args, **kwargs):
    return subprocess.run(
        PG + ["sh", "-c", 'program="$1"; shift; exec "$program" -U "$POSTGRES_USER" "$@"', "pg-tool", program, *args],
        check=True,
        timeout=180,
        **kwargs,
    )


def digest(database):
    values = {}
    for table in TABLES:
        sql = (
            "SELECT count(*) || ':' || "
            "md5(coalesce(string_agg(row_to_json(t)::text, E'\\n' ORDER BY id), '')) "
            f"FROM {table} t"
        )
        result = pg("psql", "-XqAt", "-v", "ON_ERROR_STOP=1", "-d", database, "-c", sql, capture_output=True, text=True)
        values[table] = result.stdout.strip()
    return values


def verify(path, expected):
    database = "cdc_restore_" + uuid.uuid4().hex
    created = False
    try:
        pg("createdb", database)
        created = True
        with path.open("rb") as dump:
            pg("pg_restore", "--exit-on-error", "--no-owner", "--no-privileges", "-d", database, stdin=dump)
        if digest(database) != expected:
            raise RuntimeError("Restored source contents differ from backup baseline")
        print("PASS backup:source_restore_all_six_entities", flush=True)
    finally:
        if created:
            pg("dropdb", database)


def backup(directory, do_verify):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    expected = digest("ecommerce") if do_verify else None
    path = directory / ("source-" + uuid.uuid4().hex + ".dump")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            pg("pg_dump", "-Fc", "-d", "ecommerce", stdout=out)
        with path.open("rb") as dump:
            checksum = hashlib.file_digest(dump, "sha256").hexdigest()
        if do_verify:
            if digest("ecommerce") != expected:
                raise RuntimeError("Source changed during backup; retry while quiescent")
            verify(path, expected)
        print(json.dumps({"scope": "postgres_source_only", "file": str(path), "sha256": checksum, "restore_verified": do_verify}))
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    if args.temporary:
        with tempfile.TemporaryDirectory(prefix="cdc-source-backup-") as tmp:
            backup(Path(tmp), args.verify)
    else:
        backup(Path("backups"), args.verify)


if __name__ == "__main__":
    main()
