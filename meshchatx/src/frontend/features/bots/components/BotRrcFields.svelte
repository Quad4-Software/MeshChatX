<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { defaultRrcDraft, type BotRrcDraft } from "../lib/botDrafts.js";

    interface Props {
        draft?: BotRrcDraft;
    }

    let { draft = $bindable(defaultRrcDraft()) }: Props = $props();

    function patch(update: Partial<BotRrcDraft>): void {
        draft = { ...(draft || defaultRrcDraft()), ...update };
    }
</script>

<div class="space-y-3">
    <div>
        <label class="glass-label" for="bot-rrc-hub">{t("bots.rrc_hub_hash")}</label>
        <input
            id="bot-rrc-hub"
            value={draft.hub}
            type="text"
            class="input-field font-mono text-xs"
            maxlength="64"
            spellcheck="false"
            placeholder={t("bots.rrc_hub_hash_placeholder")}
            oninput={(e) => patch({ hub: (e.target as HTMLInputElement).value })}
        />
    </div>
    <div>
        <label class="glass-label" for="bot-rrc-rooms">{t("bots.rrc_rooms")}</label>
        <input
            id="bot-rrc-rooms"
            value={draft.rooms}
            type="text"
            class="input-field"
            placeholder={t("bots.rrc_rooms_placeholder")}
            oninput={(e) => patch({ rooms: (e.target as HTMLInputElement).value })}
        />
    </div>
    <div class="grid grid-cols-2 gap-3">
        <div>
            <label class="glass-label" for="bot-rrc-nick">{t("bots.rrc_nick")}</label>
            <input
                id="bot-rrc-nick"
                value={draft.nick}
                type="text"
                class="input-field"
                maxlength="32"
                oninput={(e) => patch({ nick: (e.target as HTMLInputElement).value })}
            />
        </div>
        <div>
            <label class="glass-label" for="bot-rrc-prefix">{t("bots.rrc_prefix")}</label>
            <input
                id="bot-rrc-prefix"
                value={draft.prefix}
                type="text"
                class="input-field font-mono"
                maxlength="4"
                oninput={(e) => patch({ prefix: (e.target as HTMLInputElement).value })}
            />
        </div>
    </div>
    <div class="flex items-center justify-between gap-3">
        <label class="text-sm font-medium text-sem-fg" for="bot-rrc-mention-only">{t("bots.rrc_mention_only")}</label>
        <input
            id="bot-rrc-mention-only"
            type="checkbox"
            class="size-4 accent-blue-600"
            checked={draft.mention_only}
            onchange={(e) => patch({ mention_only: (e.target as HTMLInputElement).checked })}
        />
    </div>
    <div>
        <label class="glass-label" for="bot-rrc-rate">{t("bots.rrc_rate_seconds")}</label>
        <input
            id="bot-rrc-rate"
            value={draft.rate_seconds}
            type="number"
            min="0"
            max="3600"
            class="input-field"
            oninput={(e) => patch({ rate_seconds: (e.target as HTMLInputElement).value })}
        />
        <p class="text-xs text-sem-fg-muted mt-1">
            {t("bots.rrc_rate_seconds_hint")}
        </p>
    </div>
</div>
