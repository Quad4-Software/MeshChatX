#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Soak harness for MeshChatX: sustained workload + resource slope oracle.

Spawns a backend and a live mesh peer, drives a steady workload for N
minutes/hours, samples backend resource counters to CSV, then runs a
least-squares slope oracle. A leak shows up as a rising trend line long
before it crashes anything.

Usage:
    python3 scripts/soak/soak.py --minutes 30 --interval 10 --out /tmp/soak

Exit code 0 = PASS, 1 = FAIL (leak slope, hang, or crash).
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = int(os.environ.get("SOAK_BACKEND_PORT", "18089"))
PEER_PORT = int(os.environ.get("SOAK_PEER_PORT", "43847"))
CHAOS_PORT = int(os.environ.get("SOAK_CHAOS_PORT", "43848"))
BASE = f"http://127.0.0.1:{PORT}"


def api(path, data=None, method=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, method=method)  # noqa: S310
    if data is not None:
        req.add_header("Content-Type", "application/json")
    cookie_jar = api.__dict__.setdefault("_cookie", {})
    if cookie_jar:
        req.add_header("Cookie", cookie_jar["cookie"])
        if cookie_jar.get("csrf") and method in ("POST", "PUT", "DELETE"):
            req.add_header("X-CSRF-Token", cookie_jar["csrf"])
    resp = urllib.request.urlopen(req, timeout=20)  # noqa: S310
    set_cookie = resp.headers.get("Set-Cookie")
    if set_cookie and "cookie" not in cookie_jar:
        cookie_jar["cookie"] = set_cookie.split(";")[0]
    payload = resp.read()
    try:
        out = json.loads(payload)
        if "csrf_token" in out:
            api.__dict__["_cookie"]["csrf"] = out["csrf_token"]
        return out
    except Exception:
        return {"raw": payload[:400].decode(errors="replace")}


def post(path, data):
    return api(path, data=data, method="POST")


def wait_ready(timeout_s=240):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            d = api("/api/v1/status")
            if d.get("status") == "ok" or d.get("network_ready"):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def proc_stats(pid):
    out = {}
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith(("Threads:", "VmRSS:", "VmSize:")):
                    k, v = line.split(":")
                    out[k.strip().lower()] = int(v.split()[0])
        out["fds"] = len(os.listdir(f"/proc/{pid}/fd"))
    except OSError:
        return None
    return out


def sample(pid, row, counters):
    st = proc_stats(pid)
    if st is None:
        return False
    try:
        ifs = api("/api/v1/interface-stats").get("interface_stats", {}).get(
            "interfaces", []
        )
        rx = sum(int(i.get("rxb") or 0) for i in ifs)
        tx = sum(int(i.get("txb") or 0) for i in ifs)
        pt = api("/api/v1/path-table")
        ptable = len(pt.get("path_table", pt if isinstance(pt, list) else []))
        hubs = api("/api/v1/rrc/hubs").get("hubs", [])
        n_links = sum(1 for h in hubs if h.get("status") == 2)
    except Exception:
        return False
    counters.setdefault("_rx", []).append(rx)
    counters.setdefault("_tx", []).append(tx)
    row.update(
        ts=time.time(),
        threads=st.get("threads", 0),
        rss_mb=st.get("vmrss", 0) / 1024,
        fds=st.get("fds", 0),
        path_table=ptable,
        links=n_links,
        rx_kb=rx / 1024,
        tx_kb=tx / 1024,
    )
    return True


def workload_loop(share, state):
    """Drive a steady, realistic workload through the live backend+peer."""
    try:
        with open(os.path.join(share, "peer_ready.json")) as f:
            peer = json.load(f)
    except OSError:
        return False
    hub = peer.get("hub_hash")
    n = state["n"]
    try:
        if hub and n % 5 == 0:
            post(
                f"/api/v1/rrc/hubs/{hub}/rooms/lobby/messages",
                {"text": f"soak-{n}-{int(time.time())}"},
            )
        if n % 3 == 0:
            post(
                "/api/v1/lxmf-messages/send",
                {
                    "lxmf_message": {
                        "destination_hash": peer["lxmf_dest"],
                        "content": f"soak-{n}",
                    }
                },
            )
        if n % 60 == 0 and hub:
            post(f"/api/v1/rrc/hubs/{hub}/disconnect", {})
            time.sleep(2)
            post(f"/api/v1/rrc/hubs/{hub}/connect", {})
    except Exception:
        pass
    state["n"] = n + 1
    return True


def slope_oracle(csv_path, warmup_frac, eps):
    """Least-squares slope per metric; FAIL on significant positive slope.

    Counters that only grow (rx/tx) are normalized to per-interval rate
    first so a constant workload reads as flat.
    """
    rows = list(csv.DictReader(csv_path.open()))
    if len(rows) < 10:
        return False, ["not enough samples for a verdict"]
    start = int(len(rows) * warmup_frac)
    rows = rows[start:]
    verdicts = []
    failed = False
    for key in ("threads", "fds", "rss_mb", "path_table", "rx_kb", "tx_kb"):
        ys = [float(r[key]) for r in rows]
        if key in ("rx_kb", "tx_kb"):
            ys = [max(0.0, ys[i] - ys[i - 1]) for i in range(1, len(ys))]
            if not ys:
                continue
        n = len(ys)
        xs = list(range(n))
        mx = sum(xs) / n
        my = sum(ys) / n
        var = sum((x - mx) ** 2 for x in xs) or 1.0
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / var
        resid = [y - (slope * x + my - slope * mx) for x, y in zip(xs, ys, strict=True)]
        sd = (sum(r * r for r in resid) / max(1, n - 2)) ** 0.5
        ci = 2.5 * sd * ((1 / n) + (mx * mx / var)) ** 0.5
        floor = eps.get(key, 0.0)
        delta = ys[-1] - ys[0]
        leaky = slope > 0 and abs(slope) > ci and delta > floor
        verdicts.append(
            f"{key}: slope={slope:.4f}/sample ci={ci:.4f} delta={delta:.1f} "
            f"(floor {floor}) {'LEAK' if leaky else 'ok'}"
        )
        if leaky:
            failed = True
    return failed, verdicts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--hours", type=float, default=0)
    ap.add_argument("--interval", type=float, default=10)
    ap.add_argument("--warmup-frac", type=float, default=0.25)
    ap.add_argument("--out", default="soak-out")
    args = ap.parse_args()
    seconds = args.hours * 3600 if args.hours else args.minutes * 60

    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="meshchat-soak-")
    share = os.path.join(tmp, "share")
    os.makedirs(share)
    os.makedirs(os.path.join(tmp, "rns"))
    with open(os.path.join(tmp, "rns", "config"), "w") as f:
        f.write(
            "[reticulum]\n"
            "  enable_transport = False\n"
            "  share_instance = No\n"
            "[interfaces]\n"
            "  [[Soak Listener]]\n"
            "    type = TCPServerInterface\n"
            "    enabled = yes\n"
            f"    listen_ip = 127.0.0.1\n"
            f"    listen_port = {PEER_PORT}\n"
        )
    log = open(os.path.join(tmp, "backend.log"), "w")
    env = dict(
        os.environ,
        MESHCHAT_NO_HTTPS="1",
        MESHCHAT_TRUSTED_PROXIES="127.0.0.1/32",
        MESHCHAT_LANDLOCK="0",
        MESHCHAT_LOG_DIR=os.path.join(tmp, "logs"),
    )
    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "meshchatx.meshchat",
            "--headless",
            "--no-https",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--storage-dir",
            os.path.join(tmp, "storage"),
            "--reticulum-config-dir",
            os.path.join(tmp, "rns"),
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    peer = None
    chaos = None
    csv_path = os.path.join(args.out, f"soak_{int(time.time())}")
    os.makedirs(csv_path, exist_ok=True)
    report = []
    try:
        if not wait_ready():
            report.append("backend never became ready")
            print("\n".join(report), file=sys.stderr)
            raise SystemExit(1)
        chaos = subprocess.Popen(
            [
                sys.executable,
                "scripts/e2e/chaos-proxy.py",
                str(CHAOS_PORT),
                str(PEER_PORT),
                os.path.join(share, "chaos.mode"),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        with open(os.path.join(share, "chaos.mode"), "w") as f:
            f.write("pass")
        peer = subprocess.Popen(
            [
                sys.executable,
                "scripts/e2e/live-peer.py",
                os.path.join(tmp, "peer-rns"),
                str(CHAOS_PORT),
                share,
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        for _ in range(90):
            if os.path.exists(os.path.join(share, "peer_ready.json")):
                break
            if peer.poll() is not None:
                report.append("live peer exited early")
                print("\n".join(report), file=sys.stderr)
                raise SystemExit(1)
            time.sleep(1)
        # join the lobby once
        try:
            api("/api/v1/auth/csrf")
            peer_ready = json.load(
                open(os.path.join(share, "peer_ready.json"))
            )
            post("/api/v1/rrc/hubs", {"hub_hash": peer_ready["hub_hash"], "name": "soak-hub"})
            post(
                f"/api/v1/rrc/hubs/{peer_ready['hub_hash']}/connect",
                {},
            )
            post(
                f"/api/v1/rrc/hubs/{peer_ready['hub_hash']}/rooms",
                {"room": "lobby"},
            )
        except Exception:
            pass

        t_end = time.time() + seconds
        state = {"n": 0}
        counters = {}
        samples_path = os.path.join(csv_path, "samples.csv")
        fields = [
            "ts",
            "threads",
            "rss_mb",
            "fds",
            "path_table",
            "links",
            "rx_kb",
            "tx_kb",
        ]
        with open(samples_path, "w", newline="") as cf:
            w = csv.DictWriter(cf, fieldnames=fields)
            w.writeheader()
            while time.time() < t_end:
                row = {}
                alive = backend.poll() is None
                if not alive:
                    report.append("backend crashed during soak")
                    print("\n".join(report), file=sys.stderr)
                    raise SystemExit(1)
                if not sample(backend.pid, row, counters):
                    if backend.poll() is not None:
                        report.append("backend died during sampling")
                        print("\n".join(report), file=sys.stderr)
                        raise SystemExit(1)
                else:
                    w.writerow({k: row.get(k) for k in fields})
                    cf.flush()
                if not workload_loop(share, state):
                    pass
                time.sleep(max(0.1, args.interval))

        failed, verdicts = slope_oracle(
            __import__("pathlib").Path(samples_path),
            args.warmup_frac,
            eps={
                "threads": 2,
                "fds": 4,
                "rss_mb": 64,
                "path_table": 8,
                "rx_kb": 100,
                "tx_kb": 100,
            },
        )
        report.extend(verdicts)
        report.append("RESULT: FAIL" if failed else "RESULT: PASS")
        with open(os.path.join(csv_path, "REPORT.md"), "w") as rf:
            rf.write("# Soak report\n\n")
            for line in report:
                rf.write(f"- {line}\n")
            rf.write(f"\nworkdir: {tmp}\nbackend log: {log.name}\n")
        print("\n".join(report))
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit(1 if failed else 0)
    finally:
        for p in (peer, chaos, backend):
            if p and p.poll() is None:
                p.terminate()
        time.sleep(1)
        for p in (peer, chaos, backend):
            if p and p.poll() is None:
                p.kill()


if __name__ == "__main__":
    main()
