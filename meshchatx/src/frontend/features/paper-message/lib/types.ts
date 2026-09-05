// SPDX-License-Identifier: 0BSD

export interface PaperMessageDraft {
    destinationHash: string;
    title: string;
    content: string;
}

export interface PaperMessageSendResult {
    success: boolean;
    message?: string;
}

export interface LxmGeneratePaperUriWsResult {
    type?: string;
    status: string;
    uri?: string;
    message?: string;
}

export interface LxmIngestUriWsResult {
    type?: string;
    status: string;
    message?: string;
}

export interface PaperPrintOptions {
    canvas: HTMLCanvasElement;
    destinationHash?: string;
}
