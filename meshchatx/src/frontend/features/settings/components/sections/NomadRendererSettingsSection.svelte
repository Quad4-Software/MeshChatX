<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        micronWasmBundledInBuild?: boolean;
        micronWasmReleaseLabel?: string;
        micronWasmReleaseIsOverride?: boolean;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onopenmicronwasmmodal?: () => void;
    }

    let {
        visible = true,
        config = {},
        micronWasmBundledInBuild = false,
        micronWasmReleaseLabel = "",
        micronWasmReleaseIsOverride = false,
        onupdatefield,
        onopenmicronwasmmodal,
    }: Props = $props();

    function emitToggle(key: string, value: boolean) {
        onupdatefield?.({ key, value });
    }

    function emitString(key: string, value: string) {
        onupdatefield?.({ key, value });
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Browsing</div>
                <h2>NomadNet browser renderer</h2>
                <p>
                    Control how Micron, Markdown, HTML, and plain text pages are rendered in the Nomad browser and
                    archives. Set the default page path when opening a node without a path.
                </p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label class="setting-toggle">
                <Toggle
                    id="nomad-render-markdown"
                    checked={Boolean(config.nomad_render_markdown_enabled)}
                    onchange={(val) => emitToggle("nomad_render_markdown_enabled", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">Render Markdown (.md) pages</span>
                    <span class="setting-toggle__description">
                        When off, .md files are shown as escaped text instead of formatted Markdown.
                    </span>
                </span>
            </label>
            <label class="setting-toggle">
                <Toggle
                    id="nomad-render-html"
                    checked={Boolean(config.nomad_render_html_enabled)}
                    onchange={(val) => emitToggle("nomad_render_html_enabled", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">Render HTML (.html) pages</span>
                    <span class="setting-toggle__description">
                        When off, .html files are shown as escaped text instead of sanitized HTML.
                    </span>
                </span>
            </label>
            <label class="setting-toggle">
                <Toggle
                    id="nomad-render-plaintext"
                    checked={Boolean(config.nomad_render_plaintext_enabled)}
                    onchange={(val) => emitToggle("nomad_render_plaintext_enabled", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">Render plain text (.txt) pages</span>
                    <span class="setting-toggle__description">
                        When off, .txt files use a simpler escaped layout.
                    </span>
                </span>
            </label>
            {#if micronWasmBundledInBuild}
                <label class="setting-toggle">
                    <Toggle
                        id="nomad-micron-wasm"
                        checked={Boolean(config.nomad_micron_wasm_enabled)}
                        onchange={(val) => emitToggle("nomad_micron_wasm_enabled", val)}
                    />
                    <span class="setting-toggle__label">
                        <span class="setting-toggle__title">
                            {t("settings.nomad_micron_wasm_title")}
                        </span>
                        <span class="setting-toggle__description">
                            {t("settings.nomad_micron_wasm_desc_before_link")}
                            <a
                                class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 underline underline-offset-2"
                                href="https://github.com/Quad4-Software/micron-parser-go"
                                target="_blank"
                                rel="noopener noreferrer">{t("settings.nomad_micron_wasm_link_label")}</a
                            >{t("settings.nomad_micron_wasm_desc_after_link")}
                        </span>
                    </span>
                </label>
            {/if}
            {#if micronWasmBundledInBuild && config.nomad_micron_wasm_enabled}
                <div
                    class="space-y-2 rounded-lg border border-gray-200 bg-gray-50/80 p-3 dark:border-zinc-700 dark:bg-zinc-900/50"
                >
                    <label for="nomad-micron-default-engine" class="text-sm font-medium text-sem-fg block">
                        {t("settings.nomad_micron_default_engine_title")}
                    </label>
                    <p class="text-xs text-sem-fg-muted">
                        {t("settings.nomad_micron_default_engine_desc")}
                    </p>
                    <select
                        id="nomad-micron-default-engine"
                        value={config.nomad_micron_default_engine === "wasm" ? "wasm" : "js"}
                        class="input-field max-w-xl"
                        onchange={(e) =>
                            emitString("nomad_micron_default_engine", (e.target as HTMLSelectElement).value)}
                    >
                        <option value="js">
                            {t("settings.nomad_micron_default_engine_option_js")}
                        </option>
                        <option value="wasm">
                            {micronWasmReleaseLabel
                                ? t("settings.nomad_micron_default_engine_option_wasm_version", {
                                      version: micronWasmReleaseLabel,
                                  })
                                : t("settings.nomad_micron_default_engine_option_wasm")}
                        </option>
                    </select>
                    {#if micronWasmReleaseLabel}
                        <div class="text-xs text-sem-fg-muted font-mono">
                            {t("settings.micron_wasm_installed_version", {
                                version: micronWasmReleaseLabel,
                            })}
                            <span class="opacity-80">
                                ({micronWasmReleaseIsOverride
                                    ? t("settings.micron_wasm_version_source_override")
                                    : t("settings.micron_wasm_version_source_bundled")})
                            </span>
                        </div>
                    {/if}
                </div>
            {/if}
            {#if micronWasmBundledInBuild}
                <div class="mt-2">
                    <button type="button" class="primary-chip text-sm cursor-pointer" onclick={onopenmicronwasmmodal}>
                        {t("settings.micron_wasm_update_open_btn")}
                    </button>
                </div>
            {/if}
            <div class="space-y-2">
                <label for="nomad-default-page-path" class="text-sm font-medium text-sem-fg block">
                    Default page path (no URL path)
                </label>
                <select
                    id="nomad-default-page-path"
                    value={config.nomad_default_page_path || "/page/index.mu"}
                    class="input-field max-w-xl"
                    onchange={(e) => emitString("nomad_default_page_path", (e.target as HTMLSelectElement).value)}
                >
                    <option value="/page/index.mu">/page/index.mu (Micron)</option>
                    <option value="/page/index.html">/page/index.html (HTML)</option>
                    <option value="/page/index.md">/page/index.md (Markdown)</option>
                    <option value="/page/index.txt">/page/index.txt (plain text)</option>
                </select>
                <div class="text-xs text-sem-fg-muted">
                    Used when opening a Nomad node without a path, for hash-only links, and for the Smart Crawler
                    homepage fetch.
                </div>
            </div>
        </div>
    </section>
{/if}
