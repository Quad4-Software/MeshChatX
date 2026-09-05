# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: process_crawler_task."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


async def process_crawler_task(app: Any, task, context=None):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v

    ctx = context or app.current_context
    if not ctx:
        return

    crawler = getattr(ctx, "crawler_manager", None)
    task_id = task["id"]
    destination_hash = task["destination_hash"]
    page_path = task["page_path"]
    depth = int(task.get("depth") or 0)

    if crawler and crawler.is_opted_out(destination_hash):
        ctx.database.misc.update_crawl_task(
            task_id,
            status="cancelled",
            updated_at=datetime.now(UTC),
        )
        return

    if crawler and not crawler.node_may_request_today(destination_hash):
        # Defer until the daily slot opens.
        ctx.database.misc.update_crawl_task(
            task_id,
            status="pending",
            next_retry_at=datetime.now(UTC) + timedelta(hours=6),
            updated_at=datetime.now(UTC),
        )
        return

    if crawler:
        ok, reason, hops = crawler.path_ready_for_crawl(destination_hash)
        if not ok:
            if reason == "no_path":
                ctx.database.misc.update_crawl_task(
                    task_id,
                    status="pending",
                    next_retry_at=datetime.now(UTC) + timedelta(minutes=15),
                    updated_at=datetime.now(UTC),
                )
                return
            crawler.mark_node_requested(
                destination_hash,
                hops=hops if hops < 64 else None,
                skipped_reason=reason,
            )
            ctx.database.misc.update_crawl_task(
                task_id,
                status="skipped",
                updated_at=datetime.now(UTC),
            )
            return
    else:
        hops = 0

    ctx.database.misc.update_crawl_task(
        task_id,
        status="crawling",
        last_retry_at=datetime.now(UTC),
    )

    print(
        f"Crawler: Archiving {destination_hash}:{page_path} "
        f"(Attempt {task['retry_count'] + 1}, depth={depth})",
    )

    done_event = asyncio.Event()
    success = [False]
    content_received = [None]
    failure_reason = ["timeout"]
    started = time.monotonic()

    def on_success(content):
        success[0] = True
        content_received[0] = content
        done_event.set()

    def on_failure(reason):
        failure_reason[0] = reason
        done_event.set()

    def on_progress(progress):
        pass

    downloader = NomadnetPageDownloader(
        destination_hash=bytes.fromhex(destination_hash),
        page_path=page_path,
        data=None,
        on_page_download_success=on_success,
        on_page_download_failure=on_failure,
        on_progress_update=on_progress,
        timeout=120,
        reticulum=getattr(app, "reticulum", None),
        **nomad_link_identity_kwargs(
            app,
            bytes.fromhex(destination_hash),
            private=False,
        ),
    )

    try:
        download_task = asyncio.create_task(downloader.download())
        try:
            await asyncio.wait_for(done_event.wait(), timeout=180)
        except TimeoutError:
            failure_reason[0] = "timeout"
            downloader.cancel()
        await download_task
    except Exception as e:
        print(
            f"Crawler: Error during download for {destination_hash}:{page_path}: {e}",
        )
        failure_reason[0] = str(e)
        done_event.set()

    elapsed_ms = (time.monotonic() - started) * 1000.0
    rtt_ms = None
    try:
        from meshchatx.src.backend.crawler_manager import link_rtt_ms
        from meshchatx.src.backend.nomadnet_downloader import get_cached_active_link

        link = get_cached_active_link(bytes.fromhex(destination_hash))
        rtt_ms = link_rtt_ms(link)
    except Exception:
        rtt_ms = None
    if rtt_ms is None:
        # Wall time for a single page request is a coarse stand-in.
        rtt_ms = elapsed_ms

    if crawler:
        crawler.mark_node_requested(
            destination_hash,
            rtt_ms=rtt_ms,
            hops=hops if isinstance(hops, int) else None,
        )

    if crawler and crawler.rtt_exceeds_limit(rtt_ms):
        print(
            f"Crawler: Skipping {destination_hash} (RTT {rtt_ms:.0f}ms above limit)",
        )
        crawler.mark_node_requested(
            destination_hash,
            rtt_ms=rtt_ms,
            hops=hops if isinstance(hops, int) else None,
            skipped_reason="rtt",
        )
        ctx.database.misc.update_crawl_task(
            task_id,
            status="skipped",
            updated_at=datetime.now(UTC),
        )
        return

    if success[0]:
        content = content_received[0] or ""
        from meshchatx.src.backend.crawler_manager import content_signals_nocrawl

        if content_signals_nocrawl(content):
            print(f"Crawler: Node {destination_hash} signalled nocrawl")
            if crawler:
                crawler.record_opt_out(
                    destination_hash,
                    reason="page_signal",
                    source="signal",
                )
            ctx.database.misc.update_crawl_task(
                task_id,
                status="cancelled",
                updated_at=datetime.now(UTC),
            )
            return

        print(f"Crawler: Successfully archived {destination_hash}:{page_path}")
        app.archive_page(
            destination_hash,
            page_path,
            content,
            is_manual=False,
            context=ctx,
        )
        ctx.database.misc.update_crawl_task(
            task_id,
            status="completed",
            updated_at=datetime.now(UTC),
        )
        if crawler:
            crawler.database.misc.upsert_crawl_node_stats(
                destination_hash,
                pages_indexed=crawler.pages_indexed_for_node(destination_hash),
            )
            for child in crawler.discover_child_paths(
                destination_hash,
                content,
                parent_depth=depth,
                parent_path=page_path,
            ):
                crawler.queue_if_allowed(
                    destination_hash,
                    child,
                    depth=depth + 1,
                    announced_recently=True,
                )
    else:
        print(
            f"Crawler: Failed to archive {destination_hash}:{page_path} - {failure_reason[0]}",
        )
        retry_count = task["retry_count"] + 1
        retry_delay = ctx.config.crawler_retry_delay_seconds.get()
        backoff_delay = retry_delay * (2 ** (retry_count - 1))
        next_retry_at = datetime.now(UTC) + timedelta(seconds=backoff_delay)
        ctx.database.misc.update_crawl_task(
            task_id,
            status="failed",
            retry_count=retry_count,
            next_retry_at=next_retry_at,
            updated_at=datetime.now(UTC),
        )
