// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import PluginInstallDialog from "@/components/settings/PluginInstallDialog.vue";

describe("PluginInstallDialog", () => {
    it("requires a separate opt-in for Python backend execution", () => {
        const wrapper = mount(PluginInstallDialog, {
            props: {
                open: true,
                preview: {
                    id: "com.example.python",
                    name: "Python plugin",
                    version: "1.0.0",
                    permissions: ["backend:python", "network:fetch"],
                    signature: {},
                },
            },
            global: {
                mocks: { $t: (key) => key },
            },
        });

        expect(wrapper.vm.grantedMap["backend:python"]).toBe(false);
        expect(wrapper.vm.grantedMap["network:fetch"]).toBe(true);
        expect(wrapper.vm.selectedPermissions()).toEqual(["network:fetch"]);

        wrapper.vm.grantedMap["backend:python"] = true;
        expect(wrapper.vm.selectedPermissions()).toEqual(["backend:python", "network:fetch"]);
    });
});
