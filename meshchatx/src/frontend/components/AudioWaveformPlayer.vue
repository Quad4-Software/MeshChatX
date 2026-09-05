<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import AudioWaveformPlayerSvelte from "../features/messages/components/AudioWaveformPlayer.svelte";

export default {
    name: "AudioWaveformPlayer",
    props: {
        src: {
            type: String,
            required: true,
        },
        isOutbound: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["play"],
    data() {
        return {
            sveltePlayer: null,
        };
    },
    watch: {
        src() {
            this.mountPlayer();
        },
        isOutbound() {
            this.mountPlayer();
        },
    },
    mounted() {
        this.mountPlayer();
    },
    beforeUnmount() {
        this.unmountPlayer();
    },
    methods: {
        mountPlayer() {
            this.unmountPlayer();
            this.sveltePlayer = mount(AudioWaveformPlayerSvelte, {
                target: this.$refs.root,
                props: {
                    src: this.src,
                    isOutbound: this.isOutbound,
                    onplay: () => this.$emit("play"),
                },
            });
        },
        unmountPlayer() {
            if (this.sveltePlayer) {
                unmount(this.sveltePlayer);
                this.sveltePlayer = null;
            }
        },
    },
};
</script>
