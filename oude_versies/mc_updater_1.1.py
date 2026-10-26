#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MC Server Updater
-----------------
Controleert alle plugins in je Minecraft-server op updates via Modrinth (en als
fallback via Hangar en GitHub) en controleert/update het Paper server.jar via de PaperMC Fill API.

Geen externe packages nodig (alleen Python 3.8+ met tkinter).
Bouwen naar .exe:  pyinstaller --onefile --windowed --name MCServerUpdater mc_updater.py
"""

import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from collections import defaultdict
from datetime import datetime

try:
    import winsound
except ImportError:  # geen Windows
    winsound = None

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

APP_NAME = "MC Server Updater"
APP_VERSION = "1.1"
USER_AGENT = f"MCServerUpdater/{APP_VERSION} (persoonlijk hulpprogramma voor eigen Minecraft-server)"
MODRINTH = "https://api.modrinth.com/v2"
FILL = "https://fill.papermc.io/v3"
HANGAR = "https://hangar.papermc.io/api/v1"
GEYSERMC = "https://download.geysermc.org/v2/projects"
LOADERS = ["paper", "spigot", "bukkit"]
ALL_LOADERS = ["paper", "spigot", "bukkit", "purpur", "folia"]
NET_TIMEOUT = 30

DEFAULTS = {
    "folder": "", "jar": "server.jar", "unstable": False, "update_folder": False,
    # backups
    "keep_server_backups": True, "server_backups_max": 5,
    "keep_plugin_backups": True, "plugin_backups_max": 10,
    "backup_dir": "",
    # updates
    "auto_check": False, "ignore_list": "", "use_hangar": True, "use_github": True, "use_geysermc": True,
    "loaders": ["paper", "spigot", "bukkit"],
    # server
    "mc_override": "", "start_script": "", "net_timeout": 30,
    # gedrag
    "confirm": True, "sound": True, "topmost": False, "compact": False, "log_to_file": False,
}
TYPE_RANK = {"release": 0, "beta": 1, "alpha": 2}


# --------------------------------------------------------------------------
# Hulpfuncties (geen UI)
# --------------------------------------------------------------------------
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "mc_updater_config.json")


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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
class App(tk.Tk):
    COLS = (("plugin", "Plugin", 190), ("file", "Bestand", 220), ("current", "Huidige versie", 130),
            ("latest", "Nieuwste versie", 130), ("source", "Bron", 80), ("status", "Status", 290))

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1120x800")
        self.minsize(940, 640)
        self.q = queue.Queue()
        self.cfg = {**DEFAULTS, **load_config()}
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

        self._style()
        self._build()
        self.apply_settings()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<F5>", lambda e: self.on_check_all())
        self.after(80, self._poll)
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
        tk.Label(header, text="⛏  MC Server Updater", bg="#1f2937", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(header, text="Plugins via Modrinth, Hangar & GitHub  •  Paper via PaperMC", bg="#1f2937", fg="#9ca3af",
                 font=("Segoe UI", 10)).pack(side="left", padx=4)

        self.btn_settings = tk.Button(header, text="⚙  Instellingen", command=self.open_settings, bg="#374151",
                                      fg="white", activebackground="#4b5563", activeforeground="white",
                                      relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 10), cursor="hand2")
        self.btn_settings.pack(side="right", padx=14, pady=10)
        self.btn_start = tk.Button(header, text="▶  Server starten", command=self.start_server, bg="#059669",
                                   fg="white", activebackground="#047857", activeforeground="white",
                                   relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 10), cursor="hand2")

        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

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
            while True:
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
                    with open(os.path.join(app_dir(), "mc_updater.log"), "a", encoding="utf-8") as lf:
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
                        unstable=self.unstable_var.get(), update_folder=self.updfolder_var.get())
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
        sp = (c.get("start_script") or "").strip()
        self.btn_start.pack_forget()
        if sp and os.path.isfile(sp):
            self.btn_start.pack(side="right", padx=(0, 6), pady=10)

    def start_server(self):
        sp = (self.cfg.get("start_script") or "").strip()
        if not sp or not os.path.isfile(sp):
            messagebox.showwarning(APP_NAME, "Het startbestand bestaat niet meer. Controleer de instellingen.")
            return
        if self.cfg.get("confirm", True) and not messagebox.askyesno(
                APP_NAME, f"Server starten met:\n{sp}\n\nDoorgaan?"):
            return
        folder = self.folder_var.get().strip()
        cwd = folder if os.path.isdir(folder) else os.path.dirname(sp)
        ext = os.path.splitext(sp)[1].lower()
        try:
            if os.name != "nt":
                raise OSError("Server starten vanuit dit programma werkt alleen op Windows.")
            if ext == ".ps1":
                inner = ["powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", sp]
            elif ext in (".bat", ".cmd"):
                inner = ["cmd", "/k", "call", sp]  # /k: venster blijft open, zodat je fouten kunt lezen
            else:
                inner = [sp]
            cmd = ["cmd.exe", "/c", "start", "Minecraft server", "/D", cwd] + inner
            self.log(f"Starten: {subprocess.list2cmdline(cmd)}")
            subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.log(f"Server gestart in een nieuw venster ({os.path.basename(sp)}, map: {cwd}).", "ok")
            self.status("Server gestart in een nieuw venster.")
        except Exception as e:
            self.log(f"Server starten mislukt: {e}", "error")
            messagebox.showerror(APP_NAME, f"Server starten mislukt:\n{e}")

    def _close(self):
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
            if k in ("loaders", "folder", "jar", "unstable", "update_folder"):
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

    def _tab_gedrag(self, nb):
        f = self._frame(nb, "Gedrag")
        self._check(f, "Vraag bevestiging voor updates en het starten van de server", self.v["confirm"], 0)
        self._check(f, "Speel een geluidje af als een taak klaar is", self.v["sound"], 1)
        self._check(f, "Venster altijd bovenop andere vensters", self.v["topmost"], 2)
        self._check(f, "Compacte lijst (kleinere rijen, meer plugins in beeld)", self.v["compact"], 3)
        self._check(f, "Log bewaren in bestand (mc_updater.log naast het programma)", self.v["log_to_file"], 4)
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

    def save(self):
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
