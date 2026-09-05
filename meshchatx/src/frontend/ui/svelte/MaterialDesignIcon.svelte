<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script>
    import { getMdiIconPath } from "../../js/mdiIconNames.js";

    /** @type {{ iconName?: string, class?: string, style?: string }} */
    let { iconName = "", class: className = "", style = "" } = $props();

    const iconPath = $derived(getMdiIconPath(iconName));
</script>

<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    role="img"
    aria-label={iconName}
    fill="currentColor"
    width="20"
    height="20"
    style="display: block; {style}"
    class="antialiased shrink-0 {className}"
>
    <path d={iconPath} fill="currentColor" />
</svg>
