#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MC Server Manager
-----------------
Beheer je Minecraft-server: starten/stoppen, console, spelers en statistieken, plus plugins
bijwerken via Modrinth (met Hangar en GitHub als fallback) en het Paper server.jar via PaperMC.

Geen externe packages nodig (alleen Python 3.8+ met tkinter).
Optioneel: "pip install psutil" voor CPU- en geheugenstatistieken van de server.
Bouwen naar .exe:  pyinstaller --onefile --windowed --name MCServerManager mc_server_manager.py
"""

import hashlib
import importlib
import json
import os
import base64
import queue
import re
import socket
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from collections import defaultdict, deque
from datetime import datetime

try:
    import winsound
except ImportError:  # geen Windows
    winsound = None

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

APP_NAME = "MC Server Manager"
APP_VERSION = "2.1"
USER_AGENT = f"MCServerManager/{APP_VERSION} (persoonlijk hulpprogramma voor eigen Minecraft-server)"
MODRINTH = "https://api.modrinth.com/v2"
FILL = "https://fill.papermc.io/v3"
HANGAR = "https://hangar.papermc.io/api/v1"
GEYSERMC = "https://download.geysermc.org/v2/projects"
MCSRV = "https://api.mcsrvstat.us"
PLAYER_HIDE = ("uuid of player", "logged in with entity id")  # hoort bij een speler, maar is routine
LOADERS = ["paper", "spigot", "bukkit"]
ALL_LOADERS = ["paper", "spigot", "bukkit", "purpur", "folia"]
NET_TIMEOUT = 30

DEFAULT_NOISE = """lost connection: Disconnected
UUID of player
logged in with entity id
Reached end of stream
Disconnecting
Timed out
Saving chunks for level
All dimensions are saved
StunObserver"""

OLD_KEEP_V2 = """Starting minecraft server version
This server is running
Done (
Stopping server
Stopping the server
Started Geyser on
Failed
Error
Exception
Could not
Cannot
Unable
Unsupported
Incompatible
Outdated
Address already in use
FAILED TO BIND
EULA"""

DEFAULT_KEEP = """Done (
Stopping server
Stopping the server
Started Geyser on
Failed
Error
Exception
Could not
Cannot
Unable
Unsupported
Incompatible
Outdated
Address already in use
FAILED TO BIND
EULA"""

DEFAULTS = {
    "folder": "", "jar": "server.jar", "unstable": False, "update_folder": False,
    # backups
    "keep_server_backups": True, "server_backups_max": 3,
    "keep_plugin_backups": True, "plugin_backups_max": 3,
    "backup_dir": "",
    # updates
    "auto_check": False, "ignore_list": "", "use_hangar": True, "use_github": True, "use_geysermc": True,
    "loaders": ["paper", "spigot", "bukkit"],
    # server
    "mc_override": "", "start_script": "", "net_timeout": 30,
    # gedrag
    "confirm": True, "sound": True, "topmost": False, "compact": False, "log_to_file": False,
    # serverbeheer
    "launch_mode": "auto", "java_path": "java", "java_xms": "1G", "java_xmx": "4G", "java_extra": "",
    "stop_timeout": 60, "poll_secs": 30, "auto_restart": False, "console_max_lines": 5000, "console_font": 10,
    "graph_minutes": 5, "graph_zoom": True, "stats_secs": 2,
    "show_player_activity": True,
    "reach_host": "", "reach_port": 25565, "reach_check_bedrock": False, "reach_bedrock_port": 19132,
    "reach_auto": False,
    "clean_startup": True, "startup_keep": DEFAULT_KEEP, "clean_console": True, "compact_console": False, "console_autoscroll": True, "noise_filters": DEFAULT_NOISE,
}
TYPE_RANK = {"release": 0, "beta": 1, "alpha": 2}


# --------------------------------------------------------------------------
# Hulpfuncties (geen UI)
# --------------------------------------------------------------------------
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "mc_server_manager_config.json")
OLD_CONFIG_PATH = os.path.join(app_dir(), "mc_updater_config.json")  # oude naam: instellingen blijven behouden


def load_config():
    for path in (CONFIG_PATH, OLD_CONFIG_PATH):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def http_json(url, data=None, timeout=None, retries=3):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout or NET_TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429 and attempt < retries - 1:
                wait = e.headers.get("Retry-After") or e.headers.get("X-Ratelimit-Reset") or "5"
                try:
                    time.sleep(min(float(wait), 30))
                except ValueError:
                    time.sleep(5)
                continue
            raise
    raise last


def download(url, dest, progress=None, expected=None):
    """Download naar dest. expected = (algoritme, hexdigest) voor controle."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.new(expected[0]) if expected else None
    with urllib.request.urlopen(req, timeout=max(60, NET_TIMEOUT)) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
            if h:
                h.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if expected and h.hexdigest().lower() != expected[1].lower():
        try:
            os.remove(dest)
        except OSError:
            pass
        raise ValueError("Checksum van de download klopt niet - download is verwijderd.")


def file_hash(path, algo="sha1"):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_move(src, dst):
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)


def dir_size(path):
    total = 0
    for root, _d, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def prune_files(dirpath, keep, log=None):
    """Bewaar de 'keep' nieuwste bestanden in dirpath, verwijder de rest."""
    try:
        files = [os.path.join(dirpath, f) for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f))]
    except OSError:
        return
    files.sort(key=os.path.getmtime, reverse=True)
    for f in files[max(keep, 0):]:
        try:
            os.remove(f)
            if log:
                log(f"Oude backup verwijderd: {os.path.basename(f)}")
        except OSError:
            pass


def prune_dirs(dirpath, keep, log=None):
    """Bewaar de 'keep' nieuwste (op naam = tijdstempel) submappen, verwijder de rest."""
    try:
        dirs = sorted((d for d in os.listdir(dirpath) if os.path.isdir(os.path.join(dirpath, d))), reverse=True)
    except OSError:
        return
    for d in dirs[max(keep, 0):]:
        shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
        if log:
            log(f"Oude plugin-backups verwijderd: {d}")


def read_plugin_meta(path):
    name = ver = site = None
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for n in ("paper-plugin.yml", "plugin.yml"):
                if n in names:
                    txt = z.read(n).decode("utf-8", "replace")
                    m = re.search(r"^name:\s*['\"]?([^'\"\r\n#]+)", txt, re.M)
                    v = re.search(r"^version:\s*['\"]?([^'\"\r\n#]+)", txt, re.M)
                    w = re.search(r"^(?:website|url):\s*['\"]?([^'\"\r\n#]+)", txt, re.M)
                    if m:
                        name = m.group(1).strip()
                    if v and "${" not in v.group(1):
                        ver = v.group(1).strip()
                    if w:
                        site = w.group(1).strip()
                    break
    except Exception:
        pass
    return name, ver, site


def norm_ver(v):
    return re.sub(r"^(v|version[-_ ]?)", "", (v or "").strip().lower())


def ver_nums(v):
    m = re.match(r"(\d+(?:\.\d+)*)", norm_ver(v))
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def is_newer(latest, current):
    """Alleen True als het BEWEZEN nieuwer is: beide versienummers moeten uit cijfers te lezen zijn
    en het nieuwste moet echt hoger zijn. False = gelijk/ouder. None = niet vergelijkbaar (geen bewijs)."""
    a, b = ver_nums(latest), ver_nums(current)
    if not a or not b:
        return None
    n = max(len(a), len(b))
    a, b = a + (0,) * (n - len(a)), b + (0,) * (n - len(b))
    return a > b


def geysermc_lookup(name):
    """Geyser en Floodgate komen van download.geysermc.org (niet van Modrinth/Hangar)."""
    key = (name or "").lower()
    proj = "floodgate" if "floodgate" in key else ("geyser" if key.startswith("geyser") else None)
    if not proj:
        return None
    base = f"{GEYSERMC}/{proj}/versions/latest/builds/latest"
    d = http_json(base)
    dl = (d.get("downloads") or {}).get("spigot")  # Paper gebruikt de Spigot-versie
    if not dl:
        return None
    build = d.get("build") or d.get("number")
    try:
        build = int(build)
    except (TypeError, ValueError):
        build = None
    sha = (dl.get("sha256") or "").lower() or None
    return dict(source="GeyserMC", title=proj.capitalize(),
                version=f"{d.get('version', '?')} (b{build})" if build else str(d.get("version", "?")),
                build=build, url=f"{base}/downloads/spigot", filename=dl.get("name") or f"{proj}-spigot.jar",
                algo="sha256" if sha else None, hash=sha, page=f"https://geysermc.org/download?project={proj}",
                verified=True)


def geysermc_state(path, cur, res):
    """Bewijs voor GeyserMC: (1) identieke SHA-256 = up-to-date, (2) hoger buildnummer = update.
    Zonder bewijs: 'unknown'."""
    try:
        if res.get("hash") and file_hash(path, "sha256").lower() == res["hash"]:
            return "ok", "identiek aan de nieuwste build"
    except OSError:
        pass
    m = re.search(r"\bb(\d+)\b", cur or "")
    if m and res.get("build"):
        cur_build = int(m.group(1))
        if res["build"] > cur_build:
            return "update", f"build {cur_build} → {res['build']}"
        return "ok", f"build {cur_build} is de nieuwste"
    return "unknown", "huidige build niet te bepalen"


def hangar_lookup(name, mc, allow_unstable):
    """Zoek een plugin op Hangar (exacte naam) en geef de nieuwste geschikte versie terug."""
    res = http_json(f"{HANGAR}/projects?" + urllib.parse.urlencode({"q": name, "limit": 10}))
    want = name.lower()
    proj = next((p for p in res.get("result", []) if (p.get("name") or "").lower() == want), None)
    if not proj:
        return None
    ns = proj.get("namespace") or {}
    slug = ns.get("slug") or proj["name"]
    owner = ns.get("owner") or ""
    base = f"{HANGAR}/projects/{urllib.parse.quote(slug)}/versions"
    vers, verified = [], False
    if mc:
        try:
            vers = http_json(base + "?" + urllib.parse.urlencode(
                {"limit": 25, "platform": "PAPER", "platformVersion": mc})).get("result", [])
        except urllib.error.HTTPError:
            vers = []
        verified = bool(vers)
    if not vers:
        vers = http_json(base + "?" + urllib.parse.urlencode({"limit": 25, "platform": "PAPER"})).get("result", [])
    vers.sort(key=lambda v: v.get("createdAt", ""), reverse=True)
    for v in vers:
        chan = ((v.get("channel") or {}).get("name") or "release").lower()
        if not allow_unstable and chan != "release":
            continue
        d = (v.get("downloads") or {}).get("PAPER")
        if not d:
            continue
        url = d.get("downloadUrl") or d.get("externalUrl")
        if not url:
            continue
        fi = d.get("fileInfo") or {}
        return dict(source="Hangar", title=proj["name"], version=v["name"], url=url,
                    filename=fi.get("name") or f"{proj['name']}-{v['name']}.jar",
                    algo="sha256" if fi.get("sha256Hash") else None, hash=fi.get("sha256Hash"),
                    page=f"https://hangar.papermc.io/{owner}/{slug}", verified=verified)
    return None


def github_lookup(website, allow_unstable):
    """Als de plugin.yml naar een GitHub-repo wijst: nieuwste release met een .jar-bestand."""
    m = re.search(r"github\.com/([\w.\-]+)/([\w.\-]+?)(?:\.git)?(?:[/#?]|$)", website or "")
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    rels = http_json(f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=10")
    for rel in rels:
        if rel.get("draft") or (rel.get("prerelease") and not allow_unstable):
            continue
        assets = [a for a in rel.get("assets", []) if a["name"].lower().endswith(".jar")
                  and not re.search(r"sources|javadoc|-dev", a["name"].lower())]
        if not assets:
            continue
        a = assets[0]
        digest = a.get("digest") or ""
        return dict(source="GitHub", title=repo, version=rel.get("tag_name") or rel.get("name") or "?",
                    url=a["browser_download_url"], filename=a["name"],
                    algo="sha256" if digest.startswith("sha256:") else None,
                    hash=digest.split(":", 1)[1] if digest.startswith("sha256:") else None,
                    page=rel.get("html_url") or f"https://github.com/{owner}/{repo}", verified=False)
    return None


def fallback_lookup(name, website, mc, allow_unstable, log, hangar=True, github=True, geyser=True):
    sources = []
    if geyser:  # eerst: de officiële bron voor Geyser/Floodgate
        sources.append(("GeyserMC", lambda: geysermc_lookup(name)))
    if hangar:
        sources.append(("Hangar", lambda: hangar_lookup(name, mc, allow_unstable)))
    if github:
        sources.append(("GitHub", lambda: github_lookup(website, allow_unstable)))
    for label, fn in sources:
        try:
            r = fn()
            if r:
                return r
        except Exception as e:
            log(f"{name}: zoeken op {label} mislukt ({e})", "warn")
    return None


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def detect_server_info(folder, jar):
    """Probeert de Minecraft-versie en Paper-build van de server te vinden."""
    mc = build = None
    try:
        with open(os.path.join(folder, "version_history.json"), encoding="utf-8") as f:
            cur = json.load(f).get("currentVersion", "")
        m = re.search(r"MC:\s*([0-9][0-9A-Za-z.\-]*)", cur)
        if m:
            mc = m.group(1)
        b = re.search(r"git-Paper-(\d+)", cur) or re.match(r"\s*[0-9][0-9.]*-(\d+)-", cur)
        if b:
            build = int(b.group(1))
    except Exception:
        pass
    if not mc:
        try:
            with zipfile.ZipFile(os.path.join(folder, jar)) as z:
                if "version.json" in z.namelist():
                    d = json.loads(z.read("version.json").decode("utf-8"))
                    mc = d.get("id") or d.get("name")
        except Exception:
            pass
    if not mc:
        try:
            with open(os.path.join(folder, "logs", "latest.log"), encoding="utf-8", errors="replace") as f:
                txt = f.read(300000)
            m = re.search(r"Starting minecraft server version ([0-9][0-9A-Za-z.\-]*)", txt)
            if m:
                mc = m.group(1)
        except Exception:
            pass
    return mc, build


def guess_jar(folder):
    try:
        jars = [f for f in os.listdir(folder) if f.lower().endswith(".jar")]
    except OSError:
        return "server.jar"
    if "server.jar" in jars:
        return "server.jar"
    for pref in ("paper", "server"):
        for f in jars:
            if pref in f.lower():
                return f
    return jars[0] if jars else "server.jar"


def paper_latest(mc, allow_unstable):
    builds = http_json(f"{FILL}/projects/paper/versions/{urllib.parse.quote(mc)}/builds")
    if isinstance(builds, dict):
        builds = builds.get("builds", [])
    if not builds:
        raise ValueError(f"Geen Paper-builds gevonden voor Minecraft {mc}.")
    builds.sort(key=lambda b: b.get("id", 0), reverse=True)
    stable = [b for b in builds if str(b.get("channel", "")).upper() == "STABLE"]
    pick = builds[0] if (allow_unstable or not stable) else stable[0]
    dl = pick["downloads"]["server:default"]
    return {
        "build": int(pick["id"]),
        "channel": str(pick.get("channel", "?")).upper(),
        "name": dl.get("name"),
        "url": dl["url"],
        "sha256": (dl.get("checksums") or {}).get("sha256"),
        "size": dl.get("size"),
    }


def paper_newest_mc():
    d = http_json(f"{FILL}/projects/paper")
    versions = d.get("versions", {})
    flat = []
    if isinstance(versions, dict):
        for group in versions.values():
            flat.extend(group)
    elif isinstance(versions, list):
        flat = versions
    flat = [v for v in flat if re.fullmatch(r"\d+(\.\d+)*", v)]
    return max(flat, key=vtuple) if flat else None


def fmt_size(n):
    if not n:
        return ""
    return f"{n / 1048576:.1f} MB"


# --------------------------------------------------------------------------
# De applicatie
# --------------------------------------------------------------------------
psutil = None
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
LOG_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})(?:\s+(\w+)\]|\]\s*\[[^\]/]*/(\w+)\])\s*:?\s*(.*)$")
LIST_RE = re.compile(r"There are (\d+) of a max of (\d+) players online:?\s*(.*)$")
TPS_RE = re.compile(r"TPS from last ([\w, ]+):\s*(.+)$")
JOIN_RE = re.compile(r"^(\S+) joined the game$")
LEAVE_RE = re.compile(r"^(\S+) left the game$")
DONE_RE = re.compile(r"Done \([\d.,]+s\)!")
CONT_RE = re.compile(r"^(\s+|at |Caused by|\.\.\. \d+ more)")

STATE_UI = {"stopped": ("● Gestopt", "#6b7280"), "starting": ("● Starten…", "#d97706"),
            "online": ("● Online", "#059669"), "stopping": ("● Stoppen…", "#d97706")}

LAUNCH_MODES = [("auto", "Automatisch (startbestand als dat is ingesteld, anders Java direct)"),
                ("script", "Startbestand (.bat / .cmd / .ps1)"),
                ("java", "Java direct (met de instellingen hieronder)")]


def fmt_dur(sec):
    sec = int(sec)
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    return (f"{d}d " if d else "") + f"{h:02d}:{m:02d}:{s:02d}"


def parse_mem_mb(s):
    m = re.fullmatch(r"\s*(\d+)\s*([GgMmKk]?)[Bb]?\s*", s or "")
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2).lower()
    return n * 1024 if u == "g" else (n // 1024 if u == "k" else n)


def compile_noise(text):
    """Regels uit de instellingen -> lijst met (kleine letters) tekst of regex."""
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("re:"):
            try:
                out.append(re.compile(line[3:].strip(), re.I))
            except re.error:
                pass
        else:
            out.append(line.lower())
    return out


def load_psutil():
    global psutil
    try:
        importlib.invalidate_caches()
        import psutil as _ps
        psutil = _ps
        return True
    except ImportError:
        return False


def read_properties(folder):
    out = {}
    try:
        with open(os.path.join(folder, "server.properties"), encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def int_var(var, default):
    try:
        return int(var.get())
    except (tk.TclError, ValueError):
        return default


def split_host(text):
    """'mc.example.com:25570' -> ('mc.example.com', 25570); zonder poort -> (tekst, None)."""
    t = (text or "").strip()
    m = re.fullmatch(r"([^:\s]+):(\d{1,5})", t)
    if m and 0 < int(m.group(2)) < 65536:
        return m.group(1), int(m.group(2))
    return t, None


def _pack_varint(n):
    n &= 0xFFFFFFFF
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _recv_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(65536, n - len(buf)))
        if not chunk:
            raise ConnectionError("de server verbrak de verbinding")
        buf += chunk
    return bytes(buf)


def _read_varint_sock(sock):
    n = 0
    for i in range(5):
        b = _recv_exact(sock, 1)[0]
        n |= (b & 0x7F) << (7 * i)
        if not b & 0x80:
            return n
    raise ValueError("ongeldig antwoord van de server")


def _read_varint_buf(buf, pos):
    n = 0
    for i in range(5):
        b = buf[pos]
        pos += 1
        n |= (b & 0x7F) << (7 * i)
        if not b & 0x80:
            return n, pos
    raise ValueError("ongeldig antwoord van de server")


def _flat(d):
    if isinstance(d, str):
        return d
    if isinstance(d, dict):
        t = d.get("text", "")
        for x in d.get("extra") or []:
            t += _flat(x)
        return t
    if isinstance(d, list):
        return "".join(_flat(x) for x in d)
    return ""


def flatten_motd(d):
    return re.sub("§.", "", _flat(d)).strip()


def slp_status(host, port, timeout=5):
    """Minecraft Java 'server list ping': vraagt MOTD, versie, spelers en icoon op (zonder in te loggen)."""
    port = int(port)
    t0 = time.time()
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.settimeout(timeout)
        hb = host.encode("utf-8")
        payload = b"\x00" + _pack_varint(767) + _pack_varint(len(hb)) + hb + struct.pack(">H", port) + b"\x01"
        s.sendall(_pack_varint(len(payload)) + payload + b"\x01\x00")
        length = _read_varint_sock(s)
        if length <= 0 or length > 4000000:
            raise ValueError("ongeldig antwoord van de server")
        buf = _recv_exact(s, length)
    ms = int((time.time() - t0) * 1000)
    _pid, pos = _read_varint_buf(buf, 0)
    slen, pos = _read_varint_buf(buf, pos)
    d = json.loads(buf[pos:pos + slen].decode("utf-8", "replace"))
    pl = d.get("players") or {}
    ver = d.get("version") or {}
    return dict(online=True, motd=flatten_motd(d.get("description")), version=str(ver.get("name") or ""),
                software="", players=(pl.get("online"), pl.get("max")),
                names=[p.get("name", "") for p in (pl.get("sample") or []) if isinstance(p, dict) and p.get("name")],
                icon=d.get("favicon") or None, ip=host, port=port, hostname=None, ms=ms, src="lokaal", age=None)


def mcsrv_status(host, port, bedrock=False):
    """Vraagt api.mcsrvstat.us om van buitenaf naar je server te kijken (Java of Bedrock)."""
    port = int(port)
    addr = host if port == (19132 if bedrock else 25565) else f"{host}:{port}"
    url = MCSRV + ("/bedrock/3/" if bedrock else "/3/") + urllib.parse.quote(addr, safe=":")
    d = http_json(url, timeout=25, retries=2)
    motd = d.get("motd") if isinstance(d.get("motd"), dict) else {}
    pl = d.get("players") if isinstance(d.get("players"), dict) else {}
    dbg = d.get("debug") if isinstance(d.get("debug"), dict) else {}
    names = [p.get("name") if isinstance(p, dict) else str(p) for p in (pl.get("list") or [])]
    age = None
    if dbg.get("cachehit") and isinstance(dbg.get("cachetime"), (int, float)):
        age = max(0, int(time.time() - dbg["cachetime"]))
    return dict(online=bool(d.get("online")),
                motd="\n".join(c.strip() for c in (motd.get("clean") or []) if isinstance(c, str)).strip(),
                version=str(d.get("version") or ""), software=str(d.get("software") or ""),
                players=(pl.get("online"), pl.get("max")), names=[n for n in names if n], icon=d.get("icon"),
                ip=d.get("ip"), port=d.get("port"), hostname=d.get("hostname"), ms=None, src="mcsrvstat.us", age=age)


def describe_net_error(e):
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code} ({e.reason})"
    if isinstance(e, urllib.error.URLError):
        return f"geen verbinding ({e.reason})"
    if isinstance(e, (socket.timeout, TimeoutError)):
        return "time-out: geen antwoord"
    if isinstance(e, ConnectionRefusedError):
        return "verbinding geweigerd: er luistert niets op die poort"
    if isinstance(e, socket.gaierror):
        return "adres niet gevonden"
    return str(e) or e.__class__.__name__


def fetch_public_ip():
    req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=NET_TIMEOUT) as r:
        ip = r.read().decode("utf-8", "replace").strip()
    if not re.fullmatch(r"[0-9a-fA-F.:]{3,45}", ip):
        raise ValueError("onverwacht antwoord van de IP-dienst")
    return ip


def net_diagnose(res, host, jport, lport, srv_online):
    """Geeft (niveau, tekst). De eerste regel is de kop, de rest is uitleg."""
    ext, loc = res.get("ext"), res.get("loc")
    if res.get("local_only"):
        if loc:
            return "ok", (f"✔ De server reageert lokaal op poort {lport}.\n"
                          "Dat zegt nog niets over bereikbaarheid van buitenaf: gebruik daarvoor 'Controleer van buitenaf'.")
        tip = ("Het programma ziet de server wel draaien, dus de lokale poort klopt waarschijnlijk niet "
               "(zie server-port in server.properties)." if srv_online else "Draait de server wel? Start hem op het tabblad Server.")
        return "bad", f"✖ De server reageert niet op 127.0.0.1:{lport}.\n{res.get('loc_err', 'onbekende fout')}. {tip}"
    if res.get("ext_err"):
        return "warn", (f"De controleservice kon niet worden bereikt.\n{res['ext_err']}. "
                        "Controleer je internetverbinding en probeer het later opnieuw.")
    if ext and ext["online"]:
        return "ok", f"✔ Je server is van buitenaf bereikbaar op {host}:{jport}."
    age = ext.get("age") if ext else None
    age_note = (f"\nLet op: dit resultaat van de controleservice is {age // 60} min {age % 60} s oud (cache). Heb je net "
                "iets aangepast, probeer het dan over een paar minuten opnieuw." if age else
                "\nDe controleservice bewaart resultaten tot 5 minuten; na een aanpassing kan het even duren.")
    if loc:
        lines = ["✖ Niet bereikbaar van buitenaf, terwijl de server lokaal wél antwoordt. Mogelijke oorzaken:"]
        if "sleeping" in (loc.get("motd") or "").lower():
            lines.append("• lazymc is actief en de echte server slaapt. Dat is normaal, maar de publieke poort moet "
                         "wel naar lazymc wijzen.")
        lines += [f"• Poortdoorsturing: stuur TCP-poort {jport} in je router door naar deze pc.",
                  "• Windows Firewall: sta inkomend verkeer toe voor Java (of voor die poort).",
                  f"• Verkeerd adres: is {host} je huidige publieke IP? Gebruik 'Mijn IP opzoeken'. Deelt je provider "
                  "IP-adressen (CGNAT), dan werkt doorsturen niet."]
        if int(lport) != int(jport):
            lines.append(f"• De lokale poort ({lport}) wijkt af van de publieke poort ({jport}): de router moet "
                         f"{jport} naar {lport} doorsturen.")
        return "bad", "\n".join(lines) + age_note
    msg = (f"✖ Niet bereikbaar van buitenaf én de server reageert ook niet lokaal.\n{res.get('loc_err', 'onbekende fout')}. ")
    msg += ("Het programma ziet de server wel draaien; controleer server-port in server.properties." if srv_online
            else "Draait de server? Start hem eerst op het tabblad Server.")
    return "bad", msg + age_note


GRAPH_CHOICES = (1, 5, 15, 30, 60, 180)


def graph_label(m):
    m = int(m)
    return f"{m // 60} uur" if m % 60 == 0 else f"{m} min"


def parse_graph_label(s, default=5):
    m = re.match(r"\s*(\d+)\s*(min|uur)", s or "")
    if not m:
        return default
    return int(m.group(1)) * (60 if m.group(2) == "uur" else 1)


class Spark(tk.Canvas):
    """Kleine live-grafiek met instelbaar tijdvenster en auto-zoom."""

    def __init__(self, parent, title, color, lo=0.0, hi=None, unit="", min_span=1.0):
        super().__init__(parent, height=104, width=150, bg="#111827", highlightthickness=0)
        self.title, self.color, self.lo, self.hi, self.unit, self.min_span = title, color, lo, hi, unit, min_span
        self.data = deque(maxlen=12000)
        self.window, self.zoom, self.hi_fn = 300, True, None  # window in seconden
        self.bind("<Configure>", lambda e: self.redraw())

    def add(self, v):
        self.data.append((time.time(), v))
        self.redraw()

    def clear(self):
        self.data.clear()
        self.redraw()

    @staticmethod
    def _num(x, rng):
        return f"{x:.1f}" if rng < 10 else f"{x:.0f}"

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 50:
            return
        now = time.time()
        t0 = now - self.window
        self.create_text(6, 4, anchor="nw", fill="#9ca3af", font=("Segoe UI", 8), text=self.title)
        self.create_text(6, h - 3, anchor="sw", fill="#4b5563", font=("Segoe UI", 7),
                         text=graph_label(max(1, round(self.window / 60))))
        pts = [(t, v) for t, v in self.data if t >= t0 and v is not None]
        if not pts:
            return
        vals = [v for _, v in pts]
        fixed_hi = (self.hi_fn() if self.hi_fn else None) or self.hi
        if self.zoom:
            vmin, vmax = min(vals), max(vals)
            span = max(vmax - vmin, self.min_span)
            mid = (vmin + vmax) / 2
            lo_v, hi_v = mid - span * 0.65, mid + span * 0.65
            lo_v = max(lo_v, self.lo)
            if fixed_hi:
                hi_v = min(hi_v, fixed_hi)
            if hi_v - lo_v < self.min_span * 0.5:
                lo_v = max(self.lo, hi_v - self.min_span)
        else:
            lo_v = self.lo
            hi_v = fixed_hi or max(max(vals) * 1.2, self.min_span)
        rng = max(hi_v - lo_v, 1e-9)
        top, bot = 30, h - 14

        def X(t):
            return 4 + (t - t0) / self.window * (w - 8)

        def Y(v):
            return bot - (min(max(v, lo_v), hi_v) - lo_v) / rng * (bot - top)

        xy = []
        for t, v in pts:
            xy += [X(t), Y(v)]
        xy += [X(now), Y(vals[-1])]  # tot nu doortrekken, ook als er een tijdje geen nieuwe meting was
        if len(xy) >= 4:
            self.create_line(*xy, fill=self.color, width=2)
        self.create_text(w - 6, 4, anchor="ne", fill="white", font=("Segoe UI", 9, "bold"),
                         text=f"{vals[-1]:.1f}{self.unit}")
        self.create_text(w - 6, 18, anchor="ne", fill="#6b7280", font=("Segoe UI", 7), text=self._num(hi_v, rng))
        self.create_text(w - 6, h - 3, anchor="se", fill="#6b7280", font=("Segoe UI", 7), text=self._num(lo_v, rng))


load_psutil()


class App(tk.Tk):
    COLS = (("plugin", "Plugin", 190), ("file", "Bestand", 220), ("current", "Huidige versie", 130),
            ("latest", "Nieuwste versie", 130), ("source", "Bron", 80), ("status", "Status", 290))

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1200x880")
        self.minsize(980, 700)
        self.q = queue.Queue()
        self.cfg = {**DEFAULTS, **load_config()}
        if self.cfg.get("startup_keep") == OLD_KEEP_V2:  # oude standaardlijst -> nieuwe standaardlijst
            self.cfg["startup_keep"] = DEFAULT_KEEP
        self.rows = {}
        self.paper_info = None
        self.cur_build = None
        self.busy = False

        self.folder_var = tk.StringVar(value=self.cfg.get("folder", ""))
        self.jar_var = tk.StringVar(value=self.cfg.get("jar", "server.jar"))
        self.mc_var = tk.StringVar()
        self.build_var = tk.StringVar(value="onbekend")
        self.unstable_var = tk.BooleanVar(value=self.cfg.get("unstable", False))
        self.updfolder_var = tk.BooleanVar(value=self.cfg.get("update_folder", False))
        self.status_var = tk.StringVar(value="Kies je servermap om te beginnen.")

        # --- serverbeheer ---
        c = self.cfg
        self.srv_proc, self.srv_state, self.srv_t0, self.srv_xmx = None, "stopped", 0, None
        self.players, self.max_players = {}, None
        self.srv_lines, self.srv_hidden, self._last_tag = deque(maxlen=20000), 0, "info"
        self._sup = {"list": 0, "tps": 0, "any": 0}
        self._pcache, self._last_poll = {}, 0
        self._user_stop = self._restart_pending = self._restart_after_update = self._stop_warned = False
        self._after_exit = self._tmp_script = self._rr_job = None
        self._crash_times, self.cmd_hist, self.hist_idx = [], [], 0
        self._stop_t = self._last_nl = self._stop_deadline = 0
        self.noise = compile_noise(c.get("noise_filters", DEFAULT_NOISE))
        self.keep = compile_noise(c.get("startup_keep", DEFAULT_KEEP))
        self._startup_until = 0
        self.clean_var = tk.BooleanVar(value=bool(c.get("clean_console", True)))
        self.compact_var = tk.BooleanVar(value=bool(c.get("compact_console", False)))
        self.autoscroll_var = tk.BooleanVar(value=bool(c.get("console_autoscroll", True)))
        self.search_var, self.cmd_var, self.hidden_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.players_only_var = tk.BooleanVar(value=False)
        self.player_names, self._names_dirty, self._name_rx_c = set(), True, None
        self.reach_host_var = tk.StringVar(value=str(c.get("reach_host", "")))
        self.reach_port_var = tk.IntVar(value=int(c.get("reach_port", 25565)))
        self.reach_bed_var = tk.BooleanVar(value=bool(c.get("reach_check_bedrock", False)))
        self.reach_bport_var = tk.IntVar(value=int(c.get("reach_bedrock_port", 19132)))
        self.reach_lport_var = tk.IntVar(value=25565)
        self.reach_auto_var = tk.BooleanVar(value=bool(c.get("reach_auto", False)))
        self._net_busy, self._net_img = False, None

        self._style()
        self._build()
        self.apply_settings()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<F5>", lambda e: self.on_check_all())
        self.after(80, self._poll)
        self.after(2000, self._stats_tick)
        self.after(200, self._startup)

    # ---------------- UI opbouw ----------------
    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Big.TButton", font=("Segoe UI", 10, "bold"), padding=6)

        def fixed_map(option):  # workaround voor kleuren in Tk 8.6.9
            return [e for e in style.map("Treeview", query_opt=option) if e[:2] != ("!disabled", "!selected")]

        style.map("Treeview", foreground=fixed_map("foreground"), background=fixed_map("background"))

    def _build(self):
        header = tk.Frame(self, bg="#1f2937")
        header.pack(fill="x")
        tk.Label(header, text="⛏  MC Server Manager", bg="#1f2937", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(header, text="Server • Console • Updates via Modrinth, Hangar, GitHub & PaperMC", bg="#1f2937", fg="#9ca3af",
                 font=("Segoe UI", 10)).pack(side="left", padx=4)

        self.btn_settings = tk.Button(header, text="⚙  Instellingen", command=self.open_settings, bg="#374151",
                                      fg="white", activebackground="#4b5563", activeforeground="white",
                                      relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 10), cursor="hand2")
        self.btn_settings.pack(side="right", padx=14, pady=10)
        self.btn_start = tk.Button(header, text="▶  Server starten", command=self.start_server, bg="#059669",
                                   fg="white", activebackground="#047857", activeforeground="white",
                                   relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 10), cursor="hand2")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        body = ttk.Frame(self.nb, padding=10)
        self.tab_srv = ttk.Frame(self.nb, padding=10)
        self.tab_net = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_srv, text="   🖥  Server   ")
        self.nb.add(body, text="   🔧  Updates   ")
        self.nb.add(self.tab_net, text="   🌐  Bereikbaarheid   ")
        self._build_server_tab(self.tab_srv)
        self._build_net_tab(self.tab_net)

        # --- Server ---
        f1 = ttk.LabelFrame(body, text=" Server ", padding=8)
        f1.pack(fill="x")
        f1.columnconfigure(1, weight=1)
        ttk.Label(f1, text="Servermap:").grid(row=0, column=0, sticky="w")
        ttk.Entry(f1, textvariable=self.folder_var).grid(row=0, column=1, columnspan=4, sticky="ew", padx=6)
        self.btn_browse = ttk.Button(f1, text="Bladeren…", command=self.browse)
        self.btn_browse.grid(row=0, column=5)
        ttk.Label(f1, text="Server-jar:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(f1, textvariable=self.jar_var, width=26).grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(f1, text="Minecraft-versie:").grid(row=1, column=2, sticky="e", pady=(6, 0))
        ttk.Entry(f1, textvariable=self.mc_var, width=12).grid(row=1, column=3, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(f1, text="Huidige Paper-build:").grid(row=1, column=4, sticky="e", pady=(6, 0))
        ttk.Label(f1, textvariable=self.build_var, width=10).grid(row=1, column=5, sticky="w", pady=(6, 0))

        # --- Paper ---
        f2 = ttk.LabelFrame(body, text=" Paper (server.jar) ", padding=8)
        f2.pack(fill="x", pady=(8, 0))
        self.paper_label = tk.Label(f2, text="Nog niet gecontroleerd", font=("Segoe UI", 11, "bold"),
                                    fg="#555555", anchor="w")
        self.paper_label.pack(side="left", fill="x", expand=True)
        self.btn_paper_check = ttk.Button(f2, text="Paper controleren", command=self.on_paper_check)
        self.btn_paper_check.pack(side="left", padx=4)
        self.btn_paper_update = ttk.Button(f2, text="Paper updaten", style="Big.TButton", command=self.on_paper_update)
        self.btn_paper_update.pack(side="left", padx=4)

        # --- Plugins ---
        f3 = ttk.LabelFrame(body, text=" Plugins ", padding=8)
        f3.pack(fill="both", expand=True, pady=(8, 0))
        bar = ttk.Frame(f3)
        bar.pack(fill="x", pady=(0, 6))
        self.btn_check = ttk.Button(bar, text="Alles controleren", style="Big.TButton", command=self.on_check_all)
        self.btn_check.pack(side="left")
        self.btn_plug_check = ttk.Button(bar, text="Alleen plugins", command=self.on_plugins_check)
        self.btn_plug_check.pack(side="left", padx=4)
        self.btn_upd_sel = ttk.Button(bar, text="Geselecteerde updaten", command=lambda: self.on_plugins_update(False))
        self.btn_upd_sel.pack(side="left", padx=(14, 4))
        self.btn_upd_all = ttk.Button(bar, text="Alle updates installeren", style="Big.TButton",
                                      command=lambda: self.on_plugins_update(True))
        self.btn_upd_all.pack(side="left", padx=4)
        self.btn_backups = ttk.Button(bar, text="Backups openen", command=self.open_backups)
        self.btn_backups.pack(side="right")

        opts = ttk.Frame(f3)
        opts.pack(fill="x", pady=(0, 6))
        ttk.Checkbutton(opts, text="Ook beta/alpha-versies toestaan", variable=self.unstable_var).pack(side="left")
        ttk.Checkbutton(opts, text="Server draait: zet updates klaar in plugins/update (toegepast bij herstart)",
                        variable=self.updfolder_var).pack(side="left", padx=18)

        tf = ttk.Frame(f3)
        tf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=[c[0] for c in self.COLS], show="headings", selectmode="extended")
        for cid, text, w in self.COLS:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=w, anchor="w")
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.tag_configure("ok", foreground="#1b5e20")
        self.tree.tag_configure("update", background="#fff3e0", foreground="#e65100")
        self.tree.tag_configure("done", background="#e3f2fd", foreground="#0d47a1")
        self.tree.tag_configure("error", foreground="#b71c1c")
        self.tree.tag_configure("unknown", foreground="#757575")
        self.tree.tag_configure("busy", foreground="#555555")
        self.tree.bind("<Double-1>", self.on_double)

        # --- Voortgang + log ---
        f4 = ttk.Frame(body)
        f4.pack(fill="x", pady=(8, 0))
        ttk.Label(f4, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.pbar = ttk.Progressbar(f4, mode="determinate")
        self.pbar.pack(fill="x", pady=4)
        self.logbox = scrolledtext.ScrolledText(f4, height=9, state="disabled", font=("Consolas", 9),
                                                bg="#111827", fg="#e5e7eb", relief="flat")
        self.logbox.pack(fill="x")
        for tag, color in (("info", "#e5e7eb"), ("ok", "#34d399"), ("warn", "#fbbf24"), ("error", "#f87171")):
            self.logbox.tag_configure(tag, foreground=color)
        self.action_buttons = [self.btn_browse, self.btn_paper_check, self.btn_paper_update, self.btn_check,
                               self.btn_plug_check, self.btn_upd_sel, self.btn_upd_all]

    # ---------------- Berichten tussen threads en UI ----------------
    def log(self, text, level="info"):
        self.q.put(("log", text, level))

    def status(self, text):
        self.q.put(("status", text))

    def row(self, fn, name, cur, latest, source, status, tag):
        self.q.put(("row_set", fn, (name, fn, cur, latest, source, status), tag))

    def progress(self, value, maximum):
        self.q.put(("progress", value, maximum))

    def _poll(self):
        try:
            for _ in range(300):  # niet alles in één keer, zodat het venster soepel blijft bij veel console-uitvoer
                self._handle(self.q.get_nowait())
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _handle(self, m):
        k = m[0]
        if k == "log":
            self.logbox.config(state="normal")
            line = f"[{datetime.now():%H:%M:%S}] {m[1]}\n"
            self.logbox.insert("end", line, m[2])
            if self.cfg.get("log_to_file"):
                try:
                    with open(os.path.join(app_dir(), "mc_server_manager.log"), "a", encoding="utf-8") as lf:
                        lf.write(f"{datetime.now():%Y-%m-%d} {line}")
                except OSError:
                    pass
            self.logbox.see("end")
            self.logbox.config(state="disabled")
        elif k == "beep":
            if self.cfg.get("sound") and winsound:
                try:
                    winsound.MessageBeep(0x40)
                except Exception:
                    pass
        elif k == "status":
            self.status_var.set(m[1])
        elif k == "progress":
            self.pbar.stop()
            self.pbar.config(mode="determinate", maximum=max(m[2], 1), value=m[1])
        elif k == "spin":
            if m[1]:
                self.pbar.config(mode="indeterminate")
                self.pbar.start(12)
            else:
                self.pbar.stop()
                self.pbar.config(mode="determinate", value=0)
        elif k == "busy":
            self.busy = m[1]
            for b in self.action_buttons:
                b.config(state="disabled" if m[1] else "normal")
            if not m[1] and self._restart_after_update:
                self._restart_after_update = False
                self.log("Update klaar - server wordt opnieuw gestart…", "ok")
                self.after(800, self.srv_start)
        elif k == "clear_rows":
            self.tree.delete(*self.tree.get_children())
        elif k == "row_set":
            _, iid, values, tag = m
            if self.tree.exists(iid):
                self.tree.item(iid, values=values, tags=(tag,))
            else:
                self.tree.insert("", "end", iid=iid, values=values, tags=(tag,))
        elif k == "row_replace":
            _, old, new, values, tag = m
            if self.tree.exists(old):
                idx = self.tree.index(old)
                self.tree.delete(old)
                self.tree.insert("", idx, iid=new, values=values, tags=(tag,))
            else:
                self.tree.insert("", "end", iid=new, values=values, tags=(tag,))
        elif k == "paper_label":
            self.paper_label.config(text=m[1], fg=m[2])
        elif k == "set_mc":
            self.mc_var.set(m[1] or "")
        elif k == "net_result":
            self._net_show(m[1])
        elif k == "net_ip":
            self._net_ip_done(m[1], m[2])
        elif k == "srv_line":
            if m[1] is self.srv_proc:
                self._srv_line(m[2])
        elif k == "srv_exit":
            if m[1] is self.srv_proc:
                self._srv_exited(m[2])
        elif k == "psutil_done":
            self._psutil_done(m[1])
        elif k == "set_build":
            self.cur_build = m[1]
            self.build_var.set(str(m[1]) if m[1] else "onbekend")

    def run_bg(self, fn, *args):
        if self.busy:
            return
        self.q.put(("busy", True))
        self.busy = True

        def runner():
            try:
                fn(*args)
            except urllib.error.HTTPError as e:
                self.log(f"Netwerkfout {e.code}: {e.reason}", "error")
            except urllib.error.URLError as e:
                self.log(f"Geen verbinding: {e.reason}", "error")
            except PermissionError:
                self.log("Bestand is in gebruik - stop eerst je server en probeer opnieuw.", "error")
            except Exception as e:
                self.log(f"Fout: {e}", "error")
            finally:
                self.q.put(("spin", False))
                self.q.put(("busy", False))
                self.q.put(("beep",))

        threading.Thread(target=runner, daemon=True).start()

    # ---------------- Knoppen / acties ----------------
    def ctx(self):
        c = self.cfg
        return dict(folder=self.folder_var.get().strip(), jar=self.jar_var.get().strip() or "server.jar",
                    mc=self.mc_var.get().strip(), unstable=self.unstable_var.get(),
                    upd=self.updfolder_var.get(), build=self.cur_build,
                    loaders=list(c.get("loaders") or LOADERS),
                    ignore={x.strip().lower() for x in c.get("ignore_list", "").split(",") if x.strip()},
                    use_hangar=c.get("use_hangar", True), use_github=c.get("use_github", True),
                    use_geyser=c.get("use_geysermc", True),
                    backup_root=self.backup_root(),
                    keep_server=c.get("keep_server_backups", True), server_max=int(c.get("server_backups_max", 5)),
                    keep_plugins=c.get("keep_plugin_backups", True), plugin_max=int(c.get("plugin_backups_max", 10)))

    def backup_root(self):
        return (self.cfg.get("backup_dir") or "").strip() or os.path.join(self.folder_var.get().strip(),
                                                                          "updater_backups")

    def _save_cfg(self):
        self.cfg.update(folder=self.folder_var.get().strip(), jar=self.jar_var.get().strip(),
                        unstable=self.unstable_var.get(), update_folder=self.updfolder_var.get(),
                        reach_host=self.reach_host_var.get().strip(), reach_port=int_var(self.reach_port_var, 25565),
                        reach_check_bedrock=bool(self.reach_bed_var.get()),
                        reach_bedrock_port=int_var(self.reach_bport_var, 19132),
                        reach_auto=bool(self.reach_auto_var.get()))
        save_config(self.cfg)

    def _startup(self):
        if self.folder_var.get() and os.path.isdir(self.folder_var.get()):
            self.load_folder()
            if self.cfg.get("auto_check"):
                self.log("Automatisch controleren bij opstarten staat aan.")
                self.after(500, self.on_check_all)

    def open_settings(self):
        SettingsDialog(self)

    def apply_settings(self):
        global NET_TIMEOUT
        c = self.cfg
        try:
            NET_TIMEOUT = max(5, int(c.get("net_timeout", 30)))
        except (TypeError, ValueError):
            NET_TIMEOUT = 30
        try:
            self.attributes("-topmost", bool(c.get("topmost")))
        except tk.TclError:
            pass
        ttk.Style(self).configure("Treeview", rowheight=22 if c.get("compact") else 26)
        self.btn_start.pack_forget()
        self.btn_start.pack(side="right", padx=(0, 6), pady=10)
        self.noise = compile_noise(c.get("noise_filters", DEFAULT_NOISE))
        self.keep = compile_noise(c.get("startup_keep", DEFAULT_KEEP))
        try:
            self.console.config(font=("Consolas", int(c.get("console_font", 10))))
        except (tk.TclError, ValueError, AttributeError):
            pass
        self._schedule_rerender()
        self._apply_graph_cfg()
        self._sync_ram_var()

    # ================= Server & console =================
    def _build_server_tab(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        bar = ttk.Frame(f)
        bar.grid(row=0, column=0, sticky="ew")
        self.btn_s_start = ttk.Button(bar, text="▶  Starten", style="Big.TButton", command=self.srv_start)
        self.btn_s_stop = ttk.Button(bar, text="■  Stoppen", command=self.srv_stop)
        self.btn_s_restart = ttk.Button(bar, text="↻  Herstarten", command=lambda: self.srv_stop(restart=True))
        self.btn_s_kill = ttk.Button(bar, text="☠  Geforceerd stoppen", command=self.srv_kill)
        for b in (self.btn_s_start, self.btn_s_stop, self.btn_s_restart, self.btn_s_kill):
            b.pack(side="left", padx=(0, 6))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Label(bar, text="Max. RAM:").pack(side="left")
        self.ram_var = tk.StringVar()
        self.ram_box = ttk.Combobox(bar, textvariable=self.ram_var, width=7,
                                    values=["1G", "2G", "3G", "4G", "6G", "8G", "10G", "12G", "16G"])
        self.ram_box.pack(side="left", padx=4)
        self.ram_box.bind("<Return>", lambda e: self.ram_apply())
        ttk.Button(bar, text="Toepassen", command=self.ram_apply).pack(side="left")
        self.srv_state_lbl = tk.Label(bar, text="● Gestopt", font=("Segoe UI", 12, "bold"), fg="#6b7280")
        self.srv_state_lbl.pack(side="right", padx=8)

        mid = ttk.Frame(f)
        mid.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        mid.columnconfigure(1, weight=1)
        st = ttk.LabelFrame(mid, text=" Statistieken ", padding=8)
        st.grid(row=0, column=0, sticky="ns")
        self.sv = {}
        for i, (key, label) in enumerate((("uptime", "Uptime"), ("pid", "Proces (PID)"), ("cpu", "CPU"),
                                          ("ram", "Geheugen"), ("tps", "TPS (1 min)"), ("players", "Spelers"))):
            self.sv[key] = tk.StringVar(value="-")
            ttk.Label(st, text=label + ":").grid(row=i, column=0, sticky="w", pady=1)
            ttk.Label(st, textvariable=self.sv[key], font=("Segoe UI", 10, "bold")).grid(
                row=i, column=1, sticky="w", padx=(10, 0))
        self.psutil_frame = None
        if psutil is None:
            hf = ttk.Frame(st)
            hf.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
            self.psutil_frame = hf
            self.psutil_lbl = ttk.Label(hf, text="CPU/geheugen heeft 'psutil' nodig", foreground="#b45309")
            self.psutil_lbl.pack(anchor="w")
            self.btn_psutil = ttk.Button(hf, text="psutil installeren", command=self.install_psutil)
            self.btn_psutil.pack(anchor="w", pady=(2, 0))

        sp = ttk.Frame(mid)
        sp.grid(row=0, column=1, sticky="nsew", padx=8)
        sp.columnconfigure(0, weight=1)
        sp.rowconfigure(1, weight=1)
        gb = ttk.Frame(sp)
        gb.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        ttk.Label(gb, text="Grafiek-tijdvenster:").pack(side="left")
        self.graph_var = tk.StringVar()
        gcb = ttk.Combobox(gb, textvariable=self.graph_var, width=7, state="readonly",
                           values=[graph_label(m) for m in GRAPH_CHOICES])
        gcb.pack(side="left", padx=4)
        gcb.bind("<<ComboboxSelected>>", self._graph_pick)
        self.zoom_var = tk.BooleanVar(value=bool(self.cfg.get("graph_zoom", True)))
        ttk.Checkbutton(gb, text="Auto-zoom", variable=self.zoom_var, command=self._graph_zoom_changed).pack(
            side="left", padx=8)
        gc = ttk.Frame(sp)
        gc.grid(row=1, column=0, sticky="nsew")
        self.spark_cpu = Spark(gc, "CPU", "#34d399", lo=0, hi=100, unit="%", min_span=5)
        self.spark_ram = Spark(gc, "Geheugen", "#60a5fa", lo=0, unit=" MB", min_span=100)
        self.spark_tps = Spark(gc, "TPS", "#fbbf24", lo=0, hi=20, min_span=2)
        self.spark_ram.hi_fn = lambda: self.srv_xmx
        for w in (self.spark_cpu, self.spark_ram, self.spark_tps):
            w.pack(side="left", fill="both", expand=True, padx=3)

        pl = ttk.LabelFrame(mid, text=" Spelers online ", padding=6)
        pl.grid(row=0, column=2, sticky="ns")
        self.ptree = ttk.Treeview(pl, columns=("name", "type", "since"), show="headings", height=5,
                                  selectmode="browse")
        for cid, text, w in (("name", "Speler", 150), ("type", "Type", 70), ("since", "Online", 70)):
            self.ptree.heading(cid, text=text)
            self.ptree.column(cid, width=w, anchor="w")
        psb = ttk.Scrollbar(pl, orient="vertical", command=self.ptree.yview)
        self.ptree.configure(yscrollcommand=psb.set)
        self.ptree.pack(side="left", fill="both", expand=True)
        psb.pack(side="left", fill="y")
        self.pmenu = tk.Menu(self, tearoff=0)
        self.pmenu.add_command(label="Bericht sturen…", command=self.player_tell)
        self.pmenu.add_command(label="Kicken…", command=self.player_kick)
        self.ptree.bind("<Button-3>", self._player_menu)

        cf = ttk.LabelFrame(f, text=" Console ", padding=6)
        cf.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        cf.columnconfigure(0, weight=1)
        cf.rowconfigure(1, weight=1)
        tb = ttk.Frame(cf)
        tb.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Checkbutton(tb, text="Schone console", variable=self.clean_var).pack(side="left")
        ttk.Label(tb, textvariable=self.hidden_var, foreground="#6b7280").pack(side="left", padx=(6, 12))
        ttk.Checkbutton(tb, text="Compact", variable=self.compact_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(tb, text="Alleen spelers", variable=self.players_only_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(tb, text="Autoscroll", variable=self.autoscroll_var).pack(side="left", padx=(0, 12))
        ttk.Button(tb, text="Opslaan…", command=self.console_save).pack(side="right")
        ttk.Button(tb, text="Wissen", command=self.console_clear).pack(side="right", padx=6)
        ttk.Entry(tb, textvariable=self.search_var, width=22).pack(side="right")
        ttk.Label(tb, text="Zoeken:").pack(side="right", padx=(0, 4))

        self.console = scrolledtext.ScrolledText(cf, state="disabled", font=("Consolas", int(self.cfg.get("console_font", 10))),
                                                 bg="#0b1220", fg="#d1d5db", relief="flat", wrap="word",
                                                 insertbackground="white", height=12)
        self.console.grid(row=1, column=0, sticky="nsew")
        for tag, color in (("info", "#d1d5db"), ("warn", "#fbbf24"), ("error", "#f87171"), ("join", "#34d399"),
                           ("chat", "#93c5fd"), ("player", "#67e8f9"), ("cmd", "#c4b5fd"), ("dim", "#6b7280"), ("ok", "#4ade80")):
            self.console.tag_configure(tag, foreground=color)

        inp = ttk.Frame(cf)
        inp.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        inp.columnconfigure(1, weight=1)
        ttk.Label(inp, text="Commando:").grid(row=0, column=0, padx=(0, 6))
        self.cmd_entry = ttk.Entry(inp, textvariable=self.cmd_var)
        self.cmd_entry.grid(row=0, column=1, sticky="ew")
        self.cmd_entry.bind("<Return>", lambda e: self.on_send())
        self.cmd_entry.bind("<Up>", self._hist_up)
        self.cmd_entry.bind("<Down>", self._hist_down)
        self.btn_send = ttk.Button(inp, text="Verstuur", command=self.on_send)
        self.btn_send.grid(row=0, column=2, padx=6)
        self.quick_btns = []
        for label, cmd in (("💾  save-all", "save-all"),):
            b = ttk.Button(inp, text=label, command=lambda c=cmd: self.srv_send(c))
            b.grid(row=0, column=3 + len(self.quick_btns), padx=2)
            self.quick_btns.append(b)

        for v in (self.clean_var, self.compact_var, self.autoscroll_var):
            v.trace_add("write", self._opts_changed)
        self.search_var.trace_add("write", self._schedule_rerender)
        self.players_only_var.trace_add("write", self._schedule_rerender)
        self._set_state("stopped")

    # ---------- status / knoppen ----------
    def srv_running(self):
        return self.srv_proc is not None and self.srv_proc.poll() is None

    def _set_state(self, st):
        self.srv_state = st
        txt, col = STATE_UI[st]
        self.srv_state_lbl.config(text=txt, fg=col)
        run = st != "stopped"
        self.btn_s_start.config(state="disabled" if run else "normal")
        self.btn_s_stop.config(state="normal" if st in ("starting", "online") else "disabled")
        self.btn_s_restart.config(state="normal" if st in ("starting", "online") else "disabled")
        self.btn_s_kill.config(state="normal" if run else "disabled")
        for w in [self.cmd_entry, self.btn_send] + self.quick_btns:
            w.config(state="normal" if st in ("starting", "online") else "disabled")
        self.btn_start.config(text="▶  Server starten" if st == "stopped" else "🖥  Naar server")

    def start_server(self):
        """Knop in de balk bovenin."""
        if self.srv_running():
            self.nb.select(self.tab_srv)
        else:
            self.srv_start()

    def srv_cmdline(self):
        c = self.cfg
        folder = self.folder_var.get().strip()
        mode = c.get("launch_mode", "auto")
        sp = (c.get("start_script") or "").strip()
        if mode == "auto":
            mode = "script" if sp and os.path.isfile(sp) else "java"
        self.srv_xmx = None
        if mode == "script":
            if not sp or not os.path.isfile(sp):
                raise ValueError("Er is geen geldig startbestand ingesteld.\nZet er een bij Instellingen → Server, "
                                 "of kies bij Instellingen → Serverbeheer voor 'Java direct'.")
            ext = os.path.splitext(sp)[1].lower()
            try:
                with open(sp, encoding="utf-8", errors="replace") as fh:
                    m = re.search(r"-Xmx(\d+\s*[GgMm])", fh.read(20000))
                    self.srv_xmx = parse_mem_mb(m.group(1)) if m else None
            except OSError:
                pass
            if ext in (".bat", ".cmd"):
                run = sp
                try:
                    with open(sp, "rb") as fh:
                        lines = fh.read().decode("latin-1").splitlines(True)
                    kept = [ln for ln in lines if not re.match(r"\s*pause\s*(>\s*nul)?\s*$", ln, re.I)]
                    if len(kept) != len(lines):  # 'pause' zou de server na een crash laten hangen
                        tmp = os.path.join(os.path.dirname(sp), "_mcupdater_run" + ext)
                        with open(tmp, "wb") as fh:
                            fh.write("".join(kept).encode("latin-1"))
                        self._tmp_script, run = tmp, tmp
                except OSError:
                    pass
                return ["cmd.exe", "/c", "call", run]
            if ext == ".ps1":
                return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", sp]
            return [sp]
        jar = self.jar_var.get().strip() or "server.jar"
        if not os.path.isfile(os.path.join(folder, jar)):
            raise ValueError(f"{jar} niet gevonden in de servermap.")
        cmd = [(c.get("java_path") or "java").strip()]
        for flag, key in (("-Xms", "java_xms"), ("-Xmx", "java_xmx")):
            val = (c.get(key) or "").strip()
            if val:
                cmd.append(flag + val)
        self.srv_xmx = parse_mem_mb(c.get("java_xmx"))
        cmd += ["-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8"]
        cmd += (c.get("java_extra") or "").split()
        cmd += ["-jar", jar, "nogui"]
        return cmd

    def srv_start(self):
        if self.srv_running():
            self.nb.select(self.tab_srv)
            return
        if not self._need_folder():
            return
        try:
            cmd = self.srv_cmdline()
        except ValueError as e:
            messagebox.showwarning(APP_NAME, str(e).replace("\\n", "\n"))
            return
        folder = self.folder_var.get().strip()
        try:
            proc = subprocess.Popen(cmd, cwd=folder, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except FileNotFoundError:
            messagebox.showerror(APP_NAME, "Java (of het startbestand) is niet gevonden.\n\nVul het volledige pad "
                                           "naar java.exe in bij Instellingen → Serverbeheer.")
            return
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Server starten mislukt:\n{e}")
            return
        self.srv_proc = proc
        self.srv_t0 = time.time()
        self._user_stop = False
        self._restart_pending = False
        self._after_exit = None
        self._pcache = {}
        self._last_poll = time.time()
        self.players.clear()
        self.max_players = None
        self._refresh_players()
        for sk in (self.spark_cpu, self.spark_ram, self.spark_tps):
            sk.clear()
        self.sv["tps"].set("-")
        self._set_state("starting")
        self._console_add("▶ Starten: " + subprocess.list2cmdline(cmd), own=True)
        threading.Thread(target=self._srv_reader, args=(proc,), daemon=True).start()
        self.nb.select(self.tab_srv)
        self.log("Server gestart (via dit programma).", "ok")

    def _srv_reader(self, proc):
        try:
            for raw in iter(proc.stdout.readline, b""):
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("cp1252", "replace")
                self.q.put(("srv_line", proc, text))
        except Exception:
            pass
        code = proc.wait()
        self.q.put(("srv_exit", proc, code))

    def srv_send(self, cmd, echo=True):
        p = self.srv_proc
        if not p or p.poll() is not None:
            return False
        try:
            p.stdin.write((cmd + "\n").encode("utf-8"))
            p.stdin.flush()
        except (OSError, ValueError):
            return False
        if echo:
            self._console_add("> " + cmd, own=True)
        return True

    def srv_stop(self, after=None, restart=False):
        if not self.srv_running():
            return
        self._user_stop = True
        self._after_exit = after
        self._restart_pending = restart
        now = time.time()
        self._stop_t, self._last_nl, self._stop_warned = now, now, False
        self._stop_deadline = now + int(self.cfg.get("stop_timeout", 60))
        self._set_state("stopping")
        self.srv_send("stop")

    def _kill_tree(self):
        p = self.srv_proc
        if not p:
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            else:
                p.kill()
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    def srv_kill(self):
        if not self.srv_running():
            return
        if not messagebox.askyesno(APP_NAME, "Geforceerd stoppen kan recente wereld-wijzigingen kosten.\n\n"
                                             "Alleen doen als de server niet meer reageert. Doorgaan?"):
            return
        self._user_stop = True
        self._restart_pending = False
        self._console_add("☠ Geforceerd stoppen…", own=True)
        self._kill_tree()

    def _stop_blocking(self):
        """Veilig stoppen bij het afsluiten van het programma (wacht tot de server klaar is)."""
        self.status("Server wordt veilig gestopt…")
        self._user_stop, self._restart_pending, self._after_exit = True, False, None
        self.srv_send("stop", echo=False)
        end = time.time() + int(self.cfg.get("stop_timeout", 60))
        last_nl = time.time()
        while self.srv_running() and time.time() < end:
            self.update()
            time.sleep(0.1)
            if time.time() - last_nl > 6:  # voor startbestanden die eindigen met 'pause'
                last_nl = time.time()
                self.srv_send("", echo=False)
        if self.srv_running():
            self._kill_tree()

    def _cleanup_tmp(self):
        if self._tmp_script:
            try:
                os.remove(self._tmp_script)
            except OSError:
                pass
            self._tmp_script = None

    def _srv_exited(self, code):
        self.srv_proc = None
        self._cleanup_tmp()
        self._set_state("stopped")
        self.players.clear()
        self._refresh_players()
        for key in ("uptime", "pid", "cpu", "ram", "tps", "players"):
            self.sv[key].set("-")
        self._console_add(f"■ Server gestopt (exitcode {code}).", own=True)
        self.log(f"Server gestopt (exitcode {code}).", "ok" if code in (0, None) else "warn")
        if self._restart_pending:
            self._restart_pending = False
            self.after(1500, self.srv_start)
        elif self._after_exit:
            cb, self._after_exit = self._after_exit, None
            self.after(300, cb)
        elif code not in (0, None) and not self._user_stop and self.cfg.get("auto_restart"):
            now = time.time()
            self._crash_times = [t for t in self._crash_times if now - t < 600] + [now]
            if len(self._crash_times) <= 3:
                self.log("Server gecrasht - automatisch herstarten over 10 seconden…", "warn")
                self.after(10000, self.srv_start)
            else:
                self.log("Server is meer dan 3x in 10 minuten gecrasht - niet meer automatisch herstart.", "error")

    # ---------- console ----------
    def _parse_line(self, raw, own=False):
        if own:
            return dict(kind="own", raw=raw, tag="cmd", time=None, lvl="", msg=raw, phase="run")
        m = LOG_RE.match(raw)
        if m:
            t, lvl, msg = m.group(1), (m.group(2) or m.group(3) or "").upper(), m.group(4)
        else:
            t, lvl, msg = None, "", raw
        tag = "info"
        if lvl in ("ERROR", "SEVERE", "FATAL"):
            tag = "error"
        elif lvl in ("WARN", "WARNING"):
            tag = "warn"
        elif lvl in ("DEBUG", "TRACE"):
            tag = "dim"
        elif JOIN_RE.match(msg) or LEAVE_RE.match(msg):
            tag = "join"
        elif re.match(r"(\[Not Secure\] )?<[^>]+> ", msg):
            tag = "chat"
        elif DONE_RE.search(msg):
            tag = "ok"
        elif not m and CONT_RE.match(raw) and self._last_tag in ("error", "warn"):
            tag = self._last_tag  # stacktrace hoort bij de vorige foutregel
        player = tag in ("join", "chat") or self._is_player_line(msg)
        if player and tag == "info":
            tag = "player"
        self._last_tag = tag
        return dict(kind="srv", raw=raw, tag=tag, time=t, lvl=lvl, msg=msg, phase=self._phase(), player=player)

    def _phase(self):
        """Welke fase zat de server in toen deze regel binnenkwam: start / stop / run."""
        if self.srv_state == "starting":
            return "start"
        if self.srv_state == "stopping":
            return "stop"
        return "start" if time.time() < self._startup_until else "run"

    @staticmethod
    def _hit(patterns, raw):
        low = raw.lower()
        for p in patterns:
            if isinstance(p, str):
                if p in low:
                    return True
            elif p.search(raw):
                return True
        return False

    def _is_keep(self, e):
        """Is dit een belangrijke regel die ook tijdens opstarten/afsluiten zichtbaar moet blijven?"""
        if e["tag"] in ("error", "warn", "join", "chat", "ok"):
            return True
        if e["lvl"] in ("DEBUG", "TRACE"):
            return False
        return self._hit(self.keep, e["raw"])

    def _is_noise(self, e):
        if e.get("player"):  # alles wat bekende spelers doen blijft altijd zichtbaar
            return False
        if self.cfg.get("clean_startup", True) and e.get("phase") in ("start", "stop") and not self._is_keep(e):
            return True
        return self._hit(self.noise, e["raw"])

    def _render(self, e):
        q = self.search_var.get().strip().lower()
        if q and q not in e["raw"].lower():
            return None
        if self.players_only_var.get() and e["kind"] != "own" and not e.get("player"):
            return None
        text = e["raw"]
        if self.compact_var.get() and e["time"]:
            sym = {"WARN": "⚠ ", "WARNING": "⚠ ", "ERROR": "✖ ", "SEVERE": "✖ ", "FATAL": "✖ "}.get(e["lvl"], "")
            text = f"{e['time']}  {sym}{e['msg']}"
        return text, e["tag"]

    def _console_add(self, raw, own=False):
        e = self._parse_line(raw, own)
        self.srv_lines.append(e)
        if e["kind"] != "own" and self.clean_var.get() and self._is_noise(e):
            self.srv_hidden += 1
            self._update_hidden_label()
            return
        r = self._render(e)
        if r:
            self._text_insert(*r)

    def _text_insert(self, text, tag):
        t = self.console
        t.config(state="normal")
        t.insert("end", text + "\n", tag)
        n = int(t.index("end-1c").split(".")[0])
        mx = int(self.cfg.get("console_max_lines", 5000))
        if n > mx + 200:
            t.delete("1.0", f"{n - mx}.0")
        t.config(state="disabled")
        if self.autoscroll_var.get():
            t.see("end")

    def _update_hidden_label(self):
        n = self.srv_hidden
        self.hidden_var.set(f"🧹 {n} regel(s) verborgen" if self.clean_var.get() and n else "")

    def _opts_changed(self, *_):
        self.cfg.update(clean_console=self.clean_var.get(), compact_console=self.compact_var.get(),
                        console_autoscroll=self.autoscroll_var.get())
        self._schedule_rerender()

    def _schedule_rerender(self, *_):
        if self._rr_job:
            self.after_cancel(self._rr_job)
        self._rr_job = self.after(250, self._console_rerender)

    def _console_rerender(self):
        self._rr_job = None
        self.srv_hidden = 0
        chunks = []
        for e in self.srv_lines:
            if e["kind"] != "own" and self.clean_var.get() and self._is_noise(e):
                self.srv_hidden += 1
                continue
            r = self._render(e)
            if r:
                chunks.append(r)
        chunks = chunks[-int(self.cfg.get("console_max_lines", 5000)):]
        t = self.console
        t.config(state="normal")
        t.delete("1.0", "end")
        for text, tag in chunks:
            t.insert("end", text + "\n", tag)
        t.config(state="disabled")
        if self.autoscroll_var.get():
            t.see("end")
        self._update_hidden_label()

    def console_clear(self):
        self.srv_lines.clear()
        self.srv_hidden = 0
        self._console_rerender()

    def console_save(self):
        f = filedialog.asksaveasfilename(title="Console opslaan", defaultextension=".txt",
                                         initialfile=f"console-{datetime.now():%Y%m%d-%H%M%S}.txt",
                                         filetypes=[("Tekstbestand", "*.txt")])
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("\n".join(e["raw"] for e in self.srv_lines))
            self.log(f"Console opgeslagen: {f}", "ok")

    def on_send(self):
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        if cmd.startswith("/"):
            cmd = cmd[1:]
        if self.srv_send(cmd):
            self.cmd_hist.append(cmd)
            self.hist_idx = len(self.cmd_hist)
        else:
            self._console_add("De server draait niet.", own=True)
        self.cmd_var.set("")

    def _hist_up(self, _e):
        if self.cmd_hist and self.hist_idx > 0:
            self.hist_idx -= 1
            self.cmd_var.set(self.cmd_hist[self.hist_idx])
        return "break"

    def _hist_down(self, _e):
        if self.hist_idx < len(self.cmd_hist) - 1:
            self.hist_idx += 1
            self.cmd_var.set(self.cmd_hist[self.hist_idx])
        else:
            self.hist_idx = len(self.cmd_hist)
            self.cmd_var.set("")
        return "break"

    # ---------- regels van de server verwerken ----------
    def _srv_line(self, raw):
        raw = ANSI_RE.sub("", raw).rstrip("\r\n")
        if not raw.strip() or raw.strip() == ">":
            return
        m = LOG_RE.match(raw)
        msg = m.group(4) if m else raw
        now = time.time()
        suppress = False
        lm = LIST_RE.search(msg)
        if lm:
            self._on_list(lm)
            suppress = now < self._sup["list"]
        tm = TPS_RE.search(msg)
        if tm:
            self._on_tps(tm)
            suppress = suppress or now < self._sup["tps"]
        if now < self._sup["any"] and "nknown" in msg and "ommand" in msg:
            suppress = True
        jm = JOIN_RE.match(msg)
        if jm:
            self.players.setdefault(jm.group(1), now)
            self._add_name(jm.group(1))
            self._refresh_players()
        lv = LEAVE_RE.match(msg)
        if lv:
            self.players.pop(lv.group(1), None)
            self._refresh_players()
        if DONE_RE.search(msg) and self.srv_state == "starting":
            self._set_state("online")
            self._startup_until = time.time() + 10
            if self.reach_auto_var.get():
                self.after(20000, self._auto_net_check)
            self.after(3000, lambda: self._auto_poll() if self.srv_state == "online" else None)
        if not suppress:
            self._console_add(raw)

    def _on_list(self, lm):
        try:
            self.max_players = int(lm.group(2))
        except ValueError:
            pass
        names = [n.strip() for n in lm.group(3).split(",") if n.strip()]
        now = time.time()
        for n in names:
            self.players.setdefault(n, now)
            self._add_name(n)
        for n in list(self.players):
            if n not in names:
                del self.players[n]
        self._refresh_players()

    def _on_tps(self, tm):
        heads = [h.strip() for h in tm.group(1).split(",")]
        vals = [v.replace(",", ".") for v in re.findall(r"\d+(?:[.,]\d+)?", tm.group(2))]  # "19,9" of "19.9"
        if not vals:
            return
        d = dict(zip(heads, vals))
        try:
            tps = min(float(d.get("1m", vals[0])), 20.0)
        except ValueError:
            return
        self.sv["tps"].set(f"{tps:.1f}")
        self.spark_tps.add(tps)

    def _auto_poll(self):
        self._last_poll = time.time()
        until = self._last_poll + 4
        self._sup = {"list": until, "tps": until, "any": until}
        self.srv_send("list", echo=False)
        self.srv_send("tps", echo=False)

    # ---------- spelers ----------
    def _refresh_players(self):
        tree = self.ptree
        sel = tree.selection()
        tree.delete(*tree.get_children())
        now = time.time()
        for name in sorted(self.players, key=str.lower):
            kind = "Bedrock" if name.startswith(".") else "Java"
            tree.insert("", "end", iid=name, values=(name, kind, fmt_dur(now - self.players[name])[-8:]))
        if sel and tree.exists(sel[0]):
            tree.selection_set(sel[0])
        if self.srv_running():
            mx = self.max_players if self.max_players is not None else "?"
            self.sv["players"].set(f"{len(self.players)} / {mx}")

    def _player_menu(self, event):
        iid = self.ptree.identify_row(event.y)
        if iid:
            self.ptree.selection_set(iid)
            self.pmenu.tk_popup(event.x_root, event.y_root)

    def player_kick(self):
        sel = self.ptree.selection()
        if sel:
            reason = simpledialog.askstring(APP_NAME, f"Reden voor het kicken van {sel[0]}:", parent=self)
            if reason is not None:
                self.srv_send(f"kick {sel[0]} {reason}".strip())

    def player_tell(self):
        sel = self.ptree.selection()
        if sel:
            text = simpledialog.askstring(APP_NAME, f"Bericht aan {sel[0]}:", parent=self)
            if text:
                self.srv_send(f"msg {sel[0]} {text}")

    # ---------- statistieken ----------
    def _stats_tick(self):
        try:
            self._stats_update()
        except Exception:
            pass
        try:
            ms = max(1, int(self.cfg.get("stats_secs", 2))) * 1000
        except (TypeError, ValueError):
            ms = 2000
        self.after(ms, self._stats_tick)

    def _proc_stats(self):
        try:
            root = psutil.Process(self.srv_proc.pid)
            procs = [root] + root.children(recursive=True)
        except psutil.Error:
            return None, None
        cpu = ram = 0.0
        live = {}
        for p in procs:
            cached = self._pcache.get(p.pid)
            pr = cached or p
            live[p.pid] = pr
            try:
                c = pr.cpu_percent(None)  # eerste meting van een proces is altijd 0
                if cached:
                    cpu += c
                ram += pr.memory_info().rss
            except psutil.Error:
                pass
        self._pcache = live
        return cpu / (psutil.cpu_count() or 1), ram / 1048576

    def _stats_update(self):
        if not self.srv_running():
            return
        now = time.time()
        self.sv["uptime"].set(fmt_dur(now - self.srv_t0))
        self.sv["pid"].set(str(self.srv_proc.pid))
        if psutil:
            cpu, ram = self._proc_stats()
            self.sv["cpu"].set("-" if cpu is None else f"{cpu:.0f}%")
            if ram is None:
                self.sv["ram"].set("-")
            else:
                self.sv["ram"].set(f"{ram:.0f} MB" + (f" / {self.srv_xmx} MB" if self.srv_xmx else ""))
            self.spark_cpu.add(cpu)
            self.spark_ram.add(ram)
        else:
            self.sv["cpu"].set("psutil nodig")
            self.sv["ram"].set("psutil nodig")
        self._refresh_players()
        self.spark_tps.redraw()
        if self.srv_state == "stopping":
            if now - self._stop_t > 6 and now - self._last_nl > 5:
                self._last_nl = now
                self.srv_send("", echo=False)  # vangt een 'pause' aan het eind van een startbestand op
            if now > self._stop_deadline and not self._stop_warned:
                self._stop_warned = True
                self.log("De server stopt nog steeds. Gebruik 'Geforceerd stoppen' als hij niet meer reageert.", "warn")
        poll = int(self.cfg.get("poll_secs", 30))
        if self.srv_state == "online" and poll > 0 and now - self._last_poll >= poll:
            self._auto_poll()

    def install_psutil(self):
        if getattr(sys, "frozen", False):
            messagebox.showinfo(APP_NAME, "Installeer psutil in je Python (pip install psutil) en bouw de .exe daarna opnieuw.")
            return
        self.btn_psutil.config(state="disabled")
        self.psutil_lbl.config(text="psutil installeren…")

        def work():
            try:
                r = subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], capture_output=True, text=True,
                                   timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                ok = r.returncode == 0
            except Exception:
                ok = False
            self.q.put(("psutil_done", ok))

        threading.Thread(target=work, daemon=True).start()

    def _psutil_done(self, ok):
        if ok and load_psutil():
            if self.psutil_frame:
                self.psutil_frame.destroy()
                self.psutil_frame = None
            self.log("psutil geïnstalleerd - CPU en geheugen worden nu getoond.", "ok")
        else:
            self.psutil_lbl.config(text="Installeren mislukt (pip install psutil)")
            self.btn_psutil.config(state="normal")


    # ---------- grafieken ----------
    def _apply_graph_cfg(self):
        try:
            mins = max(1, int(self.cfg.get("graph_minutes", 5)))
        except (TypeError, ValueError):
            mins = 5
        zoom = bool(self.cfg.get("graph_zoom", True))
        for sk in (self.spark_cpu, self.spark_ram, self.spark_tps):
            sk.window, sk.zoom = mins * 60, zoom
            sk.redraw()
        self.graph_var.set(graph_label(mins))
        self.zoom_var.set(zoom)

    def _graph_pick(self, _e=None):
        self.cfg["graph_minutes"] = parse_graph_label(self.graph_var.get())
        self._save_cfg()
        self._apply_graph_cfg()

    def _graph_zoom_changed(self):
        self.cfg["graph_zoom"] = bool(self.zoom_var.get())
        self._save_cfg()
        self._apply_graph_cfg()

    # ---------- RAM wijzigen ----------
    def _launch_mode(self):
        c = self.cfg
        mode = c.get("launch_mode", "auto")
        sp = (c.get("start_script") or "").strip()
        if mode == "auto":
            mode = "script" if sp and os.path.isfile(sp) else "java"
        return mode, sp

    def _ram_current(self):
        mode, sp = self._launch_mode()
        if mode == "script":
            try:
                with open(sp, "rb") as fh:
                    t = fh.read(50000).decode("latin-1")
                m = re.search(r"-Xmx(\d+\s*[GgMm])", t)
                return m.group(1).replace(" ", "") if m else ""
            except OSError:
                return ""
        return (self.cfg.get("java_xmx") or "").strip()

    def _sync_ram_var(self):
        try:
            self.ram_var.set(self._ram_current())
        except AttributeError:
            pass

    def _edit_script_ram(self, sp, val, mb):
        """Zet -Xmx (en zo nodig -Xms) in een .bat/.cmd. Origineel wordt eenmalig bewaard als .mcupdater.bak."""
        with open(sp, "rb") as fh:
            raw = fh.read()
        text = raw.decode("latin-1")
        old = re.search(r"-Xmx(\d+\s*[GgMm])", text)
        if old:
            old_mb = parse_mem_mb(old.group(1))
            text = text[:old.start()] + "-Xmx" + val + text[old.end():]
            ms = re.search(r"-Xms(\d+\s*[GgMm])", text)
            if ms:
                ms_mb = parse_mem_mb(ms.group(1))
                if ms_mb == old_mb or (ms_mb and ms_mb > mb):  # Xms mag nooit hoger zijn dan Xmx
                    text = text[:ms.start()] + "-Xms" + val + text[ms.end():]
        else:
            j = re.search(r"(\bjavaw?(?:\.exe)?\"?)(?=[ \t][^\r\n]*-jar)", text, re.I)
            if not j:
                return None
            text = text[:j.end()] + " -Xmx" + val + text[j.end():]
        bak = sp + ".mcupdater.bak"
        if not os.path.exists(bak):
            with open(bak, "wb") as fh:
                fh.write(raw)
        with open(sp, "wb") as fh:
            fh.write(text.encode("latin-1"))
        return f"RAM in {os.path.basename(sp)} aangepast naar {val} (origineel bewaard als {os.path.basename(bak)})."

    def ram_apply(self):
        val = self.ram_var.get().strip().upper().replace(" ", "")
        mb = parse_mem_mb(val)
        if mb is None or mb < 512:
            messagebox.showwarning(APP_NAME, "Vul een geldige hoeveelheid in, bijvoorbeeld 4G of 6144M (minimaal 512M).")
            return
        if psutil:
            total = psutil.virtual_memory().total // 1048576
            if mb > total * 0.85 and not messagebox.askyesno(
                    APP_NAME, f"{val} is meer dan 85% van het geheugen van deze pc ({total // 1024} GB). De server en "
                              "Windows kunnen dan vastlopen.\n\nToch doorgaan?"):
                return
        mode, sp = self._launch_mode()
        if mode == "script":
            if not sp or not os.path.isfile(sp):
                messagebox.showwarning(APP_NAME, "Het startbestand bestaat niet (meer). Controleer Instellingen → Server.")
                return
            try:
                msg = self._edit_script_ram(sp, val, mb)
            except OSError as e:
                messagebox.showerror(APP_NAME, f"Het startbestand kon niet worden aangepast:\n{e}")
                return
            if msg is None:
                messagebox.showwarning(APP_NAME, "Ik vond geen -Xmx of java-regel in je startbestand. Pas het zelf aan, "
                                                 "of kies 'Java direct' bij Instellingen → Serverbeheer.")
                return
        else:
            self.cfg["java_xmx"] = val
            xms = parse_mem_mb(self.cfg.get("java_xms"))
            if xms and xms > mb:
                self.cfg["java_xms"] = val
            self._save_cfg()
            msg = f"Max. RAM ingesteld op {val} (Java direct)."
        self.log(msg, "ok")
        self._sync_ram_var()
        if self.srv_running():
            if messagebox.askyesno(APP_NAME, "De nieuwe RAM-instelling geldt pas na een herstart.\n\nNu veilig herstarten?"):
                self.srv_stop(restart=True)
        else:
            self.status(f"Max. RAM: {val}. Geldt bij de eerstvolgende start.")

    # ================= Bereikbaarheid =================
    def _build_net_tab(self, f):
        f.columnconfigure(0, weight=1)
        a = ttk.LabelFrame(f, text=" Adres van je server ", padding=10)
        a.grid(row=0, column=0, sticky="ew")
        a.columnconfigure(1, weight=1)
        ttk.Label(a, text="Publiek IP-adres of domein:").grid(row=0, column=0, sticky="w")
        ttk.Entry(a, textvariable=self.reach_host_var).grid(row=0, column=1, sticky="ew", padx=8)
        self.btn_myip = ttk.Button(a, text="Mijn IP opzoeken", command=self._net_find_ip)
        self.btn_myip.grid(row=0, column=2)
        pr = ttk.Frame(a)
        pr.grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Label(pr, text="Java-poort:").pack(side="left")
        ttk.Spinbox(pr, from_=1, to=65535, width=7, textvariable=self.reach_port_var).pack(side="left", padx=(4, 18))
        ttk.Checkbutton(pr, text="Bedrock (Geyser) ook controleren - UDP-poort:", variable=self.reach_bed_var).pack(side="left")
        ttk.Spinbox(pr, from_=1, to=65535, width=7, textvariable=self.reach_bport_var).pack(side="left", padx=4)
        pr2 = ttk.Frame(a)
        pr2.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(pr2, text="Lokale poort van de server (voor de lokale test):").pack(side="left")
        ttk.Spinbox(pr2, from_=1, to=65535, width=7, textvariable=self.reach_lport_var).pack(side="left", padx=4)
        ttk.Label(pr2, text="(uit server.properties)", foreground="#6b7280").pack(side="left", padx=4)
        br = ttk.Frame(a)
        br.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.btn_net_ext = ttk.Button(br, text="🌍  Controleer van buitenaf", style="Big.TButton",
                                      command=lambda: self.net_check())
        self.btn_net_ext.pack(side="left")
        self.btn_net_loc = ttk.Button(br, text="🏠  Alleen lokaal", command=lambda: self.net_check(local_only=True))
        self.btn_net_loc.pack(side="left", padx=8)
        ttk.Checkbutton(br, text="Automatisch controleren na het opstarten van de server",
                        variable=self.reach_auto_var).pack(side="left", padx=14)

        r = ttk.LabelFrame(f, text=" Resultaat ", padding=10)
        r.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        f.rowconfigure(1, weight=1)
        r.columnconfigure(0, weight=1)
        self.net_status = tk.Label(r, text="Nog niet gecontroleerd", font=("Segoe UI", 13, "bold"), fg="#6b7280",
                                   anchor="w", justify="left", wraplength=1000)
        self.net_status.grid(row=0, column=0, sticky="ew")
        card = tk.Frame(r, bg="#111827", padx=14, pady=14)
        card.grid(row=1, column=0, sticky="ew", pady=10)
        card.columnconfigure(1, weight=1)
        self.net_icon = tk.Label(card, bg="#1f2937", fg="#6b7280", text="geen\nicoon", width=14, height=7,
                                 font=("Segoe UI", 9))
        self.net_icon.grid(row=0, column=0, rowspan=2, padx=(0, 16), sticky="n")
        self.net_motd = tk.Label(card, bg="#111827", fg="#f3f4f6", font=("Consolas", 13, "bold"), justify="left",
                                 anchor="nw", text="-", wraplength=800)
        self.net_motd.grid(row=0, column=1, sticky="nw")
        self.net_info = tk.Label(card, bg="#111827", fg="#9ca3af", font=("Segoe UI", 10), justify="left",
                                 anchor="nw", text="")
        self.net_info.grid(row=1, column=1, sticky="nw", pady=(8, 0))
        self.net_bed = tk.Label(r, text="", anchor="w", justify="left", font=("Segoe UI", 10, "bold"), wraplength=1000)
        self.net_bed.grid(row=2, column=0, sticky="ew")
        self.net_diag = tk.Label(r, text="", anchor="nw", justify="left", fg="#374151", font=("Segoe UI", 10),
                                 wraplength=1000)
        self.net_diag.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(r, text="De controle van buitenaf loopt via api.mcsrvstat.us (die dienst benadert je server vanaf internet; "
                          "resultaten zijn tot 5 minuten oud). 'Mijn IP opzoeken' gebruikt api.ipify.org.",
                  foreground="#6b7280", wraplength=1000, justify="left").grid(row=4, column=0, sticky="w", pady=(10, 0))

    def _net_set_busy(self, busy):
        for b in (self.btn_net_ext, self.btn_net_loc, self.btn_myip):
            b.config(state="disabled" if busy else "normal")

    def _net_find_ip(self):
        self.btn_myip.config(state="disabled")

        def work():
            try:
                self.q.put(("net_ip", fetch_public_ip(), None))
            except Exception as e:
                self.q.put(("net_ip", None, describe_net_error(e)))

        threading.Thread(target=work, daemon=True).start()

    def _net_ip_done(self, ip, err):
        self.btn_myip.config(state="normal")
        if ip:
            self.reach_host_var.set(ip)
            self.log(f"Publiek IP-adres gevonden: {ip}", "ok")
        else:
            messagebox.showwarning(APP_NAME, f"Kon je IP-adres niet opzoeken: {err}")

    def net_check(self, local_only=False, silent=False):
        if self._net_busy:
            return
        host, port_in = split_host(self.reach_host_var.get())
        jport = min(max(int_var(self.reach_port_var, 25565), 1), 65535)
        bport = min(max(int_var(self.reach_bport_var, 19132), 1), 65535)
        lport = min(max(int_var(self.reach_lport_var, 25565), 1), 65535)
        if port_in:
            jport = port_in
            self.reach_port_var.set(jport)
        if host != self.reach_host_var.get().strip():
            self.reach_host_var.set(host)
        if not local_only and not host:
            if not silent:
                messagebox.showinfo(APP_NAME, "Vul eerst het publieke IP-adres of domein van je server in "
                                              "(of klik op 'Mijn IP opzoeken').")
            return
        self._save_cfg()
        self._net_busy = True
        self._net_set_busy(True)
        self.net_status.config(text="Bezig met controleren…", fg="#6b7280")
        threading.Thread(target=self._net_worker, daemon=True,
                         args=(host, jport, local_only, bool(self.reach_bed_var.get()), bport, lport,
                               self.srv_state == "online", silent)).start()

    def _net_worker(self, host, jport, local_only, bed, bport, lport, srv_online, silent):
        res = {"t": datetime.now().strftime("%H:%M:%S"), "local_only": local_only, "silent": silent,
               "host": host, "jport": jport, "bport": bport, "lport": lport}
        try:
            if not local_only:
                try:
                    res["ext"] = mcsrv_status(host, jport)
                except Exception as e:
                    res["ext_err"] = describe_net_error(e)
                if bed:
                    try:
                        res["bed"] = mcsrv_status(host, bport, bedrock=True)
                    except Exception as e:
                        res["bed_err"] = describe_net_error(e)
            if local_only or ("ext" in res and not res["ext"]["online"]):
                try:
                    res["loc"] = slp_status("127.0.0.1", lport)
                except Exception as e:
                    res["loc_err"] = describe_net_error(e)
            res["diag"] = net_diagnose(res, host, jport, lport, srv_online)
        except Exception as e:  # nooit het venster op 'bezig' laten staan
            res["diag"] = ("warn", f"Onverwachte fout bij het controleren.\n{e}")
        self.q.put(("net_result", res))

    def _local_icon_data(self):
        try:
            with open(os.path.join(self.folder_var.get().strip(), "server-icon.png"), "rb") as fh:
                return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")
        except OSError:
            return None

    def _net_set_icon(self, data):
        img = None
        if data:
            try:
                raw = data.split(",", 1)[1] if data.startswith("data:") else data
                img = tk.PhotoImage(data=raw)
                if img.width() <= 64:
                    img = img.zoom(2, 2)
            except Exception:
                img = None
        self._net_img = img  # referentie vasthouden, anders verdwijnt het plaatje
        if img:
            self.net_icon.config(image=img, text="", width=img.width(), height=img.height())
        else:
            self.net_icon.config(image="", text="geen\nicoon", width=14, height=7)

    def _net_show(self, res):
        self._net_busy = False
        self._net_set_busy(False)
        ext, loc, bed = res.get("ext"), res.get("loc"), res.get("bed")
        level, text = res["diag"]
        head, _, rest = text.partition("\n")
        self.net_status.config(text=head, fg={"ok": "#059669", "bad": "#b91c1c", "warn": "#d97706"}[level])
        self.net_diag.config(text=rest)
        card = ext if (ext and ext["online"]) else (loc if loc else None)
        if card:
            self.net_motd.config(text=card["motd"] or "(geen MOTD ingesteld)")
            parts = []
            if card["version"]:
                parts.append(f"Versie: {card['version']}")
            if card["software"]:
                parts.append(f"Software: {card['software']}")
            on, mx = card["players"]
            if on is not None:
                names = card["names"]
                who = f"   ({', '.join(names[:8])}{' …' if len(names) > 8 else ''})" if names else ""
                parts.append(f"Spelers: {on} / {mx if mx is not None else '?'}{who}")
            if card is ext:
                addr = card.get("hostname") or res["host"]
                parts.append(f"Adres: {addr}:{card.get('port') or res['jport']}"
                             + (f"  (IP {card['ip']})" if card.get("ip") and card["ip"] != addr else ""))
                age = card.get("age")
                parts.append(f"Bron: van buitenaf gecontroleerd om {res['t']} via mcsrvstat.us"
                             + (f" (resultaat {age // 60} min {age % 60} s oud)" if age else ""))
            else:
                parts.append(f"Bron: lokaal gecontroleerd om {res['t']} (127.0.0.1:{res['lport']}, {card['ms']} ms)")
            self.net_info.config(text="\n".join(parts))
            self._net_set_icon(card.get("icon") or (self._local_icon_data() if card is loc else None))
        else:
            self.net_motd.config(text="Geen server gevonden")
            self.net_info.config(text="")
            self._net_set_icon(None)
        if bed:
            if bed["online"]:
                on, mx = bed["players"]
                self.net_bed.config(fg="#059669", text=f"Bedrock (Geyser): ✔ bereikbaar op UDP-poort {res['bport']}"
                                                       + (f" - {bed['version']}" if bed["version"] else "")
                                                       + (f", spelers {on} / {mx}" if on is not None else ""))
            else:
                self.net_bed.config(fg="#b91c1c", text=f"Bedrock (Geyser): ✖ niet bereikbaar op UDP-poort {res['bport']}. "
                                                       "Stuur die UDP-poort door in je router en open hem in de firewall.")
        elif res.get("bed_err"):
            self.net_bed.config(fg="#6b7280", text=f"Bedrock-controle mislukt: {res['bed_err']}")
        else:
            self.net_bed.config(text="")
        self.log(head, {"ok": "ok", "bad": "warn", "warn": "warn"}[level])

    def _auto_net_check(self):
        if self.srv_state == "online" and self.reach_auto_var.get():
            self.net_check(silent=True)

    # ---------- spelers herkennen in de console ----------
    def _load_usercache(self, folder):
        try:
            with open(os.path.join(folder, "usercache.json"), encoding="utf-8") as fh:
                for x in json.load(fh):
                    if isinstance(x, dict) and isinstance(x.get("name"), str):
                        self._add_name(x["name"])
        except (OSError, ValueError):
            pass

    def _add_name(self, name):
        if name and len(name) >= 3 and name not in self.player_names:
            self.player_names.add(name)
            self._names_dirty = True

    def _name_rx(self):
        if self._names_dirty:
            names = sorted(self.player_names, key=len, reverse=True)
            self._name_rx_c = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(n) for n in names)
                                         + r")(?![A-Za-z0-9_])") if names else None
            self._names_dirty = False
        return self._name_rx_c

    def _is_player_line(self, msg):
        """Gaat deze regel over een speler die de server kent? (bots met willekeurige namen tellen niet mee)"""
        if not self.cfg.get("show_player_activity", True):
            return False
        rx = self._name_rx()
        if rx is None:
            return False
        low = msg.lower()
        if any(h in low for h in PLAYER_HIDE):
            return False
        return bool(rx.search(msg))

    def _close(self):
        if self.srv_running():
            if not messagebox.askyesno(APP_NAME, "De server draait nog.\n\nHij wordt veilig gestopt (de wereld wordt "
                                                 "opgeslagen) en daarna sluit het programma. Doorgaan?"):
                return
            self._stop_blocking()
        self._cleanup_tmp()
        self._save_cfg()
        self.destroy()

    def browse(self):
        d = filedialog.askdirectory(title="Kies de map van je Minecraft-server",
                                    initialdir=self.folder_var.get() or None)
        if d:
            self.folder_var.set(os.path.normpath(d))
            self.jar_var.set(guess_jar(d))
            self.load_folder()

    def load_folder(self):
        folder = self.folder_var.get().strip()
        if not os.path.isdir(folder):
            self.log("Die map bestaat niet.", "error")
            return
        if not self.jar_var.get().strip() or not os.path.isfile(os.path.join(folder, self.jar_var.get().strip())):
            self.jar_var.set(guess_jar(folder))
        mc, build = detect_server_info(folder, self.jar_var.get().strip())
        mc = (self.cfg.get("mc_override") or "").strip() or mc
        self.q.put(("set_mc", mc))
        self.q.put(("set_build", build))
        plugins = os.path.join(folder, "plugins")
        n = len([f for f in os.listdir(plugins) if f.lower().endswith(".jar")]) if os.path.isdir(plugins) else 0
        self.log(f"Server geladen: {folder}", "ok")
        self.log(f"Jar: {self.jar_var.get()}  |  Minecraft: {mc or 'niet gevonden (vul handmatig in)'}  |  "
                 f"Paper-build: {build or 'onbekend'}  |  {n} plugin(s)")
        props = read_properties(folder)
        try:
            self.reach_lport_var.set(int(props.get("server-port", 25565)))
        except ValueError:
            pass
        self._load_usercache(folder)
        self.status("Klaar. Klik op 'Alles controleren'.")
        self._save_cfg()

    def _need_folder(self):
        folder = self.folder_var.get().strip()
        if not os.path.isdir(folder):
            messagebox.showwarning(APP_NAME, "Kies eerst de map van je server.")
            return False
        return True

    def on_check_all(self):
        if self._need_folder():
            self._save_cfg()
            self.run_bg(self.w_check_all, self.ctx())

    def on_paper_check(self):
        if self._need_folder():
            self._save_cfg()
            self.run_bg(self.w_paper_check, self.ctx())

    def on_plugins_check(self):
        if self._need_folder():
            self._save_cfg()
            self.run_bg(self.w_plugins_check, self.ctx())

    def on_paper_update(self):
        if not self._need_folder():
            return
        if self.srv_running():
            if not messagebox.askyesno(APP_NAME, "De server draait. Veilig stoppen, Paper updaten en daarna de "
                                                 "server opnieuw starten?"):
                return
            self._save_cfg()

            def go():
                self._restart_after_update = True
                self.run_bg(self.w_paper_update, self.ctx())

            self.srv_stop(after=go)
            return
        if self.cfg.get("confirm", True) and not messagebox.askyesno(
                APP_NAME, "Het Paper-bestand wordt vervangen (de oude wordt eerst als backup opzijgezet).\n\n"
                          "Is je server gestopt?"):
            return
        self._save_cfg()
        self.run_bg(self.w_paper_update, self.ctx())

    def on_plugins_update(self, everything):
        if not self._need_folder():
            return
        if everything:
            targets = [fn for fn, r in self.rows.items() if r.get("state") == "update"]
        else:
            targets = [i for i in self.tree.selection() if self.rows.get(i, {}).get("state") == "update"]
        if not targets:
            messagebox.showinfo(APP_NAME, "Geen updates om te installeren. Controleer eerst op updates, "
                                          "of selecteer plugins met status 'Update beschikbaar'.")
            return
        if self.srv_running() and not self.updfolder_var.get():
            if not messagebox.askyesno(APP_NAME, f"De server draait. Veilig stoppen, {len(targets)} plugin(s) updaten "
                                                 "en daarna de server opnieuw starten?"):
                return
            self._save_cfg()

            def go():
                self._restart_after_update = True
                self.run_bg(self.w_plugins_update, self.ctx(), targets)

            self.srv_stop(after=go)
            return
        if self.cfg.get("confirm", True) and not self.updfolder_var.get():
            if not messagebox.askyesno(APP_NAME, f"{len(targets)} plugin(s) updaten?\n\n"
                                                 "Zorg dat je server gestopt is (of vink de optie "
                                                 "'plugins/update' aan als hij draait)."):
                return
        self._save_cfg()
        self.run_bg(self.w_plugins_update, self.ctx(), targets)

    def open_backups(self):
        d = self.backup_root()
        if os.path.isdir(d):
            try:
                os.startfile(d)
            except AttributeError:
                webbrowser.open(d)
        else:
            messagebox.showinfo(APP_NAME, "Er zijn nog geen backups gemaakt.")

    def on_double(self, _event):
        iid = self.tree.focus()
        page = self.rows.get(iid, {}).get("page")
        if page:
            webbrowser.open(page)

    # ---------------- Workers (draaien in een thread) ----------------
    def w_check_all(self, ctx):
        self.w_paper_check(ctx)
        self.w_plugins_check(ctx)

    def w_paper_check(self, ctx):
        mc = ctx["mc"]
        if not mc:
            self.log("Minecraft-versie onbekend - vul die in bij 'Minecraft-versie'.", "warn")
            self.q.put(("paper_label", "✖ Minecraft-versie onbekend", "#b71c1c"))
            return
        self.status("Paper controleren…")
        self.q.put(("spin", True))
        self.log(f"Paper: nieuwste build zoeken voor Minecraft {mc}…")
        latest = paper_latest(mc, ctx["unstable"])
        jar_path = os.path.join(ctx["folder"], ctx["jar"])
        local_hash = None
        if os.path.isfile(jar_path):
            self.status("Lokale jar controleren…")
            local_hash = file_hash(jar_path, "sha256")
        cur = ctx["build"]
        if not os.path.isfile(jar_path):
            state = "missing"
        elif local_hash and latest["sha256"] and local_hash.lower() == latest["sha256"].lower():
            state = "ok"
        elif cur is not None:
            state = "ok" if cur >= latest["build"] else "update"
        else:
            state = "update"
        latest["state"] = state
        self.paper_info = latest
        ch = latest["channel"]
        if state == "ok":
            self.q.put(("paper_label", f"✔ Paper is up-to-date  (MC {mc}, build {latest['build']}, {ch})", "#1b5e20"))
            self.log(f"Paper is up-to-date (build {latest['build']}, {ch}).", "ok")
            self.q.put(("set_build", latest["build"] if cur is None or cur < latest["build"] else cur))
        elif state == "missing":
            self.q.put(("paper_label", f"✖ {ctx['jar']} niet gevonden - nieuwste is build {latest['build']}", "#b71c1c"))
            self.log(f"{ctx['jar']} niet gevonden in de servermap.", "error")
        else:
            self.q.put(("paper_label", f"⬆ Update beschikbaar: build {cur or 'onbekend'} → {latest['build']}  ({ch})",
                        "#e65100"))
            self.log(f"Paper-update beschikbaar: build {cur or 'onbekend'} → {latest['build']} ({ch}, "
                     f"{fmt_size(latest['size'])}).", "warn")
        if ch != "STABLE":
            self.log(f"Let op: build {latest['build']} heeft kanaal {ch} (niet stabiel).", "warn")
        try:
            newest = paper_newest_mc()
            if newest and re.fullmatch(r"\d+(\.\d+)*", mc) and vtuple(newest) > vtuple(mc):
                self.log(f"Info: er bestaat een nieuwere Minecraft-versie ({newest}). Dit programma updatet alleen "
                         f"binnen {mc}; een upgrade naar een nieuwe versie doe je zelf, na controle van je plugins.")
        except Exception:
            pass
        self.q.put(("spin", False))
        self.status("Paper gecontroleerd.")

    def w_paper_update(self, ctx):
        if not self.paper_info or self.paper_info.get("state") is None:
            self.w_paper_check(ctx)
        info = self.paper_info
        if not info:
            return
        if info["state"] == "ok":
            self.log("Paper is al up-to-date, niets te doen.", "ok")
            return
        folder, jar = ctx["folder"], ctx["jar"]
        jar_path = os.path.join(folder, jar)
        tmp_dir = os.path.join(folder, "updater_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp = os.path.join(tmp_dir, jar + ".part")
        self.log(f"Paper build {info['build']} downloaden ({fmt_size(info['size'])})…")

        def cb(done, total):
            self.progress(done, total or 1)
            if total:
                self.status(f"Paper downloaden… {done * 100 // total}%")

        download(info["url"], tmp, cb, ("sha256", info["sha256"]) if info["sha256"] else None)
        self.log("Download klaar, checksum (SHA-256) klopt.", "ok")
        sdir = os.path.join(ctx["backup_root"], "server")
        btag = f"build{ctx['build']}_" if ctx.get("build") else ""
        bfile = os.path.join(sdir, f"{datetime.now():%Y%m%d-%H%M%S}_{btag}{jar}")
        if os.path.isfile(jar_path):
            os.makedirs(sdir, exist_ok=True)
            shutil.move(jar_path, bfile)  # faalt als de server nog draait
        try:
            safe_move(tmp, jar_path)
        except Exception:
            # terugzetten
            if os.path.isfile(bfile):
                shutil.move(bfile, jar_path)
            raise
        if os.path.isfile(bfile):
            if ctx["keep_server"]:
                self.log(f"Oude {jar} bewaard als {bfile}")
                prune_files(sdir, ctx["server_max"], self.log)
            else:
                os.remove(bfile)
                self.log(f"Oude {jar} verwijderd (server-backups staan uit).")
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
        info["state"] = "ok"
        self.q.put(("set_build", info["build"]))
        self.q.put(("paper_label", f"✔ Bijgewerkt naar build {info['build']} - start je server opnieuw", "#0d47a1"))
        self.log(f"Paper bijgewerkt naar build {info['build']}. Start de server opnieuw.", "ok")
        self.status("Paper bijgewerkt.")
        self.progress(1, 1)

    def w_plugins_check(self, ctx):
        pdir = os.path.join(ctx["folder"], "plugins")
        if not os.path.isdir(pdir):
            self.log("Geen 'plugins'-map gevonden in de servermap.", "error")
            return
        jars = sorted((f for f in os.listdir(pdir)
                       if f.lower().endswith(".jar") and os.path.isfile(os.path.join(pdir, f))), key=str.lower)
        self.rows = {}
        self.q.put(("clear_rows",))
        if not jars:
            self.log("Geen plugins gevonden.", "warn")
            return
        mc = ctx["mc"]
        self.log(f"{len(jars)} plugin(s) gevonden, controleren via Modrinth"
                 f"{' voor MC ' + mc if mc else ''}…")
        total = len(jars) + 2
        done = 0
        hash_to_files = defaultdict(list)
        for fn in jars:
            self.status(f"Bestand lezen: {fn}")
            path = os.path.join(pdir, fn)
            name, ver, site = read_plugin_meta(path)
            name = name or fn[:-4]
            self.rows[fn] = dict(path=path, name=name, local_ver=ver, website=site, state="busy",
                                 pid=None, page=None, cur_txt=ver or "?")
            ign = ctx["ignore"]
            if name.lower() in ign or fn.lower() in ign or fn[:-4].lower() in ign:
                self.rows[fn]["state"] = "ignored"
                self.row(fn, name, ver or "?", "", "", "⏸ Uitgesloten (instellingen)", "unknown")
            else:
                hash_to_files[file_hash(path, "sha1")].append(fn)
                self.row(fn, name, ver or "?", "", "", "Controleren…", "busy")
            done += 1
            self.progress(done, total)

        self.status("Modrinth raadplegen…")
        found = (http_json(f"{MODRINTH}/version_files", {"hashes": list(hash_to_files), "algorithm": "sha1"})
                 if hash_to_files else {})
        done += 1
        self.progress(done, total)

        by_project = defaultdict(list)  # pid -> [(fn, huidige versie)]
        missing = []
        for h, files in hash_to_files.items():
            v = found.get(h)
            for fn in files:
                if v:
                    by_project[v["project_id"]].append((fn, v))
                else:
                    missing.append(fn)
        titles = {}
        if by_project:
            ids = sorted(by_project)
            projs = http_json(f"{MODRINTH}/projects?ids=" + urllib.parse.quote(json.dumps(ids)))
            titles = {p["id"]: p.get("title") for p in projs}
        total += len(by_project) + len(missing)
        updates = 0
        for pid, items in by_project.items():
            title = titles.get(pid) or pid
            self.status(f"Controleren: {title}")
            params = {"loaders": json.dumps(ctx["loaders"] or LOADERS)}
            if mc:
                params["game_versions"] = json.dumps([mc])
            try:
                versions = http_json(f"{MODRINTH}/project/{pid}/version?" + urllib.parse.urlencode(params))
            except Exception as e:
                for fn, cur in items:
                    self.rows[fn]["state"] = "error"
                    self.row(fn, title, cur["version_number"], "", "Modrinth", f"Fout: {e}", "error")
                done += 1
                self.progress(done, total)
                continue
            for fn, cur in items:
                r = self.rows[fn]
                r.update(pid=pid, title=title, page=f"https://modrinth.com/project/{pid}")
                cur_rank = TYPE_RANK.get(cur.get("version_type", "release"), 0)
                max_rank = 2 if ctx["unstable"] else cur_rank
                latest = next((v for v in versions if TYPE_RANK.get(v.get("version_type"), 0) <= max_rank), None)
                cur_txt = cur["version_number"]
                r["cur_txt"] = cur_txt
                if latest is None:
                    r["state"] = "unknown"
                    self.row(fn, title, cur_txt, "", "Modrinth",
                             f"Geen compatibele versie{' voor ' + mc if mc else ''}", "unknown")
                elif latest["id"] == cur["id"] or latest["date_published"] <= cur["date_published"]:
                    r["state"] = "ok"
                    self.row(fn, title, cur_txt, latest["version_number"], "Modrinth", "✔ Up-to-date", "ok")
                else:
                    files = latest.get("files", [])
                    f = next((x for x in files if x.get("primary")), files[0] if files else None)
                    if not f:
                        r["state"] = "error"
                        self.row(fn, title, cur_txt, latest["version_number"], "Modrinth",
                                 "✖ Geen bestand bij nieuwste versie", "error")
                        continue
                    hashes = f.get("hashes", {})
                    algo = "sha512" if "sha512" in hashes else ("sha1" if "sha1" in hashes else None)
                    r.update(state="update", latest_txt=latest["version_number"], source="Modrinth",
                             dl=dict(url=f["url"], filename=f["filename"], algo=algo,
                                     hash=hashes.get(algo) if algo else None))
                    updates += 1
                    kind = latest.get("version_type", "release")
                    extra = "" if kind == "release" else f" ({kind})"
                    self.row(fn, title, cur_txt, latest["version_number"], "Modrinth",
                             f"⬆ Update beschikbaar{extra}", "update")
            done += 1
            self.progress(done, total)

        # ---- Fallback: plugins die niet op Modrinth staan -> Hangar / GitHub ----
        extra_found = 0
        for fn in missing:
            r = self.rows[fn]
            name, cur = r["name"], r["local_ver"]
            self.status(f"Niet op Modrinth - zoeken op Hangar/GitHub: {name}")
            self.row(fn, name, r["cur_txt"], "", "", "Zoeken op Hangar/GitHub…", "busy")
            res = fallback_lookup(name, r.get("website"), mc, ctx["unstable"], self.log,
                                  ctx["use_hangar"], ctx["use_github"], ctx["use_geyser"])
            done += 1
            self.progress(done, total)
            if not res:
                r["state"] = "unknown"
                self.row(fn, name, r["cur_txt"], "", "", "Niet gevonden (Modrinth, Hangar, GitHub)", "unknown")
                continue
            extra_found += 1
            src, latest_txt = res["source"], res["version"]
            r.update(page=res["page"], title=name, latest_txt=latest_txt, source=src,
                     dl=dict(url=res["url"], filename=res["filename"], algo=res["algo"], hash=res["hash"]))
            if src == "GeyserMC":
                r["dl"]["filename"] = fn  # bestandsnaam van de gebruiker behouden
                st, why = geysermc_state(r["path"], cur, res)
                if st == "update":
                    r["state"] = "update"
                    updates += 1
                    self.row(fn, name, cur or "?", latest_txt, src, f"⬆ Update beschikbaar ({why})", "update")
                    self.log(f"{name}: update via GeyserMC, {why}.")
                elif st == "ok":
                    r["state"] = "ok"
                    self.row(fn, name, cur or "?", latest_txt, src, f"✔ Up-to-date ({why})", "ok")
                else:
                    r["state"] = "unknown"
                    self.row(fn, name, cur or "?", latest_txt, src, f"Geen bewijs voor nieuwere build ({why})",
                             "unknown")
                continue
            if not cur:
                r["state"] = "unknown"
                self.row(fn, name, "?", latest_txt, src, f"Gevonden op {src}, lokale versie onbekend", "unknown")
            else:
                newer = is_newer(latest_txt, cur)
                if newer is None:
                    # geen bewijs: versienummer is niet te vergelijken -> GEEN update melden
                    r["state"] = "unknown"
                    self.row(fn, name, cur, latest_txt, src,
                             f"Versie niet vergelijkbaar - geen update gemeld", "unknown")
                    self.log(f"{name}: {src} geeft versie '{latest_txt}', niet te vergelijken met '{cur}'. "
                             f"Geen update gemeld.", "warn")
                elif newer:
                    r["state"] = "update"
                    updates += 1
                    note = "" if res["verified"] else " (compat. niet geverifieerd)"
                    self.row(fn, name, cur, latest_txt, src, f"⬆ Update beschikbaar{note}", "update")
                    self.log(f"{name}: {cur} → {latest_txt} gevonden op {src} (hoger versienummer).")
                else:
                    r["state"] = "ok"
                    self.row(fn, name, cur, latest_txt, src, "✔ Up-to-date", "ok")
        if extra_found:
            self.log(f"{extra_found} plugin(s) niet op Modrinth maar wel gevonden via Hangar/GitHub. "
                     f"Die zijn op naam gevonden en niet op bestandshash - controleer de bron "
                     f"(dubbelklik op de rij).", "warn")
        unknown = sum(1 for r in self.rows.values() if r["state"] == "unknown")
        self.log(f"Plugins gecontroleerd: {updates} update(s) beschikbaar, {unknown} niet controleerbaar.",
                 "warn" if updates else "ok")
        self.status(f"Klaar: {updates} update(s) beschikbaar." if updates else "Klaar: alles up-to-date.")

    def w_plugins_update(self, ctx, targets):
        folder = ctx["folder"]
        pdir = os.path.join(folder, "plugins")
        tmp_dir = os.path.join(folder, "updater_tmp")
        pbroot = os.path.join(ctx["backup_root"], "plugins")
        bdir = os.path.join(pbroot, datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(tmp_dir, exist_ok=True)
        ok = failed = 0
        n = len(targets)
        for i, fn in enumerate(targets):
            r = self.rows[fn]
            title = r.get("title", r["name"])
            dl, new_ver, src = r["dl"], r["latest_txt"], r.get("source", "")
            cur_txt = r.get("cur_txt", "?")
            self.log(f"{title} → {new_ver} downloaden van {src}…")
            self.row(fn, title, cur_txt, new_ver, src, "Downloaden…", "busy")
            tmp = os.path.join(tmp_dir, dl["filename"] + ".part")

            def cb(done, total, i=i, title=title):
                self.progress(i * 1000 + (done * 1000 // total if total else 0), n * 1000)
                if total:
                    self.status(f"{title} downloaden… {done * 100 // total}%  ({i + 1}/{n})")

            try:
                download(dl["url"], tmp, cb, (dl["algo"], dl["hash"]) if dl.get("algo") and dl.get("hash") else None)
                if not zipfile.is_zipfile(tmp):
                    os.remove(tmp)
                    raise ValueError("Download is geen jar-bestand (externe link?) - handmatig downloaden")
                os.makedirs(bdir, exist_ok=True)
                old_path = r["path"]
                if ctx["upd"]:
                    # server draait: kopie als backup, nieuwe jar in plugins/update onder de oude bestandsnaam
                    if ctx["keep_plugins"]:
                        try:
                            shutil.copy2(old_path, os.path.join(bdir, fn))
                        except Exception:
                            self.log(f"{title}: backup-kopie mislukt (bestand in gebruik?)", "warn")
                    updir = os.path.join(pdir, "update")
                    os.makedirs(updir, exist_ok=True)
                    safe_move(tmp, os.path.join(updir, fn))
                    new_fn, label = fn, "⟳ Klaar - wordt toegepast bij herstart"
                else:
                    shutil.move(old_path, os.path.join(bdir, fn))  # faalt als de server draait
                    new_fn = dl["filename"]
                    new_path = os.path.join(pdir, new_fn)
                    try:
                        safe_move(tmp, new_path)
                    except Exception:
                        shutil.move(os.path.join(bdir, fn), old_path)
                        raise
                    r["path"] = new_path
                    label = "✔ Bijgewerkt"
                    if not ctx["keep_plugins"]:
                        try:
                            os.remove(os.path.join(bdir, fn))
                        except OSError:
                            pass
                r["state"] = "done"
                r["cur_txt"] = new_ver
                if new_fn != fn:
                    self.rows[new_fn] = self.rows.pop(fn)
                self.q.put(("row_replace", fn, new_fn, (title, new_fn, new_ver, new_ver, src, label), "done"))
                self.log(f"{title} bijgewerkt naar {new_ver}.", "ok")
                ok += 1
            except PermissionError:
                self.row(fn, title, cur_txt, new_ver, src, "✖ Bestand in gebruik - stop de server", "error")
                self.log(f"{title}: bestand is in gebruik. Stop de server of gebruik de 'plugins/update'-optie.",
                         "error")
                failed += 1
            except Exception as e:
                self.row(fn, title, cur_txt, new_ver, src, f"✖ {e}", "error")
                self.log(f"{title}: mislukt - {e}", "error")
                failed += 1
            self.progress((i + 1) * 1000, n * 1000)
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
        lvl = "ok" if not failed else "warn"
        try:
            if os.path.isdir(bdir) and not os.listdir(bdir):
                os.rmdir(bdir)
        except OSError:
            pass
        if ctx["keep_plugins"]:
            prune_dirs(pbroot, ctx["plugin_max"], self.log)
        note = f" Backups: {bdir}" if ctx["keep_plugins"] and os.path.isdir(bdir) else ""
        self.log(f"Klaar: {ok} bijgewerkt, {failed} mislukt.{note}", lvl)
        self.status(f"Klaar: {ok} bijgewerkt, {failed} mislukt." + (" Start je server opnieuw." if ok else ""))


class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Instellingen")
        self.transient(app)
        self.resizable(False, False)
        c = app.cfg
        self.v = {}
        for k, default in DEFAULTS.items():
            if k in ("loaders", "folder", "jar", "unstable", "update_folder", "noise_filters", "startup_keep", "clean_console",
                     "compact_console", "console_autoscroll", "reach_host", "reach_port", "reach_check_bedrock",
                     "reach_bedrock_port", "reach_auto"):
                continue
            if isinstance(default, bool):
                self.v[k] = tk.BooleanVar(value=bool(c.get(k, default)))
            elif isinstance(default, int):
                self.v[k] = tk.IntVar(value=int(c.get(k, default)))
            else:
                self.v[k] = tk.StringVar(value=str(c.get(k, default)))
        active = set(c.get("loaders") or LOADERS)
        self.lv = {name: tk.BooleanVar(value=name in active) for name in ALL_LOADERS}

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        self._tab_backups(nb)
        self._tab_updates(nb)
        self._tab_server(nb)
        self._tab_beheer(nb)
        self._tab_grafiek(nb)
        self._tab_console(nb)
        self._tab_gedrag(nb)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(4, 10))
        ttk.Button(bar, text="Standaardwaarden herstellen", command=self.reset).pack(side="left")
        ttk.Button(bar, text="Annuleren", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Opslaan", style="Big.TButton", command=self.save).pack(side="right", padx=6)

        self.update_idletasks()
        x = app.winfo_x() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_y() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

    # ---- helpers ----
    def _frame(self, nb, title):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text=f"  {title}  ")
        f.columnconfigure(1, weight=1)
        return f

    def _hint(self, parent, text, row, col=0, span=3):
        ttk.Label(parent, text=text, foreground="#6b7280", wraplength=520, justify="left").grid(
            row=row, column=col, columnspan=span, sticky="w", pady=(0, 8))

    def _check(self, parent, text, var, row, span=3):
        ttk.Checkbutton(parent, text=text, variable=var).grid(row=row, column=0, columnspan=span, sticky="w", pady=2)

    def _spin(self, parent, label, key, row, lo, hi, suffix=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        sp = ttk.Spinbox(parent, from_=lo, to=hi, width=6, textvariable=self.v[key])
        sp.grid(row=row, column=1, sticky="w", padx=6)
        if suffix:
            ttk.Label(parent, text=suffix).grid(row=row, column=2, sticky="w")
        return sp

    def _sep(self, parent, row):
        ttk.Separator(parent).grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)

    # ---- tabs ----
    def _tab_backups(self, nb):
        f = self._frame(nb, "Backups")
        self._check(f, "Bewaar backups van het server.jar (Paper) bij elke update", self.v["keep_server_backups"], 0)
        sp1 = self._spin(f, "Aantal server.jar-backups bewaren:", "server_backups_max", 1, 1, 99, "(oudste worden automatisch gewist)")
        self._sep(f, 2)
        self._check(f, "Bewaar backups van plugins bij elke update", self.v["keep_plugin_backups"], 3)
        sp2 = self._spin(f, "Aantal update-rondes bewaren:", "plugin_backups_max", 4, 1, 99, "(per ronde alle bijgewerkte plugins)")
        self._sep(f, 5)
        ttk.Label(f, text="Backupmap:").grid(row=6, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.v["backup_dir"]).grid(row=6, column=1, sticky="ew", padx=6)
        ttk.Button(f, text="Bladeren…", command=self._pick_backup_dir).grid(row=6, column=2)
        self._hint(f, "Leeg laten = map 'updater_backups' in je servermap. Kies bijvoorbeeld een andere schijf "
                      "voor extra veiligheid.", 7)
        self.info_lbl = ttk.Label(f, text="", font=("Segoe UI", 10, "bold"))
        self.info_lbl.grid(row=8, column=0, columnspan=3, sticky="w", pady=(2, 6))
        row = ttk.Frame(f)
        row.grid(row=9, column=0, columnspan=3, sticky="w")
        ttk.Button(row, text="Backupmap openen", command=self.app.open_backups).pack(side="left")
        ttk.Button(row, text="Alle backups wissen…", command=self.wipe).pack(side="left", padx=8)

        def refresh(*_):
            sp1.config(state="normal" if self.v["keep_server_backups"].get() else "disabled")
            sp2.config(state="normal" if self.v["keep_plugin_backups"].get() else "disabled")

        self.v["keep_server_backups"].trace_add("write", refresh)
        self.v["keep_plugin_backups"].trace_add("write", refresh)
        refresh()
        self._update_info()

    def _tab_updates(self, nb):
        f = self._frame(nb, "Updates")
        self._check(f, "Automatisch controleren op updates bij het opstarten", self.v["auto_check"], 0)
        self._check(f, "Ook beta/alpha-versies toestaan", self.app.unstable_var, 1)
        self._check(f, "Server draait: updates klaarzetten in plugins/update (toegepast bij herstart)",
                    self.app.updfolder_var, 2)
        self._sep(f, 3)
        ttk.Label(f, text="Zoek plugins die niet op Modrinth staan ook bij:").grid(row=4, column=0, columnspan=3, sticky="w")
        sf = ttk.Frame(f)
        sf.grid(row=5, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(sf, text="GeyserMC (Geyser & Floodgate)", variable=self.v["use_geysermc"]).pack(side="left")
        ttk.Checkbutton(sf, text="Hangar (PaperMC)", variable=self.v["use_hangar"]).pack(side="left", padx=14)
        self._check(f, "GitHub (via website uit plugin.yml)", self.v["use_github"], 6)
        self._sep(f, 7)
        ttk.Label(f, text="Zoek versies voor deze server-software:").grid(row=8, column=0, columnspan=3, sticky="w")
        lf = ttk.Frame(f)
        lf.grid(row=9, column=0, columnspan=3, sticky="w", pady=2)
        for name in ALL_LOADERS:
            ttk.Checkbutton(lf, text=name.capitalize(), variable=self.lv[name]).pack(side="left", padx=(0, 12))
        self._hint(f, "Vink Purpur of Folia alleen aan als je server die software draait.", 10)
        self._sep(f, 11)
        ttk.Label(f, text="Plugins uitsluiten van updates:").grid(row=12, column=0, columnspan=3, sticky="w")
        ttk.Entry(f, textvariable=self.v["ignore_list"]).grid(row=13, column=0, columnspan=3, sticky="ew", pady=2)
        self._hint(f, "Komma-gescheiden namen of bestandsnamen, bijv.: Geyser-Spigot, WorldEdit. "
                      "Handig voor plugins die je bewust op een oude versie wilt houden.", 14)

    def _tab_server(self, nb):
        f = self._frame(nb, "Server")
        ttk.Label(f, text="Server-jar bestandsnaam:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(f, textvariable=self.app.jar_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Label(f, text="Vaste Minecraft-versie:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(f, textvariable=self.v["mc_override"], width=14).grid(row=1, column=1, sticky="w", padx=6)
        self._hint(f, "Leeg = automatisch herkennen. Vul dit in als de herkenning niet klopt.", 2)
        ttk.Label(f, text="Startbestand (.bat):").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(f, textvariable=self.v["start_script"]).grid(row=3, column=1, sticky="ew", padx=6)
        ttk.Button(f, text="Bladeren…", command=self._pick_script).grid(row=3, column=2)
        self._hint(f, "Als je dit invult krijg je bovenin een knop '▶ Server starten' om je server na het updaten "
                      "meteen weer op te starten.", 4)
        self._sep(f, 5)
        self._spin(f, "Netwerk-timeout:", "net_timeout", 6, 5, 180, "seconden (verhoog bij trage verbinding)")

    def _tab_beheer(self, nb):
        f = self._frame(nb, "Serverbeheer")
        ttk.Label(f, text="Hoe start de server vanuit dit programma?", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        for i, (key, label) in enumerate(LAUNCH_MODES):
            ttk.Radiobutton(f, text=label, value=key, variable=self.v["launch_mode"]).grid(
                row=1 + i, column=0, columnspan=3, sticky="w")
        ttk.Label(f, text="Java (bij 'Java direct'):").grid(row=4, column=0, sticky="w", pady=(8, 2))
        ttk.Entry(f, textvariable=self.v["java_path"]).grid(row=4, column=1, sticky="ew", padx=6, pady=(8, 2))
        ttk.Button(f, text="Bladeren…", command=self._pick_java).grid(row=4, column=2, pady=(8, 2))
        mem = ttk.Frame(f)
        mem.grid(row=5, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(mem, text="Geheugen min:").pack(side="left")
        ttk.Entry(mem, textvariable=self.v["java_xms"], width=7).pack(side="left", padx=(4, 14))
        ttk.Label(mem, text="max:").pack(side="left")
        ttk.Entry(mem, textvariable=self.v["java_xmx"], width=7).pack(side="left", padx=4)
        ttk.Label(mem, text="(bijv. 2G of 4096M)", foreground="#6b7280").pack(side="left", padx=8)
        ttk.Label(f, text="Extra Java-opties:").grid(row=6, column=0, sticky="w", pady=2)
        ttk.Entry(f, textvariable=self.v["java_extra"]).grid(row=6, column=1, columnspan=2, sticky="ew", padx=6)
        self._hint(f, "Geheugen en extra opties worden alleen gebruikt bij 'Java direct'. Met een startbestand "
                      "geldt wat daarin staat.", 7)
        self._sep(f, 8)
        self._spin(f, "Wachttijd bij stoppen:", "stop_timeout", 9, 10, 600, "seconden, daarna krijg je een waarschuwing")
        self._spin(f, "Spelers/TPS verversen:", "poll_secs", 10, 0, 600, "seconden (0 = uit; stuurt 'list' en 'tps')")
        self._check(f, "Automatisch herstarten na een crash (max. 3x per 10 minuten)", self.v["auto_restart"], 11)

    def _pick_java(self):
        f = filedialog.askopenfilename(parent=self, title="Kies java.exe",
                                       filetypes=[("Java", "java.exe javaw.exe"), ("Alle bestanden", "*.*")])
        if f:
            self.v["java_path"].set(os.path.normpath(f))

    def _tab_grafiek(self, nb):
        f = self._frame(nb, "Grafieken")
        self._spin(f, "Tijdvenster grafieken:", "graph_minutes", 0, 1, 180, "minuten (snel te kiezen op het tabblad Server)")
        self._spin(f, "Statistieken verversen:", "stats_secs", 1, 1, 30, "seconden (CPU en geheugen)")
        self._check(f, "Auto-zoom: de schaal past zich aan de gegevens aan", self.v["graph_zoom"], 2)
        self._hint(f, "Zonder auto-zoom lopen de grafieken vast van 0-100% (CPU), 0-max RAM en 0-20 TPS; "
                      "kleine schommelingen zie je dan nauwelijks. TPS krijgt een nieuw punt per verversing van "
                      "'Spelers/TPS verversen' (tabblad Serverbeheer): zet die lager voor een gedetailleerdere "
                      "TPS-grafiek.", 3)

    def _tab_console(self, nb):
        f = self._frame(nb, "Console")
        self._spin(f, "Max. regels in console:", "console_max_lines", 0, 500, 50000)
        self._spin(f, "Lettergrootte console:", "console_font", 1, 7, 20)
        self._check(f, "Alle speleracties altijd tonen (joinen, leaven, chat, commando's, doodgaan, …), ook in de strenge console",
                    self.v["show_player_activity"], 2)
        self._check(f, "Strenge schone console: tijdens opstarten en afsluiten alleen belangrijke berichten",
                    self.v["clean_startup"], 3)
        ttk.Label(f, text="Berichten die dan altijd blijven staan:", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.keep_txt = tk.Text(f, height=8, width=64, font=("Consolas", 9), wrap="none")
        self.keep_txt.grid(row=5, column=0, columnspan=3, sticky="ew", pady=2)
        self.keep_txt.insert("1.0", self.app.cfg.get("startup_keep", DEFAULT_KEEP))
        self._hint(f, "Waarschuwingen en fouten (en een stacktrace die erbij hoort) blijven altijd zichtbaar. "
                      "Alle andere opstartregels verdwijnen, behalve die één van deze teksten bevatten "
                      "(hoofdletterongevoelig, of begin met re: voor een regex). Het filter blijft nog 10 seconden "
                      "na 'Done' actief, voor plugins die laat opstarten.", 6)
        ttk.Button(f, text="Standaardlijst herstellen",
                   command=lambda: (self.keep_txt.delete("1.0", "end"), self.keep_txt.insert("1.0", DEFAULT_KEEP))
                   ).grid(row=7, column=0, columnspan=2, sticky="w")
        self._sep(f, 8)
        ttk.Label(f, text="Altijd verborgen (ook als de server draait):", font=("Segoe UI", 10, "bold")).grid(
            row=9, column=0, columnspan=3, sticky="w")
        self.noise_txt = tk.Text(f, height=6, width=64, font=("Consolas", 9), wrap="none")
        self.noise_txt.grid(row=10, column=0, columnspan=3, sticky="ew", pady=2)
        self.noise_txt.insert("1.0", self.app.cfg.get("noise_filters", DEFAULT_NOISE))
        self._hint(f, "Eén filter per regel, zelfde opmaak als hierboven. Aan/uit zet je met 'Schone console' "
                      "op het tabblad Server.", 11)
        ttk.Button(f, text="Standaardfilters herstellen",
                   command=lambda: (self.noise_txt.delete("1.0", "end"), self.noise_txt.insert("1.0", DEFAULT_NOISE))
                   ).grid(row=12, column=0, columnspan=2, sticky="w")

    def _tab_gedrag(self, nb):
        f = self._frame(nb, "Gedrag")
        self._check(f, "Vraag bevestiging voor updates en het starten van de server", self.v["confirm"], 0)
        self._check(f, "Speel een geluidje af als een taak klaar is", self.v["sound"], 1)
        self._check(f, "Venster altijd bovenop andere vensters", self.v["topmost"], 2)
        self._check(f, "Compacte lijst (kleinere rijen, meer plugins in beeld)", self.v["compact"], 3)
        self._check(f, "Log bewaren in bestand (mc_server_manager.log naast het programma)", self.v["log_to_file"], 4)
        self._hint(f, "Tip: met F5 start je een controle op alles.", 5)

    # ---- acties ----
    def _pick_backup_dir(self):
        d = filedialog.askdirectory(parent=self, title="Kies een map voor backups")
        if d:
            self.v["backup_dir"].set(os.path.normpath(d))

    def _pick_script(self):
        f = filedialog.askopenfilename(parent=self, title="Kies je startbestand",
                                       filetypes=[("Batch/scripts", "*.bat *.cmd *.ps1 *.exe"), ("Alle bestanden", "*.*")])
        if f:
            self.v["start_script"].set(os.path.normpath(f))

    def _update_info(self):
        root = self.app.backup_root()
        parts = [os.path.join(root, "server"), os.path.join(root, "plugins")]
        size = sum(dir_size(x) for x in parts if os.path.isdir(x))
        n_srv = len(os.listdir(parts[0])) if os.path.isdir(parts[0]) else 0
        n_plg = len(os.listdir(parts[1])) if os.path.isdir(parts[1]) else 0
        self.info_lbl.config(text=f"Nu opgeslagen: {n_srv} server-backup(s), {n_plg} plugin-ronde(s) - {fmt_size(size) or '0 MB'}")

    def wipe(self):
        root = self.app.backup_root()
        parts = [os.path.join(root, "server"), os.path.join(root, "plugins")]
        if not any(os.path.isdir(x) for x in parts):
            messagebox.showinfo(APP_NAME, "Er zijn geen backups om te wissen.", parent=self)
            return
        size = sum(dir_size(x) for x in parts if os.path.isdir(x))
        if messagebox.askyesno(APP_NAME, f"Alle server- en plugin-backups ({fmt_size(size)}) definitief verwijderen?",
                               parent=self):
            for x in parts:
                shutil.rmtree(x, ignore_errors=True)
            self.app.log("Alle backups gewist.", "warn")
            self._update_info()

    def reset(self):
        for k, var in self.v.items():
            var.set(DEFAULTS[k])
        for name, var in self.lv.items():
            var.set(name in DEFAULTS["loaders"])
        self.noise_txt.delete("1.0", "end")
        self.noise_txt.insert("1.0", DEFAULT_NOISE)
        self.keep_txt.delete("1.0", "end")
        self.keep_txt.insert("1.0", DEFAULT_KEEP)

    def save(self):
        for key, label in (("java_xms", "minimaal"), ("java_xmx", "maximaal")):
            val = self.v[key].get().strip()
            if val and parse_mem_mb(val) is None:
                messagebox.showwarning(APP_NAME, f"Het geheugen ({label}) '{val}' is ongeldig. Gebruik bijvoorbeeld "
                                                 "2G of 4096M.", parent=self)
                return
        app, c = self.app, self.app.cfg
        old_mc = c.get("mc_override", "")
        for k, var in self.v.items():
            try:
                c[k] = var.get()
            except tk.TclError:
                c[k] = DEFAULTS[k]
        c["server_backups_max"] = min(max(int(c["server_backups_max"]), 1), 999)
        c["plugin_backups_max"] = min(max(int(c["plugin_backups_max"]), 1), 999)
        c["net_timeout"] = min(max(int(c["net_timeout"]), 5), 180)
        c["mc_override"] = c["mc_override"].strip()
        c["ignore_list"] = c["ignore_list"].strip()
        c["backup_dir"] = c["backup_dir"].strip()
        c["start_script"] = c["start_script"].strip()
        for key, lo, hi in (("stop_timeout", 10, 600), ("poll_secs", 0, 600), ("console_max_lines", 500, 50000),
                            ("console_font", 7, 20), ("graph_minutes", 1, 180), ("stats_secs", 1, 30)):
            c[key] = min(max(int(c[key]), lo), hi)
        c["java_path"] = c["java_path"].strip() or "java"
        c["java_xms"], c["java_xmx"], c["java_extra"] = (c[k].strip() for k in ("java_xms", "java_xmx", "java_extra"))
        c["noise_filters"] = self.noise_txt.get("1.0", "end").strip()
        c["startup_keep"] = self.keep_txt.get("1.0", "end").strip()
        c["loaders"] = [n for n, var in self.lv.items() if var.get()] or list(DEFAULTS["loaders"])
        app._save_cfg()
        app.apply_settings()
        app.log("Instellingen opgeslagen.", "ok")
        if c["mc_override"] != old_mc and os.path.isdir(app.folder_var.get().strip()):
            app.load_folder()
        self.destroy()


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
