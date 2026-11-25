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
import { DURATION_UNITS, splitDurationSeconds, joinDurationSeconds } from "../../js/interfaces/unitConversion.js";

/**
 * Interval input presenting human units (seconds/minutes/hours) while the
 * bound modelValue stays in raw seconds, matching the backend contract.
 * Emits null when the field is cleared so optional intervals stay unset.
 */
export default {
    name: "DurationInput",
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
            units: DURATION_UNITS,
            unit: "seconds",
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
            const current = joinDurationSeconds(this.displayValue, this.unit);
            if (current !== null && Number(value) === current) {
                // The change originated from this input; keep what the user typed.
                return;
            }
            const split = splitDurationSeconds(value);
            this.unit = split.unit;
            this.displayValue = split.value === null ? "" : split.value;
        },
        onInput(raw) {
            this.displayValue = raw;
            this.$emit("update:modelValue", joinDurationSeconds(raw, this.unit));
        },
        onUnitChange(event) {
            const nextUnit = event.target.value;
            // Keep the same raw interval, re-expressed in the newly picked unit.
            const raw = joinDurationSeconds(this.displayValue, this.unit);
            this.unit = nextUnit;
            if (raw !== null) {
                const multiplier = (DURATION_UNITS.find((u) => u.id === nextUnit) || DURATION_UNITS[0]).multiplier;
                this.displayValue = parseFloat((raw / multiplier).toFixed(6));
            }
        },
    },
};
</script>
