<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
    }

    let { visible = true, config = {}, onupdatefield }: Props = $props();

    function emitNumber(key: string, value: string) {
        const num = Number(value);
        if (!Number.isNaN(num)) {
            onupdatefield?.({ key, value: num });
        }
    }

    function emitToggle(key: string, value: boolean) {
        onupdatefield?.({ key, value });
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Discovery</div>
                <h2>Smart Crawler</h2>
                <p>
                    Opt-in NomadNet indexer. Listens for announces, prefers nearby low-hop nodes, fetches at most one
                    page per node per day, stays within a small hop and RTT budget, and only walks a couple of levels
                    from the front page (hard cap 20 pages per node). Nodes can opt out forever with a
                    <code class="text-xs"># nocrawl</code> line on their index page, or from the Archives viewer.
                </p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <Toggle
                    id="crawler-enabled"
                    checked={Boolean(config.crawler_enabled)}
                    onchange={(val) => emitToggle("crawler_enabled", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">Enable Crawler</span>
                    <span class="setting-toggle__description">
                        Off by default. When on, archives announced Nomad nodes under the limits below.
                    </span>
                </span>
            </label>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-2">
                    <label for="crawler-max-hops" class="text-sm font-medium text-sem-fg block">Max hops</label>
                    <input
                        id="crawler-max-hops"
                        value={config.crawler_max_hops}
                        type="number"
                        min="1"
                        max="16"
                        class="input-field"
                        oninput={(e) => emitNumber("crawler_max_hops", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">Skip nodes farther than this path length (default 4).</div>
                </div>
                <div class="space-y-2">
                    <label for="crawler-max-rtt" class="text-sm font-medium text-sem-fg block">Max link RTT (ms)</label>
                    <input
                        id="crawler-max-rtt"
                        value={config.crawler_max_rtt_ms}
                        type="number"
                        min="100"
                        max="60000"
                        class="input-field"
                        oninput={(e) => emitNumber("crawler_max_rtt_ms", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">
                        Do not index nodes whose link RTT is above this (default 2500).
                    </div>
                </div>
                <div class="space-y-2">
                    <label for="crawler-max-depth" class="text-sm font-medium text-sem-fg block">Max depth</label>
                    <input
                        id="crawler-max-depth"
                        value={config.crawler_max_depth}
                        type="number"
                        min="0"
                        max="2"
                        class="input-field"
                        oninput={(e) => emitNumber("crawler_max_depth", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">
                        0 is front page only. 2 is front page plus two levels down.
                    </div>
                </div>
                <div class="space-y-2">
                    <label for="crawler-max-pages" class="text-sm font-medium text-sem-fg block"
                        >Max pages per node</label
                    >
                    <input
                        id="crawler-max-pages"
                        value={config.crawler_max_pages_per_node}
                        type="number"
                        min="1"
                        max="20"
                        class="input-field"
                        oninput={(e) => emitNumber("crawler_max_pages_per_node", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">Hard cap on indexed paths per destination (default 20).</div>
                </div>
                <div class="space-y-2">
                    <label for="crawler-req-per-day" class="text-sm font-medium text-sem-fg block"
                        >Requests per day per node</label
                    >
                    <input
                        id="crawler-req-per-day"
                        value={config.crawler_requests_per_day_per_node}
                        type="number"
                        min="1"
                        max="3"
                        class="input-field"
                        oninput={(e) =>
                            emitNumber("crawler_requests_per_day_per_node", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">
                        Default 1. Keeps scrape load trivial on constrained links.
                    </div>
                </div>
                <div class="space-y-2">
                    <label for="crawler-refresh-days" class="text-sm font-medium text-sem-fg block"
                        >Homepage refresh (days)</label
                    >
                    <input
                        id="crawler-refresh-days"
                        value={config.crawler_refresh_days}
                        type="number"
                        min="1"
                        max="365"
                        class="input-field"
                        oninput={(e) => emitNumber("crawler_refresh_days", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">
                        Re-queue a completed homepage after this many days (default 30).
                    </div>
                </div>
                <div class="space-y-2">
                    <label for="crawler-max-retries" class="text-sm font-medium text-sem-fg block">Max Retries</label>
                    <input
                        id="crawler-max-retries"
                        value={config.crawler_max_retries}
                        type="number"
                        min="1"
                        max="10"
                        class="input-field"
                        oninput={(e) => emitNumber("crawler_max_retries", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">Attempts before giving up.</div>
                </div>
                <div class="space-y-2">
                    <label for="crawler-retry-delay" class="text-sm font-medium text-sem-fg block"
                        >Retry Delay (seconds)</label
                    >
                    <input
                        id="crawler-retry-delay"
                        value={config.crawler_retry_delay_seconds}
                        type="number"
                        min="60"
                        class="input-field"
                        oninput={(e) => emitNumber("crawler_retry_delay_seconds", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">Wait time between attempts.</div>
                </div>
            </div>

            <div class="space-y-2">
                <label for="crawler-max-concurrent" class="text-sm font-medium text-sem-fg block"
                    >Max Concurrent Crawls</label
                >
                <input
                    id="crawler-max-concurrent"
                    value={config.crawler_max_concurrent}
                    type="number"
                    min="1"
                    max="2"
                    class="input-field"
                    oninput={(e) => emitNumber("crawler_max_concurrent", (e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">Capped at 2. Prefer 1 on LoRa-class links.</div>
            </div>
        </div>
    </section>
{/if}
