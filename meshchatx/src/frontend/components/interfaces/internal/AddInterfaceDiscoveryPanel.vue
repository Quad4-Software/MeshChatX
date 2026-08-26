<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <ExpandingSection class="glass-card p-0! overflow-hidden">
        <template #title><span class="text-sm font-bold">Interface Discovery</span></template>
        <template #content>
            <div class="p-6 space-y-6">
                <div class="flex items-center justify-between">
                    <div class="max-w-md">
                        <FormLabel class="glass-label mb-0!">Publish Discovery Announce</FormLabel>
                        <p class="text-xs text-gray-400">Makes your node visible to others on the network.</p>
                    </div>
                    <Toggle
                        :model-value="discovery.discoverable"
                        @update:model-value="patchField('discoverable', $event)"
                    />
                </div>
                <div
                    v-if="discovery.discoverable"
                    class="space-y-4 pt-4 border-t border-sem-border animate-in fade-in slide-in-from-top-2"
                >
                    <div>
                        <FormLabel class="glass-label">Discovery Name</FormLabel>
                        <input
                            :value="discovery.discovery_name"
                            type="text"
                            placeholder="Human-friendly name"
                            class="input-field"
                            @input="patchField('discovery_name', $event.target.value)"
                        />
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <FormLabel class="glass-label">Announce Interval (m)</FormLabel>
                            <input
                                :value="discovery.announce_interval"
                                type="number"
                                class="input-field"
                                @input="patchField('announce_interval', Number($event.target.value))"
                            />
                        </div>
                        <div>
                            <FormLabel class="glass-label">Reachable On</FormLabel>
                            <input
                                :value="discovery.reachable_on"
                                type="text"
                                placeholder="IP or Hostname"
                                class="input-field"
                                @input="patchField('reachable_on', $event.target.value)"
                            />
                        </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <FormLabel class="glass-label">Latitude (optional)</FormLabel>
                            <input
                                :value="discovery.latitude"
                                type="text"
                                inputmode="decimal"
                                autocomplete="off"
                                aria-required="false"
                                placeholder="Leave blank if unknown"
                                class="input-field"
                                @input="patchField('latitude', $event.target.value)"
                            />
                        </div>
                        <div>
                            <FormLabel class="glass-label">Longitude (optional)</FormLabel>
                            <input
                                :value="discovery.longitude"
                                type="text"
                                inputmode="decimal"
                                autocomplete="off"
                                aria-required="false"
                                placeholder="Leave blank if unknown"
                                class="input-field"
                                @input="patchField('longitude', $event.target.value)"
                            />
                        </div>
                        <div>
                            <FormLabel class="glass-label">Height in metres (optional)</FormLabel>
                            <input
                                :value="discovery.height"
                                type="text"
                                inputmode="decimal"
                                autocomplete="off"
                                aria-required="false"
                                placeholder="Leave blank if unknown"
                                class="input-field"
                                @input="patchField('height', $event.target.value)"
                            />
                        </div>
                    </div>
                    <div>
                        <FormLabel class="glass-label">{{ $t("interfaces.location_cmd_label") }}</FormLabel>
                        <input
                            :value="discovery.location_cmd"
                            type="text"
                            :placeholder="$t('interfaces.location_cmd_placeholder')"
                            class="input-field font-mono text-xs"
                            autocomplete="off"
                            @input="patchField('location_cmd', $event.target.value)"
                        />
                        <p class="text-xs text-sem-fg-muted mt-1">
                            {{ $t("interfaces.location_cmd_hint") }}
                        </p>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <FormLabel class="glass-label">Discovery stamp value</FormLabel>
                            <input
                                :value="discovery.discovery_stamp_value"
                                type="number"
                                min="1"
                                class="input-field"
                                @input="patchField('discovery_stamp_value', Number($event.target.value))"
                            />
                        </div>
                    </div>
                    <div class="flex flex-wrap items-center justify-between gap-4">
                        <div class="flex items-center justify-between gap-4 max-w-md">
                            <FormLabel class="glass-label mb-0!">Encrypt discovery</FormLabel>
                            <Toggle
                                :model-value="discovery.discovery_encrypt"
                                @update:model-value="patchField('discovery_encrypt', $event)"
                            />
                        </div>
                        <div class="flex items-center justify-between gap-4 max-w-md">
                            <FormLabel class="glass-label mb-0!">Publish IFAC in announce</FormLabel>
                            <Toggle
                                :model-value="discovery.publish_ifac"
                                @update:model-value="patchField('publish_ifac', $event)"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </ExpandingSection>
</template>

<script>
import ExpandingSection from "../ExpandingSection.vue";
import FormLabel from "../../forms/FormLabel.vue";
import Toggle from "../../forms/Toggle.vue";

export default {
    name: "AddInterfaceDiscoveryPanel",
    components: {
        ExpandingSection,
        FormLabel,
        Toggle,
    },
    props: {
        discovery: {
            type: Object,
            required: true,
        },
    },
    emits: ["patch"],
    methods: {
        patchField(key, value) {
            this.$emit("patch", { [key]: value });
        },
    },
};
</script>
