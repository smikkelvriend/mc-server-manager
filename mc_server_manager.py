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

import gzip
import hashlib
import importlib
import json
import math
import os
import base64
import concurrent.futures
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
import zlib
from collections import defaultdict, deque
from datetime import datetime

try:
    import winsound
except ImportError:  # geen Windows
    winsound = None

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

APP_NAME = "MC Server Manager"
APP_VERSION = "2.12.7"

CHANGELOG = """
2.12.7 - Kaart: onderin staat per tegel of hij geladen is of niet bestaat op de server (voor diagnose).
2.12.6 - Bedrock (NetherNet): korte groene melding als alles werkt.
2.12.5 - Bedrock-check begrijpt Geyser NetherNet: test TCP-poort in plaats van RakNet-ping.
2.12.4 - Bedrock: als Java de UDP-poort open heeft maar niet op de ping antwoordt, oranje waarschuwing in plaats van rood kruis.
2.12.3 - Bedrock-check: ping met herhaling en ook IPv6, en meldt dat Geyser luistert als Java de UDP-poort open heeft.
2.12.2 - Bedrock-check probeert ook je netwerk-adres (Geyser kan aan dat adres gebonden zijn).
2.12.1 - Bedrock-check zoekt zelf op welke UDP-poort Geyser echt gebruikt.
2.12 - Grafieken lopen soepel door; Updates-tabje knippert met aantal bij beschikbare updates.
2.11.4 - Kaart: geen dunne strepen meer tussen tegels op bepaalde zoomniveaus.
2.11.3 - Kaart: inzoomen voorbij het diepste niveau geeft geen zwart beeld meer, en renderen gebruikt de juiste wereldnaam (minecraft:overworld).
2.11.2 - Programma-update betrouwbaarder: vindt nieuwe versies ook als de GitHub-API-limiet bereikt is.
2.11.1 - Bedrock-controle leest de poort van Geyser zelf (config.yml en opstartregel) in plaats van 19132 te veronderstellen.
2.11 - Kaart zit nu in het programma zelf (geen browser nodig): tegels van squaremap, spelers live, slepen en zoomen, renderen via een menu.
2.10 - Nieuw tabblad Kaart: opent je squaremap-kaart en bedient het renderen (hele wereld, rond de spawn, pauzeren, stoppen).
2.9 - Het tabblad Kaart is weer verwijderd (werkte niet goed genoeg). Al het andere blijft zoals het was.
2.8.11 - Kaart leest regiobestanden uit alle wereldmappen die het vindt (oude en nieuwe indeling samen).
2.8.10 - De herstartvraag na een update toont nu wat er nieuw is.
2.8.9 - Kaart: lege chunks (leegte zonder blokken) worden nu als vlak getoond in plaats van als niet-ingelezen.
2.8.8 - Kaart begint gecentreerd op de spawn in plaats van op 0,0.
2.8.7 - Kaart-diagnose: toont de reden waarom een chunk niet getekend kan worden en de gebruikte wereldmap.
2.8.6 - Kaart laadt veel sneller bij het opstarten (bewaarde kaart als PNG).
2.8.5 - Kaart: in- en uitzoomen zonder haperen (zoomniveaus worden alvast voorbereid).
2.8.4 - Zwart consolevenster wordt verborgen; kaart toont bij het aanwijzen van een regio waarom stukken ontbreken.
2.8.3 - Programma-update: elke 5 minuten (en bij het terugkeren naar het venster) controleren in plaats van elke 6 uur.
2.8.2 - Kaart veel sneller en stabieler: soepel slepen en zoomen, geen ontbrekende stukken meer bij ander zoomniveau.
2.8.1 - Temperatuur wordt nu ook gelezen via de webserver van LibreHardwareMonitor (Options > Remote Web Server).
2.8 - Kaart wordt bewaard en staat direct klaar; op de achtergrond wordt hij stil bijgewerkt, ook als het tabblad dicht is.
2.7.1 - Plugin-lijst opgeruimd: geen bestandsnaam, commando's of grootte meer, kleinere tellers en tabbladen.
2.7 - Nieuw tabblad Kaart: terrein van je wereld met alle spelers live erop (naam, richting, spoor, coordinaten).
2.6.1 - Scrollen in de plugin-lijsten werkt nu ook als de muis boven een kaart staat.
2.6 - Plugins-tabblad in kaartvorm: aantrekkelijker, met filter, sortering, aan/uit per plugin en installeren per zoekresultaat.
2.5 - Vinkje bij Plugins zoeken: alleen plugins tonen die zeker werken met jouw Minecraft-versie.
2.4.2 - Plugins sorteren door op een kolomnaam te klikken (downloads, datum, naam, enz.).
2.4.1 - Slimmer zoeken: Nederlandse restwoorden blokkeren Modrinth niet meer, en bomen omhakken wordt herkend.
2.4 - Nieuw tabblad Plugins: beheren (aan/uit/verwijderen), slim zoeken op naam of beschrijving en installeren, met optioneel /plm load. Tab-aanvulling in de console.
2.3.1 - Programma-update haalt het bestand nu op via de exacte laatste commit, zodat een verouderde cache niets meer uitmaakt.
2.3 - Bedrock-controle laat nu zien wat er misgaat: eigen UDP-ping lokaal en via je domein, plus wat elke dienst zegt.
2.2 - Temperatuur van je laptop (met grafiek en waarschuwing) en automatische programma-update via een link.
2.1 - Bereikbaarheidscheck met serverkaart, speleracties altijd zichtbaar in de console, schonere opstart.
2.0 - Nieuwe naam MC Server Manager en een strengere schone console.
"""
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
    "squaremap_url": "http://localhost:8080",
    "plm_load": False, "plm_ack": False, "plugins_only_compat": False,
    "temp_enabled": True, "temp_secs": 10, "temp_warn": 85,
    "update_url": "", "selfupdate_check": True, "selfupdate_auto": False,
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


def _is_ip(h):
    return bool(re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", h or "")) or ":" in (h or "")


def _norm_ext(src, online, d=None, **kw):
    r = dict(online=online, motd="", version="", software="", players=(None, None), names=[], icon=None,
             ip=None, port=None, hostname=None, ms=None, src=src, age=None)
    r.update(kw)
    return r


def mcstatus_status(host, port, bedrock=False):
    """api.mcstatus.io: kijkt van buitenaf naar je server (korte cache, geeft ook de leeftijd van het resultaat)."""
    addr = host if int(port) == (19132 if bedrock else 25565) else f"{host}:{int(port)}"
    url = "https://api.mcstatus.io/v2/status/" + ("bedrock/" if bedrock else "java/") + urllib.parse.quote(addr, safe=":")
    d = http_json(url + "?query=false", timeout=20, retries=1)
    ver = d.get("version") if isinstance(d.get("version"), dict) else {}
    pl = d.get("players") if isinstance(d.get("players"), dict) else {}
    motd = d.get("motd") if isinstance(d.get("motd"), dict) else {}
    age = None
    ra = d.get("retrieved_at")
    if isinstance(ra, (int, float)):
        age = max(0, int(time.time() - ra / 1000))
        if age < 3:
            age = None
    names = [p.get("name_clean") or p.get("name_raw") for p in (pl.get("list") or []) if isinstance(p, dict)]
    return _norm_ext("mcstatus.io", bool(d.get("online")), motd=str(motd.get("clean") or "").strip(),
                     version=str(ver.get("name_clean") or ver.get("name") or ""), software=str(d.get("software") or ""),
                     players=(pl.get("online"), pl.get("max")), names=[n for n in names if n], icon=d.get("icon"),
                     ip=d.get("ip_address"), port=d.get("port"), age=age)


def minetools_status(host, port):
    """api.minetools.eu: pingt je Java-server live."""
    d = http_json(f"https://api.minetools.eu/ping/{urllib.parse.quote(host, safe='')}/{int(port)}", timeout=20, retries=1)
    if not isinstance(d, dict) or d.get("error") or "players" not in d:
        return _norm_ext("minetools.eu", False)
    pl = d.get("players") or {}
    ver = d.get("version") or {}
    desc = d.get("description")
    return _norm_ext("minetools.eu", True, motd=flatten_motd(desc) if desc else "", version=str(ver.get("name") or ""),
                     players=(pl.get("online"), pl.get("max")), icon=d.get("favicon"), ms=None)


def ext_status(host, port, bedrock=False):
    """Vraagt meerdere onafhankelijke diensten tegelijk en neemt het beste antwoord. Eén dienst met een
    verouderd 'offline'-antwoord kan zo niet meer het eindoordeel bepalen."""
    ips = []
    if not _is_ip(host):
        try:
            ips = sorted({i[4][0] for i in socket.getaddrinfo(host, None, socket.AF_INET)})
        except OSError:
            ips = []
    jobs = [("mcstatus.io", lambda: mcstatus_status(host, port, bedrock)),
            ("mcsrvstat.us", lambda: mcsrv_status(host, port, bedrock))]
    if not bedrock:
        jobs.append(("minetools.eu", lambda: minetools_status(host, port)))
    if ips:  # ander cache-adres dan de domeinnaam: ontloopt een oud 'offline'-antwoord
        jobs.append(("mcsrvstat.us (via IP)", lambda: dict(mcsrv_status(ips[0], port, bedrock), src="mcsrvstat.us (via IP)")))
    out, errs = [], {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        futs = {ex.submit(fn): name for name, fn in jobs}
        try:
            for f in concurrent.futures.as_completed(futs, timeout=30):
                try:
                    out.append(f.result())
                except Exception as e:
                    errs[futs[f]] = describe_net_error(e)
        except concurrent.futures.TimeoutError:
            pass
    if not out:
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errs.items()) or "geen antwoord van de controlediensten")
    online = [r for r in out if r["online"]]
    best = (min(online, key=lambda r: r["age"] or 0) if online else out[0])
    best = dict(best)
    best["tried"] = sorted((r["src"], r["online"]) for r in out) + [(k, None) for k in errs]
    best["dns"] = ips
    return best


RAKNET_MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")


def detect_geyser_port(folder, java_port=25565):
    """Leest de Bedrock-poort uit de config van Geyser (plugins/Geyser-*/config.yml). Geeft (poort, bron) of None."""
    try:
        pdir = os.path.join(folder, "plugins")
        for d in sorted(os.listdir(pdir)):
            cfg = os.path.join(pdir, d, "config.yml")
            if d.lower().startswith("geyser") and os.path.isfile(cfg):
                text = open(cfg, encoding="utf-8", errors="replace").read()
                m = re.search(r"^bedrock:\s*\n((?:[ \t]+.*\n?|\s*\n|#.*\n)+)", text, re.M)
                block = m.group(1) if m else ""
                clone = re.search(r"^\s+clone-remote-port:\s*(true|false)", block, re.M | re.I)
                port = re.search(r"^\s+port:\s*(\d+)", block, re.M)
                if clone and clone.group(1).lower() == "true":
                    return int(java_port), "clone-remote-port staat aan: Geyser gebruikt dezelfde poort als Java"
                if port:
                    return int(port.group(1)), f"{d}/config.yml"
    except OSError:
        pass
    return None


def geyser_transport(folder):
    """'nethernet', 'raknet' of 'both' uit Geyser's config (nieuwe Bedrock-verbinding), of None."""
    try:
        pdir = os.path.join(folder, "plugins")
        for d in sorted(os.listdir(pdir)):
            cfg = os.path.join(pdir, d, "config.yml")
            if d.lower().startswith("geyser") and os.path.isfile(cfg):
                text = open(cfg, encoding="utf-8", errors="replace").read()
                m = re.search(r"^\s+transport:\s*[\"']?(\w+)", text, re.M)
                return m.group(1).lower() if m else None
    except OSError:
        pass
    return None


def tcp_open(host, port, timeout=2.5):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def lan_ips():
    ips = []
    try:
        so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        so.connect(("192.0.2.1", 9))
        ips.append(so.getsockname()[0])
        so.close()
    except OSError:
        pass
    try:
        ips += [i for i in socket.gethostbyname_ex(socket.gethostname())[2]]
    except OSError:
        pass
    return [i for i in dict.fromkeys(ips) if not i.startswith("127.")]


def geyser_bind_address(folder):
    try:
        pdir = os.path.join(folder, "plugins")
        for d in sorted(os.listdir(pdir)):
            cfg = os.path.join(pdir, d, "config.yml")
            if d.lower().startswith("geyser") and os.path.isfile(cfg):
                text = open(cfg, encoding="utf-8", errors="replace").read()
                m = re.search(r"^bedrock:\s*\n((?:[ \t]+.*\n?|\s*\n|#.*\n)+)", text, re.M)
                a = re.search(r"^\s+address:\s*[\"']?([^\s\"'#]+)", m.group(1) if m else "", re.M)
                return a.group(1) if a else None
    except OSError:
        pass
    return None


def raknet_ping(host, port, timeout=4):
    """Eigen Bedrock-ping (RakNet, UDP): antwoordt Geyser op deze poort?"""
    pkt = b"\x01" + struct.pack(">Q", int(time.time() * 1000) & 0x7FFFFFFFFFFFFFFF) + RAKNET_MAGIC + os.urandom(8)
    last = None
    for fam, addr in sorted({(i[0], i[4]) for i in socket.getaddrinfo(host, int(port), socket.AF_UNSPEC, socket.SOCK_DGRAM)}):
        sock = socket.socket(fam, socket.SOCK_DGRAM)
        sock.settimeout(timeout / 2)
        try:
            t0 = time.time()
            for attempt in range(2):  # UDP kan een pakket kwijtraken: één herhaling
                try:
                    sock.sendto(pkt, addr)
                    data, _ = sock.recvfrom(4096)
                    break
                except socket.timeout:
                    if attempt:
                        raise
            if not data or data[0] != 0x1C or len(data) < 35:
                raise ValueError("onverwacht antwoord")
            n = struct.unpack(">H", data[33:35])[0]
            parts = data[35:35 + n].decode("utf-8", "replace").split(";")
            g = lambda i: parts[i] if len(parts) > i else ""
            return dict(online=True, motd=g(1), version=g(3), players=(g(4), g(5)), ms=int((time.time() - t0) * 1000))
        except Exception as e:
            last = e
        finally:
            sock.close()
    raise last or OSError("geen antwoord")


def java_udp_ports():
    """UDP-poorten die een java-proces op deze pc open heeft (Windows). Geeft een gesorteerde lijst."""
    if os.name != "nt":
        return []
    ps = ("Get-NetUDPEndpoint -EA SilentlyContinue | ForEach-Object { $p = (Get-Process -Id $_.OwningProcess -EA SilentlyContinue)."
          "ProcessName; if ($p -like 'java*') { $_.LocalPort } } | Sort-Object -Unique")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=20,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return sorted({int(x) for x in out.split() if x.isdigit()})
    except Exception:
        return []


def find_geyser_port(bport):
    """Zoekt welke UDP-poort van Java echt op een Bedrock-ping antwoordt. Geeft (poort, lijst_geprobeerd) of (None, lijst)."""
    ports = java_udp_ports()
    for pt in [pt for pt in ports if pt != bport]:
        try:
            raknet_ping("127.0.0.1", pt, timeout=1.5)
            return pt, ports
        except Exception:
            continue
    return None, ports


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
    tried = ext.get("tried") or [] if ext else []
    age_note = ("\nGeraadpleegd: " + ", ".join(f"{n} ({'online' if o else 'offline' if o is not None else 'fout'})"
                                              for n, o in tried) + ".") if tried else ""
    dns, pub = (ext.get("dns") if ext else None) or [], res.get("pubip")
    dns_note = ""
    if dns and pub and pub not in dns:
        dns_note = (f"\n• Je domein {host} wijst naar {', '.join(dns)}, maar je huidige publieke IP is {pub}. Werk het "
                    "A-record bij (of gebruik dynamic DNS).")
    elif not dns and not _is_ip(host):
        dns_note = f"\n• Het domein {host} is op deze pc niet te vinden (DNS)."
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
        return "bad", "\n".join(lines) + dns_note + age_note
    msg = (f"✖ Niet bereikbaar van buitenaf én de server reageert ook niet lokaal.\n{res.get('loc_err', 'onbekende fout')}. ")
    msg += ("Het programma ziet de server wel draaien; controleer server-port in server.properties." if srv_online
            else "Draait de server? Start hem eerst op het tabblad Server.")
    return "bad", msg + dns_note + age_note


TEMP_SCRIPT = r'''
$ErrorActionPreference = 'SilentlyContinue'
$r = @()
foreach ($ns in 'root/LibreHardwareMonitor', 'root/OpenHardwareMonitor') {
  foreach ($x in (Get-CimInstance -Namespace $ns -ClassName Sensor | Where-Object { $_.SensorType -eq 'Temperature' })) {
    $r += [pscustomobject]@{ src = 'hwmon'; name = [string]$x.Name; parent = [string]$x.Parent; value = [double]$x.Value }
  }
}
if ($r.Count -eq 0) {
  foreach ($x in (Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation)) {
    $t = if ($x.HighPrecisionTemperature) { [double]$x.HighPrecisionTemperature / 10 } else { [double]$x.Temperature }
    $r += [pscustomobject]@{ src = 'tz'; name = [string]$x.Name; parent = ''; value = $t - 273.15 }
  }
}
if ($r.Count -eq 0) {
  foreach ($x in (Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature)) {
    $r += [pscustomobject]@{ src = 'acpi'; name = [string]$x.InstanceName; parent = ''; value = ([double]$x.CurrentTemperature / 10) - 273.15 }
  }
}
ConvertTo-Json -InputObject @($r) -Compress
'''


def pick_temperature(items):
    """Kiest uit alle sensoren de beste waarde voor 'de temperatuur van de laptop'."""
    good = [x for x in items if isinstance(x, dict) and isinstance(x.get("value"), (int, float))
            and not isinstance(x.get("value"), bool) and 1 < x["value"] < 130]
    if not good:
        return None
    hw = [x for x in good if x.get("src") == "hwmon"]
    if hw:
        def has(x, keys):
            s = (str(x.get("name", "")) + " " + str(x.get("parent", ""))).lower()
            return any(k in s for k in keys)
        pool = ([x for x in hw if has({"name": x.get("name", "")}, ("package", "tctl", "tdie"))]
                or [x for x in hw if has(x, ("cpu", "core", "k10temp"))] or hw)
        best = max(pool, key=lambda x: x["value"])
        return dict(value=float(best["value"]), label=str(best.get("name") or "CPU"), src="hwmon")
    best = max(good, key=lambda x: x["value"])
    label = {"tz": "thermal zone", "acpi": "ACPI, indicatief"}.get(best.get("src"), str(best.get("name", "")))
    return dict(value=float(best["value"]), label=label, src=best.get("src"))


def parse_lhm_tree(tree):
    """Haalt de temperatuursensoren uit de data.json van de webserver van LibreHardwareMonitor."""
    out = []

    def walk(node, path):
        if not isinstance(node, dict):
            return
        text = str(node.get("Text", ""))
        kids = node.get("Children") or []
        val = str(node.get("Value", ""))
        m = re.match(r"^\s*(-?\d+(?:[.,]\d+)?)\s*\u00b0\s*C", val)
        if m and not kids:
            out.append(dict(src="hwmon", name=text, parent=" ".join(path), value=float(m.group(1).replace(",", "."))))
        for k in kids:
            walk(k, path + [text])

    walk(tree, [])
    return out


def read_lhm_web(port=8085):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/data.json", timeout=1.5) as r:
            return parse_lhm_tree(json.loads(r.read().decode("utf-8", "replace")))
    except Exception:
        return []


def read_temperature():
    """Leest de temperatuur: Windows (LibreHardwareMonitor -> thermal zone -> ACPI) of psutil op Linux/Mac."""
    items = []
    if os.name == "nt":
        items = read_lhm_web()  # webserver van LibreHardwareMonitor (nieuwere versies hebben geen WMI meer)
        if items:
            return pick_temperature(items)
        try:
            enc = base64.b64encode(TEMP_SCRIPT.encode("utf-16-le")).decode("ascii")
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                "-EncodedCommand", enc], capture_output=True, text=True, timeout=25,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out = (r.stdout or "").strip()
            if out:
                data = json.loads(out)
                items = [data] if isinstance(data, dict) else data
        except Exception:
            items = []
    elif psutil is not None and hasattr(psutil, "sensors_temperatures"):
        try:
            for chip, arr in (psutil.sensors_temperatures() or {}).items():
                for t in arr:
                    items.append(dict(src="hwmon", name=t.label or chip, parent=chip, value=float(t.current)))
        except Exception:
            pass
    return pick_temperature(items)


# ---------- automatische programma-update ----------
def update_candidates(url):
    u = (url or "").strip()
    m = re.fullmatch(r"https://github\.com/([\w.\-]+)/([\w.\-]+?)(?:\.git)?/?", u)
    if m:  # repository-link: bestand in de hoofdmap
        return [f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{b}/mc_server_manager.py"
                for b in ("main", "master")]
    m = re.fullmatch(r"https://github\.com/([\w.\-]+)/([\w.\-]+)/blob/([^/]+)/(.+)", u)
    if m:
        return [f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}/{m.group(4)}"]
    return [u] if u.lower().startswith("https://") else []


_SHA_CACHE = {}


def parse_git_refs(data, branches=("main", "master")):
    """Zoekt de commit van een branch in het antwoord van git (info/refs)."""
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    for br in branches:
        m = re.search(r"([0-9a-f]{40}) refs/heads/" + re.escape(br) + r"(?:\x00|\n|\s|$)", text)
        if m:
            return m.group(1)
    return None


def github_head_sha(owner, repo):
    """Laatste commit van de repository. Eerst de API (met ETag: een '304' telt niet mee voor de limiet), en als dat
    niet lukt (bijv. API-limiet) via het git-protocol, dat geen limiet heeft."""
    key = f"{owner}/{repo}"
    try:
        hdr = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github.sha"}
        old = _SHA_CACHE.get(key)
        if old:
            hdr["If-None-Match"] = old[0]
        req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}/commits/HEAD", headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                sha = r.read(100).decode("ascii", "replace").strip()
                etag = r.headers.get("ETag")
        except urllib.error.HTTPError as e:
            if e.code == 304 and old:
                return old[1]
            raise
        if re.fullmatch(r"[0-9a-f]{40}", sha):
            if etag:
                _SHA_CACHE[key] = (etag, sha)
            return sha
    except Exception:
        pass
    try:
        req = urllib.request.Request(f"https://github.com/{owner}/{repo}.git/info/refs?service=git-upload-pack",
                                     headers={"User-Agent": "git/2.45.0", "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return parse_git_refs(r.read(400000))
    except Exception:
        return None


def fetch_update(url):
    """Haalt het nieuwste programmabestand op en controleert of het een geldig, compleet bestand is."""
    cands = update_candidates(url)
    if not cands:
        raise ValueError("Geen geldige update-link: gebruik een https-link.")
    gm = re.fullmatch(r"https://github\.com/([\w.\-]+)/([\w.\-]+?)(?:\.git)?/?", (url or "").strip())
    if gm:  # exacte laatste commit opvragen: een bestand op commit-adres kan nooit verouderd uit de cache komen
        sha = github_head_sha(gm.group(1), gm.group(2))
        if sha:
            cands.insert(0, f"https://raw.githubusercontent.com/{gm.group(1)}/{gm.group(2)}/{sha}/mc_server_manager.py")
    last = None
    for cand in cands:
        try:
            full = cand
            if "raw.githubusercontent.com" in cand:  # voorkomt dat een oude kopie uit de cache komt
                full += ("&" if "?" in cand else "?") + f"_={int(time.time())}"
            req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=max(30, NET_TIMEOUT)) as r:
                text = r.read(8000000).decode("utf-8")
            v = re.search(r'^APP_VERSION\s*=\s*"([0-9][0-9.]*)"', text, re.M)
            if not v or "class App(tk.Tk)" not in text:
                raise ValueError("Dit lijkt niet op een MC Server Manager-bestand.")
            compile(text, "mc_server_manager.py", "exec")  # moet geldige Python zijn
            return dict(version=v.group(1), text=text, url=cand)
        except Exception as e:
            last = e
    raise last


def changelog_since(text, cur):
    m = re.search(r'^CHANGELOG\s*=\s*"""(.*?)"""', text, re.M | re.S)
    if not m:
        return ""
    out = []
    for line in m.group(1).strip().splitlines():
        mm = re.match(r"\s*(\d+(?:\.\d+)*)\s*[-:]\s*(.*)", line)
        if mm and is_newer(mm.group(1), cur):
            out.append(f"• {mm.group(1)}: {mm.group(2).strip()}")
    return "\n".join(out)


def install_update_file(script, text, backup_dir, cur_version, keep=5):
    """Zet de nieuwe versie in plaats van het huidige bestand; de vorige versie wordt bewaard."""
    os.makedirs(backup_dir, exist_ok=True)
    bak = os.path.join(backup_dir, f"mc_server_manager_{cur_version}_{datetime.now():%Y%m%d-%H%M%S}.py")
    shutil.copy2(script, bak)
    tmp = script + ".new"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, script)
    prune_files(backup_dir, keep)
    return bak


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
        super().__init__(parent, height=104, width=90, bg="#111827", highlightthickness=0)
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

    def _delay(self):
        """Hoe ver de grafiek 'achterloopt': iets meer dan de tijd tussen twee metingen. Daardoor kan de lijn altijd
        soepel tussen twee echte metingen doorlopen (geen sprongen en geen gokwerk)."""
        if len(self.data) < 3:
            return 1.0
        ts = [t for t, _ in list(self.data)[-6:]]
        gaps = sorted(b - a for a, b in zip(ts, ts[1:]))
        return min(max(gaps[len(gaps) // 2] * 1.15, 0.5), 4.0)

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 50:
            return
        now = time.time()
        td = now - self._delay()          # tijdstip dat nu rechts in de grafiek staat
        t0 = td - self.window
        self.create_text(6, 4, anchor="nw", fill="#9ca3af", font=("Segoe UI", 8), text=self.title)
        self.create_text(6, h - 3, anchor="sw", fill="#4b5563", font=("Segoe UI", 7),
                         text=graph_label(max(1, round(self.window / 60))))
        pts, nxt = [], None
        for t, v in reversed(self.data):  # van achter naar voren, stopt zodra we buiten het venster zijn
            if v is None:
                continue
            if t > td:
                nxt = (t, v)
                continue
            pts.append((t, v))
            if t < t0:
                break
        pts.reverse()
        if not pts:
            return
        if nxt and pts[-1][0] < td:  # tussen twee metingen doorrekenen: het uiteinde schuift gelijkmatig mee
            (ta, va), (tb, vb) = pts[-1], nxt
            f = (td - ta) / max(tb - ta, 1e-6)
            pts.append((td, va + (vb - va) * f))
        elif pts[-1][0] < td:
            pts.append((td, pts[-1][1]))
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
        # de schaal beweegt zachtjes mee in plaats van te springen
        if getattr(self, "_sl", None) is None or abs(self._sl - lo_v) + abs(self._sh - hi_v) > 50 * (hi_v - lo_v + 1):
            self._sl, self._sh = lo_v, hi_v
        else:
            self._sl += (lo_v - self._sl) * 0.12
            self._sh += (hi_v - self._sh) * 0.12
        lo_v, hi_v = self._sl, self._sh
        rng = max(hi_v - lo_v, 1e-9)
        top, bot = 30, h - 14

        def X(t):
            return 4 + (t - t0) / self.window * (w - 8)

        def Y(v):
            return bot - (min(max(v, lo_v), hi_v) - lo_v) / rng * (bot - top)

        xy = []
        for t, v in pts:
            xy += [X(t), Y(v)]
        if len(xy) >= 4:
            self.create_line(*xy, fill=self.color, width=2)
        last = next((v for t, v in reversed(self.data) if v is not None), vals[-1])  # echte laatste waarde
        self.create_text(w - 6, 4, anchor="ne", fill="white", font=("Segoe UI", 9, "bold"), text=f"{last:.1f}{self.unit}")
        self.create_text(w - 6, 18, anchor="ne", fill="#6b7280", font=("Segoe UI", 7), text=self._num(hi_v, rng))
        self.create_text(w - 6, h - 3, anchor="se", fill="#6b7280", font=("Segoe UI", 7), text=self._num(lo_v, rng))


load_psutil()


# ======================================================================================
#  Plugins beheren en zoeken
# ======================================================================================
STOPWORDS = set("""de het een en of dat die dit deze als dan ervoor zorgt zorg zorgen plugin plugins ik wil willen zou kan kun kunnen
mijn mij je jij jouw we wij zoek zoeken zoekt graag iets wat welke er zodat zodra is zijn ben heb hebben geef geven om te naar bij
ook nog wel niet geen voor met van in op aan uit door dan toe the a an that which makes make so when if i want looking for find me
one who how to is are of and or on in it be do does my our need needs plugin plugins something called named hebt heeft wordt worden
wordt werd moet moeten laat laten zodat dus maar want toch al alle alles elke iedereen iemand waardoor waarmee waarbij daarmee
daardoor daarbij waarvoor waar hoe zonder meteen gewoon even x""".split())

# Nederlandse stam -> Engelse zoekterm (voor beschrijvingen die in geen enkel 'concept' passen)
NL_EN = {
    "omhak": "chop", "hak": "chop", "kap": "chop", "vell": "fell", "rooi": "chop", "omzaag": "chop", "zaag": "saw",
    "slaap": "sleep", "slap": "sleep", "nacht": "night", "dag": "day", "overslaan": "skip", "geslagen": "skip",
    "speler": "player", "thuis": "home", "huis": "home", "teleport": "teleport", "beschermen": "protect",
    "bescherming": "protection", "kist": "chest", "deur": "door", "geld": "money", "munt": "coins", "winkel": "shop",
    "verkoop": "sell", "verkopen": "sell", "kopen": "buy", "vlieg": "fly", "vecht": "fight", "gevecht": "combat",
    "dood": "death", "doden": "kill", "leven": "lives", "bouw": "build", "wereld": "world", "kaart": "map",
    "regen": "rain", "onweer": "thunder", "weer": "weather", "tijd": "time", "snel": "fast", "dieren": "animals",
    "dier": "animal", "monster": "monsters", "zwaard": "sword", "bericht": "message", "welkom": "welcome",
    "kleur": "color", "naam": "name", "rang": "rank", "rechten": "permissions", "groep": "group", "beloning": "reward",
    "stem": "vote", "boom": "tree", "bomen": "trees", "hout": "wood", "erts": "ore", "mijnen": "mining",
    "automatisch": "automatic", "terugdraai": "rollback", "verberg": "hide", "onzichtbaar": "invisible",
    "wachtwoord": "password", "inlog": "login", "vriend": "friends", "gilde": "guild", "taal": "language",
    "vertaal": "translate", "bijnaam": "nickname", "titel": "title", "zijbalk": "sidebar", "inventaris": "inventory",
    "sorteer": "sort", "uitschakel": "disable", "aanpass": "customize", "instell": "configure", "beperk": "limit",
    "limiet": "limit", "grens": "border", "explosie": "explosion", "brand": "fire", "vuur": "fire", "vis": "fish",
    "boer": "farming", "plant": "plants", "gewas": "crops", "oogst": "harvest", "dorpeling": "villager",
    "paard": "horse", "huisdier": "pet", "ride": "ride", "hoed": "hat", "deeltjes": "particles", "geluid": "sound",
    "muziek": "music", "spel": "game", "wedstrijd": "match", "missie": "quest", "verhaal": "story",
    "afstand": "distance", "zichtbaar": "visible", "zicht": "view", "rand": "border", "melding": "notification",
    "waarschuw": "warning", "straf": "punishment", "verban": "ban", "mute": "mute", "scherm": "screen",
    "wapen": "weapon", "pantser": "armor", "gereedschap": "tools", "pijl": "arrow", "boog": "bow", "lava": "lava",
    "water": "water", "grot": "cave", "gebied": "region", "regio": "region", "stuk": "plot", "grond": "land",
    "hoofd": "heads", "kop": "heads", "skin": "skin", "cape": "cape", "rugzak": "backpack", "tas": "backpack",
    "ender": "ender", "portaal": "portal", "nether": "nether", "end": "end", "levels": "levels", "ervaring": "experience",
    "xp": "xp", "vliegen": "fly", "rennen": "sprint", "zwem": "swim", "klim": "climb", "ladder": "ladder",
}

# (label, trigger-regex, zoektermen, kernwoorden)
CONCEPTS = [
    ("slapen / nacht overslaan", r"slaap|slap|sleep|\bbed\b|bedden|nacht\w*\s+over|night\s*skip|nacht|night",
     ["sleep", "night skip", "skip night", "one player sleep", "single player sleep", "sleep voting"],
     ["sleep", "night", "skip", "bed", "vote", "percentage"]),
    ("thuis / teleporteren", r"teleport|\btp\b|thuis|\bhomes?\b|warps?|sethome|terugkeren",
     ["homes", "teleport", "warps", "sethome", "tpa"], ["home", "teleport", "warp", "tpa"]),
    ("land beschermen / claims", r"claim|beschermen|bescherming|griefing|grief|\bplots?\b|stuk land|protect|land\b",
     ["land claim", "grief protection", "claims", "protection plots"], ["claim", "protect", "grief", "land", "plot"]),
    ("economie / winkels", r"econom|geld|munten|coins?|money|winkel|shop|verkopen|handel|bank\b|currency",
     ["economy", "shop", "chest shop", "vault economy", "money"], ["economy", "shop", "money", "currency", "vault"]),
    ("rechten / rangen", r"rank|rangen|rechten|permissie|permission|groepen|rollen|\bgroups?\b",
     ["permissions", "luckperms", "ranks", "groups"], ["permission", "rank", "group", "luckperms"]),
    ("chat / opmaak", r"\bchat|prefix|opmaak|chatkleur|format|bericht\w* opmaken",
     ["chat format", "chat prefix", "chat colors", "chat management"], ["chat", "prefix", "format", "color"]),
    ("anti-cheat", r"cheat|hack|fly hack|xray|x-ray|valsspel|anticheat|anti-cheat",
     ["anticheat", "cheat detection", "anti xray", "anti-cheat"], ["anticheat", "cheat", "xray", "hack", "detect"]),
    ("back-ups", r"back-?up|reservekopie|wereld bewaren|automatisch opslaan",
     ["backup", "world backup", "automatic backup"], ["backup", "restore", "world"]),
    ("kaart op website", r"dynmap|bluemap|live ?map|webkaart|kaart.*(website|browser|online)|web ?map",
     ["dynmap", "live map", "web map", "bluemap"], ["map", "web", "live", "dynmap", "bluemap"]),
    ("bouwen / worldedit", r"bouwen|build|worldedit|schematic|bouwtool|selecteren|kopi[eë]ren|\bwand\b",
     ["worldedit", "build tools", "schematic", "world edit"], ["build", "worldedit", "schematic", "edit", "brush"]),
    ("prestaties / lag", r"\blag|performance|optimali|vertraging|prestatie|zwaar|\btps\b|lagg",
     ["performance", "optimization", "lag", "clearlag", "entity limit"], ["lag", "performance", "optimi", "entity", "tps"]),
    ("mobs / monsters", r"\bmobs?\b|monsters?|creeper|dieren spawn|spawnen|mob spawn",
     ["mob spawn", "mob control", "mob drops", "custom mobs", "mob stacker"], ["mob", "spawn", "monster", "drops"]),
    ("minigames", r"minigame|bedwars|skywars|parkour|hunger ?games|spleef|\bspelletjes",
     ["minigames", "bedwars", "skywars", "parkour", "hunger games"], ["minigame", "game", "arena", "bedwars", "parkour"]),
    ("welkom- / join-berichten", r"welkom|welcome|join ?(bericht|message)|leave ?message|motd|toetreden",
     ["join message", "welcome message", "motd", "join leave messages"], ["join", "welcome", "message", "motd"]),
    ("tab / scoreboard", r"\btab\b|tablist|scoreboard|zijbalk|sidebar|bossbar|nametag|header",
     ["tab list", "scoreboard", "tablist", "sidebar", "nametags"], ["tab", "scoreboard", "sidebar", "nametag", "bossbar"]),
    ("kits", r"\bkits?\b|startpakket|starter ?kit|beginnerspakket",
     ["kits", "starter kit", "kit commands"], ["kit", "starter", "items"]),
    ("jobs / skills", r"\bjobs?\b|beroepen|\bbaan\b|geld verdienen|skills|mcmmo|levelen",
     ["jobs", "job rewards", "mcmmo", "skills"], ["job", "skill", "level", "reward", "mcmmo"]),
    ("veiling / markt", r"veiling|auction|marktplaats|marketplace",
     ["auction house", "marketplace", "auction"], ["auction", "market", "bid", "sell"]),
    ("stemmen / votes", r"\bvote|stemmen|votifier|stem ?beloning",
     ["votifier", "vote rewards", "voting"], ["vote", "votifier", "reward"]),
    ("discord", r"discord",
     ["discord", "discordsrv", "discord bridge"], ["discord", "bridge", "chat"]),
    ("bedrock / crossplay", r"bedrock|geyser|floodgate|mobiel|pocket|crossplay|playstation|\bps[45]\b|xbox|switch",
     ["geyser", "floodgate", "bedrock crossplay"], ["bedrock", "geyser", "floodgate", "crossplay"]),
    ("enchants", r"enchant|betoverin",
     ["custom enchantments", "enchants", "enchant"], ["enchant", "enchantment"]),
    ("dood / graf / inventaris", r"graf\b|grave|death ?chest|items kwijt|keepinventory|keep inventory|na (de )?dood",
     ["grave", "death chest", "keep inventory", "corpse"], ["grave", "death", "chest", "inventory", "items"]),
    ("weer / tijd", r"weer\b|weather|regen|onweer|altijd dag|\bdag\b|time ?control|tijd\b|storm",
     ["weather", "time control", "always day", "weather control"], ["weather", "time", "day", "rain", "storm"]),
    ("moderatie / admin", r"essentials|moderat|\bban\b|kick|\bmute\b|straffen|admin ?tools|banhammer|commando",
     ["essentials", "moderation", "ban", "punishments", "admin tools"], ["essentials", "moderat", "ban", "mute", "kick", "punish"]),
    ("hologrammen / npc", r"hologram|\bnpc|quest|dialoog|figuur",
     ["holograms", "npc", "citizens", "quests"], ["hologram", "npc", "citizens", "quest"]),
    ("meerdere werelden", r"multiworld|multi-world|meerdere werelden|nieuwe wereld|dimensie|worldgen|terrein|biome|multiverse",
     ["multiworld", "world management", "multiverse", "world generator"], ["world", "multiverse", "dimension", "generator"]),
    ("pvp / gevechten", r"pvp|vechten|combat|duel|gevecht|arena|combatlog",
     ["pvp", "combat", "duels", "combat log"], ["pvp", "combat", "duel", "arena"]),
    ("menu's / gui", r"\bmenu|\bgui\b|server ?selector|compass|inventaris ?menu",
     ["gui menu", "deluxemenus", "server selector", "custom menu"], ["menu", "gui", "selector", "inventory"]),
    ("placeholders", r"placeholder|variabele",
     ["placeholderapi"], ["placeholder"]),
    ("lobby / hub", r"lobby|\bhub\b|wachtkamer",
     ["lobby", "hub", "server hub"], ["lobby", "hub"]),
    ("afk", r"\bafk\b|inactief|idle",
     ["afk", "afk kick", "afk detection"], ["afk", "idle", "inactive"]),
    ("willekeurig teleporteren", r"random teleport|\brtp\b|willekeurig|\bwild\b",
     ["random teleport", "rtp", "wild"], ["random", "teleport", "rtp", "wild"]),
    ("bomen omhakken", r"bom(en)?\b.*(hak|kap|vell|rooi|zaag)|(hak|kap|vell|rooi)\w*.*\bbom|tree ?(feller|capitator|chop)|timber|lumber|houthakker|boomstam|chop (down )?trees?",
     ["tree feller", "timber", "treecapitator", "lumberjack", "chop trees"], ["tree", "timber", "feller", "chop", "lumber", "log", "wood"]),
    ("farmen / oogsten", r"\bfarm|gewas|crops|oogst|harvest|replant|vein ?miner|ertsader",
     ["farming", "replant", "harvest", "vein miner"], ["farm", "replant", "harvest", "crop", "vein"]),
    ("kisten sorteren / opslag", r"sorteer|\bsort|kist.*sort|chest ?sort|opslag|storage",
     ["chest sort", "inventory sort", "storage"], ["sort", "chest", "inventory", "storage"]),
    ("kisten / deuren vergrendelen", r"vergrendel|\block|slot\b|deur.*beveilig|kist.*beveilig|chest ?lock",
     ["chest lock", "lock", "protect chests", "lockette"], ["lock", "chest", "door", "protect"]),
    ("loggen / terugdraaien", r"rollback|terugdraai|coreprotect|loggen|blocklog|logging|wie heeft|geschiedenis|griefer",
     ["coreprotect", "block logging", "rollback", "logging"], ["log", "rollback", "coreprotect", "history", "restore"]),
    ("inloggen / whitelist", r"whitelist|inloggen|login|wachtwoord|password|registreer|authme|cracked|offline",
     ["authme", "login", "whitelist", "password"], ["login", "password", "auth", "whitelist", "register"]),
    ("cosmetics / hoeden", r"cosmetic|hoed|\bhats?\b|particles|deeltjes|trail|effecten|cape",
     ["cosmetics", "hats", "particles", "trails"], ["cosmetic", "hat", "particle", "trail"]),
    ("vliegen", r"vliegen|\bfly\b|flight|\belytra",
     ["fly", "flight", "fly commands"], ["fly", "flight", "elytra"]),
    ("levens / hardcore", r"levens|\blives\b|hardcore|doodstraf",
     ["lives", "hardcore", "death penalty"], ["lives", "life", "hardcore", "death"]),
    ("onzichtbaar / vanish", r"vanish|onzichtbaar|invisible|\bspy\b",
     ["vanish", "invisible admin"], ["vanish", "invisible", "hide"]),
    ("eigen recepten / items", r"recept|recipe|crafting|\bcraft\b|nieuwe items|custom items|itemsadder|eigen items",
     ["custom recipes", "custom items", "crafting", "itemsadder"], ["recipe", "craft", "item", "custom"]),
    ("hoofden", r"\bheads?\b|hoofden|player ?heads?|\bskulls?\b",
     ["player heads", "head database"], ["head", "skull"]),
    ("statistieken / ranglijst", r"statistiek|\bstats\b|leaderboard|ranglijst|speeltijd|playtime|top ?lijst",
     ["leaderboard", "statistics", "playtime", "stats"], ["leaderboard", "stats", "playtime", "top"]),
    ("resource packs", r"resource ?pack|texture|texturepack",
     ["resource pack", "resource pack manager"], ["resource", "pack", "texture"]),
    ("crates / beloningen", r"crate|loot|lootbox|sleutel|\bkeys?\b|gacha",
     ["crates", "loot crates", "crate keys"], ["crate", "loot", "key", "reward"]),
    ("huisdieren / rijden", r"huisdier|\bpets?\b|\bmount|paard|\bhorse|rijden",
     ["pets", "mount", "horse", "pet"], ["pet", "mount", "horse", "ride"]),
    ("dorpelingen / handel", r"dorpeling|villager|trades?\b|handelaar",
     ["villager", "trading", "villager trades"], ["villager", "trade", "trading"]),
]

_ACC = str.maketrans("éèêëáàâäíìîïóòôöúùûü", "eeeeaaaaiiiioooouuuu")


def norm_text(s):
    return (s or "").lower().translate(_ACC)


def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", norm_text(s))


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9\+\-\.]+", norm_text(text)) if t]


def _translate_token(tok):
    if tok in NL_EN:
        return NL_EN[tok]
    for stem, en in NL_EN.items():
        if len(stem) >= 4 and tok.startswith(stem):
            return en
    return None


def interpret_query(text):
    """Zet een vrije zin om in zoekopdrachten. Geeft dict(name_like, queries, keywords, concepts, plain)."""
    raw = (text or "").strip()
    low = norm_text(raw)
    toks = tokenize(raw)
    content = [t for t in toks if t not in STOPWORDS and not t.isdigit() and not re.fullmatch(r"x?\d+x?", t)]
    concepts = [c for c in CONCEPTS if re.search(c[1], low)]
    name_like = 0 < len(content) <= 3 and len(toks) <= 4 and (len(content) == 1 or not concepts) and not any(
        w in toks for w in ("als", "dat", "die", "zodat", "wanneer", "that", "which", "when", "if", "ervoor", "zorgt"))
    queries, kw = [], []
    if raw:
        queries.append((raw, 1.0 if name_like else 0.4))
    if name_like and len(content) > 1:
        queries.append(("".join(content), 0.9))  # 'world edit' -> 'worldedit'
    for label, _rx, qs, keys in concepts[:3]:
        for i, q in enumerate(qs[:5]):
            queries.append((q, 0.9 - 0.08 * i))
        kw += keys
    known, unknown = [], []
    for t in content:
        e = _translate_token(t)
        (known if e else unknown).append(e or t)
    known = [w for w in dict.fromkeys(known) if w not in STOPWORDS]
    unknown = [w for w in dict.fromkeys(unknown) if w not in STOPWORDS]
    # Modrinth eist dat alle woorden voorkomen: Nederlandse restwoorden laten we daarom weg als we de rest wel vertalen
    translated = known if known else unknown
    if translated and (not name_like or (len(content) >= 2 and not concepts)):
        if not concepts:
            queries.append((" ".join(translated[:4]), 0.8))
            if len(translated) > 2:
                queries.append((" ".join(translated[:2]), 0.6))
            for w in translated[:3]:
                if len(w) > 3:
                    queries.append((w, 0.4))
        elif len(known) >= 2:
            queries.append((" ".join(known[:3]), 0.5))
    if not concepts:
        kw += translated
    seen, out = set(), []
    for q, w in queries:
        k = q.lower()
        if k and k not in seen:
            seen.add(k)
            out.append((q, w))
    return dict(name_like=name_like, queries=out[:9], keywords=list(dict.fromkeys(kw)),
                concepts=[c[0] for c in concepts[:3]], translated=translated, content=content)


def _parse_iso(s):
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _age_days(dt):
    return (datetime.utcnow() - dt).days if dt else None


def modrinth_search(query, loaders, limit=15, mc=None):
    cats = [f"categories:{x}" for x in (loaders or ALL_LOADERS)]
    facets = json.dumps([cats] + ([[f"versions:{mc}"]] if mc else []))
    d = http_json(f"{MODRINTH}/search?" + urllib.parse.urlencode(
        {"query": query, "limit": limit, "facets": facets}), timeout=20, retries=1)
    out = []
    for h in d.get("hits", []):
        out.append(dict(source="Modrinth", id=h.get("project_id"), slug=h.get("slug") or "", name=h.get("title") or "",
                        desc=h.get("description") or "", downloads=int(h.get("downloads") or 0),
                        updated=_parse_iso(h.get("date_modified")), versions=list(h.get("versions") or []),
                        cats=list(h.get("categories") or []), author=h.get("author") or "",
                        page=f"https://modrinth.com/plugin/{h.get('slug')}" if h.get("slug") else ""))
    return out


def hangar_search(query, limit=10):
    d = http_json(f"{HANGAR}/projects?" + urllib.parse.urlencode({"q": query, "limit": limit}), timeout=20, retries=1)
    out = []
    for p in d.get("result", []):
        ns = p.get("namespace") or {}
        st = p.get("stats") or {}
        out.append(dict(source="Hangar", id=None, slug=ns.get("slug") or p.get("name") or "", name=p.get("name") or "",
                        desc=p.get("description") or "", downloads=int(st.get("downloads") or 0),
                        updated=_parse_iso(p.get("lastUpdated")), versions=[], cats=[p.get("category") or ""],
                        author=ns.get("owner") or "",
                        page=f"https://hangar.papermc.io/{ns.get('owner')}/{ns.get('slug')}" if ns.get("owner") else ""))
    return out


def hangar_supports(slug, mc):
    """Heeft deze Hangar-plugin een versie voor jouw Minecraft-versie op Paper?"""
    d = http_json(f"{HANGAR}/projects/{urllib.parse.quote(slug)}/versions?" + urllib.parse.urlencode(
        {"limit": 1, "platform": "PAPER", "platformVersion": mc}), timeout=20, retries=1)
    return bool(d.get("result"))


def search_plugins(text, mc, loaders, installed=(), log=None, only_compat=False):
    """Slim zoeken: begrijpt een naam ('worldedit') én een beschrijving ('als 1 iemand slaapt wordt het dag').
    Draait meerdere zoekopdrachten tegelijk op Modrinth en Hangar, voegt de resultaten samen en rangschikt ze."""
    info = interpret_query(text)
    if not info["queries"]:
        return [], info
    jobs = []
    for q, w in info["queries"]:
        jobs.append((q, w, "Modrinth", lambda q=q: modrinth_search(q, loaders, mc=mc if only_compat else None)))
        jobs.append((q, w, "Hangar", lambda q=q: hangar_search(q)))
    hits, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(jobs))) as ex:
        futs = {ex.submit(fn): (q, w, src) for q, w, src, fn in jobs}
        try:
            for f in concurrent.futures.as_completed(futs, timeout=45):
                q, w, src = futs[f]
                try:
                    for rank, r in enumerate(f.result()):
                        hits.append((q, w, rank, r))
                except Exception as e:
                    errors.append(f"{src}: {describe_net_error(e)}")
        except concurrent.futures.TimeoutError:
            errors.append("time-out bij sommige zoekopdrachten")
    if not hits and errors:
        raise RuntimeError("; ".join(sorted(set(errors))))
    info["errors"] = sorted(set(errors))
    nq = norm_name(" ".join(info["content"])) or norm_name(text)
    merged = {}
    for q, w, rank, r in hits:
        key = norm_name(r["name"]) or norm_name(r["slug"])
        m = merged.get(key)
        if m is None:
            m = merged[key] = dict(r, sources=[r["source"]], score=0.0, queries=set(), pages={r["source"]: r["page"]},
                                   alt=[r])
        elif r["source"] not in m["sources"]:
            m["sources"].append(r["source"])
            m["pages"][r["source"]] = r["page"]
            m["alt"].append(r)
            if r["source"] == "Modrinth":  # Modrinth heeft de beste gegevens (versies, id)
                for k in ("id", "versions", "cats", "page"):
                    m[k] = r[k]
                m["source"] = "Modrinth"
            m["downloads"] = max(m["downloads"], r["downloads"])
        m["score"] += w / (rank + 3)
        m["queries"].add(q)
    kws = [k.lower() for k in info["keywords"]]
    inst = {norm_name(x) for x in installed}
    out = []
    for key, m in merged.items():
        title, desc = norm_text(m["name"]), norm_text(m["desc"])
        why = []
        s = m["score"] * 6
        hit_t = [k for k in kws if k in title]
        hit_d = [k for k in kws if k in desc and k not in hit_t]
        s += 3 * len(hit_t) + 1.2 * len(hit_d)
        if hit_t or hit_d:
            why.append("noemt: " + ", ".join((hit_t + hit_d)[:4]))
        if len(m["queries"]) > 1:
            s += 0.8 * (len(m["queries"]) - 1)
        exact = bool(nq) and (norm_name(m["name"]) == nq or norm_name(m["slug"]) == nq)
        if exact:
            s += 100
            why.insert(0, "exacte naam")
        elif info["name_like"] and nq and (norm_name(m["name"]).startswith(nq) and len(nq) >= 4):
            s += 6
            why.insert(0, "begint met jouw zoekterm")
        s += math.log10(max(m["downloads"], 1)) * 0.6
        compat = None
        if m["versions"] and mc:
            compat = mc in m["versions"]
            s += 1.5 if compat else -0.5
        age = _age_days(m["updated"])
        if age is not None:
            s += 0.6 if age < 365 else (-0.8 if age > 900 else 0)
        m.update(score=s, why="; ".join(why), exact=exact, compat=compat,
                 installed=key in inst or norm_name(m["slug"]) in inst)
        out.append(m)
    out.sort(key=lambda r: r["score"], reverse=True)
    if mc:  # Hangar vermeldt geen versies in de zoekresultaten: voor de beste resultaten apart navragen
        todo = [r for r in out if r["compat"] is None and r["source"] == "Hangar" and r["slug"]][:15]
        if todo:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                futs = {ex.submit(hangar_supports, r["slug"], mc): r for r in todo}
                try:
                    for f in concurrent.futures.as_completed(futs, timeout=25):
                        try:
                            futs[f]["compat"] = bool(f.result())
                        except Exception:
                            pass
                except concurrent.futures.TimeoutError:
                    pass
    if only_compat and mc:
        out = [r for r in out if r["compat"] is True]
    info["only_compat"] = bool(only_compat and mc)
    return out[:40], info


def read_plugin_yml(path):
    """Leest naam, versie, omschrijving en afhankelijkheden uit plugin.yml / paper-plugin.yml."""
    res = dict(name=None, version=None, desc="", website=None, depend=[], soft=[], authors="", commands=[])
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for n in ("paper-plugin.yml", "plugin.yml"):
                if n not in names:
                    continue
                txt = z.read(n).decode("utf-8", "replace")

                def val(key):
                    m = re.search(r"^" + key + r":\s*['\"]?([^'\"\r\n#]+)", txt, re.M)
                    return m.group(1).strip() if m else None

                def lst(key):
                    m = re.search(r"^" + key + r":[ \t]*(.*)$", txt, re.M)
                    if not m:
                        return []
                    v = m.group(1).strip()
                    if v.startswith("["):
                        return [x.strip(" '\"") for x in v.strip("[]").split(",") if x.strip(" '\"")]
                    if v:
                        return [v.strip("'\"")]
                    rest = txt[m.end():].splitlines()
                    out = []
                    for line in rest:
                        mm = re.match(r"^\s+-\s*['\"]?([^'\"#\s][^'\"#]*)", line)
                        if mm:
                            out.append(mm.group(1).strip())
                        elif line.strip() and not line.startswith(" "):
                            break
                    return out

                res["name"], res["website"] = val("name"), val("website") or val("url")
                v = val("version")
                res["version"] = v if v and "${" not in v else None
                res["desc"] = val("description") or ""
                res["authors"] = ", ".join(lst("authors")) or (val("author") or "")
                if n == "plugin.yml":
                    res["depend"], res["soft"] = lst("depend"), lst("softdepend")
                    cm = re.search(r"^commands:[ \t]*\n((?:[ \t]+.*\n?|\n)*)", txt, re.M)
                    if cm:
                        first = re.search(r"^([ \t]+)\S", cm.group(1), re.M)
                        if first:
                            res["commands"] = re.findall(r"^" + first.group(1) + r"['\"]?([\w:.\-]+)['\"]?:", cm.group(1), re.M)
                else:  # paper-plugin.yml: dependencies -> server -> Naam -> required
                    sec = re.search(r"^dependencies:\s*\n((?:[ \t]+.*\n?|\n)*)", txt, re.M)
                    if sec:
                        srv = re.search(r"^[ \t]+server:\s*\n((?:[ \t]{4,}.*\n?)*)", sec.group(1), re.M)
                        if srv:
                            for blk in re.finditer(r"^[ \t]+([\w.\-]+):\s*\n((?:[ \t]{6,}.*\n?)*)", srv.group(1), re.M):
                                req = re.search(r"required:\s*(\w+)", blk.group(2))
                                (res["soft"] if req and req.group(1).lower() == "false" else res["depend"]).append(blk.group(1))
                break
    except Exception:
        pass
    return res


def scan_plugins(pdir):
    """Alle plugins in de map, aan (.jar) en uit (.jar.disabled), met afhankelijkheden."""
    items = []
    try:
        files = sorted(os.listdir(pdir), key=str.lower)
    except OSError:
        return items
    for fn in files:
        low = fn.lower()
        path = os.path.join(pdir, fn)
        if not os.path.isfile(path) or not (low.endswith(".jar") or low.endswith(".jar.disabled")):
            continue
        enabled = low.endswith(".jar")
        meta = read_plugin_yml(path)
        base = fn[:-4] if enabled else fn[:-13]
        meta.update(file=fn, path=path, enabled=enabled, name=meta["name"] or base, size=os.path.getsize(path))
        items.append(meta)
    names_on = {i["name"].lower(): i for i in items if i["enabled"]}
    for i in items:
        i["needed_by"] = sorted(o["name"] for o in items if o["enabled"] and o is not i
                                and i["name"].lower() in [d.lower() for d in o["depend"]])
        i["missing"] = [d for d in i["depend"] if d.lower() not in names_on]
    return items


def toggle_plugin(item, enable):
    """Hernoemt x.jar <-> x.jar.disabled. Paper laadt alleen .jar-bestanden."""
    src = item["path"]
    dst = src[:-9] if enable else src + ".disabled"
    if os.path.exists(dst):
        raise FileExistsError(f"{os.path.basename(dst)} bestaat al.")
    os.rename(src, dst)
    return dst


def remove_plugin(item, trash_dir):
    os.makedirs(trash_dir, exist_ok=True)
    dst = os.path.join(trash_dir, item["file"])
    if os.path.exists(dst):
        dst = os.path.join(trash_dir, datetime.now().strftime("%H%M%S_") + item["file"])
    shutil.move(item["path"], dst)
    return dst


def _safe_jar_name(name, fallback):
    n = os.path.basename((name or "").replace("\\", "/")) or fallback
    n = re.sub(r"[^\w.\-+()]", "_", n)
    return n if n.lower().endswith(".jar") else n + ".jar"


def modrinth_resolve(pid, mc, loaders, unstable=False):
    """Zoekt de beste downloadbare versie van een Modrinth-project voor jouw server."""
    base = f"{MODRINTH}/project/{pid}/version?"
    loaders = loaders or ALL_LOADERS
    params = {"loaders": json.dumps(loaders)}
    verified = True
    vers = []
    if mc:
        vers = http_json(base + urllib.parse.urlencode(dict(params, game_versions=json.dumps([mc]))), retries=2)
    if not vers:
        verified = not mc and True or False
        vers = http_json(base + urllib.parse.urlencode(params), retries=2)
    if not vers:
        return None
    pick = next((v for v in vers if v.get("version_type") == "release"), None) or (vers[0] if unstable else None)
    pick = pick or vers[0]
    files = [f for f in pick.get("files", []) if str(f.get("filename", "")).lower().endswith(".jar")] or pick.get("files", [])
    if not files:
        return None
    f = next((x for x in files if x.get("primary")), files[0])
    hs = f.get("hashes") or {}
    algo = "sha512" if hs.get("sha512") else ("sha1" if hs.get("sha1") else None)
    deps = [d["project_id"] for d in pick.get("dependencies", [])
            if d.get("dependency_type") == "required" and d.get("project_id")]
    return dict(source="Modrinth", pid=pid, version=pick.get("version_number") or "?", url=f["url"],
                filename=_safe_jar_name(f.get("filename"), pid + ".jar"), algo=algo, hash=hs.get(algo) if algo else None,
                verified=verified, vtype=pick.get("version_type"), mc=list(pick.get("game_versions") or []), deps=deps)


def plan_install(result, mc, loaders, installed, unstable=False):
    """Maakt een installatieplan: de plugin zelf plus verplichte afhankelijkheden die nog niet aanwezig zijn."""
    inst = {norm_name(x) for x in installed}
    plan, notes = [], []
    if result["source"] == "Modrinth" and result.get("id"):
        r = modrinth_resolve(result["id"], mc, loaders, unstable)
        if not r:
            raise RuntimeError("Geen downloadbare versie voor jouw serversoftware gevonden op Modrinth.")
        r.update(title=result["name"], page=result["page"])
        plan.append(r)
        todo = list(r["deps"])
        seen = {result["id"]}
        while todo and len(plan) < 8:
            pid = todo.pop(0)
            if pid in seen:
                continue
            seen.add(pid)
            try:
                pj = http_json(f"{MODRINTH}/project/{pid}", retries=1)
            except Exception:
                notes.append(f"Afhankelijkheid {pid} kon niet worden opgezocht.")
                continue
            if norm_name(pj.get("title")) in inst or norm_name(pj.get("slug")) in inst:
                continue
            d = modrinth_resolve(pid, mc, loaders, unstable)
            if not d:
                notes.append(f"Verplichte afhankelijkheid '{pj.get('title')}' heeft geen passende versie: installeer die zelf.")
                continue
            d.update(title=pj.get("title") or pid, page=f"https://modrinth.com/plugin/{pj.get('slug')}", dep=True)
            plan.append(d)
            todo += [x for x in d["deps"] if x not in seen]
    else:
        h = hangar_lookup(result["name"], mc, unstable)
        if not h:
            raise RuntimeError("Geen downloadbare versie voor Paper gevonden op Hangar.")
        h = dict(h, filename=_safe_jar_name(h.get("filename"), result["name"] + ".jar"), pid=None, mc=[], deps=[],
                 vtype="release")
        plan.append(h)
        notes.append("Bij Hangar kan ik afhankelijkheden niet automatisch zien: lees de pagina van de plugin.")
    return plan, notes


def install_plan(plan, pdir, progress=None):
    """Downloadt en controleert alle bestanden uit het plan. Geeft de lijst met nieuwe bestandsnamen."""
    done = []
    os.makedirs(pdir, exist_ok=True)
    for step in plan:
        dest = os.path.join(pdir, step["filename"])
        if os.path.exists(dest) or os.path.exists(dest + ".disabled"):
            raise FileExistsError(f"{step['filename']} staat al in de plugins-map.")
    for step in plan:
        dest = os.path.join(pdir, step["filename"])
        tmp = dest + ".part"
        expected = (step["algo"], step["hash"]) if step.get("algo") and step.get("hash") else None
        try:
            download(step["url"], tmp, progress=progress, expected=expected)
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        done.append(step["filename"])
    return done


VANILLA_CMDS = """advancement attribute ban ban-ip banlist bossbar clear clone damage data datapack debug defaultgamemode deop
difficulty effect enchant execute experience xp fill fillbiome forceload function gamemode gamerule give help item kick kill list
locate loot me msg op pardon pardon-ip particle plugins pl reload recipe ride save-all save-off save-on say schedule scoreboard seed
setblock setidletimeout setworldspawn spawnpoint spectate spreadplayers stop stopsound summon tag team teammsg tell tellraw
teleport tp time title tm trigger w weather whitelist worldborder version ver tps mspt paper spark timings restart plm plugman""".split()
PLAYER_CMDS = {"ban", "pardon", "kick", "op", "deop", "msg", "tell", "w", "give", "kill", "clear", "spectate", "tp", "teleport",
               "spawnpoint", "tellraw", "xp", "experience", "effect", "enchant", "advancement", "attribute", "damage"}
TAB_SUBS = {
    ("whitelist", 0): ["add", "remove", "list", "on", "off", "reload"],
    ("gamemode", 0): ["survival", "creative", "adventure", "spectator"],
    ("defaultgamemode", 0): ["survival", "creative", "adventure", "spectator"],
    ("time", 0): ["set", "add", "query"],
    ("weather", 0): ["clear", "rain", "thunder"],
    ("difficulty", 0): ["peaceful", "easy", "normal", "hard"],
    ("gamerule", 0): ["keepInventory", "doDaylightCycle", "doWeatherCycle", "doMobSpawning", "mobGriefing", "playersSleepingPercentage",
                      "doFireTick", "commandBlockOutput", "announceAdvancements", "naturalRegeneration", "pvp", "randomTickSpeed"],
    ("effect", 0): ["give", "clear"],
    ("worldborder", 0): ["add", "set", "center", "damage", "get", "warning"],
    ("plm", 0): ["load", "unload", "reload", "enable", "disable", "restart", "info", "list", "lookup", "help", "dump", "vault"],
    ("plugman", 0): ["load", "unload", "reload", "enable", "disable", "restart", "info", "list", "lookup", "help", "dump", "vault"],
    ("timings", 0): ["on", "off", "report", "reset", "paste"],
    ("paper", 0): ["reload", "version", "heap", "dumpitem", "mobcaps", "entity", "chunk"],
    ("spark", 0): ["profiler", "tps", "healthreport", "gc", "heapsummary", "ping", "tickmonitor"],
    ("save-all", 0): ["flush"],
}
PLM_PLUGIN_SUBS = {"load", "unload", "reload", "enable", "disable", "restart", "info", "lookup"}


def complete_command(text, commands, players, plugins):
    """Tab-aanvulling voor het commandoveld. Geeft alle volledige mogelijke vervangingen van de ingevoerde tekst."""
    slash = text.startswith("/")
    body = text[1:] if slash else text
    parts = body.split(" ")
    last = parts[-1]
    pre = ("/" if slash else "") + (" ".join(parts[:-1]) + " " if len(parts) > 1 else "")
    if len(parts) == 1:
        pool = commands
    else:
        cmd, idx = parts[0].lower(), len(parts) - 2
        sub = parts[1].lower() if len(parts) > 2 else ""
        pool = TAB_SUBS.get((cmd, idx))
        if cmd == "time" and idx == 1 and sub == "set":
            pool = ["day", "night", "noon", "midnight"]
        elif cmd in ("plm", "plugman") and idx == 1 and sub in PLM_PLUGIN_SUBS:
            pool = plugins
        elif cmd == "whitelist" and idx == 1 and sub in ("add", "remove"):
            pool = players
        elif cmd == "gamemode" and idx == 1:
            pool = players
        elif cmd in ("tp", "teleport") and idx <= 1:
            pool = players
        elif cmd in PLAYER_CMDS and idx == 0:
            pool = players
        if pool is None:
            pool = players
    low = last.lower()
    return [pre + c for c in sorted({c for c in pool if c.lower().startswith(low)}, key=str.lower)]


def fmt_count(n):
    n = int(n or 0)
    if n >= 1000000:
        return f"{n / 1000000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def plugman_name(items):
    """Naam van de PlugMan(X)-plugin als die aanstaat (nodig voor /plm load)."""
    return next((i["name"] for i in items if i["enabled"] and norm_name(i["name"]).startswith("plugman")), None)


class PluginsTab(ttk.Frame):
    """Tabblad Plugins: beheren (aan/uit/verwijderen) en slim zoeken + installeren."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.q = queue.Queue()
        self.items, self.busy, self._search_mc = {}, False, ""
        self.plm_var = tk.BooleanVar(value=bool(app.cfg.get("plm_load", False)))
        self.query_var = tk.StringVar()
        self.compat_var = tk.BooleanVar(value=bool(app.cfg.get("plugins_only_compat", False)))
        self.status_var = tk.StringVar(value="")
        self.sub = ttk.Notebook(self)
        self.sub.pack(fill="both", expand=True)
        self.pg_inst = ttk.Frame(self.sub, padding=8)
        self.pg_find = ttk.Frame(self.sub, padding=8)
        self.sub.add(self.pg_inst, text="Geïnstalleerd")
        self.sub.add(self.pg_find, text="🔍 Zoeken en toevoegen")
        self._build_installed()
        self._build_find()
        box = ttk.Frame(self)
        box.pack(fill="x", pady=(8, 0))
        ttk.Checkbutton(box, text="⚠ Plugins direct laden met /plm load, zonder herstart (op eigen risico)",
                        variable=self.plm_var, command=self._plm_toggled).pack(anchor="w")
        ttk.Label(box, textvariable=self.status_var, foreground="#6b7280").pack(anchor="w", pady=(2, 0))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self._on_wheel, add="+")
        self.after(120, self._poll)

    # ---------- opbouw ----------
    def _build_installed(self):
        f = self.pg_inst
        self.card_vars, self._cards, self._desc_labels = {}, {}, []
        self.f_text, self.f_state = tk.StringVar(), tk.StringVar(value="Alles")
        self.s_key, self.s_desc = tk.StringVar(value="Naam"), False
        # --- teller-tegels ---
        tiles = tk.Frame(f, bg=self.BG)
        tiles.pack(fill="x", pady=(0, 5))
        self.tiles = {}
        for key, label, color in (("total", "Plugins", "#2563eb"), ("on", "Aan", "#16a34a"),
                                  ("off", "Uit", "#6b7280"), ("warn", "Aandacht nodig", "#d97706")):
            t = tk.Frame(tiles, bg="white", highlightbackground="#e5e7eb", highlightthickness=1)
            t.pack(side="left", padx=(0, 6))
            tk.Frame(t, bg=color, width=3).pack(side="left", fill="y")
            n = tk.Label(t, text="0", bg="white", fg=color, font=("Segoe UI", 10, "bold"))
            n.pack(side="left", padx=(8, 3))
            tk.Label(t, text=label, bg="white", fg="#4b5563", font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
            self.tiles[key] = n
        # --- filter en sortering ---
        row = tk.Frame(f, bg=self.BG)
        row.pack(fill="x", pady=(0, 6))
        e = ttk.Entry(row, textvariable=self.f_text, width=28, font=("Segoe UI", 10))
        e.pack(side="left")
        e.bind("<KeyRelease>", lambda ev: self._render())
        tk.Label(row, text="🔎 filter op naam of omschrijving", bg=self.BG, fg="#9ca3af", font=("Segoe UI", 9)).pack(side="left", padx=6)
        cb = ttk.Combobox(row, textvariable=self.f_state, values=["Alles", "Aan", "Uit", "Met probleem"], state="readonly", width=12)
        cb.pack(side="left", padx=(14, 0))
        cb.bind("<<ComboboxSelected>>", lambda ev: self._render())
        tk.Label(row, text="Sorteer op", bg=self.BG, fg="#4b5563", font=("Segoe UI", 9)).pack(side="left", padx=(14, 4))
        sc = ttk.Combobox(row, textvariable=self.s_key, values=["Naam", "Status", "Versie"], state="readonly", width=9)
        sc.pack(side="left")
        sc.bind("<<ComboboxSelected>>", lambda ev: self._render())
        self.btn_dir = self._btn(row, "▲", self._flip_sort, "#e5e7eb", "#111827", pad=6)
        self.btn_dir.pack(side="left", padx=4)
        self.count_lbl = tk.Label(row, text="", bg=self.BG, fg="#6b7280", font=("Segoe UI", 9))
        self.count_lbl.pack(side="right")
        # --- acties ---
        bar = tk.Frame(f, bg=self.BG)
        bar.pack(fill="x", pady=(0, 8))
        for text, cmd, bg, fg in (("▶  Aanzetten", lambda: self._toggle(True), "#16a34a", "white"),
                                  ("⏸  Uitzetten", lambda: self._toggle(False), "#d97706", "white"),
                                  ("🗑  Verwijderen…", self._remove, "#dc2626", "white"),
                                  ("⚡  Nu laden (/plm load)", self._load_selected, "#7c3aed", "white"),
                                  ("☑  Alles selecteren", self._select_all, "#e5e7eb", "#111827"),
                                  ("📂  Map openen", self._open_dir, "#e5e7eb", "#111827"),
                                  ("↻  Vernieuwen", self.refresh, "#e5e7eb", "#111827")):
            self._btn(bar, text, cmd, bg, fg).pack(side="left", padx=(0, 6))
        tk.Label(bar, text="Vink plugins aan om meer tegelijk te beheren, of gebruik de knop op de kaart.", bg=self.BG,
                 fg="#9ca3af", font=("Segoe UI", 9)).pack(side="right")
        # --- scrollbare lijst met kaarten ---
        wrap = tk.Frame(f, bg=self.BG)
        wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(wrap, bg=self.BG, highlightthickness=0, yscrollincrement=30)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=self.BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda ev: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._canvas_resized)

    @property
    def BG(self):
        try:
            return ttk.Style().lookup("TFrame", "background") or "#f0f0f0"
        except Exception:
            return "#f0f0f0"

    @staticmethod
    def _btn(parent, text, cmd, bg, fg, pad=10):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                      relief="flat", bd=0, padx=pad, pady=4, font=("Segoe UI", 9, "bold"), cursor="hand2")
        return b

    def _canvas_resized(self, ev):
        self.canvas.itemconfigure(self._win, width=ev.width)
        for lbl in self._desc_labels:
            try:
                lbl.config(wraplength=max(300, ev.width - 330))
            except Exception:
                pass

    def _on_wheel(self, ev):
        """Muiswiel/touchpad: scrolt de lijst waar de muis boven staat, ook boven een kaart of knop."""
        try:
            w = self.winfo_containing(ev.x_root, ev.y_root)
        except (KeyError, tk.TclError):
            return
        c = None
        while w is not None:
            if w is self.canvas or w is self.rcanvas:
                c = w
                break
            w = getattr(w, "master", None)
        if c is None:
            return
        if getattr(ev, "num", 0) == 4:
            n = -3
        elif getattr(ev, "num", 0) == 5:
            n = 3
        else:
            d = ev.delta or 0
            n = int(-d / 40) or (-1 if d > 0 else 1)
        c.yview_scroll(n, "units")

    def _flip_sort(self):
        self.s_desc = not self.s_desc
        self.btn_dir.config(text="▼" if self.s_desc else "▲")
        self._render()

    def _select_all(self):
        vis = [i["file"] for i in self._visible()]
        everything = all(self.card_vars[f].get() for f in vis if f in self.card_vars)
        for f in vis:
            if f in self.card_vars:
                self.card_vars[f].set(not everything)
        self._refresh_selection()

    def _visible(self):
        text = norm_text(self.f_text.get().strip())
        mode = self.f_state.get()
        out = []
        for it in self.items.values():
            if mode == "Aan" and not it["enabled"]:
                continue
            if mode == "Uit" and it["enabled"]:
                continue
            if mode == "Met probleem" and not (it["enabled"] and it["missing"]):
                continue
            if text and text not in norm_text(it["name"] + " " + it["desc"] + " " + it["file"]):
                continue
            out.append(it)
        keys = {"Naam": lambda i: i["name"].lower(), "Status": lambda i: (not i["enabled"], bool(i["missing"]), i["name"].lower()),
                "Grootte": lambda i: i["size"], "Versie": lambda i: (ver_nums(i["version"] or "") or (0,), i["version"] or "")}
        out.sort(key=keys[self.s_key.get()], reverse=self.s_desc)
        return out

    def _make_card(self, it):
        enabled, problem = it["enabled"], bool(it["enabled"] and it["missing"])
        accent = "#d97706" if problem else ("#16a34a" if enabled else "#9ca3af")
        fg_main, fg_sub = ("#111827", "#4b5563") if enabled else ("#6b7280", "#9ca3af")
        card = tk.Frame(self.inner, bg="white", highlightbackground="#e5e7eb", highlightthickness=1)
        card.pack(fill="x", padx=(0, 6), pady=3)
        tk.Frame(card, bg=accent, width=6).pack(side="left", fill="y")
        var = self.card_vars.setdefault(it["file"], tk.BooleanVar(value=False))
        tk.Checkbutton(card, variable=var, bg="white", activebackground="white", bd=0, highlightthickness=0,
                       command=self._refresh_selection).pack(side="left", padx=(8, 2))
        body = tk.Frame(card, bg="white")
        body.pack(side="left", fill="x", expand=True, padx=(4, 8), pady=4)
        top = tk.Frame(body, bg="white")
        top.pack(fill="x")
        tk.Label(top, text=it["name"], bg="white", fg=fg_main, font=("Segoe UI", 11, "bold")).pack(side="left")
        if it["version"]:
            tk.Label(top, text=it["version"], bg="#eef2ff" if enabled else "#f3f4f6", fg="#3730a3" if enabled else "#6b7280",
                     font=("Segoe UI", 9), padx=6).pack(side="left", padx=8)
        if problem:
            pill, pbg, pfg = "⚠ MIST " + ", ".join(it["missing"]).upper(), "#fef3c7", "#92400e"
        elif enabled:
            pill, pbg, pfg = "AAN", "#dcfce7", "#166534"
        else:
            pill, pbg, pfg = "UIT", "#e5e7eb", "#4b5563"
        tk.Label(top, text=pill, bg=pbg, fg=pfg, font=("Segoe UI", 8, "bold"), padx=7).pack(side="left")
        desc = tk.Label(body, text=it["desc"] or "(geen omschrijving in de plugin)", bg="white", fg=fg_sub, anchor="w",
                        justify="left", font=("Segoe UI", 10), wraplength=700)
        desc.pack(fill="x", pady=(2, 0))
        self._desc_labels.append(desc)
        meta = []
        if it["depend"]:
            meta.append("Heeft nodig: " + ", ".join(it["depend"]))
        if it["needed_by"]:
            meta.append("Nodig voor: " + ", ".join(it["needed_by"]))
        if meta:
            tk.Label(body, text="   ·   ".join(meta), bg="white", fg="#9ca3af", anchor="w", justify="left",
                     font=("Segoe UI", 9)).pack(fill="x", pady=(2, 0))
        right = tk.Frame(card, bg="white")
        right.pack(side="right", padx=10)
        if enabled:
            self._btn(right, "⏸  Uitzetten", lambda it=it: self._toggle(False, [it]), "#fef3c7", "#92400e").pack()
        else:
            self._btn(right, "▶  Aanzetten", lambda it=it: self._toggle(True, [it]), "#dcfce7", "#166534").pack()
        self._cards[it["file"]] = card
        return card

    def _refresh_selection(self):
        for fn, card in self._cards.items():
            on = fn in self.card_vars and self.card_vars[fn].get()
            card.config(highlightbackground="#3b82f6" if on else "#e5e7eb", highlightthickness=2 if on else 1)

    def _render(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._cards, self._desc_labels = {}, []
        vis = self._visible()
        for it in vis:
            self._make_card(it)
        if not vis:
            tk.Label(self.inner, bg=self.BG, fg="#6b7280", font=("Segoe UI", 11), pady=30,
                     text=("Geen plugins gevonden met dit filter." if self.items else
                           "Nog geen plugins. Kies je servermap (tabblad Updates) of zoek er een bij 🔍 Zoeken en toevoegen.")).pack()
        self._canvas_resized(type("E", (), {"width": max(self.canvas.winfo_width(), 800)})())
        self._refresh_selection()
        self.count_lbl.config(text=f"{len(vis)} van {len(self.items)} getoond" if len(vis) != len(self.items) else "")

    def _build_find(self):
        f = self.pg_find
        self.res_list, self.res_info, self.res_mc = [], {}, ""
        self.r_key, self.r_desc = tk.StringVar(value="Relevantie"), False
        row = ttk.Frame(f)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)
        e = ttk.Entry(row, textvariable=self.query_var, font=("Segoe UI", 11))
        e.grid(row=0, column=0, sticky="ew")
        e.bind("<Return>", lambda ev: self.search())
        self.btn_search = self._btn(row, "🔍  Zoeken", self.search, "#2563eb", "white", pad=16)
        self.btn_search.grid(row=0, column=1, padx=(8, 0), ipady=3)
        opt = tk.Frame(f, bg=self.BG)
        opt.pack(fill="x", pady=(6, 0))
        self.compat_chk = ttk.Checkbutton(opt, text="Alleen plugins die zeker werken met mijn Minecraft-versie",
                                          variable=self.compat_var, command=self._compat_toggled)
        self.compat_chk.pack(side="left")
        self.btn_rdir = self._btn(opt, "▲", self._flip_rsort, "#e5e7eb", "#111827", pad=6)
        self.btn_rdir.pack(side="right")
        rc = ttk.Combobox(opt, textvariable=self.r_key, values=["Relevantie", "Downloads", "Bijgewerkt", "Naam", "Past bij mijn MC"],
                          state="readonly", width=16)
        rc.pack(side="right", padx=4)
        rc.bind("<<ComboboxSelected>>", lambda ev: self._render_results())
        tk.Label(opt, text="Sorteer op", bg=self.BG, fg="#4b5563", font=("Segoe UI", 9)).pack(side="right")
        tk.Label(f, bg=self.BG, fg="#6b7280", wraplength=1000, justify="left", anchor="w", font=("Segoe UI", 9),
                 text="Typ een naam (“worldedit”, “luckperms”) of beschrijf wat je zoekt (“een plugin die de nacht overslaat als 1 speler "
                      "slaapt”, “spelers kunnen land claimen”). Nederlands en Engels werken allebei."
                 ).pack(fill="x", pady=(4, 2))
        self.interp_lbl = tk.Label(f, text="", bg=self.BG, fg="#2563eb", wraplength=1000, justify="left", anchor="w",
                                   font=("Segoe UI", 9))
        self.interp_lbl.pack(fill="x", pady=(0, 4))
        wrap = tk.Frame(f, bg=self.BG)
        wrap.pack(fill="both", expand=True)
        self.rcanvas = tk.Canvas(wrap, bg=self.BG, highlightthickness=0, yscrollincrement=30)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.rcanvas.yview)
        self.rcanvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.rcanvas.pack(side="left", fill="both", expand=True)
        self.rinner = tk.Frame(self.rcanvas, bg=self.BG)
        self._rwin = self.rcanvas.create_window((0, 0), window=self.rinner, anchor="nw")
        self.rinner.bind("<Configure>", lambda ev: self.rcanvas.configure(scrollregion=self.rcanvas.bbox("all")))
        self._rdesc = []

        def resized(ev):
            self.rcanvas.itemconfigure(self._rwin, width=ev.width)
            for lbl in self._rdesc:
                try:
                    lbl.config(wraplength=max(300, ev.width - 330))
                except Exception:
                    pass

        self.rcanvas.bind("<Configure>", resized)
        self._rresize = resized

        self._render_results()

    def _flip_rsort(self):
        self.r_desc = not self.r_desc
        self.btn_rdir.config(text="▼" if self.r_desc else "▲")
        self._render_results()

    def _sorted_results(self):
        k = self.r_key.get()
        keys = {"Relevantie": lambda r: r["score"], "Downloads": lambda r: r["downloads"],
                "Bijgewerkt": lambda r: r["updated"] or datetime.min, "Naam": lambda r: r["name"].lower(),
                "Past bij mijn MC": lambda r: ({True: 2, None: 1, False: 0}[r["compat"]], r["score"])}
        asc_default = k == "Naam"
        return sorted(self.res_list, key=keys[k], reverse=(not asc_default) != self.r_desc)

    def _result_card(self, r):
        mc = self.res_mc
        if r["exact"]:
            accent = "#16a34a"
        elif r["compat"] is True:
            accent = "#2563eb"
        elif r["compat"] is False:
            accent = "#d97706"
        else:
            accent = "#9ca3af"
        card = tk.Frame(self.rinner, bg="white", highlightbackground="#e5e7eb", highlightthickness=1)
        card.pack(fill="x", padx=(0, 6), pady=3)
        tk.Frame(card, bg=accent, width=6).pack(side="left", fill="y")
        body = tk.Frame(card, bg="white")
        body.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=8)
        top = tk.Frame(body, bg="white")
        top.pack(fill="x")
        tk.Label(top, text=r["name"], bg="white", fg="#111827", font=("Segoe UI", 12, "bold")).pack(side="left")

        def badge(text, bg, fg):
            tk.Label(top, text=text, bg=bg, fg=fg, font=("Segoe UI", 8, "bold"), padx=7).pack(side="left", padx=(8, 0))

        if r["exact"]:
            badge("★ BESTE MATCH", "#dcfce7", "#166534")
        if r["compat"] is True:
            badge(f"✔ PAST BIJ {mc}" if mc else "✔ COMPATIBEL", "#dbeafe", "#1e40af")
        elif r["compat"] is False:
            badge(("TOT " + r["versions"][-1]) if r["versions"] else "MC-VERSIE ONBEKEND", "#fef3c7", "#92400e")
        else:
            badge("MC-VERSIE ONBEKEND", "#f3f4f6", "#6b7280")
        if r["installed"]:
            badge("✔ GEÏNSTALLEERD", "#e5e7eb", "#4b5563")
        upd = r["updated"].strftime("%d-%m-%Y") if r["updated"] else "?"
        tk.Label(top, text=f"⬇ {fmt_count(r['downloads'])}   ·   bijgewerkt {upd}   ·   {' + '.join(r['sources'])}",
                 bg="white", fg="#6b7280", font=("Segoe UI", 9)).pack(side="right")
        desc = tk.Label(body, text=r["desc"] or "(geen omschrijving)", bg="white", fg="#374151", anchor="w", justify="left",
                        font=("Segoe UI", 10), wraplength=700)
        desc.pack(fill="x", pady=(3, 0))
        self._rdesc.append(desc)
        if r["why"]:
            tk.Label(body, text="Waarom hier: " + r["why"], bg="white", fg="#2563eb", anchor="w",
                     font=("Segoe UI", 9)).pack(fill="x", pady=(3, 0))
        if r["compat"] is False:
            tk.Label(body, text=f"Vermeldt Minecraft {mc} niet. Vaak werkt het toch, maar probeer het eerst op een testserver.",
                     bg="white", fg="#92400e", anchor="w", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 0))
        right = tk.Frame(card, bg="white")
        right.pack(side="right", padx=12)
        self._btn(right, "⬇  Installeren" if not r["installed"] else "⬇  Opnieuw", lambda r=r: self.install(r),
                  "#2563eb" if not r["installed"] else "#e5e7eb", "white" if not r["installed"] else "#111827").pack(fill="x")
        self._btn(right, "🌐  Pagina", lambda r=r: self._open_page(r), "#e5e7eb", "#111827").pack(fill="x", pady=(6, 0))

    def _render_results(self):
        for w in self.rinner.winfo_children():
            w.destroy()
        self._rdesc = []
        for r in self._sorted_results():
            self._result_card(r)
        if not self.res_list:
            tk.Label(self.rinner, bg=self.BG, fg="#6b7280", font=("Segoe UI", 11), pady=30, justify="center",
                     text=self.res_empty if getattr(self, "res_empty", "") else
                     "Zoek hierboven naar een plugin: op naam, of met een beschrijving van wat hij moet doen.").pack()
        self._rresize(type("E", (), {"width": max(self.rcanvas.winfo_width(), 800)})())

    # ---------- hulpjes ----------
    def pdir(self):
        return os.path.join(self.app.folder_var.get().strip(), "plugins")

    def _mc(self):
        return self.app.mc_var.get().strip()

    def _loaders(self):
        return list(self.app.cfg.get("loaders") or LOADERS)

    def _note(self, text):
        self.status_var.set(text)

    def on_show(self):
        self.refresh()

    def _installed_names(self):
        names = []
        for i in self.items.values():
            names += [i["name"], i["file"].split(".jar")[0]]
        return names

    # ---------- sorteren op kolom ----------
    # ---------- geïnstalleerde plugins ----------
    def refresh(self):
        self.items = {}
        pdir = self.pdir()
        if not self.app.folder_var.get().strip() or not os.path.isdir(pdir):
            self.card_vars.clear()
            self._render()
            self.count_lbl.config(text="Kies eerst je servermap (tabblad Updates).")
            return
        for it in scan_plugins(pdir):
            self.items[it["file"]] = it
        for fn in list(self.card_vars):
            if fn not in self.items:
                del self.card_vars[fn]
        on = sum(1 for i in self.items.values() if i["enabled"])
        warn = sum(1 for i in self.items.values() if i["enabled"] and i["missing"])
        for key, val in (("total", len(self.items)), ("on", on), ("off", len(self.items) - on), ("warn", warn)):
            self.tiles[key].config(text=str(val))
        self._render()
        self.app._plug_cache = None

    def _selected(self):
        return [self.items[f] for f, v in self.card_vars.items() if f in self.items and v.get()]

    def _server_running(self):
        return self.app.srv_running()

    def _with_server_stopped(self, what, action):
        """Bestanden van geladen plugins zijn op Windows vergrendeld: eerst de server veilig stoppen, dan wijzigen, dan starten."""
        if not self._server_running():
            action()
            self.refresh()
            return
        if not messagebox.askyesno(APP_NAME, f"De server draait. Voor '{what}' moet hij even stoppen "
                                             "(Windows vergrendelt de bestanden van geladen plugins).\n\n"
                                             "Veilig stoppen, wijzigen en daarna weer starten?"):
            return

        def go():
            try:
                action()
            except Exception as e:
                messagebox.showerror(APP_NAME, f"Mislukt: {e}")
            self.refresh()
            self.app.srv_start()

        self.app.srv_stop(after=go)

    def _toggle(self, enable, only=None):
        sel = [i for i in (only if only is not None else self._selected()) if i["enabled"] != enable]
        if not sel:
            messagebox.showinfo(APP_NAME, "Vink eerst plugins aan die " + ("uit" if enable else "aan") + " staan.")
            return
        if not enable:
            names = {i["name"].lower() for i in sel}
            broken = sorted({o["name"] for o in self.items.values() if o["enabled"] and o["name"].lower() not in names
                             and any(d.lower() in names for d in o["depend"])})
            if broken and not messagebox.askyesno(
                    APP_NAME, f"Let op: {', '.join(broken)} heeft deze plugin nodig en start dan niet meer goed.\n\nToch uitzetten?"):
                return
        else:
            missing = sorted({m for i in sel for m in i["missing"]})
            if missing and not messagebox.askyesno(
                    APP_NAME, f"Deze plugin heeft {', '.join(missing)} nodig, en dat staat niet aan.\n\nToch aanzetten?"):
                return

        def act():
            for i in sel:
                toggle_plugin(i, enable)
            self.app.log(("Aangezet: " if enable else "Uitgezet: ") + ", ".join(i["name"] for i in sel), "ok")

        if enable:
            try:
                act()
            except OSError as e:
                messagebox.showerror(APP_NAME, f"Aanzetten mislukt: {e}")
                return
            self.refresh()
            self._apply_changes([i["file"][:-9] if i["file"].lower().endswith(".disabled") else i["file"] for i in sel])
        else:
            self._with_server_stopped(f"{len(sel)} plugin(s) uitzetten", act)

    def _remove(self):
        sel = self._selected()
        if not sel:
            return
        if not messagebox.askyesno(APP_NAME, f"{len(sel)} plugin(s) verwijderen?\n\n" + "\n".join(i["file"] for i in sel) +
                                             "\n\nDe bestanden gaan naar een aparte map, dus je kunt ze terugzetten. "
                                             "De instellingen van de plugin (map in plugins/) blijven staan."):
            return
        trash = os.path.join(self.app.backup_root(), "verwijderde_plugins", datetime.now().strftime("%Y%m%d-%H%M%S"))

        def act():
            for i in sel:
                remove_plugin(i, trash)
            self.app.log(f"Verwijderd (verplaatst naar {trash}): " + ", ".join(i["name"] for i in sel), "ok")

        self._with_server_stopped(f"{len(sel)} plugin(s) verwijderen", act)

    def _open_dir(self):
        d = self.pdir()
        if os.path.isdir(d):
            try:
                os.startfile(d)
            except AttributeError:
                webbrowser.open(d)

    # ---------- direct laden met /plm load ----------
    def _plm_toggled(self):
        if self.plm_var.get() and not self.app.cfg.get("plm_ack"):
            if not messagebox.askyesno(
                    APP_NAME, "Op eigen risico.\n\nMet PlugMan(X) kun je een plugin laden terwijl de server draait "
                              "(/plm load <plugin>). Dat werkt niet altijd goed:\n"
                              "• plugins die andere plugins of een herstart nodig hebben kunnen vastlopen of half laden;\n"
                              "• bij uitladen en herladen kan geheugen blijven hangen;\n"
                              "• een herstart blijft de enige betrouwbare manier.\n\n"
                              "Je hebt de plugin PlugManX op de server nodig. Doorgaan?"):
                self.plm_var.set(False)
                return
            self.app.cfg["plm_ack"] = True
        self.app.cfg["plm_load"] = bool(self.plm_var.get())
        save_config(self.app.cfg)

    def _plm_load(self, bases):
        """Stuurt /plm load voor elk bestand (zonder .jar) naar de server."""
        pm = plugman_name(self.items.values()) if self.items else plugman_name(scan_plugins(self.pdir()))
        if not self._server_running():
            messagebox.showinfo(APP_NAME, "De server draait niet. Start hem: dan worden alle plugins vanzelf geladen.")
            return False
        if not pm:
            messagebox.showinfo(APP_NAME, "PlugManX staat niet aan op je server, dus /plm bestaat niet.\n\n"
                                          "Zoek en installeer “PlugManX” op het tabblad Zoeken en herstart daarna één keer.")
            return False
        for b in bases:
            self.app.srv_send(f"plm load {b}")
        self.app.log("Direct laden: " + ", ".join(f"/plm load {b}" for b in bases) + ". Kijk in de console of het gelukt is.", "warn")
        self.after(4000, self.refresh)
        return True

    def _load_selected(self):
        sel = [i for i in self._selected() if i["enabled"]]
        if not sel:
            messagebox.showinfo(APP_NAME, "Selecteer eerst plugins die aan staan.")
            return
        if not messagebox.askyesno(APP_NAME, "Direct laden op eigen risico, zonder herstart.\n\n" +
                                             "\n".join("/plm load " + i["file"][:-4] for i in sel) +
                                             "\n\nAlleen voor plugins die nog niet geladen zijn. Doorgaan?"):
            return
        self._plm_load([i["file"][:-4] for i in sel])

    def _apply_changes(self, files):
        """Nieuwe of aangezette plugins worden pas door de server gebruikt na laden: herstart of /plm load."""
        if not self._server_running():
            self._note("Klaar. De plugin wordt geladen als je de server start.")
            return
        bases = [f[:-4] if f.lower().endswith(".jar") else f for f in files]
        if self.plm_var.get():
            if self._plm_load(bases):
                return
        if messagebox.askyesno(APP_NAME, "De server draait. Een nieuwe plugin wordt pas geladen na een herstart.\n\nNu herstarten?"):
            self.app.srv_stop(restart=True)

    # ---------- zoeken ----------
    def search(self):
        text = self.query_var.get().strip()
        if not text or self.busy:
            return
        self.busy = True
        self.btn_search.config(state="disabled")
        self._note("Bezig met zoeken op Modrinth en Hangar…")
        names, mc, loaders = self._installed_names(), self._mc(), self._loaders()
        self._search_mc = mc
        only = bool(self.compat_var.get())
        if only and not mc:
            only = False
            self._note("Je Minecraft-versie is nog niet ingevuld (tabblad Updates), dus het filter staat niet aan.")
        if not self.items:
            try:
                names = [x["name"] for x in scan_plugins(self.pdir())]
            except Exception:
                names = []

        def work():
            try:
                self.q.put(("results", *search_plugins(text, mc, loaders, names, only_compat=only)))
            except Exception as e:
                self.q.put(("error", f"Zoeken mislukt: {describe_net_error(e)}"))

        threading.Thread(target=work, daemon=True).start()

    def _compat_toggled(self):
        self.app.cfg["plugins_only_compat"] = bool(self.compat_var.get())
        save_config(self.app.cfg)
        if self.query_var.get().strip():
            self.search()

    def _show_results(self, results, info):
        self.res_list, self.res_info = results, info
        self.res_mc = self._search_mc
        if info["concepts"]:
            msg = "Ik snap dit als: " + " / ".join(info["concepts"]) + "."
        elif info["name_like"]:
            msg = "Ik zoek op de naam."
        else:
            msg = "Ik zoek op: " + ", ".join(info["translated"][:6]) + "."
        msg += "  Gezocht op: " + ", ".join(q for q, _w in info["queries"][:6])
        if info.get("only_compat"):
            msg += f"   Filter aan: alleen plugins met een versie voor Minecraft {self.res_mc}."
        if info.get("errors"):
            msg += "   (let op: " + "; ".join(info["errors"]) + ")"
        self.interp_lbl.config(text=msg)
        self.r_key.set("Relevantie")
        self.r_desc = False
        self.btn_rdir.config(text="▲")
        self.res_empty = ""
        if results:
            self._note(f"{len(results)} resultaten.")
        else:
            self._note("Niets gevonden.")
            self.res_empty = ("Niets gevonden.\n\nProbeer andere woorden, de naam van de plugin, of een paar kernwoorden in het Engels "
                              "(bijv. “claim land”, “night skip”)." + ("\nOf zet het filter voor jouw Minecraft-versie uit."
                                                                    if info.get("only_compat") else ""))
        self._render_results()
        self.rcanvas.yview_moveto(0)

    # ---------- installeren ----------
    def install(self, r=None):
        if not r or self.busy:
            return
        if not self.app.folder_var.get().strip() or not os.path.isdir(self.pdir()):
            messagebox.showinfo(APP_NAME, "Kies eerst je servermap (tabblad Updates).")
            return
        if r["installed"] and not messagebox.askyesno(APP_NAME, f"{r['name']} lijkt al geïnstalleerd. Toch opnieuw proberen?"):
            return
        self.busy = True
        self._note(f"Versie zoeken voor {r['name']}…")
        names, mc, loaders, unstable = self._installed_names(), self._mc(), self._loaders(), self.app.unstable_var.get()

        def work():
            try:
                plan, notes = plan_install(r, mc, loaders, names, unstable)
                self.q.put(("plan", r, plan, notes))
            except Exception as e:
                self.q.put(("error", f"Installeren niet mogelijk: {describe_net_error(e)}"))

        threading.Thread(target=work, daemon=True).start()

    def _confirm_plan(self, r, plan, notes):
        mc = self._mc()
        lines = ["Dit wordt gedownload naar de map plugins:", ""]
        for p in plan:
            extra = " (verplichte afhankelijkheid)" if p.get("dep") else ""
            warn = "   ⚠ niet bevestigd voor jouw Minecraft-versie" if mc and not p.get("verified", True) else ""
            lines.append(f"• {p.get('title', r['name'])} {p['version']}  [{p['source']}]{extra}\n   {p['filename']}{warn}")
        if any(p.get("vtype") not in (None, "release") for p in plan):
            lines += ["", "Let op: er is alleen een bèta/alpha-versie."]
        if notes:
            lines += [""] + notes
        lines += ["", "Doorgaan?"]
        if not messagebox.askyesno(APP_NAME, "\n".join(lines)):
            self.busy = False
            self._note("Geannuleerd.")
            return
        self._note("Downloaden…")
        pdir = self.pdir()

        def work():
            try:
                self.q.put(("done", install_plan(plan, pdir), plan))
            except Exception as e:
                self.q.put(("error", f"Downloaden mislukt: {describe_net_error(e)}"))

        threading.Thread(target=work, daemon=True).start()

    # ---------- berichten van achtergrondtaken ----------
    def _poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "results":
                    self.busy = False
                    self.btn_search.config(state="normal")
                    self._show_results(m[1], m[2])
                elif m[0] == "plan":
                    self._confirm_plan(m[1], m[2], m[3])
                elif m[0] == "done":
                    self.busy = False
                    self.app.log("Geïnstalleerd: " + ", ".join(m[1]), "ok")
                    self.refresh()
                    self._note("Geïnstalleerd: " + ", ".join(m[1]))
                    self._apply_changes(m[1])
                elif m[0] == "error":
                    self.busy = False
                    self.btn_search.config(state="normal")
                    self._note(m[1])
                    self.app.log(m[1], "warn")
        except queue.Empty:
            pass
        self.after(120, self._poll)


class MapTab(ttk.Frame):
    """Tabblad Kaart: toont de squaremap-kaart van je server rechtstreeks in het programma (zonder browser).

    Het programma haalt dezelfde tegels (PNG's) op als de squaremap-website, tekent alleen wat in beeld is en doet
    niets zolang het tabblad dicht is. Spelers komen uit squaremap zelf (tiles/players.json)."""
    TILE = 512
    COLORS = ("#ef4444", "#3b82f6", "#22c55e", "#eab308", "#a855f7", "#f97316", "#14b8a6", "#ec4899")
    BG = "#0f172a"
    CACHE_MAX = 220

    def __init__(self, parent, app):
        super().__init__(parent, padding=6)
        self.app = app
        self.url_var = tk.StringVar(value=app.cfg.get("squaremap_url", "http://localhost:8080"))
        self.world_var = tk.StringVar()
        self.status_var, self.coord_var = tk.StringVar(), tk.StringVar()
        self.follow_var = tk.BooleanVar(value=False)
        self.names_var = tk.BooleanVar(value=True)
        self.q = queue.Queue()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.worlds, self.wset = [], {}
        self.cur = None                       # naam van de wereld die getoond wordt
        self.zl, self.cx, self.cz = 3, 0.0, 0.0   # zoomniveau, midden van het beeld (in blokken)
        self.zimgs = {}                       # extra uitgezoomde (vergrote) versies voor het diepste zoomniveau
        self.imgs = {}                        # (wereld, z, x, y) -> PhotoImage of None (lege tegel)
        self.sig = {}                         # (wereld, z, x, y) -> hash van de bytes, om verversen goedkoop te houden
        self.pending = set()
        self.players, self.trails = [], {}
        self.visible, self.online, self.loading = False, False, False
        self._drag, self._moved, self._dirty, self._tok = None, False, True, 0
        self._last_refresh = self._last_players = 0.0
        self._build()

    # ---------- opbouw ----------
    def _btn(self, parent, text, cmd, bg="#e5e7eb", fg="#111827"):
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat",
                         bd=0, padx=9, pady=3, font=("Segoe UI", 9, "bold"), cursor="hand2")

    def _build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 6))
        self.world_cb = ttk.Combobox(bar, textvariable=self.world_var, state="readonly", width=18)
        self.world_cb.pack(side="left")
        self.world_cb.bind("<<ComboboxSelected>>", lambda e: self._pick_world())
        self._btn(bar, "+", lambda: self._zoom(1)).pack(side="left", padx=(6, 0))
        self._btn(bar, "−", lambda: self._zoom(-1)).pack(side="left", padx=(4, 0))
        self._btn(bar, "⌂  Spawn", self.goto_spawn).pack(side="left", padx=(6, 0))
        self._btn(bar, "\U0001F3AF  Alle spelers", self.fit_players, "#2563eb", "white").pack(side="left", padx=(6, 0))
        self._btn(bar, "↻  Vernieuwen", lambda: self.refresh(True)).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(bar, text="Namen", variable=self.names_var, command=self._draw_overlay_only).pack(side="left", padx=(12, 0))
        self.render_btn = tk.Menubutton(bar, text="⚙  Renderen ▾", relief="flat", bd=0, bg="#e5e7eb", padx=9, pady=3,
                                        font=("Segoe UI", 9, "bold"), cursor="hand2")
        m = tk.Menu(self.render_btn, tearoff=0)
        for label, tpl in (("Hele wereld renderen", "fullrender {w}"), ("Alleen rond de spawn (2000 blokken)", "radiusrender {w} 2000"),
                           ("Pauzeer / hervat", "pauserender {w}"), ("Stoppen met renderen", "cancelrender {w}"),
                           ("Instellingen herladen", "reload")):
            m.add_command(label=label, command=lambda t=tpl: self.cmd(t))
        self.render_btn.config(menu=m)
        self.render_btn.pack(side="left", padx=(12, 0))
        tk.Label(bar, textvariable=self.status_var, fg="#6b7280", font=("Segoe UI", 9)).pack(side="right")
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)
        side = ttk.Frame(main, width=250)
        side.pack(side="right", fill="y", padx=(8, 0))
        side.pack_propagate(False)
        ttk.Label(side, text="Spelers op de kaart", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tree = ttk.Treeview(side, columns=("name", "pos"), show="headings", height=12, selectmode="browse")
        self.tree.heading("name", text="Speler")
        self.tree.heading("pos", text="X  Y  Z")
        self.tree.column("name", width=95, anchor="w")
        self.tree.column("pos", width=130, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=(4, 6))
        self.tree.bind("<Double-1>", lambda e: self._goto_selected())
        ttk.Checkbutton(side, text="Volg de geselecteerde speler", variable=self.follow_var).pack(anchor="w")
        ttk.Label(side, text="Adres van de kaart:", foreground="#6b7280").pack(anchor="w", pady=(10, 0))
        e = ttk.Entry(side, textvariable=self.url_var)
        e.pack(fill="x")
        e.bind("<Return>", lambda ev: self._save_url(reload=True))
        e.bind("<FocusOut>", lambda ev: self._save_url())
        self._btn(side, "Open in browser", lambda: webbrowser.open(self.url_var.get())).pack(anchor="w", pady=(6, 0))
        self.cv = tk.Canvas(main, bg=self.BG, highlightthickness=0, cursor="fleur")
        self.cv.pack(side="left", fill="both", expand=True)
        tk.Label(self, textvariable=self.coord_var, anchor="w", fg="#4b5563", font=("Consolas", 9)).pack(fill="x", pady=(4, 0))
        cv = self.cv
        cv.bind("<Configure>", lambda e: self._draw())
        cv.bind("<ButtonPress-1>", lambda e: setattr(self, "_drag", (e.x, e.y)))
        cv.bind("<B1-Motion>", self._motion)
        cv.bind("<ButtonRelease-1>", self._release)
        cv.bind("<Motion>", self._hover)
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            cv.bind(ev, self._wheel)
        cv.bind("<Double-Button-1>", lambda e: self._zoom(1, e.x, e.y))

    # ---------- netwerk (alleen in achtergrondthreads) ----------
    def _get(self, path):
        base = self.url_var.get().strip().rstrip("/")
        try:
            with urllib.request.urlopen(f"{base}/{path}", timeout=5) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            return b"" if e.code == 404 else None
        except Exception:
            return None

    def _save_url(self, reload=False):
        u = self.url_var.get().strip() or "http://localhost:8080"
        if not re.match(r"^https?://", u):
            u = "http://" + u
        self.url_var.set(u)
        if u != self.app.cfg.get("squaremap_url"):
            self.app.cfg["squaremap_url"] = u
            save_config(self.app.cfg)
            reload = True
        if reload:
            self.worlds, self.cur = [], None
            self._clear_tiles()
            self.load_worlds()

    def load_worlds(self):
        if self.loading:
            return
        self.loading = True

        def work():
            raw = self._get("tiles/settings.json")
            out = None
            try:
                data = json.loads(raw.decode("utf-8")) if raw else None
                if data:
                    worlds = sorted(data.get("worlds") or [], key=lambda w: w.get("order", 0))
                    sets = {}
                    for w in worlds:
                        s = self._get(f"tiles/{w['name']}/settings.json")
                        sets[w["name"]] = json.loads(s.decode("utf-8")) if s else {}
                    out = (worlds, sets)
            except Exception:
                out = None
            self.q.put(("worlds", out))

        self.pool.submit(work)

    def fetch_tile(self, key, replace=False):
        if key in self.pending:
            return
        self.pending.add(key)
        w, z, x, y = key

        def work():
            data = self._get(f"tiles/{w}/{z}/{x}_{y}.png")
            self.q.put(("tile", key, data, replace))

        self.pool.submit(work)

    def fetch_players(self):
        def work():
            raw = self._get("tiles/players.json")
            try:
                self.q.put(("players", json.loads(raw.decode("utf-8")) if raw else None))
            except Exception:
                self.q.put(("players", None))

        self.pool.submit(work)

    # ---------- zichtbaar / onzichtbaar ----------
    def on_show(self):
        self.visible = True
        self._tok += 1
        if not self.worlds:
            self.load_worlds()
        self._loop(self._tok)

    def on_hide(self):
        self.visible = False
        self._tok += 1

    def _loop(self, tok):
        """Eén rustige timer, alleen actief zolang het tabblad open is."""
        if tok != self._tok or not self.visible:
            return
        self._drain()
        now = time.time()
        if self.worlds and now - self._last_players > 3:
            self._last_players = now
            self.fetch_players()
        if self.worlds and now - self._last_refresh > 60:
            self.refresh()
        if not self.worlds and not self.loading and now - self._last_players > 5:
            self._last_players = now
            self.load_worlds()
        if self._dirty:
            self._dirty = False
            self._draw()
        self.after(120, lambda: self._loop(tok))

    def refresh(self, force=False):
        self._last_refresh = time.time()
        if force:
            self.sig.clear()
        for key in list(self._view_keys()):
            self.fetch_tile(key, replace=True)

    # ---------- verwerken van antwoorden (hoofdthread) ----------
    def _drain(self):
        t_end = time.time() + 0.02
        while time.time() < t_end:
            try:
                m = self.q.get_nowait()
            except queue.Empty:
                break
            if m[0] == "worlds":
                self.loading = False
                if m[1] is None:
                    self.online = False
                    self.status_var.set("Kaart niet bereikbaar: server uit of squaremap niet actief")
                    self._dirty = True
                    continue
                self.worlds, self.wset = m[1]
                self.online = True
                names = [w.get("display_name") or w["name"] for w in self.worlds]
                self.world_cb.config(values=names)
                if self.worlds and self.cur not in [w["name"] for w in self.worlds]:
                    first = next((w for w in self.worlds if w.get("type") == "normal"), self.worlds[0])
                    self._set_world(first["name"])
                self.status_var.set("")
            elif m[0] == "tile":
                self._tile(*m[1:])
            elif m[0] == "players":
                self._players(m[1])

    def _tile(self, key, data, replace):
        self.pending.discard(key)
        if data is None:
            return  # netwerkfout: later opnieuw proberen
        sig = hash(data)
        if replace and self.sig.get(key) == sig:
            return
        self.sig[key] = sig
        old = self.imgs.pop(key, None)
        if not data:
            self.imgs[key] = None
        else:
            try:
                self.imgs[key] = tk.PhotoImage(data=base64.b64encode(data).decode("ascii"))
                for zk in [k for k in self.zimgs if k[0] == key]:
                    del self.zimgs[zk]
            except tk.TclError:
                self.imgs[key] = None
        if len(self.imgs) > self.CACHE_MAX:
            keep = set(self._view_keys())
            for k in [k for k in self.imgs if k not in keep][:len(self.imgs) - self.CACHE_MAX + 40]:
                self.imgs.pop(k, None)
                self.sig.pop(k, None)
                for zk in [z for z in self.zimgs if z[0] == k]:
                    del self.zimgs[zk]
        self._dirty = True
        del old

    def _players(self, data):
        if data is None:
            return
        self.players = [p for p in (data.get("players") or []) if isinstance(p, dict) and "x" in p and "z" in p]
        names = set()
        for p in self.players:
            n = p.get("name", "?")
            names.add(n)
            tr = self.trails.setdefault(n, deque(maxlen=60))
            if not tr or abs(tr[-1][0] - p["x"]) + abs(tr[-1][1] - p["z"]) >= 3:
                tr.append((p["x"], p["z"], p.get("world")))
        for n in list(self.trails):
            if n not in names:
                del self.trails[n]
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for p in sorted(self.players, key=lambda p: p.get("name", "").lower()):
            self.tree.insert("", "end", iid=p["name"], values=(p["name"], f"{p['x']}  {p.get('y', 0)}  {p['z']}"))
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0])
        if self.follow_var.get() and sel:
            p = next((p for p in self.players if p.get("name") == sel[0]), None)
            if p:
                self.cx, self.cz = float(p["x"]), float(p["z"])
                self._dirty = True
        self._draw_overlay_only()

    # ---------- wereld en zoom ----------
    def _max_native(self, world):
        return int((self.wset.get(world) or {}).get("zoom", {}).get("max", 3))

    def _max_zoom(self):
        z = (self.wset.get(self.cur) or {}).get("zoom", {})
        return int(z.get("max", 3)) + int(z.get("extra", 1))

    def _clear_tiles(self):
        self.imgs.clear()
        self.zimgs.clear()
        self.sig.clear()
        self.pending.clear()
        self._dirty = True

    def _set_world(self, name):
        self.cur = name
        w = next((w for w in self.worlds if w["name"] == name), None)
        if w:
            self.world_var.set(w.get("display_name") or name)
        s = self.wset.get(name) or {}
        z = s.get("zoom", {})
        self.zl = int(z.get("def", min(2, int(z.get("max", 3)))))
        sp = s.get("spawn") or {}
        self.cx, self.cz = float(sp.get("x", 0)), float(sp.get("z", 0))
        self._clear_tiles()

    def _pick_world(self):
        label = self.world_var.get()
        for w in self.worlds:
            if (w.get("display_name") or w["name"]) == label:
                self._set_world(w["name"])
                break

    def goto_spawn(self):
        sp = (self.wset.get(self.cur) or {}).get("spawn") or {}
        self.cx, self.cz = float(sp.get("x", 0)), float(sp.get("z", 0))
        self._dirty = True

    def fit_players(self):
        pts = [(p["x"], p["z"]) for p in self.players if p.get("world") == self.cur]
        if not pts:
            self.status_var.set("Geen spelers in deze wereld")
            return
        xs, zs = [a for a, _ in pts], [b for _, b in pts]
        self.cx, self.cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
        W, H = max(self.cv.winfo_width(), 300), max(self.cv.winfo_height(), 200)
        span = max(max(xs) - min(xs), max(zs) - min(zs), 64) * 1.4
        mx = self._max_native(self.cur)
        zl = mx
        while zl > 0 and span * 2 ** (zl - mx) > min(W, H):
            zl -= 1
        self.zl = zl
        self._dirty = True

    def _goto_selected(self):
        sel = self.tree.selection()
        p = next((p for p in self.players if sel and p.get("name") == sel[0]), None)
        if p:
            if p.get("world") != self.cur and p.get("world") in self.wset:
                self._set_world(p["world"])
            self.cx, self.cz = float(p["x"]), float(p["z"])
            self.zl = max(self.zl, self._max_native(self.cur) - 1)
            self._dirty = True

    def _scale(self):
        return 2.0 ** (self.zl - self._max_native(self.cur))  # pixels per blok

    def _zoom(self, d, mx=None, my=None):
        nz = max(0, min(self._max_zoom(), self.zl + d))
        if nz == self.zl:
            return
        W, H = self.cv.winfo_width(), self.cv.winfo_height()
        old = self._scale()
        if mx is not None:
            wx, wz = self.cx + (mx - W / 2) / old, self.cz + (my - H / 2) / old
        self.zl = nz
        if mx is not None:
            new = self._scale()
            self.cx, self.cz = wx - (mx - W / 2) / new, wz - (my - H / 2) / new
        self._draw()

    def _wheel(self, ev):
        self._zoom(1 if (getattr(ev, "num", 0) == 4 or getattr(ev, "delta", 0) > 0) else -1, ev.x, ev.y)

    # ---------- tekenen ----------
    def _geometry(self):
        mx = self._max_native(self.cur)
        native = min(self.zl, mx)
        extra = self.zl - native
        span = self.TILE * 2 ** (mx - native)     # blokken per tegel
        return native, span, 2.0 ** (self.zl - mx)

    def _view_keys(self, margin=0.5):
        if not self.cur or self.cv.winfo_width() < 20:
            return []
        native, span, s = self._geometry()
        W, H = self.cv.winfo_width(), self.cv.winfo_height()
        x0, x1 = self.cx - W / 2 / s - span * margin, self.cx + W / 2 / s + span * margin
        z0, z1 = self.cz - H / 2 / s - span * margin, self.cz + H / 2 / s + span * margin
        out = []
        for ty in range(math.floor(z0 / span), math.floor(z1 / span) + 1):
            for tx in range(math.floor(x0 / span), math.floor(x1 / span) + 1):
                out.append((self.cur, native, tx, ty))  # voorbij het diepste niveau bestaan geen tegels: vergroot de tegels van het diepste
        return out

    def _draw(self):
        cv = self.cv
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 20 or H < 20:
            return
        cv.delete("all")
        if not self.cur:
            cv.create_text(W / 2, H / 2, fill="#94a3b8", font=("Segoe UI", 12), justify="center",
                           text=("Kaart laden…" if self.loading else
                                 "Kaart niet bereikbaar.\nStart de server en controleer of squaremap actief is\n(adres rechts in het paneel)."))
            return
        native, span, s = self._geometry()
        extra = self.zl - native
        P = self.TILE * 2 ** extra                       # tegelgrootte op het scherm in pixels
        ox, oy = round(W / 2 - self.cx * s), round(H / 2 - self.cz * s)
        t_end = time.time() + 0.03
        for key in sorted(self._view_keys(0.0), key=lambda k: abs(k[2] * span + span / 2 - self.cx) + abs(k[3] * span + span / 2 - self.cz)):
            if key in self.imgs:
                img = self.imgs[key]
                if img is not None and extra > 0:
                    img = self._zoomed(key, extra, t_end)
                if img is not None:
                    # vaste hele pixels per tegel: anders kunnen naast elkaar liggende tegels door afronden 1 pixel uit elkaar vallen
                    cv.create_image(ox + key[2] * P, oy + key[3] * P, anchor="nw", image=img, tags="t")
            else:
                self.fetch_tile(key)
        for key in self._view_keys(0.5 if extra == 0 else 0.0):  # alvast net buiten beeld ophalen, zodat slepen soepel blijft
            if key not in self.imgs:
                self.fetch_tile(key)
        sp = (self.wset.get(self.cur) or {}).get("spawn")
        if sp:
            sx, sy = self._w2c(sp.get("x", 0), sp.get("z", 0))
            cv.create_text(sx, sy, text="⌂", fill="#fde047", font=("Segoe UI", 15, "bold"), tags="t")
        self._draw_overlay()

    def _zoomed(self, key, extra, t_end):
        """Vergrote tegel (2x, 4x) voor de diepste zoomniveaus; maximaal een paar tegelijk, in kleine happen."""
        zk = (key, extra)
        img = self.zimgs.get(zk)
        if img is None:
            if time.time() > t_end:
                self._dirty = True  # de rest volgt in de volgende ronde
                return None
            f = 2 ** extra
            img = self.imgs[key].zoom(f, f)
            if len(self.zimgs) > 14:
                keep = {(k, extra) for k in self._view_keys(0.0)}
                for old in [z for z in self.zimgs if z not in keep][:10]:
                    del self.zimgs[old]
            self.zimgs[zk] = img
        return img

    def _draw_overlay_only(self):
        if self.cur and self.cv.winfo_width() > 20:
            self.cv.delete("o")
            self._draw_overlay()

    def _w2c(self, x, z):
        s = self._scale()
        return self.cv.winfo_width() / 2 + (x - self.cx) * s, self.cv.winfo_height() / 2 + (z - self.cz) * s

    def _color(self, name):
        return self.COLORS[zlib.crc32(name.encode("utf-8")) % len(self.COLORS)]

    def _draw_overlay(self):
        cv = self.cv
        W, H = cv.winfo_width(), cv.winfo_height()
        for n, tr in self.trails.items():
            pts = [self._w2c(x, z) for x, z, w in tr if w == self.cur]
            if len(pts) >= 2:
                cv.create_line(*[v for p in pts for v in p], fill=self._color(n), width=2, dash=(3, 2), tags="o")
        for p in self.players:
            if p.get("world") != self.cur:
                continue
            px, py = self._w2c(p["x"], p["z"])
            if px < -40 or py < -40 or px > W + 40 or py > H + 40:
                continue
            col = self._color(p.get("name", ""))
            if "yaw" in p:
                a = math.radians(p["yaw"])
                cv.create_line(px, py, px - math.sin(a) * 18, py + math.cos(a) * 18, fill="white", width=3, arrow="last", tags="o")
            cv.create_oval(px - 7, py - 7, px + 7, py + 7, fill=col, outline="white", width=2, tags="o")
            if self.names_var.get():
                t = cv.create_text(px, py - 18, text=p.get("name", ""), fill="white", font=("Segoe UI", 9, "bold"), tags="o")
                bb = cv.bbox(t)
                r = cv.create_rectangle(bb[0] - 4, bb[1] - 1, bb[2] + 4, bb[3] + 1, fill="#111827", outline=col, tags="o")
                cv.tag_lower(r, t)

    # ---------- bediening ----------
    def _motion(self, ev):
        if not self._drag:
            return
        dx, dy = ev.x - self._drag[0], ev.y - self._drag[1]
        self._drag = (ev.x, ev.y)
        if dx or dy:
            s = self._scale()
            self.cx -= dx / s
            self.cz -= dy / s
            self.cv.move("all", dx, dy)  # in één keer verschuiven in plaats van opnieuw tekenen
            self._moved = True
            self.follow_var.set(False)

    def _release(self, ev):
        self._drag = None
        if self._moved:
            self._moved = False
            self._draw()

    def _hover(self, ev):
        if not self.cur:
            return
        s = self._scale()
        W, H = self.cv.winfo_width(), self.cv.winfo_height()
        wx, wz = self.cx + (ev.x - W / 2) / s, self.cz + (ev.y - H / 2) / s
        txt = f"X {wx:7.0f}   Z {wz:7.0f}     zoom {self.zl}/{self._max_zoom()}"
        native, span, _s = self._geometry()
        tk_ = (self.cur, native, math.floor(wx / span), math.floor(wz / span))
        st = "geen antwoord" if tk_ not in self.imgs else ("bestaat niet op de server (404)" if self.imgs[tk_] is None else "geladen")
        txt += f"     tegel {native}/{tk_[2]}_{tk_[3]}: {st}"
        for p in self.players:
            if p.get("world") == self.cur:
                px, py = self._w2c(p["x"], p["z"])
                if abs(px - ev.x) < 12 and abs(py - ev.y) < 12:
                    txt += f"     ● {p.get('name')}  ({p['x']}, {p.get('y', 0)}, {p['z']})"
        self.coord_var.set(txt)

    def cmd(self, template):
        app = self.app
        if not app.srv_running() or app.srv_state != "online":
            self.status_var.set("De server draait niet")
            return
        w = self.cur or ""
        if "{w}" in template and not w:
            self.status_var.set("Kaart nog niet geladen")
            return
        w = w.replace("_", ":", 1)  # op de website heet de wereld minecraft_overworld, in de commando's minecraft:overworld
        c = "map " + template.format(w=w)
        if app.srv_send(c):
            self.status_var.set(f"Verstuurd: {c}")


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
        self._tab_state, self._plug_cache = None, None
        self.reach_host_var = tk.StringVar(value=str(c.get("reach_host", "")))
        self.reach_port_var = tk.IntVar(value=int(c.get("reach_port", 25565)))
        self.reach_bed_var = tk.BooleanVar(value=bool(c.get("reach_check_bedrock", False)))
        self.reach_bport_var = tk.IntVar(value=int(c.get("reach_bedrock_port", 19132)))
        self.reach_lport_var = tk.IntVar(value=25565)
        self.reach_auto_var = tk.BooleanVar(value=bool(c.get("reach_auto", False)))
        self._net_busy, self._net_img = False, None
        self._temp_busy = self._temp_warned = self._upd_busy = False
        self._temp_fail, self._upd, self._upd_prompted = 0, None, None
        self.sv_lbl = {}

        self._style()
        self._build()
        self.apply_settings()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<F5>", lambda e: self.on_check_all())
        self.after(80, self._poll)
        self.after(2000, self._stats_tick)
        self.after(3000, self._temp_tick)
        self.after(5000, self._selfupd_startup)
        self.bind("<FocusIn>", self._selfupd_focus)
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
        style.configure("TNotebook.Tab", padding=(10, 3), font=("Segoe UI", 9))
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
        self.btn_selfupd = tk.Button(header, text="⬆  Update", command=self._selfupd_ask, bg="#d97706", fg="white",
                                     activebackground="#b45309", activeforeground="white", relief="flat", bd=0,
                                     padx=12, pady=5, font=("Segoe UI", 10, "bold"), cursor="hand2")
        body = ttk.Frame(self.nb, padding=10)
        self.tab_srv = ttk.Frame(self.nb, padding=10)
        self.tab_net = ttk.Frame(self.nb, padding=10)
        self.tab_plug = PluginsTab(self.nb, self)
        self.tab_map = MapTab(self.nb, self)
        self.nb.add(self.tab_srv, text="🖥  Server")
        self.nb.add(self.tab_plug, text="🧩  Plugins")
        self.nb.add(self.tab_map, text="🗺  Kaart")
        self.nb.add(body, text="🔧  Updates")
        self.nb.add(self.tab_net, text="🌐  Bereikbaarheid")
        self._build_server_tab(self.tab_srv)
        self._build_net_tab(self.tab_net)
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)
        self.after(300, self._spark_anim)
        self.after(700, self._upd_tab_blink)

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
        elif k == "temp":
            self._temp_got(m[1])
        elif k == "selfupd":
            self._selfupd_result(m[1], m[2], m[3])
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
                                          ("ram", "Geheugen"), ("tps", "TPS (1 min)"), ("players", "Spelers"),
                                          ("temp", "Laptop-temp."))):
            self.sv[key] = tk.StringVar(value="-")
            ttk.Label(st, text=label + ":").grid(row=i, column=0, sticky="w", pady=1)
            self.sv_lbl[key] = ttk.Label(st, textvariable=self.sv[key], font=("Segoe UI", 10, "bold"))
            self.sv_lbl[key].grid(row=i, column=1, sticky="w", padx=(10, 0))
        self.psutil_frame = None
        if psutil is None:
            hf = ttk.Frame(st)
            hf.grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))
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
        self.spark_temp = Spark(gc, "Temperatuur", "#f87171", lo=0, hi=110, unit=" °C", min_span=10)
        self.spark_ram.hi_fn = lambda: self.srv_xmx
        for w in (self.spark_cpu, self.spark_ram, self.spark_tps, self.spark_temp):
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
        self.cmd_entry.bind("<Tab>", lambda e: self._tab_complete(1))
        self.cmd_entry.bind("<Shift-Tab>", lambda e: self._tab_complete(-1))
        self.cmd_entry.bind("<ISO_Left_Tab>", lambda e: self._tab_complete(-1))
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

    # ---------- Tab-aanvulling in het commandoveld ----------
    def _plugin_cmds(self):
        """(commando's, pluginnamen) uit de plugins-map; 2 minuten bewaard."""
        pdir = os.path.join(self.folder_var.get().strip(), "plugins")
        c = self._plug_cache
        if c and c[0] == pdir and time.time() - c[1] < 120:
            return c[2], c[3]
        cmds, names = [], []
        try:
            for it in scan_plugins(pdir):
                if it["enabled"]:
                    cmds += it["commands"]
                    names += [it["name"]]
                names.append(it["file"].split(".jar")[0])
        except Exception:
            pass
        self._plug_cache = (pdir, time.time(), sorted(set(cmds)), sorted(set(names), key=str.lower))
        return self._plug_cache[2], self._plug_cache[3]

    def _tab_complete(self, direction=1):
        text = self.cmd_var.get()
        st = self._tab_state
        if st and text == st["cur"]:
            st["i"] = (st["i"] + direction) % len(st["cands"])
        else:
            cmds, plugs = self._plugin_cmds()
            cands = complete_command(text, sorted(set(VANILLA_CMDS) | set(cmds)),
                                     sorted(self.player_names, key=str.lower), plugs)
            if not cands:
                return "break"
            st = self._tab_state = {"cands": cands, "i": 0 if direction > 0 else len(cands) - 1, "cur": None}
            if len(cands) > 1:
                shown = ", ".join(c.split(" ")[-1] for c in cands[:40]) + (" …" if len(cands) > 40 else "")
                self._console_add(f"Mogelijkheden: {shown}", own=True)
                cp = os.path.commonprefix(cands)
                if len(cp) > len(text):  # eerst aanvullen tot het gemeenschappelijke stuk
                    st["cur"], st["i"] = cp, -1 if direction > 0 else 0
                    self.cmd_var.set(cp)
                    self.cmd_entry.icursor("end")
                    return "break"
        new = st["cands"][st["i"]]
        st["cur"] = new
        self.cmd_var.set(new)
        self.cmd_entry.icursor("end")
        return "break"

    def _spark_anim(self):
        """Laat de grafieken doorlopen (ca. 20x per seconde), maar alleen als ze in beeld zijn."""
        try:
            if self.state() != "iconic" and self.nb.select() == str(self.tab_srv):
                for sk in (self.spark_cpu, self.spark_ram, self.spark_tps, self.spark_temp):
                    if sk.data:
                        sk.redraw()
        except tk.TclError:
            pass
        self.after(50, self._spark_anim)

    def _upd_tab_blink(self):
        """Updates-tabje valt op (knippert + aantal) zodra er een plugin- of Paper-update is."""
        try:
            n = sum(1 for r in self.rows.values() if r.get("state") == "update")
            if str(self.paper_label.cget("text")).startswith("⬆"):
                n += 1
            if n:
                self._blink = not getattr(self, "_blink", False)
                txt = f"{'🔴' if self._blink else '🟠'}  Updates ({n})"
            else:
                txt = "🔧  Updates"
            if txt != getattr(self, "_upd_txt", None):
                self._upd_txt = txt
                self.nb.tab(self.nb.index(self.nb.tabs()[3]), text=txt)
        except tk.TclError:
            pass
        self.after(700, self._upd_tab_blink)

    def _tab_changed(self, _e=None):
        try:
            cur = self.nb.select()
            if cur == str(self.tab_plug):
                self.tab_plug.on_show()
            if cur == str(self.tab_map):
                self.tab_map.on_show()
            else:
                self.tab_map.on_hide()
        except tk.TclError:
            pass

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
        gm = re.search(r"Started Geyser on (?:UDP )?port (\d+)", msg)
        if gm and gm.group(1).isdigit() and 0 < int(gm.group(1)) < 65536:
            if int(gm.group(1)) != int_var(self.reach_bport_var, 19132):
                self.reach_bport_var.set(int(gm.group(1)))
                self.log(f"Geyser luistert op UDP-poort {gm.group(1)}: Bedrock-poort bij Bereikbaarheid aangepast.", "info")
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
        for sk in (self.spark_cpu, self.spark_ram, self.spark_tps, self.spark_temp):
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
        ttk.Label(r, text="De controle van buitenaf vraagt tegelijk mcstatus.io, mcsrvstat.us en minetools.eu om je server "
                          "vanaf internet te bereiken; één 'online' is genoeg. 'Mijn IP opzoeken' gebruikt api.ipify.org.",
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
        det = detect_geyser_port(self.folder_var.get().strip(), jport) if self.reach_bed_var.get() else None
        if det and det[0] != bport:
            bport = det[0]
            self.reach_bport_var.set(bport)
            self.log(f"Bedrock-poort aangepast naar {bport} (gelezen uit {det[1]}).", "info")
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
        self._nn_mode = geyser_transport(self.folder_var.get().strip()) if self.reach_bed_var.get() else None
        threading.Thread(target=self._net_worker, daemon=True,
                         args=(host, jport, local_only, bool(self.reach_bed_var.get()), bport, lport,
                               self.srv_state == "online", silent)).start()

    def _net_worker(self, host, jport, local_only, bed, bport, lport, srv_online, silent):
        res = {"t": datetime.now().strftime("%H:%M:%S"), "local_only": local_only, "silent": silent,
               "host": host, "jport": jport, "bport": bport, "lport": lport}
        try:
            if not local_only:
                try:
                    res["ext"] = ext_status(host, jport)
                except Exception as e:
                    res["ext_err"] = describe_net_error(e)
                if bed and getattr(self, "_nn_mode", None) == "nethernet":
                    res["nn"] = {"loc": tcp_open("127.0.0.1", bport), "own": tcp_open(host, bport, 4)}
                    bed = False
                if bed:
                    try:
                        raknet_ping("127.0.0.1", bport, timeout=1.5)
                    except Exception:
                        found, ports = find_geyser_port(bport)
                        res["udp_ports"] = ports
                        if found:
                            res["bed_found"] = found
                            bport = res["bport"] = found
                    try:
                        res["bed"] = ext_status(host, bport, bedrock=True)
                    except Exception as e:
                        res["bed_err"] = describe_net_error(e)
                    if not (res.get("bed") and res["bed"]["online"]):
                        for lip in lan_ips():
                            try:
                                res["bed_lan"] = (lip, raknet_ping(lip, bport, timeout=1.5))
                                break
                            except Exception:
                                pass
                        for key, h in (("bed_loc", "localhost"), ("bed_own", host)):
                            try:
                                res[key] = raknet_ping(h, bport)
                            except Exception as e:
                                res[key + "_err"] = describe_net_error(e) if not isinstance(e, socket.timeout) else "geen antwoord"
            if not local_only and "ext" in res and not res["ext"]["online"]:
                try:
                    res["pubip"] = fetch_public_ip()
                except Exception:
                    pass
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
                parts.append(f"Bron: van buitenaf gecontroleerd om {res['t']} via {card.get('src', '?')}"
                             + (f" (resultaat {age // 60} min {age % 60} s oud)" if age else ""))
            else:
                parts.append(f"Bron: lokaal gecontroleerd om {res['t']} (127.0.0.1:{res['lport']}, {card['ms']} ms)")
            self.net_info.config(text="\n".join(parts))
            self._net_set_icon(card.get("icon") or (self._local_icon_data() if card is loc else None))
        else:
            self.net_motd.config(text="Geen server gevonden")
            self.net_info.config(text="")
            self._net_set_icon(None)
        if res.get("bed_found") and self.reach_bport_var.get() != res["bed_found"]:
            self.reach_bport_var.set(res["bed_found"])
        bl, bo = res.get("bed_loc"), res.get("bed_own")
        nn = res.get("nn")
        if nn:
            L = [f"Bedrock (Geyser): staat op NetherNet (poort {res['bport']}). De ping-test en externe diensten werken hier niet "
                 "meer: die gebruiken het oude RakNet."]
            L.append("Naam en motd in de serverlijst lopen via TCP naar Geyser. Zet de poort dus voor TCP én UDP open.")
            L.append(f"TCP {res['bport']} lokaal: " + ("✔ open." if nn["loc"] else "✖ gesloten: luistert Geyser wel op TCP?"))
            L.append(f"TCP {res['bport']} via {res['host']}: " + ("✔ bereikbaar." if nn["own"] else
                     "✖ niet bereikbaar. Router: stuur TCP 19132 ook door (niet alleen UDP) en sta het toe in de Windows Firewall."))
            if nn["loc"] and nn["own"]:
                self.net_bed.config(fg="#059669", justify="left",
                                    text=f"Bedrock (Geyser): ✔ bereikbaar op {res['host']}:{res['bport']}")
            else:
                self.net_bed.config(fg="#d97706", text="\n".join(L), justify="left")
        elif bed and not bed["online"]:
            tried = ", ".join(f"{n} ({'online' if o else 'offline' if o is not None else 'fout'})" for n, o in bed.get("tried", []))
            lines = [f"Bedrock (Geyser): ✖ de controlediensten zien hem niet op UDP-poort {res['bport']}."]
            listening = res["bport"] in (res.get("udp_ports") or [])
            if listening:
                lines = [f"Bedrock (Geyser): ⚠ draait en luistert op UDP-poort {res['bport']} (Java heeft de poort open), "
                         "maar de ping-test krijgt geen antwoord.",
                         "Dat zegt weinig: Geyser kan pings negeren. Verbindt Bedrock bij jou wel, dan werkt het gewoon."]
            if res.get("bed_found"):
                lines.append(f"Geyser gevonden op UDP-poort {res['bed_found']} (automatisch ingesteld). "
                             "Zet in je router de UDP-doorsturing op die poort.")
            elif res.get("udp_ports") is not None and not listening:
                lines.append("Java heeft geen UDP-poort open die op Bedrock antwoordt" +
                             (f" (open: {', '.join(map(str, res['udp_ports']))})." if res["udp_ports"] else
                              " (er is helemaal geen UDP-poort van Java open: draait Geyser wel? Bij lazymc slaapt de server)."))
            lines.append("Lokaal: " + (f"✔ Geyser antwoordt op deze pc ({bl['ms']} ms)." if bl else
                                      f"✖ geen antwoord op 127.0.0.1:{res['bport']} ({res.get('bed_loc_err', '?')}). "
                                      "Draait Geyser en klopt de poort in config.yml?"))
            lines.append(f"Via {res['host']}: " + (f"✔ antwoordt vanaf deze pc ({bo['ms']} ms)." if bo else
                                                   f"✖ geen antwoord ({res.get('bed_own_err', '?')})."))
            if res.get("bed_lan") and not bl:
                lines.append(f"✔ Geyser antwoordt wél op je netwerk-adres {res['bed_lan'][0]} (niet op 127.0.0.1): "
                             "Geyser is aan dat adres gebonden. Dat is prima voor Bedrock zelf.")
            if bl and not bo:
                lines.append("→ UDP-poort doorsturen in je router en toestaan in de firewall ontbreekt waarschijnlijk.")
            elif bl and bo:
                lines.append("→ Geyser draait en je domein bereikt hem. De diensten kunnen een oud 'offline' bewaren of UDP "
                             "van buiten niet doorkrijgen. Test ook met een telefoon via mobiel internet.")
            if tried:
                lines.append("Geraadpleegd: " + tried + ".")
            self.net_bed.config(fg="#d97706" if ((bl and bo) or listening) else "#b91c1c", text="\n".join(lines), justify="left")
        elif bed:
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

    # ================= Temperatuur =================
    def _temp_tick(self):
        if not self.cfg.get("temp_enabled", True):
            self.sv["temp"].set("uit")
            self.after(10000, self._temp_tick)
            return
        if self._temp_busy:
            self.after(3000, self._temp_tick)
            return
        self._temp_busy = True

        def work():
            try:
                r = read_temperature()
            except Exception:
                r = None
            self.q.put(("temp", r))

        threading.Thread(target=work, daemon=True).start()

    def _temp_got(self, r):
        self._temp_busy = False
        try:
            secs = min(max(int(self.cfg.get("temp_secs", 10)), 2), 300)
            warn = int(self.cfg.get("temp_warn", 85))
        except (TypeError, ValueError):
            secs, warn = 10, 85
        if r:
            self._temp_fail = 0
            v = r["value"]
            self.sv["temp"].set(f"{v:.0f} °C  ({r['label']})")
            self.sv_lbl["temp"].config(foreground="#b91c1c" if v >= warn else ("#d97706" if v >= warn - 10 else ""))
            self.spark_temp.add(v)
            if v >= warn and not self._temp_warned:
                self._temp_warned = True
                self.log(f"Let op: de temperatuur is {v:.0f} °C (waarschuwing vanaf {warn} °C).", "warn")
            elif v < warn - 5:
                self._temp_warned = False
        else:
            self._temp_fail += 1
            self.sv["temp"].set("geen sensor")
            if self._temp_fail == 3:
                self.log("Geen temperatuursensor gevonden. Zie Instellingen → Grafieken voor de mogelijkheden; "
                         "ik probeer het daarna nog maar eens per 2 minuten.", "warn")
        self.after((120 if self._temp_fail >= 3 else secs) * 1000, self._temp_tick)

    # ================= Programma-update =================
    def _selfupd_startup(self):
        if self.cfg.get("selfupdate_check", True) and (self.cfg.get("update_url") or "").strip():
            self.selfupdate_check()
        self.after(5 * 60 * 1000, self._selfupd_startup)  # elke 5 minuten kijken of er een nieuwe versie is

    def _selfupd_focus(self, _e=None):
        """Als je het venster weer actief maakt (en de laatste controle > 1 minuut geleden is) meteen even kijken."""
        if (_e is None or _e.widget is self) and time.time() - getattr(self, "_upd_last", 0) > 300 \
                and self.cfg.get("selfupdate_check", True) and (self.cfg.get("update_url") or "").strip():
            self.selfupdate_check()

    def selfupdate_check(self, manual=False):
        url = (self.cfg.get("update_url") or "").strip()
        if not url:
            if manual:
                messagebox.showinfo(APP_NAME, "Vul eerst een update-link in bij Instellingen → Programma-update.")
            return
        if self._upd_busy:
            return
        self._upd_busy = True
        self._upd_last = time.time()

        def work():
            try:
                self.q.put(("selfupd", fetch_update(url), None, manual))
            except Exception as e:
                self.q.put(("selfupd", None, describe_net_error(e), manual))

        threading.Thread(target=work, daemon=True).start()

    def _selfupd_result(self, info, err, manual):
        self._upd_busy = False
        if err:
            if manual or not getattr(self, "_upd_err_logged", False):
                self.log(f"Programma-update controleren mislukt: {err}", "warn")
            self._upd_err_logged = True
            if manual:
                messagebox.showwarning(APP_NAME, f"Controleren op een programma-update is mislukt:\n{err}")
            return
        if not is_newer(info["version"], APP_VERSION):
            self._upd = None
            self.btn_selfupd.pack_forget()
            self._upd_err_logged = False
            if manual or not getattr(self, "_upd_uptodate_logged", False):
                self.log(f"Het programma is up-to-date (versie {APP_VERSION}).", "ok")
                self._upd_uptodate_logged = True
            if manual:
                messagebox.showinfo(APP_NAME, f"Je hebt de nieuwste versie ({APP_VERSION}).")
            return
        self._upd = info
        self.btn_selfupd.config(text=f"⬆  Update {info['version']}")
        self.btn_selfupd.pack(side="right", padx=(0, 6), pady=10)
        self.log(f"Nieuwe versie van het programma beschikbaar: {info['version']} (jij hebt {APP_VERSION}).", "warn")
        if self.cfg.get("selfupdate_auto") and not manual:
            self.selfupdate_install()
        elif manual or self._upd_prompted != info["version"]:
            self._selfupd_ask()

    def _selfupd_ask(self):
        info = self._upd
        if not info:
            return
        self._upd_prompted = info["version"]
        notes = changelog_since(info["text"], APP_VERSION)
        if messagebox.askyesno(APP_NAME, f"Nieuwe versie {info['version']} beschikbaar (jij hebt {APP_VERSION}).\n\n"
                                         + (notes + "\n\n" if notes else "") + "Nu installeren?"):
            self.selfupdate_install()

    def selfupdate_install(self):
        info = self._upd
        if not info:
            return
        if getattr(sys, "frozen", False):
            messagebox.showinfo(APP_NAME, "Automatisch bijwerken werkt alleen als je het .py-bestand draait. Download het "
                                          "nieuwe bestand en bouw de .exe opnieuw.")
            return
        script = os.path.abspath(__file__)
        try:
            bak = install_update_file(script, info["text"], os.path.join(app_dir(), "programma_backups"), APP_VERSION)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Installeren van de update is mislukt:\n{e}")
            return
        self._upd = None
        self.btn_selfupd.pack_forget()
        notes = changelog_since(info["text"], APP_VERSION)
        lines = notes.splitlines()
        notes = "\n".join(lines[:12]) + (f"\n… en nog {len(lines) - 12} meer" if len(lines) > 12 else "")
        self.log(f"Programma bijgewerkt naar versie {info['version']}. De vorige versie staat in {bak}", "ok")
        for ln in lines:
            self.log("Nieuw: " + ln.lstrip("• "), "info")
        if messagebox.askyesno(APP_NAME, f"Versie {info['version']} is geïnstalleerd.\n\n"
                                         + (f"Wat is er nieuw:\n{notes}\n\n" if notes else "") + "Nu herstarten om hem te gebruiken?"
                                         + ("\n(De server wordt eerst veilig gestopt.)" if self.srv_running() else "")):
            self._restart_self()

    def _restart_self(self):
        if self.srv_running():
            self._stop_blocking()
        self._cleanup_tmp()
        self._save_cfg()
        try:
            exe = sys.executable
            pw = os.path.join(os.path.dirname(exe), "pythonw.exe")
            if os.name == "nt" and os.path.exists(pw):
                exe = pw  # herstarten zonder zwart consolevenster
            subprocess.Popen([exe, os.path.abspath(__file__)] + sys.argv[1:], cwd=app_dir(), close_fds=True)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Herstarten mislukt: {e}\nStart het programma zelf opnieuw.")
            return
        self.destroy()

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
                     "reach_bedrock_port", "reach_auto", "plm_load", "plm_ack", "plugins_only_compat", "squaremap_url"):
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
        self._tab_update(nb)
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
        self._sep(f, 4)
        self._check(f, "Temperatuur van de laptop meten en tonen", self.v["temp_enabled"], 5)
        self._spin(f, "Meten elke:", "temp_secs", 6, 2, 300, "seconden")
        self._spin(f, "Waarschuwen vanaf:", "temp_warn", 7, 50, 110, "°C (rood + melding in het logboek)")
        self._hint(f, "Zonder extra software leest het programma de 'thermal zone'-temperatuur van Windows. Niet elke "
                      "laptop levert die, en het is niet altijd de echte CPU-temperatuur. Voor de nauwkeurige "
                      "CPU-temperatuur: start LibreHardwareMonitor (als beheerder) en laat hem openstaan; het "
                      "programma gebruikt die dan automatisch.", 8)

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

    def _tab_update(self, nb):
        f = self._frame(nb, "Programma-update")
        ttk.Label(f, text=f"Huidige versie: {APP_VERSION}", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(f, text="Link naar de nieuwste versie:").grid(row=1, column=0, sticky="w", pady=(10, 2))
        ttk.Entry(f, textvariable=self.v["update_url"]).grid(row=1, column=1, columnspan=2, sticky="ew", padx=6,
                                                             pady=(10, 2))
        self._hint(f, "Bijvoorbeeld de link naar je GitHub-repository (https://github.com/jouwnaam/mc-server-manager, met "
                      "het bestand mc_server_manager.py in de hoofdmap) of de directe https-link naar het bestand zelf.", 2)
        self._check(f, "Bij het opstarten (en daarna elke 6 uur) automatisch op een nieuwe versie controleren",
                    self.v["selfupdate_check"], 3)
        self._check(f, "Nieuwe versies zonder te vragen installeren (herstarten blijft aan jou)",
                    self.v["selfupdate_auto"], 4)
        ttk.Button(f, text="Nu controleren", command=self._check_update_now).grid(row=5, column=0, sticky="w", pady=(8, 0))
        self._hint(f, "Het programma vervangt zichzelf door het bestand van die link, na een controle dat het geldige "
                      "Python-code is met een hoger versienummer. De vorige versie blijft bewaard in de map "
                      "programma_backups. Wie die link beheert, bepaalt dus welke code er draait: gebruik alleen je "
                      "eigen link. Je instellingen blijven behouden.", 6)

    def _check_update_now(self):
        self.app.cfg["update_url"] = self.v["update_url"].get().strip()
        self.app.selfupdate_check(manual=True)

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
        c["update_url"] = c["update_url"].strip()
        for key, lo, hi in (("stop_timeout", 10, 600), ("poll_secs", 0, 600), ("console_max_lines", 500, 50000),
                            ("console_font", 7, 20), ("graph_minutes", 1, 180), ("stats_secs", 1, 30), ("temp_secs", 2, 300),
                            ("temp_warn", 50, 110)):
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


def hide_own_console():
    """Verbergt het zwarte consolevenster als dat alleen bij dit programma hoort (python.exe i.p.v. pythonw.exe)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        hwnd = k.GetConsoleWindow()
        if hwnd:
            procs = (ctypes.c_uint * 4)()
            if k.GetConsoleProcessList(procs, 4) <= 1:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


if __name__ == "__main__":
    hide_own_console()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
