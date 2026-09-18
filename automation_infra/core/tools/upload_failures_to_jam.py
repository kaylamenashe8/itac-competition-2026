#!/usr/bin/env python3
"""Uploads the screen recordings left behind by failed Playwright tests to Jam.

Playwright writes a video (and optionally a trace) for every test it was told to retain
artifacts for. This tool pairs each video with its trace, builds the Jam create payload,
and hands both to the Jam CLI, which uploads the video and lines the run's console logs,
network requests and typed input up against the video timeline. What you get back per
failure is one watchable URL to drop in Qase, Slack or a PR.

Two artifact layouts are discovered automatically:

1. Node Playwright  — test-results/<test-slug>/video.webm  + trace.zip
   One directory per failed test; the directory name becomes the Jam title.
2. Python Playwright — <dir>/<stem>.webm + <stem>.zip
   What record_video_dir produces; video and trace pair by filename stem. This is the
   layout jam_recorder.py writes, where the stem is the test name.

Uploads are recorded in a ledger (.jam_uploaded.json, in the artifacts dir) keyed by the
video's path, size and mtime, so re-running after a partial failure re-uploads only what
did not make it. --force ignores the ledger.

Requires the Jam CLI (curl -fsSL https://native.jam.dev/install | bash) and an
authenticated session (`jam auth login`, or JAM_TOKEN in the environment). ffmpeg/ffprobe
are used to read the video's dimensions and to extract its poster frame.

Usage:
    # Upload every failure Playwright left in test-results/
    ./upload_failures_to_jam.py --artifacts-dir test-results

    # See what would be uploaded, without uploading
    ./upload_failures_to_jam.py --dry-run

    # File them in a Jam folder, compress idle spans, print a paste-ready summary
    ./upload_failures_to_jam.py --folder "ITAC failures" --speedup --markdown
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import zipfile

logger = logging.getLogger(__name__)

DEFAULT_ARTIFACTS_DIR = "test-results"
LEDGER_FILENAME = ".jam_uploaded.json"
VIDEO_SUFFIXES = (".webm", ".mp4")

# Jam's create payload requires a url. Playwright's trace records the page the test was on,
# so it is read from there when possible; this stands in when there is no trace to read.
FALLBACK_URL = "https://app.nanit.com"

# Falls back to this when ffprobe cannot read the stream — Jam validates that
# screenDimensions is present, not that it matches the file.
FALLBACK_DIMENSIONS = {"width": 1280, "height": 720}

# The CLI exits 3 on an auth failure; every other nonzero code is a real upload error
# worth reporting per-video rather than aborting the batch.
JAM_EXIT_AUTH = 3

# Sniffed from the trace in preference order: the URL a test explicitly navigated to beats
# a frame navigation, which beats the first request the page happened to make.
_GOTO_RE = re.compile(r'"apiName"\s*:\s*"[^"]*goto"[^}]*?"url"\s*:\s*"(https?://[^"]+)"')
_NAVIGATED_RE = re.compile(r'"type"\s*:\s*"frame-navigated"[^}]*?"url"\s*:\s*"(https?://[^"]+)"')
_ANY_URL_RE = re.compile(r'"url"\s*:\s*"(https?://[^"]+)"')


# ── Discovery ───────────────────────────────────────────────────


def find_failures(artifacts_dir: str) -> list[dict]:
    """Returns one {title, video, trace} per recording found under artifacts_dir.

    Walks once and decides the layout per directory: a video literally named video.* is
    Node Playwright's per-test directory, so the directory names the test and any trace.zip
    beside it belongs to it. Anything else pairs by filename stem.
    """
    failures: list[dict] = []
    for dirpath, _dirnames, filenames in os.walk(artifacts_dir):
        videos = sorted(f for f in filenames if f.endswith(VIDEO_SUFFIXES))
        if not videos:
            continue
        traces = sorted(f for f in filenames if f.endswith(".zip"))

        for video in videos:
            stem = os.path.splitext(video)[0]
            if stem == "video":
                # Node layout: the directory is the test, so the lone trace.zip is its trace.
                title = os.path.basename(dirpath.rstrip(os.sep)) or stem
                trace = "trace.zip" if "trace.zip" in traces else (traces[0] if len(traces) == 1 else None)
            else:
                title = stem
                trace = f"{stem}.zip" if f"{stem}.zip" in traces else None

            failures.append(
                {
                    "title": title,
                    "video": os.path.join(dirpath, video),
                    "trace": os.path.join(dirpath, trace) if trace else None,
                }
            )
    return sorted(failures, key=lambda f: f["video"])


# ── Payload ─────────────────────────────────────────────────────


def probe_dimensions(video_path: str) -> dict:
    """Reads the video's pixel dimensions with ffprobe, falling back to a default."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                video_path,
            ],
            capture_output=True, text=True, check=True, timeout=30,
        ).stdout
        stream = json.loads(out)["streams"][0]
        return {"width": int(stream["width"]), "height": int(stream["height"])}
    except Exception as e:
        logger.warning(f"Could not probe {os.path.basename(video_path)} ({e}); using default dimensions")
        return dict(FALLBACK_DIMENSIONS)


def url_from_trace(trace_path: str | None) -> str | None:
    """Best-effort read of the page under test from a Playwright trace.

    The trace is a zip of newline-delimited JSON; rather than model its schema (which
    changes between Playwright versions) this scans the raw text for the most specific
    URL pattern it can find. Returns None when there is no trace or nothing matches.
    """
    if not trace_path or not os.path.exists(trace_path):
        return None
    try:
        with zipfile.ZipFile(trace_path) as zf:
            names = [n for n in zf.namelist() if n.endswith(".trace")]
            for name in names:
                text = zf.read(name).decode("utf-8", errors="replace")
                for pattern in (_GOTO_RE, _NAVIGATED_RE, _ANY_URL_RE):
                    for match in pattern.finditer(text):
                        url = match.group(1)
                        if "about:blank" not in url:
                            return url
    except Exception as e:
        logger.warning(f"Could not read URL from {os.path.basename(trace_path)}: {e}")
    return None


def build_payload(failure: dict, args) -> dict:
    """Builds the Jam create payload for one recording."""
    title = f"{args.title_prefix}{failure['title']}" if args.title_prefix else failure["title"]
    payload = {
        "kind": "video",
        "title": title,
        "url": args.url or url_from_trace(failure["trace"]) or FALLBACK_URL,
        "videoPath": os.path.abspath(failure["video"]),
        "screenDimensions": probe_dimensions(failure["video"]),
    }
    if failure["trace"]:
        # Attaches the run's console logs and network requests to the video timeline.
        payload["playwrightTracePath"] = os.path.abspath(failure["trace"])
    if args.description:
        payload["description"] = args.description
    return payload


# ── Upload ──────────────────────────────────────────────────────


def jam_binary() -> str | None:
    """Locates the Jam CLI, including the install path the installer uses but which a
    non-login shell may not have on PATH."""
    found = shutil.which("jam")
    if found:
        return found
    fallback = os.path.expanduser("~/.local/bin/jam")
    return fallback if os.path.isfile(fallback) and os.access(fallback, os.X_OK) else None


def check_auth(jam: str) -> bool:
    """Confirms the CLI has a usable session before uploading anything."""
    result = subprocess.run([jam, "--json", "auth", "status"], capture_output=True, text=True)
    return result.returncode == 0


def upload(jam: str, payload: dict, args) -> str | None:
    """Uploads one payload and returns the Jam URL, or None when the upload failed.

    The payload goes via a temp file rather than argv: it carries absolute paths and a
    free-text title, and the CLI's @file form exists precisely to avoid quoting those.
    """
    payload_path = os.path.join(args.artifacts_dir, ".jam_payload.json")
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    cmd = [jam, "--json", "create", "jam", f"@{payload_path}"]
    if args.folder:
        cmd += ["--folder", args.folder]
    # --speedup compresses idle spans, but the CLI derives them from the trace.
    if args.speedup and "playwrightTracePath" in payload:
        cmd.append("--speedup")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        logger.error(f"  timed out after {args.timeout}s")
        return None
    finally:
        if os.path.exists(payload_path):
            os.remove(payload_path)

    if result.returncode != 0:
        logger.error(f"  upload failed (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}")
        return None
    try:
        return json.loads(result.stdout).get("url")
    except (json.JSONDecodeError, AttributeError):
        logger.error(f"  could not parse Jam receipt: {result.stdout.strip()}")
        return None


# ── Ledger ──────────────────────────────────────────────────────


def ledger_key(video_path: str) -> str:
    """Identifies a recording by content-ish identity, so a re-run of the suite that
    rewrites the same path produces a new key and uploads again."""
    st = os.stat(video_path)
    return f"{os.path.abspath(video_path)}:{st.st_size}:{int(st.st_mtime)}"


def load_ledger(artifacts_dir: str) -> dict:
    path = os.path.join(artifacts_dir, LEDGER_FILENAME)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_ledger(artifacts_dir: str, ledger: dict) -> None:
    path = os.path.join(artifacts_dir, LEDGER_FILENAME)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    os.replace(tmp, path)


# ── Entry point ─────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--artifacts-dir", default=DEFAULT_ARTIFACTS_DIR,
                        help=f"Directory Playwright wrote videos/traces to (default: {DEFAULT_ARTIFACTS_DIR})")
    parser.add_argument("--url", default=None,
                        help="URL to record on each Jam (default: read from the trace, else FALLBACK_URL)")
    parser.add_argument("--title-prefix", default="",
                        help='Prepended to each Jam title, e.g. "RC 4.59 — "')
    parser.add_argument("--description", default=None, help="Description set on every Jam created")
    parser.add_argument("--folder", default=None, help="Jam folder to file the Jams in (name or ID)")
    parser.add_argument("--speedup", action="store_true",
                        help="Compress idle spans in the video (needs a trace; skipped for videos without one)")
    parser.add_argument("--force", action="store_true", help="Re-upload recordings already in the ledger")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded and exit")
    parser.add_argument("--markdown", action="store_true", help="Print a paste-ready markdown list at the end")
    parser.add_argument("--timeout", type=int, default=600, help="Per-upload timeout in seconds (default: 600)")
    args = parser.parse_args()

    if not os.path.isdir(args.artifacts_dir):
        logger.error(f"No such artifacts directory: {args.artifacts_dir}")
        sys.exit(1)

    failures = find_failures(args.artifacts_dir)
    if not failures:
        logger.info(f"No videos found under {args.artifacts_dir}/ — nothing to upload.")
        return

    ledger = load_ledger(args.artifacts_dir)
    pending = []
    for failure in failures:
        key = ledger_key(failure["video"])
        if not args.force and key in ledger:
            logger.info(f"skip  {failure['title']} — already uploaded: {ledger[key]}")
            continue
        failure["key"] = key
        pending.append(failure)

    if not pending:
        logger.info("Everything found has already been uploaded. Use --force to upload again.")
        return

    logger.info(f"\nFound {len(pending)} recording(s) to upload from {args.artifacts_dir}/\n")

    if args.dry_run:
        for failure in pending:
            payload = build_payload(failure, args)
            logger.info(f"would upload: {payload['title']}")
            logger.info(json.dumps(payload, indent=2))
        return

    jam = jam_binary()
    if not jam:
        logger.error("Jam CLI not found. Install it with:\n  curl -fsSL https://native.jam.dev/install | bash")
        sys.exit(1)
    if not check_auth(jam):
        logger.error("Jam CLI is not authenticated. Run `jam auth login`, or set JAM_TOKEN.")
        sys.exit(JAM_EXIT_AUTH)

    uploaded: list[tuple[str, str]] = []
    failed: list[str] = []
    for failure in pending:
        logger.info(f"uploading  {failure['title']}")
        if not failure["trace"]:
            logger.info("  (no trace alongside it — the Jam will have the video but no console/network panels)")
        payload = build_payload(failure, args)
        url = upload(jam, payload, args)
        if url:
            logger.info(f"  -> {url}")
            ledger[failure["key"]] = url
            uploaded.append((payload["title"], url))
            # Saved per upload so an interrupted batch never re-uploads what already landed.
            save_ledger(args.artifacts_dir, ledger)
        else:
            failed.append(failure["title"])

    logger.info(f"\nUploaded {len(uploaded)} of {len(pending)} recording(s).")
    if args.markdown and uploaded:
        logger.info("\n--- paste into Qase / Slack / the PR ---")
        for title, url in uploaded:
            logger.info(f"- [{title}]({url})")
    if failed:
        logger.error(f"\nFailed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
