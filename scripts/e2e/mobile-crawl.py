#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Mobile UI crawler for MeshChatX on a connected Android device.

Walks the installed app via uiautomator: dumps the view hierarchy, taps
safe clickable nodes, watches logcat for crashes, and presses Back to
restore. Exits 0 with a SKIP note when no device or app is present, so
it is safe to wire into optional test steps.

    python3 scripts/e2e/mobile-crawl.py [--steps 40] [--out DIR]

Exit code 0 = pass or skipped, 1 = crash/error found.
"""

import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PKG = "com.meshchatx"
ACTIVITY = "com.meshchatx/.MainActivity"

SKIP_LABEL = re.compile(
    r"delete|remove|wipe|clear|erase|format|flash|uninstall|block|unblock|"
    r"call|dial|hang|send|shutdown|restart|reboot|logout|purge|destroy|"
    r"factory|reset|import|export|upload|download|backup|restore|sign|"
    r"authorize|approve|grant|execute|panic|save|apply|submit|confirm|"
    r"accept|agree|allow|deny|yes|ok\b|connect|disconnect|enable|disable|"
    r"provision|announce|pair|add|create|new|update|install|set|switch|"
    r"start|stop|run|purchase|pay|subscribe|continue",
    re.I,
)

CRASH_RE = re.compile(
    r"FATAL EXCEPTION.*com\.meshchatx|AndroidRuntime.*com\.meshchatx|"
    r"Process com\.meshchatx.*died|ANR in com\.meshchatx|"
    r"com\.meshchatx.*FATAL",
    re.I,
)


ADB_BIN = "/usr/bin/env"


def adb(*args, check=True, capture=True, timeout=30):
    res = subprocess.run(
        [ADB_BIN, "adb", *args],
        capture_output=capture,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {res.stderr.strip()}")
    return res


def device_ready():
    try:
        out = adb("devices").stdout
    except (FileNotFoundError, RuntimeError):
        return None, "adb not installed"
    lines = [line for line in out.splitlines()[1:] if line.strip() and "\t" in line]
    if not lines:
        return None, "no device attached"
    serial = lines[0].split("\t")[0].strip()
    if "device" not in lines[0]:
        return None, "device not ready"
    return serial, None


def app_installed(serial):
    out = adb("-s", serial, "shell", "pm", "list", "packages", PKG).stdout
    return f"package:{PKG}" in out


def logcat_errors(serial):
    try:
        out = adb(
            "-s", serial, "logcat", "-d", "-t", "400", capture=True, timeout=15
        ).stdout
    except Exception:
        return []
    return [line for line in out.splitlines() if CRASH_RE.search(line)]


def dump_ui(serial, workdir):
    remote = "/data/local/tmp/mcx-crawl-ui.xml"
    adb("-s", serial, "shell", "uiautomator", "dump", remote, timeout=30)
    local = Path(workdir) / "ui.xml"
    out = adb("-s", serial, "shell", "cat", remote, timeout=30).stdout
    local.write_text(out, encoding="utf-8", errors="replace")
    try:
        return ET.fromstring(out)  # noqa: S314 - uiautomator dump from our own device
    except ET.ParseError:
        return None


BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def clickable_nodes(root):
    nodes = []
    for el in root.iter("node"):
        if el.get("clickable") != "true":
            continue
        text = (el.get("text") or "").strip()
        desc = (el.get("content-desc") or "").strip()
        label = text or desc
        bounds = el.get("bounds") or ""
        m = BOUNDS_RE.match(bounds)
        if not m:
            continue
        x1, y1, x2, y2 = (int(v) for v in m.groups())
        nodes.append(
            {
                "label": label,
                "cx": (x1 + x2) // 2,
                "cy": (y1 + y2) // 2,
                "res": el.get("resource-id") or "",
            }
        )
    return nodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--out", default="mobile-crawl-out")
    ap.add_argument("--pause-ms", type=int, default=700)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    serial, err = device_ready()
    if not serial:
        print(f"SKIP: {err}")
        return 0
    if not app_installed(serial):
        print(f"SKIP: {PKG} not installed on {serial}")
        return 0

    adb("-s", serial, "logcat", "-c")
    adb("-s", serial, "shell", "am", "start", "-n", ACTIVITY)
    time.sleep(4)

    visited = set()
    report = []
    crashed = False
    dump_failures = 0
    for step in range(args.steps):
        focus = adb(
            "-s",
            serial,
            "shell",
            "dumpsys",
            "window",
            check=False,
            timeout=15,
        ).stdout
        if PKG not in focus:
            adb("-s", serial, "shell", "am", "start", "-n", ACTIVITY)
            time.sleep(2)
            report.append(f"step {step}: refocused app")
            continue
        root = dump_ui(serial, out_dir)
        if root is None:
            dump_failures += 1
            report.append(f"step {step}: ui dump parse failed")
            if dump_failures >= 8:
                print("RESULT: FAIL - ui dumps never parsed")
                return 1
            continue
        nodes = clickable_nodes(root)
        safe = [n for n in nodes if n["label"] and not SKIP_LABEL.search(n["label"])]
        target = None
        for n in safe:
            key = (n["label"], n["res"])
            if key not in visited:
                target = n
                visited.add(key)
                break
        if target is None and safe:
            target = safe[0]
        if target is None:
            report.append(f"step {step}: no clickable nodes")
            adb("-s", serial, "shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(args.pause_ms / 1000)
            continue
        adb(
            "-s",
            serial,
            "shell",
            "input",
            "tap",
            str(target["cx"]),
            str(target["cy"]),
        )
        report.append(f"step {step}: tap '{target['label']}'")
        time.sleep(args.pause_ms / 1000)
        errs = logcat_errors(serial)
        if errs:
            crashed = True
            report.extend(f"CRASH: {line}" for line in errs[:6])
            try:
                with open(out_dir / f"crash-step{step}.png", "wb") as fh:
                    subprocess.run(
                        [ADB_BIN, "adb", "-s", serial, "exec-out", "screencap", "-p"],
                        stdout=fh,
                        timeout=30,
                        check=False,
                    )
            except Exception:
                pass
            break
        # Go back so the next step samples a sibling branch.
        if step % 3 == 2:
            adb("-s", serial, "shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(args.pause_ms / 1000)

    with open(out_dir / "final.png", "wb") as fh:
        subprocess.run(
            [ADB_BIN, "adb", "-s", serial, "exec-out", "screencap", "-p"],
            stdout=fh,
            timeout=30,
            check=False,
        )
    (out_dir / "crawl-report.txt").write_text("\n".join(report) + "\n")
    for line in report:
        print(line)
    if crashed:
        print("RESULT: FAIL - crash detected")
        return 1
    if len(visited) == 0:
        print("RESULT: FAIL - no UI targets were tapped")
        return 1
    print(f"RESULT: PASS - {len(visited)} unique targets tapped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
