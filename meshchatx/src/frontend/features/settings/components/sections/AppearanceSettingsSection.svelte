<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ThemeColorsCard from "../ThemeColorsCard.svelte";
    import ChatAppearanceCard from "../ChatAppearanceCard.svelte";
    import MessageBubbleColorsCard from "../MessageBubbleColorsCard.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        detailedOutboundSendStatus?: boolean;
        outboundTransferProgressEnabled?: boolean;
        messageTimestampGroupingEnabled?: boolean;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onthemechange?: () => void;
        onthemepresetchange?: (presetId?: string) => void;
        onaccentcolorchange?: () => void;
        oncustomcanvascolorchange?: () => void;
        oncustomsurfacecolorchange?: () => void;
        onmessagessidebarpositionchange?: () => void;
        onappsidebarlayoutchange?: () => void;
        onmessagefontsizechange?: () => void;
        onmessageiconsizechange?: () => void;
        onuitransparencychange?: () => void;
        onuiglassenabledchange?: () => void;
        onmessagesmultipaneenabledchange?: () => void;
        onnomadtabsenabledchange?: () => void;
        onrrcenabledchange?: () => void;
        onrrcunreadbadgesenabledchange?: () => void;
        onresetappearancedefaults?: () => void;
        ondetailedoutboundsendstatuschange?: (event: Event) => void;
        onoutboundtransferprogressenabledchange?: (event: Event) => void;
        onmessagetimestampgroupingchange?: (event: Event) => void;
        onbubblecolorchange?: (type: string) => void;
    }

    let {
        visible = true,
        config = {},
        detailedOutboundSendStatus = false,
        outboundTransferProgressEnabled = false,
        messageTimestampGroupingEnabled = false,
        onupdatefield,
        onthemechange,
        onthemepresetchange,
        onaccentcolorchange,
        oncustomcanvascolorchange,
        oncustomsurfacecolorchange,
        onmessagessidebarpositionchange,
        onappsidebarlayoutchange,
        onmessagefontsizechange,
        onmessageiconsizechange,
        onuitransparencychange,
        onuiglassenabledchange,
        onmessagesmultipaneenabledchange,
        onnomadtabsenabledchange,
        onrrcenabledchange,
        onrrcunreadbadgesenabledchange,
        onresetappearancedefaults,
        ondetailedoutboundsendstatuschange,
        onoutboundtransferprogressenabledchange,
        onmessagetimestampgroupingchange,
        onbubblecolorchange,
    }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{t("app.appearance")}</div>
                <h2>{t("app.appearance")}</h2>
                <p>{t("app.appearance_description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-6">
            <ThemeColorsCard
                {config}
                {onupdatefield}
                {onthemechange}
                {onthemepresetchange}
                {onaccentcolorchange}
                {oncustomcanvascolorchange}
                {oncustomsurfacecolorchange}
            />

            <ChatAppearanceCard
                {config}
                {detailedOutboundSendStatus}
                {outboundTransferProgressEnabled}
                {messageTimestampGroupingEnabled}
                {onupdatefield}
                {onmessagessidebarpositionchange}
                {onappsidebarlayoutchange}
                {onmessagefontsizechange}
                {onmessageiconsizechange}
                {onuitransparencychange}
                {onuiglassenabledchange}
                {onmessagesmultipaneenabledchange}
                {onnomadtabsenabledchange}
                {onrrcenabledchange}
                {onrrcunreadbadgesenabledchange}
                {onresetappearancedefaults}
                {ondetailedoutboundsendstatuschange}
                {onoutboundtransferprogressenabledchange}
                {onmessagetimestampgroupingchange}
            />

            <MessageBubbleColorsCard {config} {onupdatefield} {onbubblecolorchange} />
        </div>
    </section>
{/if}
