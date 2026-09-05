<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { Comport, InterfaceModule, KernelInterface } from "../lib/types.js";
    import AddInterfaceTcpDetails from "./AddInterfaceTcpDetails.svelte";
    import AddInterfaceBackboneDetails from "./AddInterfaceBackboneDetails.svelte";
    import AddInterfaceUdpDetails from "./AddInterfaceUdpDetails.svelte";
    import AddInterfaceI2pDetails from "./AddInterfaceI2pDetails.svelte";
    import AddInterfaceRNodeDetails from "./AddInterfaceRNodeDetails.svelte";
    import AddInterfaceSerialDetails from "./AddInterfaceSerialDetails.svelte";
    import AddInterfaceAutoDetails from "./AddInterfaceAutoDetails.svelte";
    import AddInterfaceHttpDetails from "./AddInterfaceHttpDetails.svelte";
    import AddInterfaceExternalDetails from "./AddInterfaceExternalDetails.svelte";

    interface Props {
        interfaceType: string | null;
        form: Record<string, any>;
        comports: Comport[];
        comportsLoading: boolean;
        hostKernelInterfaces: KernelInterface[];
        hostKernelInterfacesLoading: boolean;
        installedModules: InterfaceModule[];
        modulesPath: string;
        customIsBusy: boolean;
        onpatch: (patch: Record<string, any>) => void;
        onrefreshcomports: () => void;
        onuploadmodule: (file: File) => void;
        ondeletemodule: (typeName: string) => void;
    }

    let {
        interfaceType,
        form,
        comports,
        comportsLoading,
        hostKernelInterfaces,
        hostKernelInterfacesLoading,
        installedModules,
        modulesPath,
        customIsBusy,
        onpatch,
        onrefreshcomports,
        onuploadmodule,
        ondeletemodule,
    }: Props = $props();
</script>

<div class="space-y-6">
    <div class="flex items-center gap-2 pb-2 border-b border-sem-border">
        <MaterialDesignIcon iconName="cog-outline" class="w-5 h-5 text-gray-400" />
        <h3 class="font-bold text-sem-fg">Connection Details</h3>
    </div>

    {#if !interfaceType}
        <div
            class="h-48 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-sem-border rounded-3xl"
        >
            <MaterialDesignIcon
                iconName="arrow-left-bold"
                class="w-10 h-10 text-gray-200 dark:text-zinc-800 animate-bounce-left"
            />
            <p class="text-sm text-gray-400 dark:text-zinc-600 mt-2">
                Select an interface type to configure connection settings.
            </p>
        </div>
    {:else if interfaceType === "TCPClientInterface"}
        <AddInterfaceTcpDetails
            targetHost={form.targetHost}
            targetPort={form.targetPort}
            kissFraming={form.kissFraming}
            i2pTunneled={form.i2pTunneled}
            bootstrapOnly={form.bootstrapOnly}
            connectTimeout={form.connectTimeout}
            maxReconnectTries={form.maxReconnectTries}
            fixedMtu={form.fixedMtu}
            ontargethostchange={(v) => onpatch({ targetHost: v })}
            ontargetportchange={(v) => onpatch({ targetPort: v })}
            onkissframingchange={(v) => onpatch({ kissFraming: v })}
            oni2ptunneledchange={(v) => onpatch({ i2pTunneled: v })}
            onbootstraponlychange={(v) => onpatch({ bootstrapOnly: v })}
            onconnecttimeoutchange={(v) => onpatch({ connectTimeout: v })}
            onmaxreconnecttrieschange={(v) => onpatch({ maxReconnectTries: v })}
            onfixedmtuchange={(v) => onpatch({ fixedMtu: v })}
        />
    {:else if interfaceType === "BackboneInterface"}
        <AddInterfaceBackboneDetails
            listenMode={form.backboneListenMode}
            targetHost={form.targetHost}
            targetPort={form.targetPort}
            transportIdentity={form.transportIdentity}
            bootstrapOnly={form.bootstrapOnly}
            listenIp={form.listenIp}
            listenPort={form.listenPort}
            listenDevice={form.listenDevice}
            connectTimeout={form.connectTimeout}
            maxReconnectTries={form.maxReconnectTries}
            fixedMtu={form.fixedMtu}
            blockFastFlapping={form.blockFastFlapping}
            fastFlappingBlockTime={form.fastFlappingBlockTime}
            fastFlappingThreshold={form.fastFlappingThreshold}
            fastFlappingGrace={form.fastFlappingGrace}
            {hostKernelInterfaces}
            {hostKernelInterfacesLoading}
            onlistenmodechange={(v) => onpatch({ backboneListenMode: v })}
            ontargethostchange={(v) => onpatch({ targetHost: v })}
            ontargetportchange={(v) => onpatch({ targetPort: v })}
            ontransportidentitychange={(v) => onpatch({ transportIdentity: v })}
            onbootstraponlychange={(v) => onpatch({ bootstrapOnly: v })}
            onlistenipchange={(v) => onpatch({ listenIp: v })}
            onlistenportchange={(v) => onpatch({ listenPort: v })}
            onlistendevicechange={(v) => onpatch({ listenDevice: v })}
            onconnecttimeoutchange={(v) => onpatch({ connectTimeout: v })}
            onmaxreconnecttrieschange={(v) => onpatch({ maxReconnectTries: v })}
            onfixedmtuchange={(v) => onpatch({ fixedMtu: v })}
            onblockfastflappingchange={(v) => onpatch({ blockFastFlapping: v })}
            onfastflappingblocktimechange={(v) => onpatch({ fastFlappingBlockTime: v })}
            onfastflappingthresholdchange={(v) => onpatch({ fastFlappingThreshold: v })}
            onfastflappinggracechange={(v) => onpatch({ fastFlappingGrace: v })}
        />
    {:else if interfaceType === "UDPInterface"}
        <AddInterfaceUdpDetails
            listenIp={form.listenIp}
            listenPort={form.listenPort}
            forwardIp={form.forwardIp}
            forwardPort={form.forwardPort}
            device={form.udpDevice}
            onlistenipchange={(v) => onpatch({ listenIp: v })}
            onlistenportchange={(v) => onpatch({ listenPort: v })}
            onforwardipchange={(v) => onpatch({ forwardIp: v })}
            onforwardportchange={(v) => onpatch({ forwardPort: v })}
            ondevicechange={(v) => onpatch({ udpDevice: v })}
        />
    {:else if interfaceType === "I2PInterface"}
        <AddInterfaceI2pDetails
            connectable={form.i2pConnectable}
            peers={form.i2pPeers}
            connectTimeout={form.connectTimeout}
            fixedMtu={form.fixedMtu}
            onconnectablechange={(v) => onpatch({ i2pConnectable: v })}
            onpeerschange={(v) => onpatch({ i2pPeers: v })}
            onconnecttimeoutchange={(v) => onpatch({ connectTimeout: v })}
            onfixedmtuchange={(v) => onpatch({ fixedMtu: v })}
        />
    {:else if interfaceType === "RNodeInterface" || interfaceType === "RNodeIPInterface"}
        <AddInterfaceRNodeDetails
            rnodeTransport={form.rnodeTransport}
            port={form.rnodePort}
            rnodeTcpHost={form.rnodeTcpHost}
            rnodeTcpPort={form.rnodeTcpPort}
            frequency={form.rnodeFrequency}
            bandwidth={form.rnodeBandwidth}
            spreadingFactor={form.rnodeSpreadingFactor}
            codingRate={form.rnodeCodingRate}
            txpower={form.rnodeTxpower}
            flowControl={form.rnodeFlowControl}
            autotune={form.rnodeAutotune}
            idCallsign={form.rnodeIdCallsign}
            idInterval={form.rnodeIdInterval}
            {comports}
            {comportsLoading}
            onrnodetransportchange={(v) => onpatch({ rnodeTransport: v })}
            onportchange={(v) => onpatch({ rnodePort: v })}
            onrnodetcphostchange={(v) => onpatch({ rnodeTcpHost: v })}
            onrnodetcpportchange={(v) => onpatch({ rnodeTcpPort: v })}
            onfrequencychange={(v) => onpatch({ rnodeFrequency: v })}
            onbandwidthchange={(v) => onpatch({ rnodeBandwidth: v })}
            onspreadingfactorchange={(v) => onpatch({ rnodeSpreadingFactor: v })}
            oncodingratechange={(v) => onpatch({ rnodeCodingRate: v })}
            ontxpowerchange={(v) => onpatch({ rnodeTxpower: v })}
            onflowcontrolchange={(v) => onpatch({ rnodeFlowControl: v })}
            onautotunechange={(v) => onpatch({ rnodeAutotune: v })}
            onidcallsignchange={(v) => onpatch({ rnodeIdCallsign: v })}
            onidintervalchange={(v) => onpatch({ rnodeIdInterval: v })}
            {onrefreshcomports}
        />
    {:else if ["SerialInterface", "KISSInterface", "AX25KISSInterface"].includes(interfaceType)}
        <AddInterfaceSerialDetails
            {interfaceType}
            port={form.rnodePort}
            speed={form.serialSpeed}
            databits={form.serialDatabits}
            parity={form.serialParity}
            stopbits={form.serialStopbits}
            callsign={form.ax25Callsign}
            ssid={form.ax25Ssid}
            preamble={form.kissPreamble}
            txtail={form.kissTxtail}
            {comports}
            {comportsLoading}
            onportchange={(v) => onpatch({ rnodePort: v })}
            onspeedchange={(v) => onpatch({ serialSpeed: v })}
            ondatabitschange={(v) => onpatch({ serialDatabits: v })}
            onparitychange={(v) => onpatch({ serialParity: v })}
            onstopbitschange={(v) => onpatch({ serialStopbits: v })}
            oncallsignchange={(v) => onpatch({ ax25Callsign: v })}
            onssidchange={(v) => onpatch({ ax25Ssid: v })}
            onpreamblechange={(v) => onpatch({ kissPreamble: v })}
            ontxtailchange={(v) => onpatch({ kissTxtail: v })}
            {onrefreshcomports}
        />
    {:else if interfaceType === "AutoInterface"}
        <AddInterfaceAutoDetails
            groupId={form.autoGroupId}
            multicastAddressType={form.autoMulticastType}
            devices={form.autoDevices}
            ignoredDevices={form.autoIgnoredDevices}
            discoveryScope={form.autoDiscoveryScope}
            discoveryPort={form.autoDiscoveryPort}
            dataPort={form.autoDataPort}
            {hostKernelInterfaces}
            {hostKernelInterfacesLoading}
            ongroupidchange={(v) => onpatch({ autoGroupId: v })}
            onmulticastaddresstypechange={(v) => onpatch({ autoMulticastType: v })}
            ondeviceschange={(v) => onpatch({ autoDevices: v })}
            onignoreddeviceschange={(v) => onpatch({ autoIgnoredDevices: v })}
            ondiscoveryscopechange={(v) => onpatch({ autoDiscoveryScope: v })}
            ondiscoveryportchange={(v) => onpatch({ autoDiscoveryPort: v })}
            ondataportchange={(v) => onpatch({ autoDataPort: v })}
        />
    {:else if interfaceType === "HTTPInterface"}
        <AddInterfaceHttpDetails
            mode={form.httpMode}
            serverUrl={form.httpServerUrl}
            pollInterval={form.httpPollInterval}
            listenHost={form.httpListenHost}
            listenPort={form.httpListenPort}
            mtu={form.httpMtu}
            httpVersion={form.httpVersion}
            userAgent={form.httpUserAgent}
            checkUserAgent={form.httpCheckUserAgent}
            tlsVerify={form.httpTlsVerify}
            tlsCertfile={form.httpTlsCertfile}
            tlsKeyfile={form.httpTlsKeyfile}
            onmodechange={(v) => onpatch({ httpMode: v })}
            onserverurlchange={(v) => onpatch({ httpServerUrl: v })}
            onpollintervalchange={(v) => onpatch({ httpPollInterval: v })}
            onlistenhostchange={(v) => onpatch({ httpListenHost: v })}
            onlistenportchange={(v) => onpatch({ httpListenPort: v })}
            onmtuchange={(v) => onpatch({ httpMtu: v })}
            onhttpversionchange={(v) => onpatch({ httpVersion: v })}
            onuseragentchange={(v) => onpatch({ httpUserAgent: v })}
            oncheckuseragentchange={(v) => onpatch({ httpCheckUserAgent: v })}
            ontlsverifychange={(v) => onpatch({ httpTlsVerify: v })}
            ontlscertfilechange={(v) => onpatch({ httpTlsCertfile: v })}
            ontlskeyfilechange={(v) => onpatch({ httpTlsKeyfile: v })}
        />
    {:else if interfaceType === "__external__"}
        <AddInterfaceExternalDetails
            customTypeName={form.customTypeName}
            customOptionsJson={form.customOptionsJson}
            {installedModules}
            {modulesPath}
            overwrite={form.customOverwrite}
            isBusy={customIsBusy}
            oncustomtypenamechange={(v) => onpatch({ customTypeName: v })}
            oncustomoptionsjsonchange={(v) => onpatch({ customOptionsJson: v })}
            onoverwritechange={(v) => onpatch({ customOverwrite: v })}
            {onuploadmodule}
            {ondeletemodule}
        />
    {:else if interfaceType === "LocalInterface"}
        <div
            class="text-sm text-sem-fg leading-snug p-4 rounded-xl bg-gray-50 dark:bg-zinc-800/40 border border-sem-border"
        >
            <div class="font-semibold mb-1">Local Loopback Interface</div>
            <p class="text-xs text-sem-fg-muted">
                Loopback interface within this Reticulum instance. No extra transport settings required.
            </p>
        </div>
    {:else if interfaceType === "PipeInterface"}
        <div
            class="text-sm text-sem-fg leading-snug p-4 rounded-xl bg-gray-50 dark:bg-zinc-800/40 border border-sem-border"
        >
            <div class="font-semibold mb-1">Pipe Interface</div>
            <p class="text-xs text-sem-fg-muted">
                Pipe interface connects to an external subprocess command standard input / output.
            </p>
        </div>
    {/if}
</div>
