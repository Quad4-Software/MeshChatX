<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "./Toggle.svelte";

    interface Props {
        mode: "client" | "server";
        serverUrl: string | null;
        pollInterval: number | string | null;
        listenHost: string | null;
        listenPort: number | string | null;
        mtu: number | string | null;
        httpVersion: number | string | null;
        userAgent: string | null;
        checkUserAgent: boolean;
        tlsVerify: boolean;
        tlsCertfile: string | null;
        tlsKeyfile: string | null;
        onmodechange?: (val: "client" | "server") => void;
        onserverurlchange?: (val: string) => void;
        onpollintervalchange?: (val: string) => void;
        onlistenhostchange?: (val: string) => void;
        onlistenportchange?: (val: string) => void;
        onmtuchange?: (val: string) => void;
        onhttpversionchange?: (val: string) => void;
        onuseragentchange?: (val: string) => void;
        oncheckuseragentchange?: (val: boolean) => void;
        ontlsverifychange?: (val: boolean) => void;
        ontlscertfilechange?: (val: string) => void;
        ontlskeyfilechange?: (val: string) => void;
    }

    let {
        mode = "client",
        serverUrl = null,
        pollInterval = 0.1,
        listenHost = "0.0.0.0",
        listenPort = 8080,
        mtu = 4096,
        httpVersion = 1,
        userAgent = "RNS-HTTP-Tunnel/1.0",
        checkUserAgent = true,
        tlsVerify = true,
        tlsCertfile = null,
        tlsKeyfile = null,
        onmodechange,
        onserverurlchange,
        onpollintervalchange,
        onlistenhostchange,
        onlistenportchange,
        onmtuchange,
        onhttpversionchange,
        onuseragentchange,
        oncheckuseragentchange,
        ontlsverifychange,
        ontlscertfilechange,
        ontlskeyfilechange,
    }: Props = $props();
</script>

<div class="space-y-4">
    <!-- Mode Toggle: Client vs Server -->
    <div class="flex items-center gap-2">
        <button
            type="button"
            class="text-xs py-1 px-3 rounded-full border transition-colors {mode === 'client'
                ? 'bg-teal-500/10 border-teal-500 text-teal-700 dark:text-teal-400 font-bold'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => onmodechange?.("client")}
        >
            Client Mode
        </button>
        <button
            type="button"
            class="text-xs py-1 px-3 rounded-full border transition-colors {mode === 'server'
                ? 'bg-teal-500/10 border-teal-500 text-teal-700 dark:text-teal-400 font-bold'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => onmodechange?.("server")}
        >
            Server Mode
        </button>
    </div>

    {#if mode === "client"}
        <div>
            <label for="http-server-url" class="glass-label block font-medium mb-1">Server URL</label>
            <input
                id="http-server-url"
                value={serverUrl ?? ""}
                type="text"
                placeholder="https://example.com:8080/rns"
                class="input-field"
                oninput={(e) => onserverurlchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="http-poll-interval" class="glass-label block font-medium mb-1">Poll Interval (seconds)</label>
            <input
                id="http-poll-interval"
                value={pollInterval ?? 0.1}
                type="number"
                step="0.05"
                min="0.01"
                class="input-field"
                oninput={(e) => onpollintervalchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    {:else}
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label for="http-listen-host" class="glass-label block font-medium mb-1">Listen Host</label>
                <input
                    id="http-listen-host"
                    value={listenHost ?? "0.0.0.0"}
                    type="text"
                    placeholder="0.0.0.0"
                    class="input-field"
                    oninput={(e) => onlistenhostchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="http-listen-port" class="glass-label block font-medium mb-1">Listen Port</label>
                <input
                    id="http-listen-port"
                    value={listenPort ?? 8080}
                    type="number"
                    placeholder="8080"
                    class="input-field"
                    oninput={(e) => onlistenportchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div>
                <label for="http-tls-certfile" class="glass-label block font-medium mb-1"
                    >TLS Cert File (optional)</label
                >
                <input
                    id="http-tls-certfile"
                    value={tlsCertfile ?? ""}
                    type="text"
                    placeholder="/path/to/cert.pem"
                    class="input-field"
                    oninput={(e) => ontlscertfilechange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="http-tls-keyfile" class="glass-label block font-medium mb-1">TLS Key File (optional)</label>
                <input
                    id="http-tls-keyfile"
                    value={tlsKeyfile ?? ""}
                    type="text"
                    placeholder="/path/to/key.pem"
                    class="input-field"
                    oninput={(e) => ontlskeyfilechange?.((e.target as HTMLInputElement).value)}
                />
            </div>
        </div>
    {/if}

    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="http-mtu" class="glass-label block font-medium mb-1">HTTP MTU</label>
            <input
                id="http-mtu"
                value={mtu ?? 4096}
                type="number"
                class="input-field"
                oninput={(e) => onmtuchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="http-version" class="glass-label block font-medium mb-1">HTTP Version</label>
            <select
                id="http-version"
                value={String(httpVersion ?? 1)}
                class="input-field"
                onchange={(e) => onhttpversionchange?.((e.target as HTMLSelectElement).value)}
            >
                <option value="1">HTTP/1.1</option>
                <option value="2">HTTP/2</option>
            </select>
        </div>
    </div>

    <div>
        <label for="http-user-agent" class="glass-label block font-medium mb-1">User Agent</label>
        <input
            id="http-user-agent"
            value={userAgent ?? "RNS-HTTP-Tunnel/1.0"}
            type="text"
            class="input-field font-mono text-xs"
            oninput={(e) => onuseragentchange?.((e.target as HTMLInputElement).value)}
        />
    </div>

    <div class="flex flex-wrap items-center gap-4 pt-2">
        <div class="flex items-center gap-2">
            <Toggle
                id="http-check-user-agent"
                checked={checkUserAgent}
                onchange={(val) => oncheckuseragentchange?.(val)}
            />
            <label for="http-check-user-agent" class="cursor-pointer mb-0! text-xs font-medium">Verify User Agent</label
            >
        </div>
        <div class="flex items-center gap-2">
            <Toggle id="http-tls-verify" checked={tlsVerify} onchange={(val) => ontlsverifychange?.(val)} />
            <label for="http-tls-verify" class="cursor-pointer mb-0! text-xs font-medium">TLS Verification</label>
        </div>
    </div>
</div>
