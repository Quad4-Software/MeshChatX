<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        destinationHash?: string;
    }

    let { destinationHash = "" }: Props = $props();
</script>

<div data-testid="messages-stub" data-hash={destinationHash}>MessagesStub {destinationHash}</div>
