// SPDX-License-Identifier: 0BSD

declare module "*.css";

declare module "*?raw" {
    const content: string;
    export default content;
}
