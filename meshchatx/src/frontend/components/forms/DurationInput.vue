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
            @input="onInput(($event.target as HTMLInputElement).value)"
        />
        <select :value="unit" class="input-field w-auto! shrink-0" @change="onUnitChange">
            <option v-for="opt in units" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
        </select>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { DURATION_UNITS, splitDurationSeconds, joinDurationSeconds } from "../../js/interfaces/unitConversion.js";

/**
 * Interval input presenting human units (seconds/minutes/hours) while the
 * bound modelValue stays in raw seconds, matching the backend contract.
 * Emits null when the field is cleared so optional intervals stay unset.
 */
const props = withDefaults(
    defineProps<{
        modelValue?: number | string | null;
        placeholder?: string;
    }>(),
    {
        modelValue: null,
        placeholder: "",
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: number | null];
}>();

const units = DURATION_UNITS;
const unit = ref("seconds");
const displayValue = ref<number | string>("");

function syncFromModel(value: number | string | null | undefined) {
    if (value === null || value === undefined || value === "") {
        displayValue.value = "";
        return;
    }
    const current = joinDurationSeconds(displayValue.value, unit.value);
    if (current !== null && Number(value) === current) {
        // The change originated from this input; keep what the user typed.
        return;
    }
    const split = splitDurationSeconds(value);
    unit.value = split.unit;
    displayValue.value = split.value === null ? "" : split.value;
}

watch(() => props.modelValue, syncFromModel, { immediate: true });

function onInput(raw: string) {
    displayValue.value = raw;
    emit("update:modelValue", joinDurationSeconds(raw, unit.value));
}

function onUnitChange(event: Event) {
    const nextUnit = (event.target as HTMLSelectElement).value;
    // Keep the same raw interval, re-expressed in the newly picked unit.
    const raw = joinDurationSeconds(displayValue.value, unit.value);
    unit.value = nextUnit;
    if (raw !== null) {
        const multiplier = (DURATION_UNITS.find((u) => u.id === nextUnit) || DURATION_UNITS[0]).multiplier;
        displayValue.value = parseFloat((raw / multiplier).toFixed(6));
    }
}
</script>
