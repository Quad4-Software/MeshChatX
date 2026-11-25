<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex gap-2">
        <input
            :value="displayValue"
            type="number"
            min="0"
            step="any"
            :placeholder="placeholder"
            class="input-field"
            @input="onInput($event.target.value)"
        />
        <select :value="unit" class="input-field w-auto! shrink-0" @change="onUnitChange">
            <option v-for="opt in units" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
        </select>
    </div>
</template>

<script>
import { BITRATE_UNITS, splitBitrate, joinBitrate } from "../../js/interfaces/unitConversion.js";

/**
 * Bitrate input presenting human units (bps/kbps/Mbps) while the bound
 * modelValue stays in raw bits per second, matching the backend contract.
 * Emits null when the field is cleared so optional bitrates stay unset.
 */
export default {
    name: "BitrateInput",
    props: {
        modelValue: {
            type: [Number, String],
            default: null,
        },
        placeholder: {
            type: String,
            default: "",
        },
    },
    emits: ["update:modelValue"],
    data() {
        return {
            units: BITRATE_UNITS,
            unit: "kbps",
            displayValue: "",
        };
    },
    watch: {
        modelValue: {
            immediate: true,
            handler(value) {
                this.syncFromModel(value);
            },
        },
    },
    methods: {
        syncFromModel(value) {
            if (value === null || value === undefined || value === "") {
                this.displayValue = "";
                return;
            }
            const current = joinBitrate(this.displayValue, this.unit);
            if (current !== null && Number(value) === current) {
                // The change originated from this input; keep what the user typed.
                return;
            }
            const split = splitBitrate(value);
            this.unit = split.unit;
            this.displayValue = split.value === null ? "" : split.value;
        },
        onInput(raw) {
            this.displayValue = raw;
            this.$emit("update:modelValue", joinBitrate(raw, this.unit));
        },
        onUnitChange(event) {
            const nextUnit = event.target.value;
            // Keep the same raw bitrate, re-expressed in the newly picked unit.
            const raw = joinBitrate(this.displayValue, this.unit);
            this.unit = nextUnit;
            if (raw !== null) {
                const multiplier = (BITRATE_UNITS.find((u) => u.id === nextUnit) || BITRATE_UNITS[0]).multiplier;
                this.displayValue = parseFloat((raw / multiplier).toFixed(6));
            }
        },
    },
};
</script>
