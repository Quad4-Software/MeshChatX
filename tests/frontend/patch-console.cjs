"use strict";

const { Console } = require("node:console");

function shouldSuppress(args) {
    const first = args[0];
    const text = typeof first === "string" ? first : first instanceof Error ? first.message : "";
    return text.includes("Not implemented: navigation to another Document");
}

const originalConsoleProtoError = Console.prototype.error;
Console.prototype.error = function (...args) {
    if (shouldSuppress(args)) {
        return;
    }
    return originalConsoleProtoError.apply(this, args);
};

const originalGlobalConsoleError = console.error;
console.error = function (...args) {
    if (shouldSuppress(args)) {
        return;
    }
    return originalGlobalConsoleError.apply(console, args);
};
