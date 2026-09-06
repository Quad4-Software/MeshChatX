<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Privacy</div>
                <h2>Banished</h2>
                <p>Manage Banished users and nodes</p>
            </div>
            <RouterLink :to="{ name: 'blocked' }" class="primary-chip"> Manage Banished </RouterLink>
        </header>
        <div class="settings-section__body">
            <p class="text-sm text-sem-fg-muted">
                Banished users and nodes will not be able to send you messages, and their announces will be ignored.
            </p>
        </div>
    </section>
</template>

<script>
export default {
    name: "BlockedSettingsSection",
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
    },
};
</script>
