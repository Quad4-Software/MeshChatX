// SPDX-License-Identifier: 0BSD

import { isDestinationHash } from "../../../js/meshValidate.js";

export function isValidForwarderDestinationHash(value: unknown): boolean {
    return isDestinationHash(value);
}
