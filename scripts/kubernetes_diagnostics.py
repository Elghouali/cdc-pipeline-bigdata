#!/usr/bin/env python3
"""Collect bounded Spark logs from the disposable CI namespace, with secret redaction.

Do not dump environment variables, manifests, or unredacted pod logs.
"""
import base64
import json
import subprocess
from pathlib import Path
from urllib.parse import quote


KUBECTL = ["kubectl", "-n", "cdc-pipeline"]
OUTPUT = Path("artifacts/spark-driver-diagnostics.txt")


def invoke(args, timeout=30):
    result = subprocess.run(
        KUBECTL + args, capture_output=True, text=True, timeout=timeout, check=False
    )
    return result.returncode, result.stdout, result.stderr


def collect():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Fail closed: do not collect potentially sensitive logs unless the current
    # ephemeral Secret can be read and used to remove literal credential values.
    try:
        code, stdout, _ = invoke(["get", "secret", "cdc-secrets", "-o", "json"])
        if code:
            raise RuntimeError("Secret unavailable")
        encoded = json.loads(stdout)["data"]
        if not encoded:
            raise RuntimeError("Empty Secret")
        variants = set()
        for value in encoded.values():
            decoded = base64.b64decode(value, validate=True).decode()
            if not decoded:
                continue
            variants.update((decoded, value, quote(decoded, safe="")))
        if not variants:
            raise RuntimeError("No credential values to redact")
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.SubprocessError):
        OUTPUT.write_text("Driver logs omitted: could not establish redaction.\n")
        return

    def redact(text):
        for value in sorted(variants, key=len, reverse=True):
            text = text.replace(value, "[REDACTED]")
        return text

    chunks = []
    for layer in ("bronze", "silver", "gold"):
        label = "app.kubernetes.io/component=spark-" + layer
        try:
            code, stdout, stderr = invoke(["get", "pods", "-l", label, "-o", "json"])
            if code:
                chunks.append(redact(stderr))
                continue
            for pod in json.loads(stdout).get("items", []):
                name = pod["metadata"]["name"]
                for status in pod.get("status", {}).get("containerStatuses", []):
                    # Record exit reason and count without serializing env/config.
                    state = status.get("state", {})
                    last = status.get("lastState", {})
                    terminated = state.get("terminated") or last.get("terminated") or {}
                    waiting = state.get("waiting") or {}
                    chunks.append(redact(json.dumps({
                        "pod": name,
                        "container": status["name"],
                        "restarts": status.get("restartCount", 0),
                        "waiting": waiting.get("reason"),
                        "exit_code": terminated.get("exitCode"),
                        "termination_reason": terminated.get("reason"),
                    })))
                for previous in (False, True):
                    args = ["logs", name, "-c", "spark", "--tail=200"]
                    if previous:
                        args.append("--previous")
                    _, stdout, stderr = invoke(args)
                    chunks.append(f"--- {name} previous={previous} ---")
                    chunks.append(redact(stdout + stderr))
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
            chunks.append(f"{layer}: diagnostics unavailable ({type(exc).__name__})")
    readiness = Path("/tmp/cdc-trino-readiness.log")
    if readiness.is_file():
        chunks.append("--- Last Trino readiness response ---")
        chunks.append(redact(readiness.read_text(errors="replace")[-10000:]))
    OUTPUT.write_text("\n".join(chunks) + "\n", encoding="utf-8")


if __name__ == "__main__":
    collect()
