import { mount } from "@vue/test-utils";

export const snapshotMaterialDesignIcon = {
    name: "MaterialDesignIcon",
    template: '<span class="mdi-snapshot" :data-icon="iconName"></span>',
    props: ["iconName"],
};

export const snapshotTransitionGroup = {
    template: '<div class="snapshot-transition-group"><slot /></div>',
};

export function snapshotI18nMock() {
    return (key) => key;
}

export function normalizeSnapshotHtml(html) {
    return String(html)
        .replace(/\sdata-v-[a-f0-9]+/g, "")
        .replace(/\s+id="[^"]*"/g, "")
        .replace(/\s+style="[^"]*"/g, "")
        .replace(/<!--[\s\S]*?-->/g, "")
        .replace(/>\s+</g, "><")
        .trim();
}

export function mountSnapshot(component, options = {}) {
    const { props, slots, global = {} } = options;
    return mount(component, {
        props,
        slots,
        global: {
            mocks: {
                $t: snapshotI18nMock(),
                ...(global.mocks || {}),
            },
            stubs: {
                MaterialDesignIcon: snapshotMaterialDesignIcon,
                TransitionGroup: snapshotTransitionGroup,
                ...(global.stubs || {}),
            },
            ...global,
        },
    });
}

export function expectHtmlSnapshot(wrapper) {
    expect(normalizeSnapshotHtml(wrapper.html())).toMatchSnapshot();
}
