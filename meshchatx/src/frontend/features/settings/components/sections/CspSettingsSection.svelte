<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
    }

    let { visible = true, config = {}, onupdatefield }: Props = $props();

    function emitValue(key: string, value: string) {
        onupdatefield?.({ key, value });
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Security</div>
                <h2>{t("app.csp_settings")}</h2>
                <p>{t("app.csp_description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="space-y-2">
                <label for="csp-connect-src" class="text-sm font-medium text-sem-fg block">
                    {t("app.csp_extra_connect_src")}
                </label>
                <input
                    id="csp-connect-src"
                    value={config.csp_extra_connect_src || ""}
                    type="text"
                    class="input-field font-mono text-xs"
                    placeholder="https://api.example.com, wss://socket.example.com"
                    oninput={(e) => emitValue("csp_extra_connect_src", (e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">
                    {t("app.csp_extra_connect_src_description")}
                </div>
            </div>

            <div class="space-y-2">
                <label for="csp-img-src" class="text-sm font-medium text-sem-fg block">
                    {t("app.csp_extra_img_src")}
                </label>
                <input
                    id="csp-img-src"
                    value={config.csp_extra_img_src || ""}
                    type="text"
                    class="input-field font-mono text-xs"
                    placeholder="https://tiles.example.com, https://cdn.example.com"
                    oninput={(e) => emitValue("csp_extra_img_src", (e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">
                    {t("app.csp_extra_img_src_description")}
                </div>
            </div>

            <div class="space-y-2">
                <label for="csp-frame-src" class="text-sm font-medium text-sem-fg block">
                    {t("app.csp_extra_frame_src")}
                </label>
                <input
                    id="csp-frame-src"
                    value={config.csp_extra_frame_src || ""}
                    type="text"
                    class="input-field font-mono text-xs"
                    placeholder="https://video.example.com"
                    oninput={(e) => emitValue("csp_extra_frame_src", (e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">
                    {t("app.csp_extra_frame_src_description")}
                </div>
            </div>

            <div class="space-y-2">
                <label for="csp-script-src" class="text-sm font-medium text-sem-fg block">
                    {t("app.csp_extra_script_src")}
                </label>
                <input
                    id="csp-script-src"
                    value={config.csp_extra_script_src || ""}
                    type="text"
                    class="input-field font-mono text-xs"
                    placeholder="https://scripts.example.com"
                    oninput={(e) => emitValue("csp_extra_script_src", (e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">
                    {t("app.csp_extra_script_src_description")}
                </div>
            </div>

            <div class="space-y-2">
                <label for="csp-style-src" class="text-sm font-medium text-sem-fg block">
                    {t("app.csp_extra_style_src")}
                </label>
                <input
                    id="csp-style-src"
                    value={config.csp_extra_style_src || ""}
                    type="text"
                    class="input-field font-mono text-xs"
                    placeholder="https://fonts.example.com"
                    oninput={(e) => emitValue("csp_extra_style_src", (e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">
                    {t("app.csp_extra_style_src_description")}
                </div>
            </div>
        </div>
    </section>
{/if}
