// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import { getGuideContent } from "./guideContent.js";
import type { MicronTab } from "./types.js";

export { getGuideContent };

/**
 * Return default starter template content for a new Micron document.
 */
export function getDefaultContent(): string {
    return `\`Ffd0
\`=
            _                                                           _
           (_)                                                         (_)
  _ __ ___  _  ___ _ __ ___  _ __ ______ _ __   __ _ _ __ ___  ___ _ __ _ ___
 | '_ \` _ \\| |/ __| '__/ _ \\| '_ \\______| '_ \\ / _\` | '__/ __|/ _ \\ '__| / __|
 | | | | | | | (__| | | (_) | | | |     | |_) | (_| | |  \\__ \\\\  __/ |_ | \\__ \\\\
 |_| |_| |_|_|\\___|_|  \\___/|_| |_|     | .__/ \\__,_|_|  |___/\\___|_(_)| |___/
                                        | |                           _/ |
                                        |_|                          |__/

\`=
\`f

\`!Welcome to Micron Editor\`!
-
Micron is a lightweight, terminal-friendly monospace markup format used in Reticulum applications such as \`!MeshChatX\`! and \`!NomadNet\`!.

Micron supports sections, dividers, links, partials, anchors, tables, and dynamic input fields for low-bandwidth mesh pages.

Open the \`!${t("tools.micron_editor.guide_tab")}\`! tab for the full reference, or use \`+\` to add another file.

\`!With Micron, you can\`\`:

\`c Align\`b

\`r text,

\`a
\`c
set \`B005 backgrounds, \`b and \`*\` \`B777\`Ffffcombine any number of\`f\`b\`_\`_ \`Ff00f\`Ff80o\`Ffd0r\`F9f0m\`F0f2a\`F0fdt\`F07ft\`F43fi\`F70fn\`Fe0fg \`ftags.
\`\`

>Getting Started

Start editing your Micron markup in the editor pane. The preview will update automatically.

>Formatting

Text can be \`!bold\`! by using \\\`!, \\\`_, and \\\`*.

>Colors

Foreground colors: \`Ff00\`Ff80o\`Ffd0r\`F9f0m\`F0f2a\`F0fdt\`F07ft\`F43fi\`F70fn\`Fe0fg\`f
Background colors: \`Bf00\`Bf80o\`Bfd0r\`B9f0m\`B0f2a\`B0fdt\`B07ft\`B43fi\`B70fn\`Be0fg\`b

>Links

Create links with \\\`[ tag: \`_\`[Example Link\`example.com]\`]\`_

>Literals

Use \\\`= to start/end literal blocks that won't be interpreted.

\`=
This is a literal block
\`=
`;
}

/**
 * Factory for creating default main tab.
 */
export function createDefaultTab(): MicronTab {
    return {
        id: Date.now(),
        name: t("tools.micron_editor.main_tab"),
        content: getDefaultContent(),
    };
}

/**
 * Factory for creating default quick guide tab.
 */
export function createGuideTab(id = Date.now()): MicronTab {
    return {
        id,
        name: t("tools.micron_editor.guide_tab"),
        content: getGuideContent(),
    };
}
