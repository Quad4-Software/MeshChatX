<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        listenIp: string | null;
        listenPort: number | string | null;
        forwardIp: string | null;
        forwardPort: number | string | null;
        device: string | null;
        onlistenipchange?: (val: string) => void;
        onlistenportchange?: (val: string) => void;
        onforwardipchange?: (val: string) => void;
        onforwardportchange?: (val: string) => void;
        ondevicechange?: (val: string) => void;
    }

    let {
        listenIp = null,
        listenPort = null,
        forwardIp = null,
        forwardPort = null,
        device = null,
        onlistenipchange,
        onlistenportchange,
        onforwardipchange,
        onforwardportchange,
        ondevicechange,
    }: Props = $props();
</script>

<div class="space-y-4">
    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="udp-listen-ip" class="glass-label block font-medium mb-1">Listen IP</label>
            <input
                id="udp-listen-ip"
                value={listenIp ?? ""}
                type="text"
                placeholder="0.0.0.0"
                class="input-field"
                oninput={(e) => onlistenipchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="udp-listen-port" class="glass-label block font-medium mb-1">Listen Port</label>
            <input
                id="udp-listen-port"
                value={listenPort ?? ""}
                type="number"
                placeholder="4242"
                class="input-field"
                oninput={(e) => onlistenportchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    </div>
    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="udp-forward-ip" class="glass-label block font-medium mb-1">Forward IP</label>
            <input
                id="udp-forward-ip"
                value={forwardIp ?? ""}
                type="text"
                placeholder="255.255.255.255"
                class="input-field"
                oninput={(e) => onforwardipchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="udp-forward-port" class="glass-label block font-medium mb-1">Forward Port</label>
            <input
                id="udp-forward-port"
                value={forwardPort ?? ""}
                type="number"
                placeholder="4242"
                class="input-field"
                oninput={(e) => onforwardportchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    </div>
    <div>
        <label for="udp-device" class="glass-label block font-medium mb-1">Device (optional)</label>
        <input
            id="udp-device"
            value={device ?? ""}
            type="text"
            placeholder="e.g. eth0 or wlan0"
            class="input-field"
            oninput={(e) => ondevicechange?.((e.target as HTMLInputElement).value)}
        />
    </div>
</div>
