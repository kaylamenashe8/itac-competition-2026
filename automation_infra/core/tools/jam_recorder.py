#!/usr/bin/env python3
"""Playwright session recorder that leaves Jam-uploadable artifacts behind on failure.

Wraps a Playwright session so that a test which raises leaves a matched pair of files
in the artifacts directory:

    test-results/<name>.webm   the screen recording
    test-results/<name>.zip    the Playwright trace (console, network, typed input)

A session that completes cleanly leaves nothing — videos are deleted rather than kept,
so the artifacts directory only ever holds failures. upload_failures_to_jam.py reads
that directory and pushes each pair to Jam, where the trace's console and network events
are lined up against the video timeline.

The two files deliberately share a stem: that is how the uploader pairs them.

Usage:
    from jam_recorder import recorded_session

    async def test_login():
        async with recorded_session("test_login") as page:
            await page.goto("https://app.nanit.com")
            await page.click("text=Sign In")     # raises -> video + trace kept

Then upload whatever failed:

    ./upload_failures_to_jam.py --markdown

Run this file directly to record a self-check (one failing session, one passing) and
confirm the artifacts land as expected:

    ./jam_recorder.py --self-check
"""

import argparse
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

DEFAULT_ARTIFACTS_DIR = os.environ.get("JAM_RECORD_DIR", "test-results")
DEFAULT_VIEWPORT = (1280, 720)

# Playwright needs screenshots=True in the trace for Jam to line the trace's events up
# against the video: the CLI matches them through the trace's screencast frames.
TRACE_OPTIONS = {"screenshots": True, "snapshots": True, "sources": True}


@asynccontextmanager
async def recorded_session(
    name: str,
    artifacts_dir: str = DEFAULT_ARTIFACTS_DIR,
    headless: bool = True,
    viewport: tuple[int, int] = DEFAULT_VIEWPORT,
    base_url: str | None = None,
    browser_type: str = "chromium",
):
    """Yields a Playwright Page, keeping its video and trace only if the body raises.

    Teardown order is forced by Playwright: tracing has to stop while the context is
    still open, but a video's path only resolves once the context has closed. So the
    trace is written first, the video object is held across the close, and the file is
    renamed (or removed) afterwards.
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    failed = False

    async with async_playwright() as p:
        browser = await getattr(p, browser_type).launch(headless=headless)
        context_args = {
            "viewport": {"width": viewport[0], "height": viewport[1]},
            "record_video_dir": artifacts_dir,
            "record_video_size": {"width": viewport[0], "height": viewport[1]},
        }
        if base_url is not None:
            context_args["base_url"] = base_url

        context = await browser.new_context(**context_args)
        await context.tracing.start(**TRACE_OPTIONS)
        page = await context.new_page()
        logger.info(f"Recording '{name}' into {artifacts_dir}/")

        try:
            yield page
        except BaseException:
            # Covers KeyboardInterrupt and pytest's own failure exceptions, not just Exception.
            failed = True
            raise
        finally:
            video = page.video
            await _stop_tracing(context, artifacts_dir, name, failed)
            await context.close()
            await browser.close()
            if video is not None:
                await _finalize_video(video, artifacts_dir, name, failed)


async def _stop_tracing(context, artifacts_dir: str, name: str, failed: bool) -> None:
    """Writes the trace beside the video on failure, discards it otherwise.
    Fails silently — a trace is diagnostic, never worth breaking teardown over."""
    try:
        if failed:
            path = os.path.join(artifacts_dir, f"{name}.zip")
            await context.tracing.stop(path=path)
            logger.info(f"Saved failure trace: {path}")
        else:
            await context.tracing.stop()
    except Exception as e:
        logger.warning(f"Failed to stop tracing: {e}")


async def _finalize_video(video, artifacts_dir: str, name: str, failed: bool) -> None:
    """Renames the recording to match its trace's stem on failure, deletes it otherwise.

    Playwright names videos by an internal hash, so the rename is what lets
    upload_failures_to_jam pair a video with the trace from the same session. Both
    branches go through the file rather than Video.delete(), which needs a live context
    — and the context has to be closed first for the video to be finalized.
    """
    try:
        source = await video.path()
        if not failed:
            os.remove(source)
            return
        target = os.path.join(artifacts_dir, f"{name}.webm")
        os.replace(source, target)
        logger.info(f"Saved failure video: {target}")
    except Exception as e:
        logger.warning(f"Failed to finalize video: {e}")


async def _self_check(artifacts_dir: str) -> None:
    """Records one failing and one passing session, then reports what was left behind."""
    try:
        async with recorded_session("selfcheck_failing", artifacts_dir=artifacts_dir) as page:
            await page.goto("https://example.com")
            await page.click("text=NoSuchButton", timeout=1500)
    except Exception as e:
        logger.info(f"failing session raised as expected: {type(e).__name__}")

    async with recorded_session("selfcheck_passing", artifacts_dir=artifacts_dir) as page:
        await page.goto("https://example.com")
    logger.info("passing session completed")

    left = sorted(os.listdir(artifacts_dir))
    logger.info(f"\nArtifacts in {artifacts_dir}/: {left}")
    expected = ["selfcheck_failing.webm", "selfcheck_failing.zip"]
    kept_passing = [f for f in left if f.startswith("selfcheck_passing")]
    if all(e in left for e in expected) and not kept_passing:
        logger.info("Self-check PASSED: failure kept video + trace, pass left nothing.")
    else:
        logger.error("Self-check FAILED: unexpected artifacts. See the listing above.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--self-check", action="store_true",
                        help="Record a failing and a passing session and verify the artifacts")
    parser.add_argument("--artifacts-dir", default=DEFAULT_ARTIFACTS_DIR,
                        help=f"Where to write videos and traces (default: {DEFAULT_ARTIFACTS_DIR})")
    args = parser.parse_args()

    if not args.self_check:
        parser.print_help()
        return
    asyncio.run(_self_check(args.artifacts_dir))


if __name__ == "__main__":
    main()
