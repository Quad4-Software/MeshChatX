// SPDX-License-Identifier: 0BSD
import { beforeEach } from "vitest";
import { registerFallbackMessages } from "../../../meshchatx/src/frontend/js/i18n.js";
import en from "../../../meshchatx/src/frontend/locales/en.json";

registerFallbackMessages(en);

beforeEach(() => {
    document.body.innerHTML = "";
});
