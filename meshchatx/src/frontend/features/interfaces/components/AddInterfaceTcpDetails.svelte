<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "./Toggle.svelte";
    import BundledDocsHint from "./BundledDocsHint.svelte";
    import { t } from "../../../js/i18n.js";
    import { RETICULUM_MIN_FIXED_MTU } from "../lib/constants.js";

    interface Props {
        targetHost: string | null;
        targetPort: number | string | null;
        kissFraming: boolean;
        i2pTunneled: boolean;
        bootstrapOnly: boolean;
        connectTimeout: number | string | null;
        maxReconnectTries: number | string | null;
        fixedMtu: number | string | null;
        ontargethostchange?: (val: string) => void;
        ontargetportchange?: (val: string) => void;
        onkissframingchange?: (val: boolean) => void;
        oni2ptunneledchange?: (val: boolean) => void;
        onbootstraponlychange?: (val: boolean) => void;
        onconnecttimeoutchange?: (val: string) => void;
        onmaxreconnecttrieschange?: (val: string) => void;
        onfixedmtuchange?: (val: string) => void;
    }

    let {
        targetHost = null,
        targetPort = null,
        kissFraming = false,
        i2pTunneled = false,
        bootstrapOnly = true,
        connectTimeout = null,
        maxReconnectTries = null,
        fixedMtu = null,
        ontargethostchange,
        ontargetportchange,
        onkissframingchange,
        oni2ptunneledchange,
        onbootstraponlychange,
        onconnecttimeoutchange,
        onmaxreconnecttrieschange,
        onfixedmtuchange,
    }: Props = $props();
</script>

<div class="space-y-4">
    <div>
        <label for="tcp-target-host" class="glass-label block font-medium mb-1">Target Host</label>
        <input
            id="tcp-target-host"
            value={targetHost ?? ""}
            type="text"
            placeholder="e.g. 1.2.3.4 or example.com"
            class="input-field"
            oninput={(e) => ontargethostchange?.((e.target as HTMLInputElement).value)}
        />
    </div>
    <div>
        <label for="tcp-target-port" class="glass-label block font-medium mb-1">Target Port</label>
        <input
            id="tcp-target-port"
            value={targetPort ?? ""}
            type="number"
            placeholder="4242"
            class="input-field"
            oninput={(e) => ontargetportchange?.((e.target as HTMLInputElement).value)}
        />
    </div>
    <div class="flex items-center gap-2">
        <Toggle id="tcp-kiss-framing" checked={kissFraming} onchange={(val) => onkissframingchange?.(val)} />
        <label for="tcp-kiss-framing" class="cursor-pointer mb-0! text-sm">
            Use KISS framing (legacy compatibility)
        </label>
    </div>
    <div class="flex items-center gap-2">
        <Toggle id="tcp-i2p-tunneled" checked={i2pTunneled} onchange={(val) => oni2ptunneledchange?.(val)} />
        <label for="tcp-i2p-tunneled" class="cursor-pointer mb-0! text-sm"> I2P Tunneled (target is an I2P b32) </label>
    </div>
    <div class="flex items-start gap-2">
        <Toggle id="tcp-bootstrap-only" checked={bootstrapOnly} onchange={(val) => onbootstraponlychange?.(val)} />
        <div class="min-w-0">
            <label for="tcp-bootstrap-only" class="cursor-pointer mb-0! text-sm block">
                {t("interfaces.discovery_default_bootstrap_only")}
            </label>
            <BundledDocsHint paragraphClass="text-xs text-sem-fg-muted mt-0.5" />
        </div>
    </div>
    <div class="grid grid-cols-3 gap-3">
        <div>
            <label for="tcp-connect-timeout" class="glass-label block font-medium mb-1">Connect Timeout (s)</label>
            <input
                id="tcp-connect-timeout"
                value={connectTimeout ?? ""}
                type="number"
                min="0"
                placeholder="default"
                class="input-field"
                oninput={(e) => onconnecttimeoutchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="tcp-max-reconnect-tries" class="glass-label block font-medium mb-1">Max Reconnect Tries</label>
            <input
                id="tcp-max-reconnect-tries"
                value={maxReconnectTries ?? ""}
                type="number"
                min="0"
                placeholder="default"
                class="input-field"
                oninput={(e) => onmaxreconnecttrieschange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="tcp-fixed-mtu" class="glass-label block font-medium mb-1">Fixed MTU</label>
            <input
                id="tcp-fixed-mtu"
                value={fixedMtu ?? ""}
                type="number"
                min={RETICULUM_MIN_FIXED_MTU}
                placeholder="auto"
                class="input-field"
                oninput={(e) => onfixedmtuchange?.((e.target as HTMLInputElement).value)}
            />
            <p class="mt-1 text-xs text-sem-fg-muted">
                {t("interfaces.fixed_mtu_hint", { min: RETICULUM_MIN_FIXED_MTU })}
            </p>
        </div>
    </div>
</div>
