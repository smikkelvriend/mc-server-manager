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

import ast
import gzip
import hashlib
import hmac
import http.server
import ipaddress
import secrets
import importlib
import io
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
import types
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
APP_VERSION = "2.45"
# Zet op True als deze versie zonder herstart kan worden toegepast (alleen als er geen vensterindeling of
# opstartcode verandert). Het programma controleert dat daarnaast zelf nog met een code-vergelijking.
HOT_SAFE = False

CHANGELOG = """
2.45 - Nieuwe interface: de tegels Processor en Geheugen zijn vervangen door de waarden in de grafiek Belasting, met een tegel Spelers ervoor in de plaats. De console is groter.
2.44 - De nieuwe interface is nu het hoofdscherm: hij opent bij het starten van het programma (uit te zetten bij Instellingen) en het klassieke scherm blijft op de taakbalk. Nieuw tabblad Updates voor het programma zelf, met wat er nieuw is en de instellingen voor automatisch bijwerken. Knop Klassiek scherm in de zijbalk.
2.43 - Nieuw: knop "Nieuwe interface" bovenin. Opent een moderner scherm in een eigen venster (Overzicht met processor, temperatuur en spelersskins, Console met logboek doorzoeken, Spelers met whitelist en bans, Plugins en updates samen, Kaart, Backups, Instellingen). Het oude scherm blijft werken. Het nieuwe scherm is alleen bereikbaar vanaf deze computer.
2.42 - Plugins: nieuwe knop "PLM uitladen" (/plm unload) naast "PLM laden", ook op de telefoon. De namen van de PLM-knoppen en het vinkje zijn korter gemaakt.
2.41 - Het tabblad Updates is samengevoegd met Plugins: onder Plugins staan nu drie subtabs (Geïnstalleerd, Updates, Zoeken en toevoegen). Het tabblad Plugins knippert met het aantal beschikbare updates.
2.40 - De grafieken (CPU, geheugen, TPS) zakken naar 0 zolang de server uit staat of slaapt, in plaats van te stoppen. Kan zonder herstart worden toegepast.
2.39 - Het vinkje voor de slaapstand op het tabblad Server heet nu "Auto slaapstand".
2.38 - Nieuwe knop "Nu in slaapstand" op het tabblad Server: zet de server meteen in slaapstand, ook als de automatische slaapstand uit staat.
2.37 - Nieuw: venster Whitelist en bans (whitelist, bans, IP-bans, operators; ook via rechtsklik op een speler), logboek doorzoeken (alle logs inclusief .gz, filter op speler, soort en datum), slaapstand-knop op het Server-tabblad met statistieken en rooster, en gezondheidscontrole (schijf, TPS, geheugen).
2.36 - Fix: de spelerskop in het spelersmenu knipperde af en toe omdat de lijst bij elke verversing werd leeggemaakt en opnieuw opgebouwd. Rijen blijven nu staan en worden alleen bijgewerkt.
2.35 - De kaart wordt op de achtergrond voorgeladen (bij het opstarten van het programma en 30 seconden nadat de server online is), zodat hij er meteen staat als je het tabblad Kaart opent.
2.34 - Slaapstand: eerste stap voor Bedrock met NetherNet. Het programma luistert nu ook op TCP van de Bedrock-poort, logt wat de Bedrock-client daar vraagt en wekt de server bij een join-verzoek. Experimenteel: het formaat is nog niet bevestigd.
2.33 - Slaapstand: in de Bedrock-serverlijst staat nu duidelijk "💤 Server slaapt" met "Join = starten, wacht ±1 min". (Een melding bij het joinen zelf is bij Bedrock niet mogelijk zonder het volledige Bedrock-protocol na te bouwen.)
2.32 - Nieuw: Slaapstand (Instellingen > Starten & Java). Als er X minuten niemand online is, stopt de server veilig en luistert het programma op de serverpoort. In de serverlijst staat dan "Server slaapt"; zodra iemand probeert te joinen start de server vanzelf weer (die speler probeert het na ca. een minuut opnieuw). Niet tijdens kaartgeneratie.
2.31 - Grafieken verbruiken veel minder processortijd (alleen hertekenen als de lijn echt verschuift: van ca. 15% naar 4% van een kern in rust); de knop "Pagina" bij plugin-zoekresultaten werkt weer.
2.30 - De Backuper-instellingen scrollen nu (muiswiel en balk). Aanvinkvakjes, keuzerondjes, scrollbalken en lijstrijen schalen mee met de Windows-schermschaling.
2.29 - Backups-tabblad toonde de bestanden van je serverfolder als backups: bij ftp/sftp/webdav-opslag is "backupsFolder" een map op een andere computer en wordt niet meer als lokale map gelezen.
2.28 - Opgeschoonde, modernere interface: één vlak kleurenschema (licht en donker), rustiger knoppen (blauw = hoofdactie, groen = starten/aanzetten, rood = verwijderen, de rest grijs), duidelijkere tabbladen, uitleg bovenaan tabbladen, welkomsttekst in de console en een logischere volgorde in Instellingen.
2.27 - Pijltje omhoog/omlaag haalt ook commando's terug die de server afkeurde (om ze te verbeteren); alleen de Tab-aanvulling slaat die over. Volgorde van de geschiedenis blijft kloppen na herstart.
2.26 - Fout hersteld: het Instellingen-venster toonde alleen het tabblad Backups (een dubbele functienaam brak het opbouwen), en de uptime/online-tijd had een ander formaat gekregen.
2.25 - De grafieken (CPU, geheugen, TPS, temperatuur) blijven bewaard bij een herstart van de server of het programma en lopen gewoon door; een onderbreking wordt als gat getoond.
2.24 - Soepel zoomen werkt nu ook op de diepste zoomniveaus (voorbij wat squaremap rendert), zonder sprong aan het eind.
2.23 - Tab in de console geeft nu dezelfde aanvullingen als de echte console (via het kleine hulpplugin MCMTab, wordt automatisch geplaatst; herstart de server één keer). Kaart zoomt veel vlotter (een frame in één keer), meldt eerlijk wanneer squaremap niet bereikbaar is en probeert dan opnieuw. Resterende helpregels ("Aliases: …") verdwijnen uit de console.
2.22 - Soepel zoomen met echte tussenbeelden (via Pillow, wordt eenmalig met een knop geïnstalleerd; zonder Pillow blijft het stapsgewijs). Help-regels van de server komen niet meer in de console terecht tijdens het leren van commando's.
2.21 - Zoomen op de kaart gebruikt veel meer tussenstappen (ca. 16). Tab-aanvulling: leert via /help <plugin>, geeft bij plugin-commando's geen spelersnamen meer en vergeet commando's die de server afkeurt.
2.20 - Kaart zoomt soepel (animatie tussen de niveaus) in het programma en op de telefoon, ook met twee vingers.
2.19 - Nieuw tabblad Backups (Backuper beheren), spelerskoppen (Java en Bedrock) in lijsten, kaart en telefoon, en Tab-aanvulling kent nu ook plugin-commando's.
2.18.1 - Plugins die up-to-date zijn tonen overal gewoon "Up-to-date".
2.18 - Telefoon-app heeft nu alle functies: server, plugins (zoeken/installeren), updates, kaart met gebied genereren, beheer, bereikbaarheid en instellingen.
2.17 - Updates kunnen zonder herstart worden toegepast als het programma dat veilig vindt; de server blijft dan draaien.
2.16.1 - Chunky pauzeert zodra er een speler online komt (met reden op de kaart) en hervat als de server leeg is.
2.16 - Telefoon: bedien je server op afstand via een webpagina/app met wachtwoord (tabblad Beheer, Telefoon).
2.15 - Donker thema (Instellingen -> Gedrag).
2.14.1 - Kaart werkt ook als de server uit staat: gebruikt de opgeslagen tegels van squaremap.
2.14 - Nieuw tabblad Beheer: spelersstatistieken, Windows-meldingen, server-tuning en wereldgrootte met opruimen.
2.13 - Kaart: sleep een gebied (zoals Knipprogramma), het programma laat Chunky het genereren met voortgangsbalk en werkt daarna de kaart bij.
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
    "confirm": True, "sound": True, "topmost": False, "compact": False, "dark_mode": False, "log_to_file": False,
    # serverbeheer
    "launch_mode": "auto", "java_path": "java", "java_xms": "1G", "java_xmx": "4G", "java_extra": "",
    "stop_timeout": 60, "poll_secs": 30, "auto_restart": False, "console_max_lines": 5000, "console_font": 10,
    "graph_minutes": 5, "graph_zoom": True, "stats_secs": 2,
    "show_player_activity": True,
    "squaremap_url": "http://localhost:8080",
    "notify_crash": True, "notify_start": False, "notify_join": False, "notify_leave": False, "notify_chunky": True,
    "notify_update": True, "notify_ignore": "",
    "chunky_autopause": True, "chunky_autoresume": True,
    "cmd_history": [], "learned_cmds": [], "pil_asked": False, "mcmtab_done": False, "sleep_enabled": False, "sleep_minutes": 10,
    "sleep_sched": False, "sleep_from": "22:00", "sleep_to": "08:00", "sleep_days": "1234567", "sleep_stats": {},
    "health_disk": True, "health_disk_gb": 5, "health_tps": True, "health_tps_min": 15, "health_tps_mins": 5,
    "health_ram": True, "health_ram_pct": 90,
    "remote_enabled": False, "remote_port": 8765, "remote_pass": "", "remote_lan_only": True,
    "plm_load": False, "plm_ack": False, "plugins_only_compat": False,
    "temp_enabled": True, "temp_secs": 10, "temp_warn": 85,
    "update_url": "", "desk_main": True, "selfupdate_check": True, "selfupdate_auto": False,
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


Image_ = ImageTk_ = None


def load_pil():
    """Pillow (optioneel): nodig voor het soepel zoomen op de kaart."""
    global Image_, ImageTk_
    try:
        importlib.invalidate_caches()
        from PIL import Image as _I, ImageTk as _IT
        Image_, ImageTk_ = _I, _IT
        return True
    except Exception:
        return False


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


# --------------------------------------------------------------------------
# Updates zonder herstart (hot reload)
# --------------------------------------------------------------------------
HOT_FRESH = {"SettingsDialog"}                 # vensters die bij elk openen opnieuw gebouwd worden
HOT_BUILD = ("__init__", "_build", "_style")   # onderdelen die de indeling opbouwen: wijziging = herstart nodig


def _top_info(tree):
    """Geeft (klassen, functies, losse toewijzingen, overige regels) van een module-AST."""
    classes, funcs, assigns, other = {}, {}, {}, []
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            classes[n.name] = n
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[n.name] = n
        elif isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) for t in n.targets):
            for t in n.targets:
                assigns[t.id] = ast.dump(n.value)
        elif isinstance(n, (ast.Import, ast.ImportFrom)) or (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)):
            continue
        else:
            other.append(ast.dump(n))
    return classes, funcs, assigns, other


def hot_check(old_src, new_src):
    """Kan de nieuwe versie zonder herstart worden toegepast? Geeft (ok, reden)."""
    try:
        a, b = ast.parse(old_src), ast.parse(new_src)
    except SyntaxError as e:
        return False, f"onleesbaar bestand ({e})"
    flag = any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "HOT_SAFE" for t in n.targets)
               and isinstance(n.value, ast.Constant) and n.value.value is True for n in b.body)
    if not flag:
        return False, "deze versie is niet als veilig voor direct toepassen gemarkeerd"
    ca, fa, aa, oa = _top_info(a)
    cb, fb, ab, ob = _top_info(b)
    if sorted(oa) != sorted(ob):
        return False, "de opstartcode van het programma is veranderd"
    for name, node in cb.items():
        old = ca.get(name)
        if old is None:
            continue
        if [ast.dump(x) for x in old.bases] != [ast.dump(x) for x in node.bases]:
            return False, f"{name} heeft een andere basis"
        if name in HOT_FRESH:
            continue
        om = {m.name: ast.dump(m) for m in old.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for m in node.body:
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith(HOT_BUILD):
                if om.get(m.name) != ast.dump(m):
                    return False, f"de opbouw van het venster ({name}.{m.name}) is veranderd"
    return True, ""


def _patch_fn(old, new):
    try:
        if len(old.__code__.co_freevars) != len(new.__code__.co_freevars):
            return False
        old.__code__ = new.__code__
        old.__defaults__ = new.__defaults__
        old.__kwdefaults__ = new.__kwdefaults__
        old.__doc__ = new.__doc__
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _patch_class(old, new):
    stale = 0
    for k, v in list(new.__dict__.items()):
        if k in ("__dict__", "__weakref__", "__module__", "__qualname__", "__doc__"):
            continue
        ov = old.__dict__.get(k)
        if isinstance(v, types.FunctionType) and isinstance(ov, types.FunctionType):
            if not _patch_fn(ov, v):
                setattr(old, k, v)
                stale += 1
        elif isinstance(v, (staticmethod, classmethod)) and isinstance(ov, type(v)):
            if not _patch_fn(ov.__func__, v.__func__):
                setattr(old, k, v)
                stale += 1
        else:
            setattr(old, k, v)
    return stale


def hot_apply(new_src, old_src):
    """Laadt de nieuwe code in het draaiende programma: bestaande functies krijgen de nieuwe code (knoppen en timers
    gebruiken die meteen), nieuwe functies en klassen worden toegevoegd. Geeft het aantal functies dat pas bij een herstart
    verandert."""
    d = sys.modules[__name__].__dict__
    code = compile(new_src, os.path.abspath(__file__), "exec")
    ta, tb = ast.parse(old_src), ast.parse(new_src)
    changed = {k for k, v in _top_info(tb)[2].items() if _top_info(ta)[2].get(k) != v}
    snap = dict(d)
    name = d["__name__"]
    d["__name__"] = "mcm_hot"               # voorkomt dat het hoofdprogramma nog eens start
    try:
        exec(code, d)
    except BaseException:
        d.clear()
        d.update(snap)
        raise
    finally:
        d["__name__"] = name
    stale = 0
    for k in [k for k in d if k not in snap or d[k] is not snap[k]]:
        newv, oldv = d[k], snap.get(k)
        if isinstance(newv, types.FunctionType) and isinstance(oldv, types.FunctionType):
            if _patch_fn(oldv, newv):
                d[k] = oldv
            else:
                stale += 1
        elif isinstance(newv, type) and isinstance(oldv, type):
            stale += _patch_class(oldv, newv)
            d[k] = oldv
        elif k in snap and k not in changed and not k.startswith("__"):
            d[k] = oldv                      # toestand van het programma blijft zoals hij was
    return stale


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
        self._lt = 0.0
        self.window, self.zoom, self.hi_fn = 300, True, None  # window in seconden
        self.bind("<Configure>", lambda e: self.redraw())

    def add(self, v):
        self.data.append((time.time(), v))
        self.redraw()

    def clear(self):
        self.data.clear()
        self.redraw()

    def gap(self):
        """Markeert een onderbreking (server uit): de lijn loopt daar niet door, de geschiedenis blijft staan."""
        if self.data and self.data[-1][1] is not None:
            self.data.append((time.time(), None))
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

    def tick(self):
        """Alleen opnieuw tekenen als de lijn minstens een halve pixel is opgeschoven (scheelt veel processortijd)."""
        step = min(max(self.window / max(self.winfo_width(), 40) * 0.5, 0.05), 1.0)
        if time.time() - self._lt >= step:
            self.redraw()

    def redraw(self):
        self._lt = time.time()
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
                if t <= td and pts and pts[-1][1] is not None:
                    pts.append((t, None))
                continue
            if t > td:
                nxt = (t, v)
                continue
            pts.append((t, v))
            if t < t0:
                break
        pts.reverse()
        while pts and pts[-1][1] is None:
            pts.pop()
            nxt = None
        if not pts:
            return
        if nxt and pts[-1][0] < td:  # tussen twee metingen doorrekenen: het uiteinde schuift gelijkmatig mee
            (ta, va), (tb, vb) = pts[-1], nxt
            f = (td - ta) / max(tb - ta, 1e-6)
            pts.append((td, va + (vb - va) * f))
        elif pts[-1][0] < td:
            pts.append((td, pts[-1][1]))
        vals = [v for _, v in pts if v is not None]
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
        for t, v in pts + [(0, None)]:
            if v is None:
                if len(xy) >= 4:
                    self.create_line(*xy, fill=self.color, width=2)
                xy = []
            else:
                xy += [X(t), Y(v)]
        last = next((v for t, v in reversed(self.data) if v is not None), vals[-1])  # echte laatste waarde
        self.create_text(w - 6, 4, anchor="ne", fill="white", font=("Segoe UI", 9, "bold"), text=f"{last:.1f}{self.unit}")
        self.create_text(w - 6, 18, anchor="ne", fill="#6b7280", font=("Segoe UI", 7), text=self._num(hi_v, rng))
        self.create_text(w - 6, h - 3, anchor="se", fill="#6b7280", font=("Segoe UI", 7), text=self._num(lo_v, rng))


load_psutil()
load_pil()


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
    ("chunky", 0): ["start", "pause", "continue", "cancel", "progress", "world", "shape", "center", "radius", "corners", "spawn", "quiet", "silent", "worldborder", "selection", "trim", "confirm", "patterns", "reload", "help"],
}
PLM_PLUGIN_SUBS = {"load", "unload", "reload", "enable", "disable", "restart", "info", "lookup"}


def complete_command(text, commands, players, plugins, history=(), plugin_cmds=()):
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
        known = cmd in VANILLA_CMDS
        if pool is None or (not known and cmd not in PLAYER_CMDS):
            # onbekend (plugin)commando: woorden uit eerder gebruikte regels op dezelfde plek, anders spelers
            pref = " ".join(parts[:-1]).lower()
            hw = sorted({h.split(" ")[len(parts) - 1] for h in history if h.lower().startswith(pref + " " if pref else "")
                         and len(h.split(" ")) >= len(parts)}, key=str.lower)
            # bij een plugin-commando zijn spelers zelden de juiste suggestie: dan alleen wat je eerder gebruikte
            pool = list(hw) + (list(pool) if pool else []) if hw or pool else ([] if cmd in plugin_cmds else players)
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


# --------------------------------------------------------------------------
# Donker thema
# --------------------------------------------------------------------------
DARK = dict(bg="#181c24", card="#222833", field="#2a3140", border="#374151", fg="#e5e7eb", muted="#9ca3af", acc="#2563eb")
DARK_ON = False
_DK_BG = {"white": DARK["card"], "#ffffff": DARK["card"], "#f0f0f0": DARK["bg"], "systembuttonface": DARK["bg"],
          "#e5e7eb": DARK["border"], "#f3f4f6": DARK["field"], "#eef2ff": "#1e2a4a", "#dcfce7": "#14532d",
          "#fff3e0": "#3b2a12", "#e3f2fd": "#12263f", "#fef3c7": "#3b2f0f", "#fee2e2": "#451a1a", "#ececec": DARK["bg"]}
_DK_FG = {"#111827": "#f3f4f6", "#374151": "#d1d5db", "#4b5563": "#cbd5e1", "#6b7280": "#9ca3af", "#555555": "#cbd5e1",
          "#3730a3": "#a5b4fc", "#92400e": "#fbbf24", "#2563eb": "#60a5fa", "#1b5e20": "#4ade80", "#b71c1c": "#f87171",
          "#b91c1c": "#f87171", "#e65100": "#fb923c", "#0d47a1": "#60a5fa", "#757575": "#9ca3af", "#166534": "#4ade80",
          "#059669": "#34d399", "#d97706": "#fbbf24", "#b45309": "#fbbf24", "black": "#f3f4f6", "#000000": "#f3f4f6",
          "systemwindowtext": "#f3f4f6", "systembuttontext": "#f3f4f6"}
_DK_BGKEYS = {"background", "bg", "highlightbackground", "activebackground", "selectcolor", "troughcolor", "highlightcolor",
              "fieldbackground", "selectbackground"}
_DK_FGKEYS = {"foreground", "fg", "activeforeground", "disabledforeground", "insertbackground", "selectforeground"}


def _dk_map(d):
    for k in list(d):
        lk = str(k).lstrip("-").lower()
        v = d[k]
        if not isinstance(v, str):
            continue
        low = v.lower()
        if lk in _DK_BGKEYS and low in _DK_BG:
            d[k] = _DK_BG[low]
        elif lk in _DK_FGKEYS and low in _DK_FG:
            d[k] = _DK_FG[low]
    return d


def install_dark(root):
    """Zet het donkere thema aan: kleuren die in de code staan worden vertaald; moet vóór het bouwen van de vensters."""
    global DARK_ON
    if DARK_ON:
        return
    DARK_ON = True
    orig = tk.Misc._options

    def options(self, cnf, kw=None):
        d = dict(tk._cnfmerge((cnf, kw)) if kw else tk._cnfmerge(cnf))
        return orig(self, _dk_map(d))

    tk.Misc._options = options
    otag = ttk.Treeview.tag_configure

    def tag_configure(self, tagname, option=None, **kw):
        if kw:
            kw = _dk_map(dict(kw))
        return otag(self, tagname, option, **kw)

    ttk.Treeview.tag_configure = tag_configure
    D = DARK
    root.configure(bg=D["bg"])
    for pat, val in (("*Background", D["bg"]), ("*Foreground", D["fg"]), ("*Entry.Background", D["field"]),
                     ("*Spinbox.Background", D["field"]), ("*Listbox.Background", D["field"]), ("*Text.Background", D["field"]),
                     ("*activeBackground", D["border"]), ("*activeForeground", D["fg"]), ("*selectColor", D["field"]),
                     ("*Menu.Background", D["card"]), ("*Menu.Foreground", D["fg"]), ("*insertBackground", D["fg"]),
                     ("*highlightBackground", D["bg"]), ("*disabledForeground", D["muted"])):
        root.option_add(pat, val)


LIGHT = dict(bg="#f0f0f0", card="#ffffff", field="#ffffff", border="#d1d5db", fg="#111827", muted="#6b7280", acc="#2563eb",
             btn="#e5e7eb", hover="#d1d5db", tab="#e5e7eb", head="#e5e7eb", accfg="#2563eb")
DARK.update(btn="#374151", hover="#4b5563", tab="#222833", head="#374151", accfg="#60a5fa")


def flat_style(style, P):
    """Een rustig, vlak uiterlijk voor alle knoppen, tabbladen en lijsten (licht en donker, op elk besturingssysteem hetzelfde)."""
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    F = "Segoe UI"
    try:
        sc = max(1.0, style.master.winfo_fpixels("1i") / 96.0)  # schermschaal (Windows-schaling 125%, 150%, ...)
    except Exception:
        sc = 1.0
    ind = max(12, round(13 * sc))
    style.configure(".", background=P["bg"], foreground=P["fg"], fieldbackground=P["field"], bordercolor=P["border"],
                    lightcolor=P["bg"], darkcolor=P["bg"], troughcolor=P["field"], selectbackground=P["acc"],
                    selectforeground="white", insertcolor=P["fg"], focuscolor=P["bg"], font=(F, 10))
    style.configure("TFrame", background=P["bg"])
    style.configure("TLabel", background=P["bg"], foreground=P["fg"])
    style.configure("TLabelframe", background=P["bg"], bordercolor=P["border"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=P["bg"], foreground=P["muted"], font=(F, 9, "bold"))
    style.configure("TButton", background=P["btn"], foreground=P["fg"], bordercolor=P["btn"], lightcolor=P["btn"],
                    darkcolor=P["btn"], padding=(12, 5), relief="flat", focusthickness=0)
    style.map("TButton", background=[("disabled", P["btn"]), ("pressed", P["hover"]), ("active", P["hover"])],
              foreground=[("disabled", P["muted"])], bordercolor=[("disabled", P["border"]), ("active", P["hover"])],
              lightcolor=[("active", P["hover"])], darkcolor=[("active", P["hover"])])
    for name, col, hov in (("Big.TButton", P["acc"], "#1d4ed8"), ("Accent.TButton", P["acc"], "#1d4ed8"),
                           ("Danger.TButton", "#dc2626", "#b91c1c"), ("Good.TButton", "#059669", "#047857")):
        style.configure(name, background=col, foreground="white", bordercolor=col, lightcolor=col, darkcolor=col,
                        font=(F, 10, "bold"), padding=(14, 6), relief="flat")
        style.map(name, background=[("disabled", P["btn"]), ("pressed", hov), ("active", hov)],
                  foreground=[("disabled", P["muted"])], bordercolor=[("disabled", P["btn"]), ("active", hov)],
                  lightcolor=[("active", hov)], darkcolor=[("active", hov)])
    style.configure("TCheckbutton", background=P["bg"], foreground=P["fg"], indicatorbackground=P["field"],
                    indicatorforeground="white", indicatorcolor=P["field"], padding=2, indicatorsize=ind, indicatormargin=(0, 0, 4, 0))
    style.map("TCheckbutton", background=[("active", P["bg"])],
              indicatorcolor=[("selected", P["acc"]), ("active", P["hover"])],
              indicatorbackground=[("selected", P["acc"]), ("active", P["hover"])])
    style.configure("TRadiobutton", background=P["bg"], foreground=P["fg"], indicatorbackground=P["field"],
                    indicatorcolor=P["field"], padding=2, indicatorsize=ind, indicatormargin=(0, 0, 4, 0))
    style.map("TRadiobutton", background=[("active", P["bg"])], indicatorcolor=[("selected", P["acc"])],
              indicatorbackground=[("selected", P["acc"])])
    for w in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(w, fieldbackground=P["field"], foreground=P["fg"], background=P["btn"], insertcolor=P["fg"],
                        arrowcolor=P["muted"], bordercolor=P["border"], lightcolor=P["border"], darkcolor=P["border"], padding=4)
    style.map("TEntry", bordercolor=[("focus", P["acc"])], lightcolor=[("focus", P["acc"])], darkcolor=[("focus", P["acc"])])
    style.map("TCombobox", fieldbackground=[("readonly", P["field"])], foreground=[("readonly", P["fg"])],
              selectbackground=[("readonly", P["field"])], selectforeground=[("readonly", P["fg"])],
              bordercolor=[("focus", P["acc"])])
    style.configure("TNotebook", background=P["bg"], bordercolor=P["border"], tabmargins=(8, 6, 8, 0))
    style.configure("TNotebook.Tab", background=P["tab"], foreground=P["muted"], padding=(14, 6), bordercolor=P["border"],
                    font=(F, 10))
    style.map("TNotebook.Tab", background=[("selected", P["card"]), ("active", P["hover"])],
              foreground=[("selected", P["accfg"]), ("active", P["fg"])], font=[("selected", (F, 10, "bold"))])
    style.configure("Treeview", background=P["card"], fieldbackground=P["card"], foreground=P["fg"], bordercolor=P["border"],
                    rowheight=round(26 * sc), font=(F, 10), borderwidth=1)
    style.map("Treeview", background=[("selected", P["acc"])], foreground=[("selected", "white")])
    style.configure("Treeview.Heading", background=P["head"], foreground=P["fg"], bordercolor=P["border"], relief="flat",
                    font=(F, 9, "bold"), padding=(6, 5))
    style.map("Treeview.Heading", background=[("active", P["hover"])])
    style.configure("TScrollbar", background=P["btn"], troughcolor=P["bg"], arrowcolor=P["muted"], bordercolor=P["bg"],
                    lightcolor=P["btn"], darkcolor=P["btn"], relief="flat", arrowsize=round(13 * sc))
    style.map("TScrollbar", background=[("active", P["hover"])])
    style.configure("TProgressbar", background=P["acc"], troughcolor=P["btn"], bordercolor=P["btn"], lightcolor=P["acc"],
                    darkcolor=P["acc"])
    style.configure("TSeparator", background=P["border"])
    style.configure("TMenubutton", background=P["btn"], foreground=P["fg"], padding=(10, 5))
    style.configure("TPanedwindow", background=P["bg"])
    style.configure("Muted.TLabel", foreground=P["muted"], font=(F, 9))
    style.configure("Title.TLabel", font=(F, 13, "bold"))
    style.configure("Card.TFrame", background=P["card"])


def dark_style(style):
    flat_style(style, DARK)


def _vi(n):
    out = bytearray()
    n &= 0xFFFFFFFF
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _rvi(data, pos):
    n = sh = 0
    while True:
        b = data[pos]
        pos += 1
        n |= (b & 0x7F) << sh
        if not b & 0x80:
            return n, pos
        sh += 7
        if sh > 35:
            raise ValueError("varint")


def _mc_str(t):
    b = t.encode("utf-8")
    return _vi(len(b)) + b


def _mc_pkt(pid, payload=b""):
    body = _vi(pid) + payload
    return _vi(len(body)) + body


RAKNET_MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")


def sleep_allowed(cfg, now=None):
    """Mag de server nu in slaapstand? Zonder rooster altijd; met rooster alleen op de gekozen dagen en uren."""
    if not cfg.get("sleep_sched"):
        return True
    t = time.localtime(now or time.time())
    if str(t.tm_wday + 1) not in str(cfg.get("sleep_days", "1234567")):
        return False
    try:
        a = [int(x) for x in str(cfg.get("sleep_from", "22:00")).split(":")[:2]]
        b = [int(x) for x in str(cfg.get("sleep_to", "08:00")).split(":")[:2]]
    except ValueError:
        return True
    cur, lo, hi = t.tm_hour * 60 + t.tm_min, a[0] * 60 + a[1], b[0] * 60 + b[1]
    return (lo <= cur < hi) if lo <= hi else (cur >= lo or cur < hi)


class WakeListener:
    """Luistert op de serverpoort terwijl de server slaapt. Een speler die probeert te joinen wekt de server; de serverlijst
    toont intussen een slaapmelding. Java: gewone Minecraft-handshake. Bedrock (Geyser): RakNet, alleen als er een poort is."""

    def __init__(self, jport, bport, motd, max_players, on_wake, log):
        self.jport, self.bport, self.motd, self.maxp = jport, bport, motd, max_players
        self.on_wake, self.log = on_wake, log
        self.socks, self._stop, self._woken = [], False, False
        self.guid = secrets.randbits(63)

    def start(self):
        errs = []
        try:
            t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            t.bind(("0.0.0.0", int(self.jport)))
            t.listen(8)
            self.socks.append(t)
            threading.Thread(target=self._accept, args=(t,), daemon=True).start()
        except OSError as e:
            errs.append(f"Java-poort {self.jport}: {e}")
        if self.bport:
            try:
                u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                u.bind(("0.0.0.0", int(self.bport)))
                self.socks.append(u)
                threading.Thread(target=self._udp, args=(u,), daemon=True).start()
                # NetherNet (nieuwe Bedrock-transport): de client vraagt eerst via TCP/HTTP hoe hij moet verbinden
                h = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                h.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                h.bind(("0.0.0.0", int(self.bport)))
                h.listen(8)
                self.socks.append(h)
                threading.Thread(target=self._http_accept, args=(h,), daemon=True).start()
            except OSError as e:
                errs.append(f"Bedrock-poort {self.bport}: {e}")
        return errs

    def stop(self):
        self._stop = True
        for s in self.socks:
            try:
                s.close()
            except OSError:
                pass
        self.socks = []

    def _wake(self, who):
        if not self._woken:
            self._woken = True
            self.on_wake(who)

    # ---- Java ----
    def _accept(self, srv):
        while not self._stop:
            try:
                c, _a = srv.accept()
            except OSError:
                return
            threading.Thread(target=self._conn, args=(c,), daemon=True).start()

    @staticmethod
    def _read_pkt(c):
        data = b""
        n = sh = 0
        while True:
            b = c.recv(1)
            if not b:
                raise OSError("dicht")
            n |= (b[0] & 0x7F) << sh
            if not b[0] & 0x80:
                break
            sh += 7
            if sh > 21:
                raise ValueError("te lang")
        if n > 4096:
            raise ValueError("te groot")
        while len(data) < n:
            chunk = c.recv(n - len(data))
            if not chunk:
                raise OSError("dicht")
            data += chunk
        return data

    def _conn(self, c):
        try:
            c.settimeout(5)
            d = self._read_pkt(c)
            pid, p = _rvi(d, 0)
            if pid != 0:
                return
            proto, p = _rvi(d, p)
            ln, p = _rvi(d, p)
            p += ln + 2
            state, p = _rvi(d, p)
            if state == 1:
                self._read_pkt(c)  # status request
                js = json.dumps({"version": {"name": "Slaapstand", "protocol": proto},
                                 "players": {"max": self.maxp, "online": 0},
                                 "description": {"text": self.motd}}, ensure_ascii=False)
                c.sendall(_mc_pkt(0, _mc_str(js)))
                try:
                    d2 = self._read_pkt(c)
                    pid2, p2 = _rvi(d2, 0)
                    if pid2 == 1:
                        c.sendall(_mc_pkt(1, d2[p2:p2 + 8]))
                except (OSError, ValueError, IndexError):
                    pass
            elif state in (2, 3):
                name = "?"
                try:
                    d2 = self._read_pkt(c)
                    pid2, p2 = _rvi(d2, 0)
                    ln2, p2 = _rvi(d2, p2)
                    name = d2[p2:p2 + ln2].decode("utf-8", "replace")[:32] or "?"
                except (OSError, ValueError, IndexError):
                    pass
                msg = json.dumps({"text": "De server sliep en wordt nu gestart.\nProbeer het over ongeveer een minuut opnieuw."},
                                 ensure_ascii=False)
                c.sendall(_mc_pkt(0, _mc_str(msg)))
                self._wake(name)
        except (OSError, ValueError, IndexError):
            pass
        finally:
            try:
                c.close()
            except OSError:
                pass

    # ---- Bedrock NetherNet (signalering over HTTP; formaat nog niet bevestigd, daarom wordt alles gelogd) ----
    def _http_accept(self, srv):
        while not self._stop:
            try:
                c, a = srv.accept()
            except OSError:
                return
            threading.Thread(target=self._http_conn, args=(c, a), daemon=True).start()

    def _http_conn(self, c, addr):
        try:
            c.settimeout(3)
            data = b""
            while b"\r\n\r\n" not in data and len(data) < 4096:
                chunk = c.recv(2048)
                if not chunk:
                    break
                data += chunk
            head = data.decode("latin-1", "replace")
            first = head.split("\r\n", 1)[0][:200]
            self.log(f"Slaapstand (Bedrock/HTTP) van {addr[0]}: {first}", "info")
            body = json.dumps({"motd": "Server slaapt", "message": "De server wordt gestart, probeer het over een minuut opnieuw"})
            c.sendall(("HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nContent-Length: %d\r\n"
                       "Connection: close\r\n\r\n%s" % (len(body.encode()), body)).encode())
            if "join" in first.lower():
                self._wake("Bedrock-speler")
        except OSError:
            pass
        finally:
            try:
                c.close()
            except OSError:
                pass

    # ---- Bedrock ----
    def _udp(self, u):
        while not self._stop:
            try:
                data, addr = u.recvfrom(2048)
            except OSError:
                return
            if not data:
                continue
            if data[0] in (1, 2) and len(data) >= 9:
                info = f"MCPE;💤 Server slaapt;924;1.21.0;0;{self.maxp};{self.guid};Join = starten, wacht ±1 min;Survival;1;{self.bport};{self.bport}"
                b = info.encode("utf-8")
                try:
                    u.sendto(b"\x1c" + data[1:9] + struct.pack(">Q", self.guid) + RAKNET_MAGIC + struct.pack(">H", len(b)) + b, addr)
                except OSError:
                    pass
            elif data[0] == 5:  # open connection request: iemand probeert te verbinden
                self.log(f"Slaapstand (Bedrock/RakNet) verbindingspoging van {addr[0]}", "info")
                self._wake("Bedrock-speler")
            else:
                self.log(f"Slaapstand (Bedrock/UDP) onbekend pakket 0x{data[0]:02x} ({len(data)} bytes) van {addr[0]}", "info")


def make_scroll_frame(parent):
    """Geeft (buitenste frame, binnenste frame): zet dingen in het binnenste frame; het buitenste scrolt (muiswiel + balk)."""
    P = DARK if DARK_ON else LIGHT
    outer = ttk.Frame(parent)
    cv = tk.Canvas(outer, highlightthickness=0, bg=P["bg"])
    sb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
    inner = ttk.Frame(cv)
    win = cv.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
    cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
    cv.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)

    def over(ev):
        try:
            w = cv.winfo_containing(ev.x_root, ev.y_root)
        except (KeyError, tk.TclError):
            return False
        while w is not None:
            if w is cv:
                return True
            w = getattr(w, "master", None)
        return False

    def wheel(ev):
        if over(ev) and cv.bbox("all") and cv.bbox("all")[3] > cv.winfo_height():
            d = -1 if (getattr(ev, "num", 0) == 4 or getattr(ev, "delta", 0) > 0) else 1
            cv.yview_scroll(d * 3, "units")

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        cv.bind_all(seq, wheel, add="+")
    return outer, inner


def make_btn(parent, text, cmd, bg="#e5e7eb", fg="#111827", padx=10, pady=4):
    """Knop in het vaste kleurenschema: blauw = hoofdactie, groen = aanzetten/starten, rood = verwijderen, grijs = de rest."""
    P = DARK if DARK_ON else LIGHT
    b = bg.lower()
    if b in ("#16a34a", "#059669", "#15803d", "#047857", "#dcfce7"):
        col, tx, hov = ("#059669", "white", "#047857") if b != "#dcfce7" else (P["btn"], P["fg"], P["hover"])
    elif b in ("#dc2626", "#b91c1c", "#fee2e2"):
        col, tx, hov = ("#dc2626", "white", "#b91c1c") if b != "#fee2e2" else (P["btn"], "#dc2626", P["hover"])
    elif b in ("#2563eb", "#1d4ed8", "#3b82f6"):
        col, tx, hov = P["acc"], "white", "#1d4ed8"
    else:  # grijs, oranje, paars, pastel: allemaal rustig grijs
        col, tx, hov = P["btn"], P["fg"], P["hover"]
    btn = tk.Button(parent, text=text, command=cmd, bg=col, fg=tx, activebackground=hov, activeforeground=tx,
                    relief="flat", bd=0, padx=padx + 2, pady=pady + 1, font=("Segoe UI", 9, "bold"), cursor="hand2",
                    highlightthickness=0, disabledforeground=P["muted"])
    btn.bind("<Enter>", lambda e: btn.config(bg=hov) if str(btn["state"]) != "disabled" else None)
    btn.bind("<Leave>", lambda e: btn.config(bg=col))
    return btn


def dark_titlebar(win):
    """Donkere titelbalk (Windows 10/11)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1)
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


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
        ttk.Checkbutton(box, text="⚠ Direct laden via PLM, zonder herstart (eigen risico)",
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
                                  ("⚡  PLM laden", self._load_selected, "#7c3aed", "white"),
                                  ("⏏  PLM uitladen", self._unload_selected, "#7c3aed", "white"),
                                  ("☑  Alles selecteren", self._select_all, "#e5e7eb", "#111827"),
                                  ("📂  Map openen", self._open_dir, "#e5e7eb", "#111827"),
                                  ("↻  Vernieuwen", self.refresh, "#e5e7eb", "#111827")):
            self._btn(bar, text, cmd, bg, fg).pack(side="left", padx=(0, 6))
        tk.Label(bar, text="Vink plugins aan om meerdere tegelijk te beheren.", bg=self.BG,
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
        return make_btn(parent, text, cmd, bg, fg, pad, 3)

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
                           "Nog geen plugins. Kies je servermap (Plugins › Updates) of zoek er een bij 🔍 Zoeken en toevoegen.")).pack()
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
            self.count_lbl.config(text="Kies eerst je servermap (Plugins › Updates).")
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

    def _remove(self, only=None):
        sel = only if only is not None else self._selected()
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

    def _open_page(self, r):
        url = (r.get("page") or "") if isinstance(r, dict) else ""
        if re.match(r"^https?://", url):
            webbrowser.open(url)
        else:
            messagebox.showinfo(APP_NAME, "Van deze plugin is geen webpagina bekend.")

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

    def _plm_unload(self, names):
        """Stuurt /plm unload voor elke plugin (op pluginnaam) naar de server."""
        pm = plugman_name(self.items.values()) if self.items else plugman_name(scan_plugins(self.pdir()))
        if not self._server_running():
            messagebox.showinfo(APP_NAME, "De server draait niet, dus er is niets om uit te laden.")
            return False
        if not pm:
            messagebox.showinfo(APP_NAME, "PlugManX staat niet aan op je server, dus /plm bestaat niet.\n\n"
                                          "Zoek en installeer “PlugManX” op het tabblad Zoeken en herstart daarna één keer.")
            return False
        for n in names:
            self.app.srv_send(f"plm unload {n}")
        self.app.log("Direct uitladen: " + ", ".join(f"/plm unload {n}" for n in names) + ". Kijk in de console of het gelukt is.", "warn")
        self.after(4000, self.refresh)
        return True

    def _unload_selected(self):
        sel = [i for i in self._selected() if i["enabled"] and not norm_name(i["name"]).startswith("plugman")]
        if not sel:
            messagebox.showinfo(APP_NAME, "Selecteer eerst plugins die aan staan (PlugManX zelf kan niet worden uitgeladen).")
            return
        if not messagebox.askyesno(APP_NAME, "Direct uitladen op eigen risico, zonder herstart.\n\n" +
                                             "\n".join("/plm unload " + i["name"] for i in sel) +
                                             "\n\nDe plugin blijft in de map staan en wordt bij de volgende herstart weer geladen. "
                                             "Plugins die door andere plugins nodig zijn kunnen problemen geven. Doorgaan?"):
            return
        self._plm_unload([i["name"] for i in sel])

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
            self._note("Je Minecraft-versie is nog niet ingevuld (Plugins › Updates), dus het filter staat niet aan.")
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
            messagebox.showinfo(APP_NAME, "Kies eerst je servermap (Plugins › Updates).")
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
        self._url_now = self.url_var.get()
        self._predec, self._disk_mode, self._last_retry = {}, False, 0.0
        self.url_var.trace_add("write", lambda *a: setattr(self, "_url_now", self.url_var.get()))
        self.world_var = tk.StringVar()
        self.status_var, self.coord_var = tk.StringVar(), tk.StringVar()
        self.follow_var = tk.BooleanVar(value=False)
        self.names_var = tk.BooleanVar(value=True)
        self.q = queue.Queue()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.worlds, self.wset = [], {}
        self.cur = None                       # naam van de wereld die getoond wordt
        self.zl, self.cx, self.cz = 3, 0.0, 0.0   # zoomniveau, midden van het beeld (in blokken)
        self.zfrac, self._anim_job, self._anchor, self._wp = 0.0, None, None, 512
        self.raw, self.pilsrc, self._nat, self._anim_from, self._za = {}, {}, None, 0, None   # soepel zoomen: tussenstap tussen twee niveaus
        self.zimgs = {}                       # extra uitgezoomde (vergrote) versies voor het diepste zoomniveau
        self.imgs = {}                        # (wereld, z, x, y) -> PhotoImage of None (lege tegel)
        self.sig = {}                         # (wereld, z, x, y) -> hash van de bytes, om verversen goedkoop te houden
        self.pending = set()
        self.players, self.trails = [], {}
        self.visible, self.online, self.loading = False, False, False
        self._drag, self._moved, self._dirty, self._tok = None, False, True, 0
        self._last_refresh = self._last_players = 0.0
        self.sel_mode, self.sel, self._selstart, self._seltmp = False, None, None, None
        self.gen = {"state": "idle"}          # idle | ready | running | paused | rendering | done
        self.autorender_var = tk.BooleanVar(value=True)
        self.autopause_var = tk.BooleanVar(value=bool(app.cfg.get("chunky_autopause", True)))
        self.autoresume_var = tk.BooleanVar(value=bool(app.cfg.get("chunky_autoresume", True)))
        self._fast_until = 0.0
        self._build()

    # ---------- opbouw ----------
    def _btn(self, parent, text, cmd, bg="#e5e7eb", fg="#111827"):
        return make_btn(parent, text, cmd, bg, fg, 8, 2)

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
        self.sel_btn = self._btn(bar, "\U0001F4D0  Gebied genereren", self.toggle_sel, "#7c3aed", "white")
        self.sel_btn.pack(side="left", padx=(6, 0))
        tk.Label(bar, textvariable=self.status_var, fg="#6b7280", font=("Segoe UI", 9)).pack(side="right")
        self.pil_btn = self._btn(bar, "✨  Soepel zoomen aanzetten", self._ask_pil, "#0ea5e9", "white")
        if Image_ is None and not getattr(sys, "frozen", False):
            self.pil_btn.pack(side="right", padx=(0, 8))
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)
        side = ttk.Frame(main, width=250)
        side.pack(side="right", fill="y", padx=(8, 0))
        side.pack_propagate(False)
        ttk.Label(side, text="Spelers op de kaart", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tree = ttk.Treeview(side, columns=("name", "pos"), show="headings", height=12, selectmode="browse")
        self.app.heads.watch_tree(self.tree, lambda iid: iid)
        self.app.heads.on_change.append(lambda: self._draw_overlay_only() if self.visible else None)
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
        self.coord_lbl = tk.Label(self, textvariable=self.coord_var, anchor="w", fg="#4b5563", font=("Consolas", 9))
        self.coord_lbl.pack(fill="x", pady=(4, 0))
        self._build_gen()
        cv = self.cv
        cv.bind("<Configure>", lambda e: self._draw())
        cv.bind("<ButtonPress-1>", self._press)
        self.winfo_toplevel().bind("<Escape>", lambda e: self.toggle_sel(False) if self.sel_mode else None, add="+")
        cv.bind("<B1-Motion>", self._motion)
        cv.bind("<ButtonRelease-1>", self._release)
        cv.bind("<Motion>", self._hover)
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            cv.bind(ev, self._wheel)
        cv.bind("<Double-Button-1>", lambda e: self._zoom(1, e.x, e.y))

    # ---------- netwerk (alleen in achtergrondthreads) ----------
    def _upd_webdir(self):
        """Waar squaremap zijn kaart op schijf bewaart (voor als de server uit staat). Alleen vanuit de hoofdthread aanroepen."""
        base = os.path.join(self.app.folder_var.get().strip(), "plugins", "squaremap")
        path = "web"
        try:
            with open(os.path.join(base, "config.yml"), encoding="utf-8", errors="replace") as fh:
                m = re.search(r"web-directory:\s*\n\s+path:\s*['\"]?([^'\"\n#]+)", fh.read())
                if m and m.group(1).strip():
                    path = m.group(1).strip()
        except OSError:
            pass
        self._webdir = path if os.path.isabs(path) else os.path.join(base, path)

    def _disk(self, path):
        """Leest een bestand uit de opgeslagen kaart. None = er is geen opgeslagen kaart; b'' = die tegel bestaat niet."""
        wd = getattr(self, "_webdir", None)
        if not wd or not os.path.isfile(os.path.join(wd, "tiles", "settings.json")) or path.endswith("players.json"):
            return None
        try:
            with open(os.path.join(wd, *path.split("/")), "rb") as fh:
                self._from_disk = True
                return fh.read()
        except OSError:
            self._from_disk = True
            return b""

    def _get(self, path):
        if time.time() < getattr(self, "_disk_until", 0):
            return self._disk(path)
        base = (self._url_now or "").strip().rstrip("/")
        try:
            with urllib.request.urlopen(f"{base}/{path}", timeout=5) as r:
                self._from_disk = False
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self._from_disk = False
                return b""
        except Exception:
            pass
        # geen verbinding: server uit of squaremap niet actief -> gebruik de opgeslagen kaart
        d = self._disk(path)
        if d is not None:
            self._disk_until = time.time() + 8
        return d

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
        self._upd_webdir()

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
            if data and Image_ is not None:  # alvast uitpakken in deze achtergrondthread: scheelt haperingen bij het zoomen
                try:
                    self._predec[key] = Image_.open(io.BytesIO(data)).convert("RGBA")
                except Exception:
                    pass
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
    def _ask_pil(self):
        if Image_ is not None:
            return
        if not messagebox.askyesno(APP_NAME, "Voor soepel zoomen op de kaart gebruikt het programma het pakket Pillow (ongeveer 10 MB, via pip).\n\n"
                                             "Zonder Pillow werkt de kaart gewoon, maar zoomt hij in sprongen.\n\nNu installeren?"):
            return
        self.pil_btn.config(state="disabled", text="Pillow installeren…")

        def work():
            try:
                r = subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], capture_output=True, text=True, timeout=300,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                ok = r.returncode == 0
            except Exception:
                ok = False
            self.q.put(("pil", ok))
        threading.Thread(target=work, daemon=True).start()

    def on_show(self):
        self.visible = True
        self._tok += 1
        if Image_ is None and not self.app.cfg.get("pil_asked") and not getattr(sys, "frozen", False):
            self.app.cfg["pil_asked"] = True
            self.app._save_cfg()
            self.after(800, self._ask_pil)
        if not self.worlds:
            self.load_worlds()
        elif time.time() - self._last_refresh > 4:
            self._last_refresh = 0   # meteen verversen met de nieuwste tegels (de voorgeladen kunnen oud zijn)
        self._loop(self._tok)

    def on_hide(self):
        self.visible = False
        self._tok += 1

    # ---------- alvast laden op de achtergrond, zodat de kaart er meteen staat als je het tabblad opent ----------
    def prewarm(self):
        """Haalt de wereldlijst en de tegels rond het startpunt op terwijl het tabblad nog dicht is."""
        if self.visible or getattr(self, "_warming", False):
            return
        self._warming = True
        self._warm_end = time.time() + 45
        self._warm_asked = False
        self._warm_tried = False
        if self._disk_mode:
            self._disk_until = 0
        if not self.worlds or self._disk_mode:
            self._warm_tried = True
            self.load_worlds()
        self._warm_loop()

    def _warm_loop(self):
        if self.visible or time.time() > self._warm_end:
            self._warming = False
            return
        self._drain()
        if self.worlds and self.cur and not self._warm_asked:
            self._warm_asked = True
            W, H = (self.cv.winfo_width(), self.cv.winfo_height()) if self.cv.winfo_width() >= 20 else (1100, 700)
            for key in self._view_keys(0.5, (W, H)):
                if key not in self.imgs:
                    self.fetch_tile(key)
            self.fetch_players()
        elif not self.worlds and not self.loading and self._warm_tried:
            self._warming = False   # niets te laden (squaremap niet bereikbaar en geen opgeslagen kaart)
            return
        if self._warm_asked and not self.pending and not self.loading:
            self._warming = False
            return
        self.after(150, self._warm_loop)

    def _loop(self, tok):
        """Eén rustige timer, alleen actief zolang het tabblad open is."""
        if tok != self._tok or not self.visible:
            return
        self._drain()
        now = time.time()
        if self.worlds and now - self._last_players > 3:
            self._last_players = now
            self.fetch_players()
        if self.worlds and now - self._last_refresh > (10 if now < self._fast_until else 60):
            self.refresh()
        if self._disk_mode and not self.loading and now - self._last_retry > 8:
            self._last_retry = now
            self._disk_until = 0
            self.load_worlds()
        if not self.worlds and not self.loading and now - self._last_players > 5:
            self._last_players = now
            self.load_worlds()
        if self._dirty:
            self._dirty = False
            self._draw()
        self.after(120, lambda: self._loop(tok))

    def refresh(self, force=False):
        self._last_refresh = time.time()
        self._upd_webdir()
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
                    self.status_var.set("Geen kaart: squaremap niet bereikbaar en nog niets opgeslagen")
                    self._dirty = True
                    continue
                self.worlds, self.wset = m[1]
                self.online = True
                names = [w.get("display_name") or w["name"] for w in self.worlds]
                self.world_cb.config(values=names)
                if self.worlds and self.cur not in [w["name"] for w in self.worlds]:
                    first = next((w for w in self.worlds if w.get("type") == "normal"), self.worlds[0])
                    self._set_world(first["name"])
                was_disk = self._disk_mode
                self._disk_mode = bool(getattr(self, "_from_disk", False))
                self.status_var.set("Squaremap niet bereikbaar: opgeslagen kaart (ik probeer het opnieuw)" if self._disk_mode else "")
                if was_disk and not self._disk_mode:
                    self.refresh(force=True)
            elif m[0] == "tile":
                self._tile(*m[1:])
            elif m[0] == "players":
                self._players(m[1])
            elif m[0] == "pil":
                if m[1] and load_pil():
                    self.pil_btn.pack_forget()
                    self.status_var.set("Soepel zoomen staat aan")
                    self.app.log("Pillow geïnstalleerd: de kaart zoomt nu soepel.", "ok")
                else:
                    self.pil_btn.config(state="normal", text="✨  Soepel zoomen aanzetten")
                    messagebox.showinfo(APP_NAME, "Installeren mislukt. Probeer in een opdrachtvenster: pip install pillow")

    def _tile(self, key, data, replace):
        self.pending.discard(key)
        if data is None:
            return  # netwerkfout: later opnieuw proberen
        sig = hash(data)
        if replace and self.sig.get(key) == sig:
            return
        self.sig[key] = sig
        old = self.imgs.pop(key, None)
        self.pilsrc.pop(key, None)
        pd = self._predec.pop(key, None)
        if pd is not None and data:
            self.pilsrc[key] = pd
        if data:
            self.raw[key] = data
        else:
            self.raw.pop(key, None)
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
                self.raw.pop(k, None)
                self.pilsrc.pop(k, None)
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
        self.raw.clear()
        self.pilsrc.clear()
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
        self.zfrac = 0.0
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
        self.zfrac = 0.0
        self._dirty = True

    def _goto_selected(self):
        sel = self.tree.selection()
        p = next((p for p in self.players if sel and p.get("name") == sel[0]), None)
        if p:
            if p.get("world") != self.cur and p.get("world") in self.wset:
                self._set_world(p["world"])
            self.cx, self.cz = float(p["x"]), float(p["z"])
            self.zl = max(self.zl, self._max_native(self.cur) - 1)
            self.zfrac = 0.0
            self._dirty = True

    def _scale(self):
        return self._geometry()[2]  # pixels per blok (afgerond op hele tegelpixels, ook tijdens het soepele zoomen)

    # tijdens het zoomen: tegel van het volgende niveau verkleind met een kleine breuk (zoom p, subsample q) -> breedte in pixels

    def _zoom(self, d, mx=None, my=None):
        nz = max(0, min(self._max_zoom(), self.zl + d))
        if nz == self.zl:
            return
        W, H = max(self.cv.winfo_width(), 1), max(self.cv.winfo_height(), 1)
        if mx is None:
            mx, my = W / 2, H / 2
        old = self._scale()
        wx, wz = self.cx + (mx - W / 2) / old, self.cz + (my - H / 2) / old
        ze = self.zl + self.zfrac
        self._anim_from = round(ze)
        self.zl = nz
        nat = self._max_native(self.cur)
        # soepel alleen tussen de echte tegelniveaus (en alleen met Pillow); de extra vergrotingen daarbuiten springen gewoon
        self.zfrac = 0.0 if Image_ is None else max(-1.0, min(1.0, ze - nz))
        self._za = (time.time(), self.zfrac)
        self._anchor = (mx, my, wx, wz)
        self._nat = None
        self._fix_center()
        self._draw()
        if self.zfrac and self._anim_job is None:
            self._anim_job = self.after(5, self._anim_tick)

    def _fix_center(self):
        if not self._anchor:
            return
        mx, my, wx, wz = self._anchor
        W, H = max(self.cv.winfo_width(), 1), max(self.cv.winfo_height(), 1)
        sc = self._scale()
        self.cx, self.cz = wx - (mx - W / 2) / sc, wz - (my - H / 2) / sc

    def _anim_tick(self):
        """Tijdgestuurde animatie (ca. 0,3 s, eerst snel dan zacht): zoveel tussenbeelden als de computer aankan."""
        self._anim_job = None
        if not self.zfrac or not self._za:
            return
        t0, z0 = self._za
        t = (time.time() - t0) / 0.30
        self.zfrac = 0.0 if t >= 1 else z0 * (1 - t) ** 3
        if abs(self.zfrac) < 0.004:
            self.zfrac = 0.0
        self._fix_center()
        self._draw()
        if self.zfrac:
            self._anim_job = self.after(2, self._anim_tick)
        else:
            self._anchor = self._nat = None
            self._dirty = True

    def _wheel(self, ev):
        self._zoom(1 if (getattr(ev, "num", 0) == 4 or getattr(ev, "delta", 0) > 0) else -1, ev.x, ev.y)

    # ---------- tekenen ----------
    def _geometry(self):
        mx = self._max_native(self.cur)
        ze = self.zl + self.zfrac
        native = self._nat if (self.zfrac and self._nat is not None) else min(math.ceil(ze - 1e-9), mx)
        ex = ze - native
        span = self.TILE * 2 ** (mx - native)     # blokken per tegel
        wp = round(self.TILE * 2 ** round(ex)) if abs(ex - round(ex)) <= 1e-6 else max(8, round(self.TILE * 2 ** ex))
        self._wp = wp
        return native, span, wp / span

    def _view_keys(self, margin=0.5, wh=None):
        if not self.cur or (wh is None and self.cv.winfo_width() < 20):
            return []
        native, span, s = self._geometry()
        W, H = wh if wh else (self.cv.winfo_width(), self.cv.winfo_height())
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
                                 "Geen kaart gevonden.\nStart de server met squaremap en laat hem eerst renderen;\ndaarna staat de kaart ook offline klaar."))
            return
        if self.zfrac:
            self._nat = self._pick_native()
        native, span, s = self._geometry()
        ex = self.zl + self.zfrac - native
        extra = round(ex) if abs(ex - round(ex)) < 1e-6 else ex
        P = self._wp                                     # tegelgrootte op het scherm in pixels
        ox, oy = round(W / 2 - self.cx * s), round(H / 2 - self.cz * s)
        done = bool((self.zfrac or extra > 0) and Image_ is not None and self._comp(W, H, native, span))
        t_end = time.time() + (0.03 if not self.zfrac else 0.15)
        for key in ([] if done else sorted(self._view_keys(0.0), key=lambda k: abs(k[2] * span + span / 2 - self.cx) + abs(k[3] * span + span / 2 - self.cz))):
            if key in self.imgs:
                img = self.imgs[key]
                if img is not None and extra != round(extra):
                    img = self._pscaled(key, P, t_end)
                elif img is not None and extra > 0:
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

    def _comp(self, W, H, native, span):
        """Een zoomframe in een keer: tegels op echte resolutie aan elkaar plakken en het beeld met een enkele (vloeiende) schaling in het venster zetten.
        Veel sneller dan elke tegel afzonderlijk te schalen."""
        T = self.TILE
        s = self._wp / span
        x0, x1 = self.cx - W / 2 / s, self.cx + W / 2 / s
        z0, z1 = self.cz - H / 2 / s, self.cz + H / 2 / s
        tx0, tx1 = math.floor(x0 / span), math.floor(x1 / span)
        ty0, ty1 = math.floor(z0 / span), math.floor(z1 / span)
        if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 90:
            return False
        try:
            bg = tuple(v // 256 for v in self.cv.winfo_rgb(self.cv.cget("bg")))
        except tk.TclError:
            bg = (226, 232, 240)
        mos = Image_.new("RGB", ((tx1 - tx0 + 1) * T, (ty1 - ty0 + 1) * T), bg)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                key = (self.cur, native, tx, ty)
                if key not in self.imgs:
                    self.fetch_tile(key)
                    continue
                im = self._pilsrc(key) if self.imgs[key] is not None else None
                if im is not None:
                    mos.paste(im, ((tx - tx0) * T, (ty - ty0) * T), im)
        k = T / span
        box = ((x0 - tx0 * span) * k, (z0 - ty0 * span) * k, (x1 - tx0 * span) * k, (z1 - ty0 * span) * k)
        try:
            out = mos.resize((W, H), getattr(Image_, "Resampling", Image_).BILINEAR, box=box, reducing_gap=2.0)
            ci = getattr(self, "_compimg", None)
            if ci is not None and ci.width() == W and ci.height() == H:
                ci.paste(out)
            else:
                ci = self._compimg = ImageTk_.PhotoImage(out)
        except Exception:
            return False
        self.cv.create_image(0, 0, anchor="nw", image=ci, tags="t")
        return True

    def _pilsrc(self, key):
        im = self.pilsrc.get(key)
        if im is None:
            raw = self.raw.get(key)
            if not raw:
                return None
            try:
                im = Image_.open(io.BytesIO(raw)).convert("RGBA")
            except Exception:
                return None
            if len(self.pilsrc) > 100:
                self.pilsrc.clear()
            self.pilsrc[key] = im
        return im

    def _pscaled(self, key, wp, t_end):
        """Tegel op elke gewenste grootte (Pillow, vloeiend geschaald) voor het soepele zoomen."""
        zk = (key, ("p", wp))
        img = self.zimgs.get(zk)
        if img is None:
            if time.time() > t_end:
                self._dirty = True
                return None
            src = self._pilsrc(key)
            if src is None:
                return None
            try:
                img = ImageTk_.PhotoImage(src.resize((wp, wp), getattr(Image_, "Resampling", Image_).BILINEAR))
            except Exception:
                return None
            if len(self.zimgs) > 220:
                keep = {(k, ("p", wp)) for k in self._view_keys(0.0)}
                for old in [z for z in self.zimgs if z not in keep][:150]:
                    del self.zimgs[old]
            self.zimgs[zk] = img
        return img

    def _pick_native(self):
        """Tijdens het zoomen: kies het tegelniveau (oud of nieuw) dat voor het hele beeld al geladen is."""
        mx = self._max_native(self.cur)
        ze = self.zl + self.zfrac
        hi, lo = min(math.ceil(ze - 1e-9), mx), max(0, min(math.floor(ze + 1e-9), mx))
        if hi == lo:
            return hi
        W, H = self.cv.winfo_width(), self.cv.winfo_height()
        sc = 2.0 ** (ze - mx)
        for nat in (hi, lo):
            span = self.TILE * 2 ** (mx - nat)
            x0, x1 = self.cx - W / 2 / sc, self.cx + W / 2 / sc
            z0, z1 = self.cz - H / 2 / sc, self.cz + H / 2 / sc
            keys = [(self.cur, nat, tx, ty) for ty in range(math.floor(z0 / span), math.floor(z1 / span) + 1)
                    for tx in range(math.floor(x0 / span), math.floor(x1 / span) + 1)]
            if all(k in self.imgs for k in keys):
                return nat
            if nat == hi:
                for k in keys:
                    self.fetch_tile(k)
        return self._anim_from if self._anim_from in (hi, lo) else lo

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
        self._draw_area()
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
            hd = self.app.heads.photo(p.get("name", ""))
            if hd is not None:
                cv.create_rectangle(px - 14, py - 14, px + 14, py + 14, fill=col, outline="white", width=2, tags="o")
                cv.create_image(px, py, image=hd, tags="o")
            else:
                cv.create_oval(px - 7, py - 7, px + 7, py + 7, fill=col, outline="white", width=2, tags="o")
            if self.names_var.get():
                t = cv.create_text(px, py - 24, text=p.get("name", ""), fill="white", font=("Segoe UI", 9, "bold"), tags="o")
                bb = cv.bbox(t)
                r = cv.create_rectangle(bb[0] - 4, bb[1] - 1, bb[2] + 4, bb[3] + 1, fill="#111827", outline=col, tags="o")
                cv.tag_lower(r, t)

    # ---------- bediening ----------
    def _motion(self, ev):
        if self.sel_mode:
            return self._sel_motion(ev)
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
        if self.sel_mode:
            return self._sel_release(ev)
        self._drag = None
        if self._moved:
            self._moved = False
            self._draw()

    def _press(self, ev):
        if self.sel_mode and self.cur:
            self._selstart = self._c2w(ev.x, ev.y)
            self._seltmp = None
        else:
            self.zfrac, self._anchor = 0.0, None   # sleep stopt een lopende zoom-animatie
            self._drag = (ev.x, ev.y)
            self._dirty = True

    def _c2w(self, x, y):
        s = self._scale()
        return (self.cx + (x - self.cv.winfo_width() / 2) / s, self.cz + (y - self.cv.winfo_height() / 2) / s)

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

    # ---------- gebied kiezen + Chunky ----------
    def _build_gen(self):
        f = self.gen_fr = tk.Frame(self, bg="#111827", padx=10, pady=8)
        top = tk.Frame(f, bg="#111827")
        top.pack(fill="x")
        self.gen_title = tk.Label(top, text="", bg="#111827", fg="white", font=("Segoe UI", 10, "bold"), anchor="w")
        self.gen_title.pack(side="left")
        self.gen_close = self._btn(top, "✕", self.gen_hide, "#374151", "white")
        self.gen_close.pack(side="right", padx=(6, 0))
        self.gen_stop = self._btn(top, "■  Stop", self.gen_cancel, "#b91c1c", "white")
        self.gen_stop.pack(side="right", padx=(6, 0))
        self.gen_pause = self._btn(top, "⏸  Pauze", self.gen_toggle_pause, "#4b5563", "white")
        self.gen_pause.pack(side="right", padx=(6, 0))
        self.gen_start = self._btn(top, "▶  Start genereren", self.gen_begin, "#059669", "white")
        self.gen_start.pack(side="right", padx=(6, 0))
        mid = tk.Frame(f, bg="#111827")
        mid.pack(fill="x", pady=(8, 0))
        self.gen_pb = ttk.Progressbar(mid, mode="determinate", maximum=100)
        self.gen_pb.pack(side="left", fill="x", expand=True)
        self.gen_info = tk.Label(mid, text="", bg="#111827", fg="#d1d5db", font=("Segoe UI", 9), anchor="e", width=80)
        self.gen_info.pack(side="left", padx=(10, 0))
        self.gen_auto = tk.Checkbutton(f, text="Daarna automatisch de kaart bijwerken (squaremap)", variable=self.autorender_var,
                                       bg="#111827", fg="#d1d5db", selectcolor="#111827", activebackground="#111827",
                                       activeforeground="white", font=("Segoe UI", 9))
        self.gen_auto.pack(anchor="w", pady=(6, 0))
        row = tk.Frame(f, bg="#111827")
        row.pack(anchor="w", fill="x")
        for var, text, key in ((self.autopause_var, "Pauzeer zodra er een speler online komt", "chunky_autopause"),
                               (self.autoresume_var, "Hervat vanzelf als de server weer leeg is", "chunky_autoresume")):
            tk.Checkbutton(row, text=text, variable=var, bg="#111827", fg="#d1d5db", selectcolor="#111827",
                           activebackground="#111827", activeforeground="white", font=("Segoe UI", 9),
                           command=lambda v=var, k=key: self._save_opt(k, v)).pack(side="left", padx=(0, 16))

    def _save_opt(self, key, var):
        self.app.cfg[key] = bool(var.get())
        self.app._save_cfg()

    def _gen_players(self):
        """Namen van spelers die online zijn, zonder de namen die je bij Meldingen negeert (bijv. bots)."""
        ign = {x.strip().lower() for x in str(self.app.cfg.get("notify_ignore", "")).split(",") if x.strip()}
        return sorted(n for n in self.app.players if n.lower() not in ign)

    def players_changed(self, who=None):
        """Aangeroepen als iemand binnenkomt of weggaat: Chunky pauzeren of hervatten."""
        g, app = self.gen, self.app
        names = self._gen_players()
        if g.get("state") == "running" and self.autopause_var.get() and names:
            app.srv_send("chunky pause", echo=False)
            g.update(state="paused", auto=True, reason=f"{who or names[0]} is online gekomen" if who else
                     f"{', '.join(names[:3])} is online")
            app.log(f"Chunky gepauzeerd: {g['reason']}.", "warn")
            app.tab_beheer.notify("notify_chunky", "Chunky gepauzeerd", g["reason"])
            self._gen_refresh_ui()
            self._draw_overlay_only()
        elif g.get("state") == "paused" and g.get("auto") and not names and self.autoresume_var.get():
            app.srv_send("chunky continue", echo=False)
            g.update(state="running", auto=False, reason="")
            app.log("Chunky hervat: de server is weer leeg.", "ok")
            self._gen_refresh_ui()
            self._draw_overlay_only()
        elif g.get("state") == "waiting" and not names:
            self._gen_start_cmds()

    def gen_show(self):
        if not self.gen_fr.winfo_ismapped():
            self.gen_fr.pack(fill="x", before=self.coord_lbl, pady=(6, 0))

    def gen_hide(self):
        if self.gen["state"] in ("running", "paused", "waiting"):
            self.status_var.set("Er loopt nog een taak: stop of pauzeer die eerst")
            return
        self.gen = {"state": "idle"}
        self.sel = None
        self.gen_fr.pack_forget()
        self._draw_overlay_only()

    def toggle_sel(self, on=None):
        if self.gen["state"] in ("running", "paused", "rendering", "waiting"):
            self.status_var.set("Er loopt al een taak")
            return
        self.sel_mode = (not self.sel_mode) if on is None else on
        self.sel_btn.config(bg="#4c1d95" if self.sel_mode else "#7c3aed",
                            text="\U0001F4D0  Sleep een gebied op de kaart…" if self.sel_mode else "\U0001F4D0  Gebied genereren")
        self.cv.config(cursor="crosshair" if self.sel_mode else "fleur")
        self._selstart = None
        if self.sel_mode:
            self.status_var.set("")

    def _snap(self, a, b):
        x1, x2 = sorted((a[0], b[0]))
        z1, z2 = sorted((a[1], b[1]))
        return (math.floor(x1 / 16) * 16, math.floor(z1 / 16) * 16, (math.floor(x2 / 16) + 1) * 16, (math.floor(z2 / 16) + 1) * 16)

    def _sel_motion(self, ev):
        if not self._selstart:
            return
        self._seltmp = self._snap(self._selstart, self._c2w(ev.x, ev.y))
        self._draw_overlay_only()

    def _sel_release(self, ev):
        if not self._selstart:
            return
        r = self._snap(self._selstart, self._c2w(ev.x, ev.y))
        self._selstart = self._seltmp = None
        self.toggle_sel(False)
        if (r[2] - r[0]) < 32 or (r[3] - r[1]) < 32:
            self._draw_overlay_only()
            return
        self.sel = r
        self.gen = {"state": "ready", "world": self.cur, "area": r, "chunks": ((r[2] - r[0]) // 16) * ((r[3] - r[1]) // 16)}
        self._gen_refresh_ui()
        self._draw_overlay_only()

    def _draw_area(self):
        r = self._seltmp or (self.gen.get("area") if self.gen.get("world") == self.cur else None)
        if not r:
            return
        x1, y1 = self._w2c(r[0], r[1])
        x2, y2 = self._w2c(r[2], r[3])
        st = self.gen["state"]
        col = {"running": "#22c55e", "paused": "#f59e0b", "rendering": "#38bdf8", "done": "#22c55e"}.get(st, "#c084fc")
        self.cv.create_rectangle(x1, y1, x2, y2, outline=col, width=2, dash=(6, 3), fill=col, stipple="gray12", tags="o")
        cur = self.gen.get("cur")
        if cur and st in ("running", "paused"):
            cx, cy = self._w2c(cur[0] * 16 + 8, cur[1] * 16 + 8)
            self.cv.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="white", outline=col, width=2, tags="o")

    def _bukkit_world(self):
        lvl = read_properties(self.app.folder_var.get().strip()).get("level-name", "world")
        n = (self.cur or "").lower()
        return lvl + "_nether" if "nether" in n else lvl + "_the_end" if n.endswith("end") else lvl

    def _chunky_installed(self):
        try:
            return any(f.lower().startswith("chunky") and f.lower().endswith(".jar")
                       for f in os.listdir(os.path.join(self.app.folder_var.get().strip(), "plugins")))
        except OSError:
            return False

    @staticmethod
    def _fmt_n(n):
        return f"{int(n):,}".replace(",", ".")

    def _gen_refresh_ui(self):
        g, st = self.gen, self.gen["state"]
        self.gen_show()
        a = g.get("area")
        size = f"{a[2] - a[0]} × {a[3] - a[1]} blokken  ({self._fmt_n(g['chunks'])} chunks)" if a else ""
        pb = self.gen_pb
        pb.stop()
        pb.config(mode="determinate")
        for b in (self.gen_start, self.gen_pause, self.gen_stop):
            b.pack_forget()
        if st == "ready":
            self.gen_title.config(text="Gebied: " + size)
            self.gen_info.config(text="Klaar om te genereren")
            pb["value"] = 0
            self.gen_stop.pack(side="right", padx=(6, 0))
            self.gen_stop.config(text="✕  Ander gebied", command=lambda: (self.gen_hide(), self.toggle_sel(True)))
            self.gen_start.pack(side="right", padx=(6, 0))
        elif st == "waiting":
            self.gen_title.config(text="⏳  Wacht tot de server leeg is  •  " + size)
            self.gen_info.config(text="Chunky start zodra alle spelers weg zijn")
            self.gen_stop.config(text="✕  Annuleren", command=self.gen_cancel)
            self.gen_stop.pack(side="right", padx=(6, 0))
        elif st in ("running", "paused"):
            if st == "paused" and g.get("reason"):
                self.gen_title.config(text="⏸  Gepauzeerd: " + g["reason"])
                self.gen_info.config(text="Hervat vanzelf als de server weer leeg is" if self.autoresume_var.get() and g.get("auto")
                                     else "Klik op Hervat om verder te gaan")
            else:
                self.gen_title.config(text=("Chunks genereren" if st == "running" else "⏸  Gepauzeerd") + "  •  " + size)
            self.gen_stop.config(text="■  Stop", command=self.gen_cancel)
            self.gen_stop.pack(side="right", padx=(6, 0))
            self.gen_pause.config(text="⏸  Pauze" if st == "running" else "▶  Hervat")
            self.gen_pause.pack(side="right", padx=(6, 0))
        elif st == "rendering":
            self.gen_title.config(text="✔ Chunks klaar  •  kaart wordt bijgewerkt…")
            self.gen_info.config(text="De kaart ververst vanzelf zodra squaremap klaar is")
            pb.config(mode="indeterminate")
            pb.start(20)
        elif st == "done":
            self.gen_title.config(text="✔ Klaar  •  " + size)
            self.gen_info.config(text="")
            pb["value"] = 100

    def gen_begin(self):
        app = self.app
        if not app.srv_running() or app.srv_state != "online":
            messagebox.showinfo(APP_NAME, "De server draait niet. Start hem eerst op het tabblad Server.")
            return
        if not self._chunky_installed():
            messagebox.showinfo(APP_NAME, "Chunky staat niet in de plugins-map. Zet hem aan of installeer hem via het tabblad "
                                          "Plugins (zoeken: Chunky) en herstart de server.")
            return
        a = self.gen["area"]
        w = self._bukkit_world()
        if self.autopause_var.get() and self._gen_players():
            self.gen.update(state="waiting", bworld=w, reason="", auto=False)
            app.log("Chunky wacht tot de server leeg is (er zijn spelers online).", "info")
            self._gen_refresh_ui()
            self._draw_overlay_only()
            return
        self._gen_start_cmds()

    def _gen_start_cmds(self):
        app = self.app
        a = self.gen["area"]
        w = self.gen.get("bworld") or self._bukkit_world()
        self.gen.update(state="running", bworld=w, t0=time.time(), pct=0.0, done=0, reason="", auto=False)
        for c in (f"chunky world {w}", "chunky shape rectangle", f"chunky corners {a[0]} {a[1]} {a[2]} {a[3]}",
                  "chunky quiet 2", "chunky start"):
            app.srv_send(c, echo=False)
        app.log(f"Chunky gestart voor {w}: {a[0]},{a[1]} t/m {a[2]},{a[3]} ({self.gen['chunks']} chunks).", "info")
        self.gen_info.config(text="Starten…")
        self.gen_pb["value"] = 0
        self._gen_refresh_ui()
        self._draw_overlay_only()

    def gen_toggle_pause(self):
        st = self.gen["state"]
        if st == "running":
            self.app.srv_send("chunky pause", echo=False)
            self.gen["state"] = "paused"
        elif st == "paused":
            self.app.srv_send("chunky continue", echo=False)
            self.gen.update(state="running", reason="", auto=False)
        self._gen_refresh_ui()
        self._draw_overlay_only()

    def gen_cancel(self):
        if self.gen["state"] == "waiting":
            self.gen = {"state": "ready", "world": self.gen.get("world"), "area": self.gen.get("area"), "chunks": self.gen.get("chunks")}
            self._gen_refresh_ui()
            return
        if self.gen["state"] in ("running", "paused"):
            self.app.srv_send("chunky cancel", echo=False)
            self.gen = {"state": "ready", "world": self.gen.get("world"), "area": self.gen.get("area"), "chunks": self.gen.get("chunks")}
            self._gen_refresh_ui()
            self.gen_info.config(text="Gestopt")
            self._draw_overlay_only()

    def on_chunky(self, msg):
        """Leest een Chunky-regel uit de console. Geeft True terug als die regel bij de lopende taak hoorde."""
        km = re.search(r"Task (running|finished|paused|cancelled|canceled|stopped)\b", msg)
        if not km or self.gen["state"] not in ("running", "paused"):
            return False
        kind = km.group(1)
        pm = re.search(r"Processed:\s*(\d+) chunks \(([\d.,]+)%\)", msg)
        em = re.search(r"(?:ETA|Total time):\s*([\d:]+)", msg)
        rm = re.search(r"Rate:\s*([\d.,]+) cps", msg)
        cm = re.search(r"Current:\s*(-?\d+),\s*(-?\d+)", msg)
        done, pct = (pm.group(1), pm.group(2)) if pm else (None, None)
        eta, rate = (em.group(1) if em else None), (rm.group(1) if rm else None)
        cx, cz = (cm.group(1), cm.group(2)) if cm else (None, None)
        g = self.gen
        num = lambda x: float(x.replace(",", ".")) if x else 0.0
        if kind == "running":
            g["pct"] = num(pct)
            g["done"] = int(done or 0)
            if cx is not None:
                g["cur"] = (int(cx), int(cz))
            self.gen_pb["value"] = g["pct"]
            self.gen_info.config(text=f"{g['pct']:.1f} %  •  {self._fmt_n(g['done'])} / {self._fmt_n(g['chunks'])} chunks  •  "
                                      f"nog {eta or '?'}  •  {num(rate):.0f} chunks/s")
            self._dirty_overlay()
            return True
        if kind == "finished":
            g["pct"] = 100.0
            self.gen_pb["value"] = 100
            self.app.log("Chunky is klaar met genereren.", "ok")
            self._gen_finished()
            return True
        if kind in ("cancelled", "canceled", "stopped") and g["state"] != "ready":
            self.gen_cancel()
            return True
        return False

    def _dirty_overlay(self):
        now = time.time()
        if now - getattr(self, "_ov_t", 0) > 1.0:
            self._ov_t = now
            self._draw_overlay_only()

    def _gen_finished(self):
        g = self.gen
        a = g["area"]
        if self.autorender_var.get():
            cx, cz = (a[0] + a[2]) // 2, (a[1] + a[3]) // 2
            r = max(a[2] - a[0], a[3] - a[1]) // 2 + 32
            g["state"] = "rendering"
            self._fast_until = time.time() + 900
            self.cmd(f"radiusrender {{w}} {r} {cx} {cz}")
            self.after(60000, self._gen_render_done)
        else:
            g["state"] = "done"
        self.app.tab_beheer.notify("notify_chunky", "Gebied gegenereerd", f"Chunky is klaar ({g['chunks']} chunks).")
        self._gen_refresh_ui()
        self._draw_overlay_only()

    def _gen_render_done(self):
        if self.gen["state"] == "rendering":
            self.gen["state"] = "done"
            self._gen_refresh_ui()
            self.refresh(True)
            self._draw_overlay_only()

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


# --------------------------------------------------------------------------
# Bediening op afstand (telefoon): kleine beveiligde webserver in het programma
# --------------------------------------------------------------------------
def _png(w, h, rgb_rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rgb_rows)

    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(raw, 6)) + ch(b"IEND", b""))


# --------------------------------------------------------------------------
# Spelerskoppen (Java en Bedrock)
# --------------------------------------------------------------------------
def png_decode(data):
    """Leest een PNG (8 bit, niet-interlaced) en geeft (breedte, hoogte, rijen met (r,g,b,a)). Voor skins; zonder extra pakketten."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("geen PNG")
    pos, idat, plte, hdr = 8, b"", None, None
    while pos + 8 <= len(data):
        n, typ = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif typ == b"PLTE":
            plte = body
        elif typ == b"IDAT":
            idat += body
        pos += 12 + n
    if not hdr:
        raise ValueError("geen header")
    w, h, depth, ct, _c, _f, inter = hdr
    if depth != 8 or inter != 0 or ct not in (2, 3, 6):
        raise ValueError("PNG-soort niet ondersteund")
    bpp = {2: 3, 3: 1, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * bpp
    rows, prev = [], bytearray(stride)
    for y in range(h):
        off = y * (stride + 1)
        ft, line = raw[off], bytearray(raw[off + 1:off + 1 + stride])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                line[i] = (line[i] + a) & 255
            elif ft == 2:
                line[i] = (line[i] + b) & 255
            elif ft == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        rows.append(bytes(line))
        prev = line
    out = []
    for r in rows:
        px = []
        for x in range(w):
            if ct == 6:
                px.append(tuple(r[x * 4:x * 4 + 4]))
            elif ct == 2:
                px.append((r[x * 3], r[x * 3 + 1], r[x * 3 + 2], 255))
            else:
                i = r[x] * 3
                px.append((plte[i], plte[i + 1], plte[i + 2], 255))
        out.append(px)
    return w, h, out


def head_from_skin(skin_png, scale=6):
    """Knipt het gezicht (met hoed-laag) uit een skin en maakt er een PNG van (8 x 8 pixels, vergroot)."""
    w, h, px = png_decode(skin_png)
    if w < 48 or h < 16:
        raise ValueError("skin te klein")
    rows = []
    for y in range(8):
        row = []
        for x in range(8):
            r, g, b, a = px[8 + y][8 + x]
            hr, hg, hb, ha = px[8 + y][40 + x]
            if ha:
                f = ha / 255.0
                r, g, b = round(hr * f + r * (1 - f)), round(hg * f + g * (1 - f)), round(hb * f + b * (1 - f))
            row.append((r, g, b))
        rows.append(row)
    return _png(8 * scale, 8 * scale, [b"".join(bytes(p) * scale for p in row) for row in rows for _ in range(scale)])


def head_placeholder(name, scale=6):
    """Eigen simpel hoofdje (huidkleur van de naam, haar en ogen) voor als de skin niet op te halen is."""
    hh = zlib.crc32(name.lower().encode("utf-8", "replace"))
    skin = [(224, 172, 130), (198, 134, 96), (240, 200, 170), (160, 104, 72)][hh & 3]
    hair = [(60, 40, 25), (30, 30, 30), (150, 100, 40), (200, 170, 70), (120, 60, 30)][(hh >> 2) % 5]
    eye, mouth = (255, 255, 255), (150, 80, 70)
    grid = []
    for y in range(8):
        row = []
        for x in range(8):
            c = skin
            if y < 2 or (y == 2 and x in (0, 1, 6, 7)):
                c = hair
            elif y == 4 and x in (1, 2, 5, 6):
                c = eye if x in (1, 6) else (50, 70, 160)
            elif y == 6 and 2 <= x <= 5:
                c = mouth
            row.append(c)
        grid.append(row)
    return _png(8 * scale, 8 * scale, [b"".join(bytes(p) * scale for p in row) for row in grid for _ in range(scale)])


def floodgate_prefix(folder):
    try:
        with open(os.path.join(folder, "plugins", "floodgate", "config.yml"), encoding="utf-8") as fh:
            m = re.search(r"^username-prefix:\s*[\"']?([^\"'\n#]*)", fh.read(), re.M)
            if m:
                return m.group(1).strip()
    except OSError:
        pass
    return "."


def _http_bytes(url, timeout=8, limit=400000):
    rq = urllib.request.Request(url, headers={"User-Agent": "MC-Server-Manager"})
    with urllib.request.urlopen(rq, timeout=timeout) as r:
        return r.read(limit)


def fetch_head(name, bedrock, prefix):
    """Haalt de kop van een speler op. Java: via mc-heads.net. Bedrock: skin via de Geyser-API (xuid) en dan zelf uitknippen."""
    q = urllib.parse.quote
    if not bedrock:
        data = _http_bytes(f"https://mc-heads.net/avatar/{q(name)}/48")
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("geen afbeelding")
        return data
    gt = name[len(prefix):] if prefix and name.startswith(prefix) else name
    last = None
    for cand in dict.fromkeys((gt, gt.replace("_", " "))):
        try:
            xu = json.loads(_http_bytes(f"https://api.geysermc.org/v2/xbox/xuid/{q(cand)}").decode("utf-8")).get("xuid")
            if not xu:
                continue
            sk = json.loads(_http_bytes(f"https://api.geysermc.org/v2/skin/{xu}").decode("utf-8"))
            tid = sk.get("texture_id")
            if not tid and sk.get("value"):
                tex = json.loads(base64.b64decode(sk["value"]).decode("utf-8"))
                url = tex["textures"]["SKIN"]["url"]
            else:
                url = f"https://textures.minecraft.net/texture/{tid}"
            return head_from_skin(_http_bytes(url))
        except Exception as e:  # noqa
            last = e
    raise ValueError(f"skin niet gevonden ({last})")


class Heads:
    """Haalt spelerskoppen op (met opslag op schijf), toont ze in lijsten en op de kaart en levert ze aan de telefoon."""
    SIZE = 24

    def __init__(self, app):
        self.app = app
        self.dir = os.path.join(app_dir(), "heads")
        self.png, self.img, self.pending, self.watch = {}, {}, set(), []
        self.q = queue.Queue()
        self.on_change = []
        self.lock = threading.Lock()

    def _key(self, name):
        return name.lower()

    def _file(self, name, ext):
        return os.path.join(self.dir, hashlib.sha1(self._key(name).encode("utf-8")).hexdigest()[:16] + ext)

    def is_bedrock(self, name, typ=""):
        if typ:
            return typ.lower().startswith("bed")
        pre = floodgate_prefix(self.app.folder_var.get().strip()) if hasattr(self.app, "folder_var") else "."
        return bool(pre) and name.startswith(pre)

    def _load_disk(self, name):
        try:
            p = self._file(name, ".png")
            if os.path.isfile(p) and time.time() - os.path.getmtime(p) < 7 * 86400:
                with open(p, "rb") as fh:
                    d = fh.read()
                self.png[self._key(name)] = d
                return d
        except OSError:
            pass
        return None

    def _miss_recent(self, name):
        try:
            return time.time() - os.path.getmtime(self._file(name, ".miss")) < 3600
        except OSError:
            return False

    def _fetch(self, name, bedrock):
        d = None
        try:
            d = fetch_head(name, bedrock, floodgate_prefix(self.app.folder_var.get().strip()) if hasattr(self.app, "folder_var") else ".")
            os.makedirs(self.dir, exist_ok=True)
            with open(self._file(name, ".png"), "wb") as fh:
                fh.write(d)
        except Exception:
            d = None
            try:
                os.makedirs(self.dir, exist_ok=True)
                open(self._file(name, ".miss"), "w").close()
            except OSError:
                pass
        return d

    def request(self, name, typ=""):
        k = self._key(name)
        if not name or k in self.png or k in self.pending:
            return
        if self._load_disk(name) is not None or self._miss_recent(name):
            return
        self.pending.add(k)
        bed = self.is_bedrock(name, typ)

        def work():
            d = self._fetch(name, bed)
            self.q.put((k, d))
        threading.Thread(target=work, daemon=True).start()

    def png_bytes(self, name, typ=""):
        """Voor de telefoon (aanroep vanuit een andere thread): PNG-bytes, desnoods het eigen hoofdje."""
        k = self._key(name)
        d = self.png.get(k) or self._load_disk(name)
        if d is None and not self._miss_recent(name):
            d = self._fetch(name, self.is_bedrock(name, typ))
            if d:
                self.png[k] = d
        return d or head_placeholder(name)

    def photo(self, name, typ=""):
        """Hoofdje als afbeelding voor Tk (alleen hoofdthread). Zolang de skin er niet is: een eigen hoofdje."""
        k = self._key(name)
        self.request(name, typ)
        d = self.png.get(k)
        key = (k, bool(d))
        im = self.img.get(key)
        if im is None:
            try:
                im = tk.PhotoImage(data=base64.b64encode(d or head_placeholder(name)).decode("ascii"))
                f = max(1, im.width() // self.SIZE)
                if f > 1:
                    im = im.subsample(f, f)
            except tk.TclError:
                return None
            self.img[key] = im
        return im

    def pump(self):
        changed = False
        while True:
            try:
                k, d = self.q.get_nowait()
            except queue.Empty:
                break
            self.pending.discard(k)
            if d:
                self.png[k] = d
                for key in [x for x in self.img if x[0] == k]:
                    self.img.pop(key, None)
                changed = True
        if changed:
            self.sync()
            for fn in self.on_change:
                try:
                    fn()
                except Exception:
                    pass

    def watch_tree(self, tree, namefn, typfn=None):
        """Zet bij elke rij van de lijst het hoofdje van de speler (de rij moet als naam dienen of namefn(iid) geven)."""
        tree.configure(show="tree headings", style="Heads.Treeview")
        tree.column("#0", width=40, minwidth=40, stretch=False, anchor="center")
        tree.heading("#0", text="")
        self.watch.append((tree, namefn, typfn))

    def sync(self):
        for ent in list(self.watch):
            tree, namefn, typfn = ent
            try:
                if not tree.winfo_exists():
                    self.watch.remove(ent)
                    continue
                if not tree.winfo_ismapped():
                    continue
                for iid in tree.get_children():
                    nm = namefn(iid)
                    if not nm:
                        continue
                    im = self.photo(nm, typfn(iid) if typfn else "")
                    if im is not None and str(im) not in (tree.item(iid, "image") or ()):
                        tree.item(iid, image=im)
            except tk.TclError:
                pass


# ---------- Whitelist, bans en operators ----------
def offline_uuid(name):
    h = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    h[6] = (h[6] & 0x0F) | 0x30
    h[8] = (h[8] & 0x3F) | 0x80
    x = h.hex()
    return f"{x[:8]}-{x[8:12]}-{x[12:16]}-{x[16:20]}-{x[20:]}"


def mojang_uuid(name):
    try:
        data = http_json(f"https://api.mojang.com/users/profiles/minecraft/{urllib.parse.quote(name)}", timeout=6, retries=1)
        raw = (data or {}).get("id") or ""
        if len(raw) == 32:
            return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}", data.get("name") or name
    except Exception:
        pass
    return None, name


class ListsDialog(tk.Toplevel):
    """Whitelist, bans (spelers en IP-adressen) en operators bekijken en aanpassen, zonder commando's te typen."""
    KINDS = (
        ("whitelist", "Whitelist", "whitelist.json", (("name", "Speler", 170), ("uuid", "UUID", 280))),
        ("bans", "Bans", "banned-players.json", (("name", "Speler", 140), ("reason", "Reden", 240), ("created", "Sinds", 140), ("source", "Door", 90))),
        ("ips", "IP-bans", "banned-ips.json", (("name", "IP-adres", 140), ("reason", "Reden", 240), ("created", "Sinds", 140), ("source", "Door", 90))),
        ("ops", "Operators", "ops.json", (("name", "Speler", 170), ("level", "Niveau", 70), ("uuid", "UUID", 280))),
    )

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Whitelist en bans")
        self.transient(app)
        self.geometry("780x480")
        self.trees = {}
        top = ttk.Frame(self, padding=(10, 10, 10, 0))
        top.pack(fill="x")
        self.info = ttk.Label(top, text="")
        self.info.pack(side="left")
        make_btn(top, "↻  Vernieuwen", self.reload).pack(side="right")
        self.wl_btn = make_btn(top, "", self.toggle_whitelist)
        self.wl_btn.pack(side="right", padx=8)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)
        for key, title, _fn, cols in self.KINDS:
            fr = ttk.Frame(nb, padding=6)
            nb.add(fr, text=" " + title + " ")
            tr = ttk.Treeview(fr, columns=[c[0] for c in cols], show="headings", selectmode="extended")
            for cid, text, w in cols:
                tr.heading(cid, text=text)
                tr.column(cid, width=w, anchor="w")
            sb = ttk.Scrollbar(fr, orient="vertical", command=tr.yview)
            tr.configure(yscrollcommand=sb.set)
            bar = ttk.Frame(fr)
            bar.pack(side="bottom", fill="x", pady=(6, 0))
            make_btn(bar, "＋  Toevoegen…", lambda k=key: self.add(k), "#059669", "white").pack(side="left")
            make_btn(bar, "Verwijderen", lambda k=key: self.remove(k), "#dc2626", "white").pack(side="left", padx=6)
            tr.pack(side="left", fill="both", expand=True)
            sb.pack(side="left", fill="y")
            self.trees[key] = tr
        self.reload()

    # ---- bestanden ----
    def _folder(self):
        return self.app.folder_var.get().strip()

    def _path(self, key):
        fn = next(k[2] for k in self.KINDS if k[0] == key)
        return os.path.join(self._folder(), fn)

    def _read(self, key):
        try:
            with open(self._path(key), encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else []
        except (OSError, ValueError):
            return []

    def _write(self, key, data):
        with open(self._path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def reload(self):
        online = self.app.srv_state == "online"
        self.info.config(text=("Server draait: wijzigingen gaan met server-commando's." if online
                               else "Server staat uit: wijzigingen gaan rechtstreeks in de bestanden."))
        props = read_properties(self._folder())
        wl_on = props.get("white-list", "false").lower() == "true"
        self.wl_btn.config(text="Whitelist staat aan: uitzetten" if wl_on else "Whitelist staat uit: aanzetten")
        self._wl_on = wl_on
        for key, _t, _fn, cols in self.KINDS:
            tr = self.trees[key]
            tr.delete(*tr.get_children())
            for e in self._read(key):
                if key == "ips":
                    vals = (e.get("ip", ""), e.get("reason", ""), e.get("created", ""), e.get("source", ""))
                    iid = e.get("ip", "")
                elif key == "bans":
                    vals = (e.get("name", ""), e.get("reason", ""), e.get("created", ""), e.get("source", ""))
                    iid = e.get("name", "")
                elif key == "ops":
                    vals = (e.get("name", ""), e.get("level", ""), e.get("uuid", ""))
                    iid = e.get("name", "")
                else:
                    vals = (e.get("name", ""), e.get("uuid", ""))
                    iid = e.get("name", "")
                try:
                    tr.insert("", "end", iid=iid or None, values=vals)
                except tk.TclError:
                    pass

    # ---- acties ----
    def _online(self):
        return self.app.srv_state == "online"

    def _entry_for(self, name):
        """(uuid, naam) voor een speler, wanneer de server uit staat."""
        props = read_properties(self._folder())
        if name.startswith("."):
            raise ValueError("Bedrock-spelers kun je alleen toevoegen of verwijderen als de server draait.")
        if props.get("online-mode", "true").lower() == "false":
            return offline_uuid(name), name
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            uid, real = mojang_uuid(name)
        finally:
            self.config(cursor="")
        if not uid:
            raise ValueError(f"'{name}' niet gevonden bij Mojang (of geen internet). Controleer de naam.")
        return uid, real

    def add(self, key):
        what = "IP-adres" if key == "ips" else "spelernaam"
        name = simpledialog.askstring(APP_NAME, f"Voer de {what} in:", parent=self)
        name = (name or "").strip()
        if not name:
            return
        reason = ""
        if key in ("bans", "ips"):
            reason = simpledialog.askstring(APP_NAME, "Reden (mag leeg blijven):", parent=self) or ""
        if self._online():
            cmd = {"whitelist": f"whitelist add {name}", "bans": f"ban {name} {reason}".strip(),
                   "ips": f"ban-ip {name} {reason}".strip(), "ops": f"op {name}"}[key]
            self.app.srv_send(cmd)
            self.after(1500, self.reload)
            return
        try:
            data = self._read(key)
            now = time.strftime("%Y-%m-%d %H:%M:%S %z")
            if key == "ips":
                if any(e.get("ip") == name for e in data):
                    return
                data.append({"ip": name, "created": now, "source": "MC Server Manager", "expires": "forever", "reason": reason or "Banned by an operator."})
            else:
                uid, real = self._entry_for(name)
                if any(e.get("uuid") == uid for e in data):
                    messagebox.showinfo(APP_NAME, f"{real} staat al in deze lijst.", parent=self)
                    return
                if key == "whitelist":
                    data.append({"uuid": uid, "name": real})
                elif key == "ops":
                    data.append({"uuid": uid, "name": real, "level": 4, "bypassesPlayerLimit": False})
                else:
                    data.append({"uuid": uid, "name": real, "created": now, "source": "MC Server Manager",
                                 "expires": "forever", "reason": reason or "Banned by an operator."})
            self._write(key, data)
        except (ValueError, OSError) as e:
            messagebox.showwarning(APP_NAME, str(e), parent=self)
            return
        self.reload()

    def remove(self, key):
        sel = self.trees[key].selection()
        if not sel:
            return
        names = [self.trees[key].item(i, "values")[0] for i in sel]
        if not messagebox.askyesno(APP_NAME, "Verwijderen uit de lijst:\n\n" + "\n".join(names), parent=self):
            return
        if self._online():
            for n in names:
                self.app.srv_send({"whitelist": f"whitelist remove {n}", "bans": f"pardon {n}",
                                   "ips": f"pardon-ip {n}", "ops": f"deop {n}"}[key])
            self.after(1500, self.reload)
            return
        try:
            data = [e for e in self._read(key) if (e.get("ip") if key == "ips" else e.get("name")) not in names]
            self._write(key, data)
        except OSError as e:
            messagebox.showwarning(APP_NAME, str(e), parent=self)
        self.reload()

    def toggle_whitelist(self):
        new = not self._wl_on
        if self._online():
            self.app.srv_send("whitelist on" if new else "whitelist off")
            self.after(1500, self.reload)
            return
        path = os.path.join(self._folder(), "server.properties")
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                txt = f.read()
            val = "true" if new else "false"
            if re.search(r"(?m)^white-list=", txt):
                txt = re.sub(r"(?m)^white-list=.*$", "white-list=" + val, txt)
            else:
                txt += ("" if txt.endswith("\n") else "\n") + "white-list=" + val + "\n"
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
        except OSError as e:
            messagebox.showwarning(APP_NAME, str(e), parent=self)
        self.reload()


# ---------- Logboek doorzoeken ----------
LOG_KINDS = (
    ("Alles", None),
    ("Joinen", re.compile(r"joined the game|logged in with entity", re.I)),
    ("Verlaten", re.compile(r"left the game|lost connection", re.I)),
    ("Chat", re.compile(r"\]: (?:\[Not Secure\] )?<[^>]+> ")),
    ("Commando's", re.compile(r"issued server command|\]: \S+ issued", re.I)),
    ("Doodgaan", re.compile(r"was (?:slain|shot|killed|blown|burned|pricked|squashed|fireballed|pummeled|impaled|struck|doomed|hit|stung|skewered|obliterated|squished|poked|roasted)|"
                            r"\b(?:drowned|starved|suffocated|withered|died|froze|fell from|fell off|fell out|hit the ground|went up in flames|burned to death|"
                            r"tried to swim in lava|discovered the floor|experienced kinetic energy|blew up|was killed)\b", re.I)),
    ("Waarschuwingen en fouten", re.compile(r"/(?:WARN|ERROR|FATAL)\]")),
)
LOG_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
LOG_TIME_RE = re.compile(r"^\[(\d\d:\d\d:\d\d)")


def list_log_files(folder):
    """[(datum, pad)] van latest.log en alle (gecomprimeerde) oude logs, van oud naar nieuw."""
    d = os.path.join(folder, "logs")
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for fn in names:
        p = os.path.join(d, fn)
        if not os.path.isfile(p) or not (fn.endswith(".log") or fn.endswith(".log.gz")):
            continue
        m = LOG_DATE_RE.match(fn)
        date = m.group(1) if m else time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(p)))
        out.append((date, fn, p))
    out.sort()
    return out


def search_logs(folder, terms, player, kind_re, d_from, d_to, limit, emit, cancelled):
    """Zoekt in alle logbestanden. emit((datum, tijd, regel)) per treffer; geeft het aantal doorzochte bestanden terug."""
    terms = [t.lower() for t in terms]
    player = (player or "").lower()
    n = 0
    files = 0
    for date, fn, p in list_log_files(folder):
        if (d_from and date < d_from) or (d_to and date > d_to):
            continue
        if cancelled():
            break
        files += 1
        try:
            f = gzip.open(p, "rt", encoding="utf-8", errors="replace") if fn.endswith(".gz") else open(p, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with f:
            try:
                for line in f:
                    low = line.lower()
                    if terms and not all(t in low for t in terms):
                        continue
                    if player and player not in low:
                        continue
                    if kind_re is not None and not kind_re.search(line):
                        continue
                    tm = LOG_TIME_RE.match(line)
                    emit((date, tm.group(1) if tm else "", line.rstrip("\r\n")))
                    n += 1
                    if n >= limit or cancelled():
                        return files
            except (OSError, EOFError, zlib.error):
                continue
    return files


class LogSearchDialog(tk.Toplevel):
    LIMIT = 5000

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Logboek doorzoeken")
        self.transient(app)
        self.geometry("900x560")
        self.rq = queue.Queue()
        self.cancel = False
        self.busy = False
        self.v_term, self.v_player = tk.StringVar(), tk.StringVar()
        self.v_kind = tk.StringVar(value=LOG_KINDS[0][0])
        self.v_from, self.v_to = tk.StringVar(), tk.StringVar()
        f = ttk.Frame(self, padding=10)
        f.pack(fill="x")
        ttk.Label(f, text="Zoekwoord(en):").grid(row=0, column=0, sticky="w")
        e = ttk.Entry(f, textvariable=self.v_term, width=34)
        e.grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(f, text="Speler:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(f, textvariable=self.v_player, width=18).grid(row=0, column=3, sticky="w", padx=6)
        ttk.Label(f, text="Soort:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(f, textvariable=self.v_kind, state="readonly", width=24, values=[k[0] for k in LOG_KINDS]).grid(
            row=1, column=1, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(f, text="Van:").grid(row=1, column=2, sticky="w", padx=(12, 0), pady=(6, 0))
        pr = ttk.Frame(f)
        pr.grid(row=1, column=3, sticky="w", padx=6, pady=(6, 0))
        ttk.Entry(pr, textvariable=self.v_from, width=11).pack(side="left")
        ttk.Label(pr, text="  tot  ").pack(side="left")
        ttk.Entry(pr, textvariable=self.v_to, width=11).pack(side="left")
        ttk.Label(f, text="Datums als JJJJ-MM-DD (leeg = alles). Meerdere zoekwoorden: de regel moet ze allemaal bevatten.",
                  foreground="#6b7280").grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.btn = make_btn(f, "🔎  Zoeken", self.go, "#2563eb", "white")
        self.btn.grid(row=0, column=4, rowspan=2, padx=(14, 0), sticky="ns")
        e.bind("<Return>", lambda ev: self.go())
        self.status = tk.StringVar(value="Doorzoekt latest.log en alle oude logs (ook de .gz-bestanden) in de map logs.")
        ttk.Label(self, textvariable=self.status).pack(fill="x", padx=10)
        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree = ttk.Treeview(mid, columns=("when", "line"), show="headings", selectmode="extended")
        self.tree.heading("when", text="Datum en tijd")
        self.tree.heading("line", text="Regel")
        self.tree.column("when", width=140, anchor="w", stretch=False)
        self.tree.column("line", width=700, anchor="w")
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.full = tk.StringVar()
        ttk.Entry(self, textvariable=self.full, state="readonly").pack(fill="x", padx=10, pady=(0, 4))
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        make_btn(bar, "Kopieer selectie", self.copy).pack(side="left")
        self.tree.bind("<<TreeviewSelect>>", self._sel)
        self.protocol("WM_DELETE_WINDOW", self._close)
        e.focus_set()

    def _close(self):
        self.cancel = True
        self.destroy()

    def _sel(self, _e=None):
        sel = self.tree.selection()
        if sel:
            self.full.set(self.tree.item(sel[0], "values")[1])

    def copy(self):
        lines = [self.tree.item(i, "values")[1] for i in (self.tree.selection() or self.tree.get_children())]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))

    def go(self):
        if self.busy:
            self.cancel = True
            return
        for v in (self.v_from, self.v_to):
            if v.get().strip() and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.get().strip()):
                messagebox.showwarning(APP_NAME, "Vul datums in als JJJJ-MM-DD, bijvoorbeeld 2026-10-26.", parent=self)
                return
        folder = self.app.folder_var.get().strip()
        if not list_log_files(folder):
            self.status.set("Geen logbestanden gevonden in de map logs van de server.")
            return
        self.tree.delete(*self.tree.get_children())
        self.full.set("")
        terms = self.v_term.get().split()
        player = self.v_player.get().strip()
        kind_re = dict(LOG_KINDS)[self.v_kind.get()]
        d_from, d_to = self.v_from.get().strip(), self.v_to.get().strip()
        self.cancel, self.busy = False, True
        self.btn.config(text="■  Stoppen")
        self.status.set("Zoeken…")
        self.count = 0

        def work():
            files = search_logs(folder, terms, player, kind_re, d_from, d_to, self.LIMIT,
                                lambda r: self.rq.put(("hit", r)), lambda: self.cancel)
            self.rq.put(("done", files))
        threading.Thread(target=work, daemon=True).start()
        self.after(80, self._pump)

    def _pump(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        t_end = time.time() + 0.03
        while time.time() < t_end:
            try:
                m = self.rq.get_nowait()
            except queue.Empty:
                break
            if m[0] == "hit":
                d, t, line = m[1]
                self.tree.insert("", "end", values=((d + " " + t).strip(), line))
                self.count += 1
            else:
                self.busy = False
                self.btn.config(text="🔎  Zoeken")
                extra = f" (alleen de eerste {self.LIMIT}; maak je zoekopdracht specifieker)" if self.count >= self.LIMIT else ""
                self.status.set(f"{self.count} regel(s) gevonden in {m[1]} bestand(en).{extra}" if self.count
                                else f"Niets gevonden in {m[1]} bestand(en).")
                return
        if self.busy:
            self.status.set(f"Zoeken… {self.count} gevonden")
            self.after(60, self._pump)


# Hulpplugin voor Tab-aanvulling (bron: hulpplugin/MCMTab.java in de repository)
MCMTAB_JAR_B64 = (
    "UEsDBAoAAAgAAAWBWl0AAAAAAAAAAAAAAAADAAQAbmwv/soAAFBLAwQKAAAIAAAFgVpdAAAAAAAAAAAAAAAABwAAAG5sL21jbS9Q"
    "SwMEFAAICAgABYFaXQAAAAAAAAAAAAAAABMAAABubC9tY20vTUNNVGFiLmNsYXNzhVdrexPHFX7Hlj0raX2JuC7lIuoAEo4tYijB"
    "MjFYCqROJJNW5mK7SbqWx/bi9a6ykgymtOk1SZMmTdIrlKQhvdCkpE3SVrZxodD706ff+ql/of+g+VB6Zle2LCwIz8No9p1zzpz7"
    "Gf/jf9duANiHvwdQh3oOn4oGNDJst52J2GhxasooxHJmccKwYqf1GT32GC1PuN8MjQcNyyj0MtRHoicCUODnCKgIQmVosszYdHY6"
    "lk6mB/VRBv+EKKTsiQnhMGyORFOusGLBMGMmoYY1EfNOexQ0MyQ8trCeLRhiPB5OJ8MZ4cwIJ5zWLZ3IwlO6FbaKYSLq0HVrpmia"
    "JENYYTs34xCB1RlAK+7jCKlYg7UMG+92IYPPsMZthnURTylTp7NMwSGSnugJBesZ7iNndHrO6Ey4PwFshMaxScUnsJmhpcKZNPV8"
    "noGP286APi0YdtSSm7qDgczeSk4jJyXt6WndGkvrOXlHWMV2fNJzX1oUJu0xhsM1BI6sErjyCkeMmyJbiHkSejjuZ2itHB8bPU2n"
    "AezELo6Iiih2LzmsBjvF3bBm7CkyrXulJp6UKk3KUHQ1xPEAw7YKPGBnitlJ74IjZ7MiVzBsS0GnZ7kX+wDasEfFg+hiUKSnPE+v"
    "iaz2prRln4pPYT85NS8KfdmsyOeNUZOU9kWGoyc4DjDsWpHjWc/tsaRt5W1TlKOQEdaYcBTEGdSRp/o6hvWOc3s6up9UcJABAfTi"
    "EMdhFX1IVHnUiwpDwBE5U8+KPtNkOFAjbvdOjTLE8QjDhjvhRNEwXeWOUrbJeulLnA8giU/LCl4rd4+peBwpipeey5EhDB0fk4pV"
    "gnukiAEp4pgs2eS9CBV8RsVnkSGLs8v5y7A2UiP0Co4zbFlRUWWOzkrmKzhJ7qQQP27ZZ6wynucYomhW6pgIOUaoOivQoCNERlAq"
    "D6M+iFN4SsXT+Dx5YErMEk60Va2HoJ4gRpHlGFMhMF4l32VQjIJw9IJNfWJ9FW9/GScBkzA4TquYAkU5tJqE4jOp5wfE2YLbKocl"
    "h6XClv7yWQTLRHpGhQPZOGZ0syiOkSo7a1RXjeyQzEUVM/JybuSPTOcKsxI7q2IW5yRGOXxWCvRF+qP90jfnVXwRXyJl9LGxOxrf"
    "0j3DCr7MwPxS0ldVfA1fJ/7Ttmz7Vf0nOak7GfFMUVhZsTKbXdup3mpr/Bye53hBxTfx4lLduB5L6Hmxf5/XCI875iMia4+tnhge"
    "1f3lUxL3LbzM8YqKb+PVqk5fTUhpMObuZChrFMJIwo/X8R2O76r4Hr5PM9ClsQw7liUrqY0QKSWi7owlvW8KV8PxwaNPUy/ZlFpF"
    "XCZyA/RDWZQXqOVFRhJ3p5Tj5kcMwYI+SkmfM0VBcLzBEK7ZqFZ0KI4fUyOsGN7nOPpsyshTZr0pp/rbDM2VU3kQxGVkpWY/U/Fz"
    "XKE0Kbcq6ZxkjWLvkRznOd5dusg9G5x07DMyzgquUrpslzPrVyp+jfe9IGYMaYY3CKu7wXIuJPGhit9IBqVge2gQl/A7FSU5uIN5"
    "sjBN3ZumOqVg0o1fS8qwxEBxelQ4g7rb1RXbOmJ52yaKUnaKukP5KLA8UKiFXK9Sf/mE5oy91GgYxiOpj/N4zz0oanT1kRr5Nsxx"
    "ixLn7nI4/kTa1mAlmzJ20cmKo4Y0MOi9ljolHQ2qfssSjjsHhewn5eynd4RCTzz5zwcmH3m0ztHXFvqlYYaG3XNgH9CGYZ7WRhdc"
    "Q+vCMulOEiDRwO4SeKiphJYKfcAVvh5+bKAdzQJaJc8bqKfLgHRo3Tw2pNpDW+qvY2MJ2xj9tpWw4/10e6jjDmygo4TYMmXcp/l8"
    "JezVfB1LPHRpo3yCoZ2ukddvBad1E6GbCd1Cu63owDYcRBgJsv0anYbAbtNhHYfCiZlx4l4s++P39P8G/uAZWvciyWkhy2bbb+Gh"
    "Cwhovhu+t9Hgu6r56rtC3aGeEh6ONywiORQ6ModHtYYS+lvPl5CON5IXn4jz0CAZG1ck31s4pymhE2VbNF424SZOxf2LGB6aw+fi"
    "Ac2/gCelqymA8aAWXAC9Hi5gj9xNE6Rq6jxy8SaNnF64iHVaU2u8hDOXENQCEvvCySu3/6k1hp7VAvP4Cmlz8gouLqJ3aB7fIOd1"
    "lfDSh3htDj+I+0mZiw2kzFB96FJmyBfqzUgXB0gOJ7htqL6dUM1P6I54cBFvkoJv0f3BW7h8Ad1a8CYuL+AnpBMpU1azTe6kms2a"
    "qjWToq3+1nAJP13AL+pAmv3b1Uxd1mxjnBPyS/rQOAW6hPck3q41lvDBAn5bB99VCkQXG2Qn8U45wOMUOWAXveojFN4ouih4B/AA"
    "DlGYj6KT5nyMxuoeGikP4lU6fRd78R79YXONXoHXsR//wkP4j3z1oZv56UH3KHrYIA7RDQ+zIfQyE4fZGXrIyUR5CcFmShUB1U2V"
    "Sxw3OXo5/uiuSY42yh+OUxxUw5PA3o9Q91+03CYlmu/JQfud7v6yy/cRorehgtfkARIc76wl8/9MKtXhL/irW2aMxt1z+Bv8/wdQ"
    "SwcI6/2zvG0HAAC8DQAAUEsDBBQACAgIAAWBWl0AAAAAAAAAAAAAAAAKAAAAcGx1Z2luLnltbHWNuw7CMAxF93yFt4JEAxVbVhYY"
    "OsEPuKlVRUqcKI9+P6YgJAYmX1nnnssYyMB4GR84qZVycZENDPqkAjpJ7HWwQX8ATK7/Qt2gh3OnZio2u1S337X5lHxbHMMaYxYx"
    "3ClLBUZkXOTuxNMj8tq8d7yAkDOBjVyip72yMQTkuRgFIMMVp1cC+Fm5caXMhz8TG9+KRAPHt0M9AVBLBwidcD/GmQAAAOcAAABQ"
    "SwECCgAKAAAIAAAFgVpdAAAAAAAAAAAAAAAAAwAEAAAAAAAAAAAAAAAAAAAAbmwv/soAAFBLAQIKAAoAAAgAAAWBWl0AAAAAAAAA"
    "AAAAAAAHAAAAAAAAAAAAAAAAACUAAABubC9tY20vUEsBAhQAFAAICAgABYFaXev9s7xtBwAAvA0AABMAAAAAAAAAAAAAAAAASgAA"
    "AG5sL21jbS9NQ01UYWIuY2xhc3NQSwECFAAUAAgICAAFgVpdnXA/xpkAAADnAAAACgAAAAAAAAAAAAAAAAD4BwAAcGx1Z2luLnlt"
    "bFBLBQYAAAAABAAEAOMAAADJCAAAAAA="
)


def app_icon_png(size=192):
    """Eenvoudig app-icoon (grasblok) zonder afbeeldingsbestand."""
    g = ["GGGGGGGGGGGGGGGG", "GGgGGGGGgGGGGgGG", "GGGGGgGGGGGGGGGG", "GGGGGGGGGGGgGGGG", "DDDDDDDDDDDDDDDD", "DdDDDDdDDDDdDDDD",
         "DDDDDDDDDDDDDDdD", "DDDdDDDDDDDDDDDD", "DDDDDDDDDdDDDDDD", "DDdDDDDDDDDDDDDD", "DDDDDDdDDDDDDdDD", "DDDDDDDDDDDDDDDD",
         "DdDDDDDDDdDDDDDD", "DDDDDDDDDDDDDDDD", "DDDDdDDDDDDDdDDD", "DDDDDDDDDDDDDDDD"]
    pal = {"G": (91, 175, 52), "g": (70, 150, 40), "D": (134, 96, 67), "d": (110, 78, 52)}
    k = size // 16
    rows = []
    for y in range(16):
        row = []
        for x in range(16):
            row += list(pal[g[y][x]]) * k
        rows += [row] * k
    return _png(k * 16, k * 16, rows)


# ---------- Hulpfuncties voor de nieuwe interface ----------
LIST_FILES = {"whitelist": "whitelist.json", "bans": "banned-players.json", "ips": "banned-ips.json", "ops": "ops.json"}


def lists_read(folder, key):
    try:
        with open(os.path.join(folder, LIST_FILES[key]), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def lists_write(folder, key, data):
    with open(os.path.join(folder, LIST_FILES[key]), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def set_property(folder, key, val):
    path = os.path.join(folder, "server.properties")
    with open(path, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    if re.search(r"(?m)^" + re.escape(key) + "=", txt):
        txt = re.sub(r"(?m)^" + re.escape(key) + "=.*$", lambda m: f"{key}={val}", txt)
    else:
        txt += ("" if txt.endswith("\n") else "\n") + f"{key}={val}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def lists_file_add(folder, key, name, reason=""):
    """Voegt rechtstreeks in het bestand toe (server staat uit). Geeft (ok, bericht)."""
    data = lists_read(folder, key)
    now = time.strftime("%Y-%m-%d %H:%M:%S %z")
    if key == "ips":
        if any(e.get("ip") == name for e in data):
            return True, "Stond er al in"
        data.append({"ip": name, "created": now, "source": "MC Server Manager", "expires": "forever", "reason": reason or "Banned by an operator."})
    else:
        if name.startswith("."):
            return False, "Bedrock-spelers kun je alleen toevoegen als de server draait."
        if read_properties(folder).get("online-mode", "true").lower() == "false":
            uid, real = offline_uuid(name), name
        else:
            uid, real = mojang_uuid(name)
            if not uid:
                return False, f"'{name}' niet gevonden bij Mojang (of geen internet)."
        if any(e.get("uuid") == uid for e in data):
            return True, "Stond er al in"
        if key == "whitelist":
            data.append({"uuid": uid, "name": real})
        elif key == "ops":
            data.append({"uuid": uid, "name": real, "level": 4, "bypassesPlayerLimit": False})
        else:
            data.append({"uuid": uid, "name": real, "created": now, "source": "MC Server Manager", "expires": "forever",
                         "reason": reason or "Banned by an operator."})
    lists_write(folder, key, data)
    return True, "Toegevoegd"


def lists_file_remove(folder, key, names):
    data = [e for e in lists_read(folder, key) if (e.get("ip") if key == "ips" else e.get("name")) not in names]
    lists_write(folder, key, data)


def open_app_window(url):
    """Opent een adres in een eigen venster zonder adresbalk (Edge of Chrome in app-modus); anders gewoon de browser."""
    cands = []
    if os.name == "nt":
        for env in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
            base = os.environ.get(env)
            if base:
                cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    else:
        cands += [shutil.which(n) or "" for n in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser")]
    prof = os.path.join(app_dir(), "mc_server_manager_venster")
    for exe in cands:
        if exe and os.path.isfile(exe):
            try:
                subprocess.Popen([exe, "--app=" + url, "--window-size=1440,920", "--no-first-run", "--no-default-browser-check",
                                  "--user-data-dir=" + prof], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                return True
            except OSError:
                continue
    webbrowser.open(url)
    return False


# <<DESK_PAGE
DESK_PAGE = r"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MC Server Manager</title><link rel="icon" href="/icon.png"><style>
:root{color-scheme:dark;--bg:#0e1115;--side:#12161b;--card:#161a20;--in:#0f1318;--b:#232a33;--b2:#33404d;--t:#e7eaee;--m:#8e98a6;--m2:#aab3bf;--g:#3ddc97;--g2:#5be8a6;--bl:#6ea8fe;--a:#3b82f6;--y:#f5a524;--r:#ff8a93;--rb:#2a1519;--rbd:#5b2a30}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--t);font:14px/1.4 Inter,"Segoe UI",system-ui,sans-serif;display:flex;overflow:hidden}
svg.i{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:none}
aside{width:236px;flex:none;padding:20px 14px;display:flex;flex-direction:column;gap:20px;background:var(--side);border-right:1px solid var(--b);overflow:auto}
.logo{display:flex;align-items:center;gap:10px;padding:0 6px;font-weight:600;font-size:15px}
.logo i{width:30px;height:30px;border-radius:8px;background:var(--g);display:flex;align-items:center;justify-content:center;color:var(--bg)}
.srvbox{padding:10px 12px;border-radius:10px;background:#1a1f26;border:1px solid #28303a;display:flex;flex-direction:column;gap:1px}
.srvbox b{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.srvbox span{font-size:12px;color:var(--m)}
nav{display:flex;flex-direction:column;gap:2px}
nav a{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:8px;color:var(--m2);cursor:pointer;user-select:none}
nav a:hover{background:#181d24}nav a.on{background:#1f2630;color:#fff;font-weight:500}nav a.on svg{color:var(--g)}
nav a span.nm{flex:1}.bd{min-width:20px;padding:1px 7px;border-radius:99px;background:var(--y);color:#1a1204;font-size:12px;font-weight:600;text-align:center}
.sleepbox{margin-top:auto;display:flex;flex-direction:column;gap:10px;padding:14px;border-radius:12px;background:#171c23;border:1px solid #28303a}
.sleepbox .h{display:flex;align-items:center;justify-content:space-between;font-weight:600}.sleepbox small{font-size:12px;color:var(--m)}
.sw{width:34px;height:20px;border-radius:99px;background:#3a4452;position:relative;cursor:pointer;flex:none;transition:.15s}
.sw::after{content:"";position:absolute;left:3px;top:3px;width:14px;height:14px;border-radius:50%;background:var(--bg);transition:.15s}
.sw.on{background:var(--g)}.sw.on::after{left:17px}
main{flex:1;min-width:0;display:flex;flex-direction:column;padding:22px 28px;gap:18px;overflow:auto}
header{display:flex;align-items:center;gap:14px;flex:none}
h1{margin:0;font-size:22px;font-weight:600;letter-spacing:-.01em}
.pill{display:inline-flex;align-items:center;gap:8px;padding:5px 12px;border-radius:99px;font-weight:500;font-size:13px;background:#123024;color:var(--g2)}
.pill i{width:8px;height:8px;border-radius:50%;background:currentColor}
.pill.y{background:#2e2410;color:var(--y)}.pill.r{background:var(--rb);color:var(--r)}.pill.b{background:#14233d;color:var(--bl)}
.sp{flex:1}
button{font:inherit;cursor:pointer;color:var(--t);background:#171c23;border:1px solid var(--b2);border-radius:9px;padding:9px 16px;font-weight:500}
button:hover{background:#1d232b}button:disabled{opacity:.4;cursor:default}
button.sm{padding:5px 11px;font-size:13px;border-radius:7px}
button.pri{background:var(--a);border-color:var(--a);color:#fff;font-weight:600}button.pri:hover{background:#2f6fe0}
button.go{background:#12392a;border-color:#1f5a40;color:var(--g2)}button.bad{background:var(--rb);border-color:var(--rbd);color:var(--r)}
button.warn{background:#2e2410;border-color:#5b4414;color:var(--y)}button.ghost{background:transparent}
input,select,textarea{font:inherit;background:var(--in);border:1px solid var(--b);color:var(--t);border-radius:8px;padding:8px 11px;min-width:0}
input:focus,select:focus{outline:2px solid #2d4f8f;border-color:transparent}
input[type=checkbox]{width:18px;height:18px;accent-color:var(--a);padding:0;flex:none}
.card{padding:16px 18px;border-radius:14px;background:var(--card);border:1px solid var(--b);display:flex;flex-direction:column;gap:8px;min-width:0;min-height:0}
.card>h3{margin:0 0 4px;font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px}.card>h3 .sp{flex:1}
.tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;flex:none}
.tile{gap:6px}.tile .k{font-size:12px;color:var(--m);font-weight:500;text-transform:uppercase;letter-spacing:.06em}
.tile .v{font-size:28px;font-weight:600;letter-spacing:-.02em}.tile .v small{font-size:16px;color:var(--m);font-weight:500}
.tile canvas{width:100%;height:32px;display:block}.meter{height:8px;border-radius:99px;background:#222a34;margin-top:10px;overflow:hidden}.meter i{display:block;height:100%;background:var(--bl);transition:width .5s}
.mid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);gap:14px;height:210px;flex:none}
.low{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);gap:14px;flex:1;min-height:440px}
.two{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:14px;align-items:start}
.leg{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--m2);font-weight:400}.leg i{width:10px;height:3px;border-radius:2px}
canvas.big{flex:1;min-height:0;width:100%;display:block}
.pl{display:flex;align-items:center;gap:12px;padding:7px 0;border-top:1px solid var(--b)}.pl:first-of-type{border-top:0}
.pl .n{flex:1;min-width:0}.pl .n b{display:block;font-weight:500;overflow:hidden;text-overflow:ellipsis}.pl .n small{display:block;font-size:12px;color:var(--m)}
.skin{width:34px;height:34px;border-radius:7px;image-rendering:pixelated;background:#222a34;flex:none;display:flex;align-items:center;justify-content:center;font-weight:600;overflow:hidden}
.skin img{width:100%;height:100%;display:block;image-rendering:pixelated}
.skin.sm{width:22px;height:22px;border-radius:5px;font-size:11px}
.con{background:#0a0d11;border:1px solid var(--b);border-radius:14px;display:flex;flex-direction:column;min-height:0;overflow:hidden}
.con .bar{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #1c232b}
.con .log{flex:1;min-height:0;overflow:auto;padding:10px 16px;font:12.5px/1.7 "JetBrains Mono",Consolas,ui-monospace,monospace;white-space:pre-wrap;word-break:break-word}
.con .log div.e{color:#fca5a5}.con .log div.w{color:#f5c76a}.con .log div.o{color:var(--g2)}.con .log div.c{color:#b69cff}.con .log div{color:#c9d1db}
.con form{display:flex;align-items:center;gap:10px;padding:10px 12px;border-top:1px solid #1c232b}
.con form span{font-family:Consolas,monospace;color:var(--g)}.con form input{flex:1;background:transparent;border:0;font:12.5px Consolas,monospace;padding:6px}
.con form input:focus{outline:0}
.att{display:flex;align-items:center;gap:12px;padding:9px 0;border-top:1px solid var(--b)}.att:first-of-type{border-top:0}
.att .ic{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#123024;color:var(--g);flex:none}
.att .ic.y{background:#3a2a0c;color:var(--y)}.att .ic.r{background:var(--rb);color:var(--r)}.att .ic svg{width:14px;height:14px;stroke-width:2.6}
.att .tx{flex:1;min-width:0}.att .rt{font-size:12px;color:var(--m)}
.li{display:flex;gap:10px;align-items:center;padding:9px 0;border-top:1px solid var(--b)}.li:first-child{border-top:0}.li>div{flex:1;min-width:0}
.li b{display:block;overflow:hidden;text-overflow:ellipsis;font-weight:500}.li small{color:var(--m);display:block}
.tag{font-size:11px;border-radius:6px;padding:1px 6px;background:var(--b);margin-left:6px;font-weight:400}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.row>.sp{flex:1}
.lab{display:flex;gap:10px;align-items:center;justify-content:space-between;padding:8px 0;border-top:1px solid var(--b)}.lab:first-child{border-top:0}.lab>span{flex:1}.lab input:not([type=checkbox]),.lab select{width:46%;flex:none}
.mut{color:var(--m)}.ok{color:var(--g)}.err{color:var(--r)}.yel{color:var(--y)}.hide{display:none!important}
.bar2{height:10px;background:var(--in);border-radius:6px;overflow:hidden}.bar2 i{display:block;height:100%;background:var(--g);transition:width .5s}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:6px 4px;border-top:1px solid var(--b);text-align:left}th{color:var(--m);font-weight:600;border:0}td.n,th.n{text-align:right}
.seg{display:inline-flex;gap:2px;padding:2px;border-radius:8px;background:var(--in)}.seg button{border:0;background:transparent;color:var(--m);padding:4px 12px;font-size:12px;border-radius:6px}.seg button.on{background:#242c37;color:#fff}
#busy{height:3px;background:#1c232b;border-radius:3px;overflow:hidden;flex:none}#busy i{display:block;height:100%;background:var(--bl);transition:width .4s}
#busy.ind i{width:40%!important;animation:ind 1.2s infinite ease-in-out}@keyframes ind{0%{margin-left:-40%}100%{margin-left:100%}}
#toast{position:fixed;right:24px;bottom:24px;max-width:420px;background:#2b3440;border:1px solid var(--b2);padding:12px 16px;border-radius:12px;display:none;z-index:30;box-shadow:0 8px 30px #000a}
#dlg{position:fixed;inset:0;background:#000b;z-index:40;display:none;align-items:center;justify-content:center;padding:20px}#dlg .card{max-width:460px;width:100%;white-space:pre-wrap}
#off{position:fixed;inset:0;background:#0e1115ee;z-index:50;display:none;align-items:center;justify-content:center;text-align:center;padding:30px;font-size:16px}
#mapbox{position:relative;height:calc(100vh - 260px);min-height:360px;background:#0a0d11;border-radius:12px;overflow:hidden;touch-action:none}#mapbox canvas{width:100%;height:100%;display:block}
.mapbtn{position:absolute;right:10px;display:flex;flex-direction:column;gap:6px}.mapbtn button{width:38px;height:38px;padding:0;font-size:19px;background:#161a20dd}
.con.log2 .log{height:46vh;flex:none}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:#2a323c;border-radius:8px}::-webkit-scrollbar-track{background:transparent}
@media(max-width:1100px){.tiles{grid-template-columns:repeat(2,1fr)}.mid,.low,.two{grid-template-columns:1fr;height:auto}aside{width:200px}}
</style></head><body>
<aside>
 <div class="logo"><i><svg class="i" viewBox="0 0 24 24" style="stroke-width:2.4"><path d="M4 7l8-4 8 4v10l-8 4-8-4z"/><path d="M4 7l8 4 8-4M12 11v10"/></svg></i>MC Server Manager</div>
 <div class="srvbox"><b id="sname">Server</b><span id="sver">…</span></div>
 <nav id="nav"></nav>
 <div class="sleepbox"><div class="h">Auto slaapstand<div class="sw" id="swSleep" onclick="sleepAuto()" role="switch" tabindex="0"></div></div>
  <small id="sleepTx">Server stopt na een tijd zonder spelers en start vanzelf bij de eerste join.</small>
  <button id="btnSleep" onclick="sleepNow()">Nu in slaapstand</button></div>
 <button class="ghost sm" onclick="go('/api/classic')">Klassiek scherm</button>
</aside>
<main>
 <header><h1 id="ttl">Overzicht</h1><span class="pill" id="pill"><i></i><span id="pillTx">…</span></span><div class="sp"></div>
  <button class="go" id="bStart" onclick="act('start')">Starten</button><button id="bRestart" onclick="act('restart')">Herstarten</button><button class="bad" id="bStop" onclick="act('stop')">Stoppen</button></header>
 <div id="busy" class="hide"><i style="width:0"></i></div>
 <div id="view" style="display:flex;flex-direction:column;gap:18px;flex:1;min-height:0"></div>
</main>
<div id="toast"></div><div id="dlg"><div class="card"><div id="dmsg"></div><div class="row" style="margin-top:14px" id="dbtn"></div></div></div>
<div id="off">Verbinding met het programma is weg.<br><span class="mut" style="font-size:13px">Is MC Server Manager nog open? Dit scherm verbindt vanzelf opnieuw.</span></div>
<script>
const $=i=>document.getElementById(i);let S={},since=0,nsince=0,asince=0,busy=0,tab=(()=>{try{return localStorage.getItem('dtab')||'ov'}catch(e){return'ov'}})(),LOG=[],cur={},LOG2=[],fails=0;
const hd=(n,t)=>'/head/'+encodeURIComponent(n)+'?t='+encodeURIComponent(t||'');
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
function toast(t,ms=4500){const e=$('toast');e.textContent=t;e.style.display='block';clearTimeout(toast.t);toast.t=setTimeout(()=>e.style.display='none',ms)}
function ask(msg,yes='Ja',no='Annuleren'){return new Promise(r=>{$('dmsg').textContent=msg;$('dbtn').innerHTML='';
 for(const [t,v,c] of [[no,false,''],[yes,true,'pri']]){const b=document.createElement('button');b.textContent=t;b.className=c;b.onclick=()=>{$('dlg').style.display='none';r(v)};$('dbtn').appendChild(b)}$('dlg').style.display='flex'})}
async function api(p,b){let r;try{r=await fetch(p,b?{method:'POST',headers:{'Content-Type':'application/json','X-MC':'1'},body:JSON.stringify(b)}:{headers:{'X-MC':'1'}})}catch(e){toast('Geen verbinding met het programma');throw e}
 if(r.status==401){$('off').style.display='flex';$('off').firstChild.textContent='Open dit scherm via de knop "Nieuwe interface" in het programma.';throw 0}let j={};try{j=await r.json()}catch(e){}if(!r.ok&&j.error){toast(j.error);throw j.error}return j}
const go=async(p,b,msg)=>{try{const j=await api(p,b);if(msg||j.msg)toast(msg||j.msg);return j}catch(e){return null}};
const ico={ov:'<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
 con:'<path d="M4 17l6-6-6-6M12 19h8"/>',pl:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5M16 5.2a3.5 3.5 0 010 6.6M18 14.800c2 .6 3.200 2.500 3.500 5.200"/>',
 plug:'<path d="M10 4a2 2 0 114 0v2h4a1 1 0 011 1v4h-2a2 2 0 100 4h2v4a1 1 0 01-1 1h-4v-2a2 2 0 10-4 0v2H6a1 1 0 01-1-1v-4h2a2 2 0 100-4H5V7a1 1 0 011-1h4z"/>',
 upd:'<path d="M12 3v12M7 10l5 5 5-5M4 20h16"/>',
 map:'<path d="M9 4L3 6.500v13L9 17l6 2.500 6-2.500v-13L15 7zM9 4v13M15 7v12.500"/>',bk:'<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.700 3.600 3 8 3s8-1.300 8-3V6M4 12v6c0 1.700 3.600 3 8 3s8-1.300 8-3v-6"/>',
 set:'<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.900 4.900l2.100 2.100M17 17l2.100 2.100M4.900 19.100L7 17M17 7l2.100-2.100"/>'};
const TABS=[['ov','Overzicht'],['con','Console'],['pl','Spelers'],['plug','Plugins'],['upd','Updates'],['map','Kaart'],['bk','Backups'],['set','Instellingen']];
function build(){$('nav').innerHTML=TABS.map(t=>`<a data-t="${t[0]}" onclick="setTab('${t[0]}')"><svg class="i" viewBox="0 0 24 24">${ico[t[0]==='plug'?'plug':t[0]]}</svg><span class="nm">${t[1]}</span><span class="bd hide" id="bd-${t[0]}"></span></a>`).join('');setTab(TABS.some(t=>t[0]==tab)?tab:'ov')}
function setTab(t){if(cur.stop)cur.stop();cur={};tab=t;try{localStorage.setItem('dtab',t)}catch(e){}
 document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('on',a.dataset.t==t));$('ttl').textContent=TABS.find(x=>x[0]==t)[1];$('view').innerHTML='';(V[t]||V.ov)();if(S.stats)draw()}
const V={};
/* ---------- helpers ---------- */
const num=s=>{const m=String(s==null?'':s).replace(',','.').match(/-?\d+(\.\d+)?/);return m?parseFloat(m[0]):null};
function spark(id,d,col,lo,hi){const c=$(id);if(!c)return;const w=c.clientWidth||100,h=c.clientHeight||32,dpr=window.devicePixelRatio||1;c.width=w*dpr;c.height=h*dpr;const x=c.getContext('2d');x.scale(dpr,dpr);
 d=(d||[]).filter(v=>v!=null);if(d.length<2)return;let l=lo!=null?lo:Math.min(...d),hh=hi!=null?hi:Math.max(...d);if(hh-l<1e-6){hh=l+1}
 x.strokeStyle=col;x.lineWidth=2;x.lineJoin='round';x.beginPath();d.forEach((v,i)=>{const X=i/(d.length-1)*w,Y=h-2-(Math.min(Math.max(v,l),hh)-l)/(hh-l)*(h-4);i?x.lineTo(X,Y):x.moveTo(X,Y)});x.stroke()}
function bigChart(id,series){const c=$(id);if(!c)return;const w=c.clientWidth||600,h=c.clientHeight||150,dpr=window.devicePixelRatio||1;c.width=w*dpr;c.height=h*dpr;const x=c.getContext('2d');x.scale(dpr,dpr);
 x.strokeStyle='#232a33';x.lineWidth=1;for(let i=0;i<4;i++){const y=10+i*(h-20)/3;x.beginPath();x.moveTo(0,y);x.lineTo(w,y);x.stroke()}
 x.fillStyle='#6b7684';x.font='11px sans-serif';[100,66,33,0].forEach((v,i)=>x.fillText(v+'%',4,10+i*(h-20)/3-3));
 for(const [d,col] of series){if(!d||d.length<2)continue;x.strokeStyle=col;x.lineWidth=2.5;x.lineJoin='round';x.beginPath();d.forEach((v,i)=>{const X=i/(d.length-1)*w,Y=h-10-Math.min(Math.max(v,0),100)/100*(h-20);i?x.lineTo(X,Y):x.moveTo(X,Y)});x.stroke()}}
function skin(n,t,cls){const d=document.createElement('span');d.className='skin '+(cls||'');const im=new Image();im.src=hd(n,t);im.alt='';im.onerror=()=>{im.remove();d.textContent=(n.replace(/^\./,'')[0]||'?').toUpperCase()};d.appendChild(im);return d}
function skinHtml(n,t,cls){return `<span class="skin ${cls||''}"><img src="${hd(n,t)}" alt="" onerror="this.remove();"></span>`}
function ago(ts){const s=Math.max(0,Date.now()/1000-ts);return s<90?'zojuist':s<5400?Math.round(s/60)+' min geleden':s<172800?Math.round(s/3600)+' uur geleden':Math.round(s/86400)+' dagen geleden'}
const fb2=n=>n>1e9?(n/1e9).toFixed(1).replace('.',',')+' GB':n>1e6?(n/1e6).toFixed(0)+' MB':Math.round(n/1e3)+' kB';
const dt=t=>new Date(t*1000).toLocaleString('nl',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'});
const OKI='<svg class="i" viewBox="0 0 24 24"><path d="M5 12.500l4.500 4.500L19 7.500"/></svg>',WARNI='<svg class="i" viewBox="0 0 24 24"><path d="M12 7v6M12 17h.01"/></svg>';
/* ---------- Overzicht ---------- */
V.ov=()=>{$('view').innerHTML=`<section class="tiles">
 <div class="card tile"><span class="k">TPS</span><span class="v" id="vTps">-</span><canvas id="sTps"></canvas></div>
 <div class="card tile"><span class="k">Spelers</span><span class="v" id="vPl">-</span></div>
 <div class="card tile"><span class="k">Temperatuur</span><span class="v" id="vTmp">-</span><canvas id="sTmp"></canvas></div></section>
 <section class="mid"><div class="card"><h3>Belasting <span class="leg"><i style="background:#6ea8fe"></i>Geheugen <b id="lgRam" style="color:var(--t)"></b></span><span class="leg"><i style="background:#f5a524"></i>Processor <b id="lgCpu" style="color:var(--t)"></b></span></h3><canvas class="big" id="cBig"></canvas></div>
 <div class="card"><h3>Spelers online <span class="sp"></span><a class="mut" style="cursor:pointer;font-size:13px;color:var(--bl)" onclick="setTab('pl')">Alles beheren</a></h3><div id="ovPl" style="overflow:auto"></div></div></section>
 <section class="low"><div class="con"><div class="bar"><b>Console</b><span class="mut" style="font-size:12px" id="cleanTx"></span><div class="sp"></div></div><div class="log" id="con"></div>
 <form onsubmit="return send('cmd')"><span>&gt;</span><input id="cmd" placeholder="Typ een commando" autocomplete="off" autocapitalize="off" spellcheck="false" onkeydown="cmdKey(event)"><button class="pri sm">Verstuur</button></form></div>
 <div class="card"><h3>Aandacht</h3><div id="att"></div></div></section>`;
 LOG.forEach(addLine);cur.bk=null;attBackup();cur.t=setInterval(attBackup,60000);cur.stop=()=>clearInterval(cur.t)};
async function attBackup(){const j=await go('/api/backuper');if(!j||!$('att'))return;cur.bkInfo=j.backups&&j.backups.length?{ago:ago(j.backups[0].mtime),size:fb2(j.backups[0].size)}:(j.jar?{none:1}:null);drawAtt()}
function att(cls,icon,text,right,btn){return `<div class="att"><span class="ic ${cls}">${icon}</span><span class="tx">${text}</span>${btn||''}${right?`<span class="rt">${right}</span>`:''}</div>`}
function drawAtt(){const e=$('att');if(!e||!S.stats)return;const j=S;let h='';
 if(j.selfupd)h+=att('y',WARNI,'Nieuwe programmaversie '+esc(j.selfupd),'',`<button class="sm" onclick="setTab('upd')">Bekijken</button>`);
 if(j.paperupd)h+=att('y',WARNI,'Paper-update beschikbaar','',`<button class="sm" onclick="setTab('plug')">Bekijken</button>`);
 if(j.pupd)h+=att('y',WARNI,j.pupd+' plugin-update'+(j.pupd>1?'s':'')+' beschikbaar','',`<button class="sm" onclick="setTab('plug')">Bekijken</button>`);
 const b=cur.bkInfo;if(b&&b.ago)h+=att('',OKI,'Laatste backup '+b.ago,b.size);else if(b&&b.none)h+=att('y',WARNI,'Nog geen backups gevonden','');
 if(j.disk!=null)h+=att(j.disk<5?'r':'',j.disk<5?WARNI:OKI,'Schijf: '+j.disk.toFixed(0)+' GB vrij','');
 if(j.sleep&&j.sleep.on)h+=att('',OKI,j.sleep.sleeping?'De server slaapt en start bij de eerste join':'Auto slaapstand staat aan',esc(j.stats.sleep&&j.stats.sleep!='-'?j.stats.sleep:''));
 if(j.status&&j.state!='stopped'&&j.busy)h+=att('y',WARNI,esc(j.status),'');
 e.innerHTML=h||'<span class="mut">Alles in orde.</span>'}
/* ---------- Console ---------- */
const CMDS=['list','say ','whitelist add ','whitelist remove ','whitelist list','ban ','pardon ','kick ','op ','deop ','gamemode ','tp ','time set ','weather ','difficulty ','save-all','stop','tps','seed','give ','kill ','effect '];
const HIST=(()=>{try{return JSON.parse(localStorage.getItem('dhist')||'[]')}catch(e){return[]}})();let hi=-1;
function cmdKey(e){const i=e.target;if(e.key=='ArrowUp'){if(hi<HIST.length-1){hi++;i.value=HIST[hi]}e.preventDefault()}else if(e.key=='ArrowDown'){hi=Math.max(-1,hi-1);i.value=hi<0?'':HIST[hi];e.preventDefault()}
 else if(e.key=='Tab'){e.preventDefault();const v=i.value.toLowerCase();if(!v)return;const m=CMDS.filter(c=>c.startsWith(v));if(m.length==1)i.value=m[0];else if(m.length>1){let p=m[0];for(const c of m)while(!c.startsWith(p))p=p.slice(0,-1);i.value=p;toast(m.join('   '),3500)}}}
function send(id){const i=$(id||'cmd'),v=i.value.trim();if(v){HIST.unshift(v);HIST.splice(50);hi=-1;try{localStorage.setItem('dhist',JSON.stringify(HIST))}catch(e){}go('/api/cmd',{cmd:v}).then(j=>{if(j&&j.ok===false)toast(j.msg)});i.value='';setTimeout(poll,500)}return false}
function addLine(l){const c=$('con');if(!c)return;const f=($('cfilter')||{}).value;if(f&&!l[1].toLowerCase().includes(f.toLowerCase()))return;const bot=c.scrollHeight-c.scrollTop-c.clientHeight<40;const d=document.createElement('div');d.className=l[2];d.textContent=l[1];c.appendChild(d);
 while(c.childElementCount>600)c.removeChild(c.firstChild);if(bot)c.scrollTop=c.scrollHeight}
V.con=()=>{$('view').innerHTML=`<div class="seg" style="align-self:flex-start"><button class="on" id="mLive" onclick="conMode(0)">Live console</button><button id="mSrch" onclick="conMode(1)">Logboek doorzoeken</button></div>
 <div id="conLive" style="display:flex;flex-direction:column;flex:1;min-height:0"><div class="con" style="flex:1"><div class="bar"><b>Console</b><label class="mut" style="display:flex;gap:6px;align-items:center;font-size:12px"><input type="checkbox" id="clean" onchange="go('/api/clean',{on:this.checked})">schoon</label><div class="sp"></div>
 <input id="cfilter" placeholder="Filter…" style="width:180px" oninput="refilter()"></div><div class="log" id="con"></div>
 <form onsubmit="return send('cmd')"><span>&gt;</span><input id="cmd" placeholder="Typ een commando. Tab vult aan, pijltje omhoog haalt het vorige terug" autocomplete="off" autocapitalize="off" spellcheck="false" onkeydown="cmdKey(event)"><button class="pri sm">Verstuur</button></form></div></div>
 <div id="conSrch" style="display:none;flex-direction:column;gap:12px;flex:1;min-height:0"></div>`;LOG.forEach(addLine);$('cmd').focus()};
function refilter(){const c=$('con');c.innerHTML='';LOG.forEach(addLine)}
function conMode(m){$('mLive').classList.toggle('on',!m);$('mSrch').classList.toggle('on',!!m);$('conLive').style.display=m?'none':'flex';$('conSrch').style.display=m?'flex':'none';if(m&&!$('conSrch').innerHTML)srchUI()}
const KINDS=['Alles','Joinen','Verlaten','Chat',"Commando's",'Doodgaan','Waarschuwingen en fouten'];
function srchUI(){$('conSrch').innerHTML=`<div class="card"><div class="row"><input id="sq" placeholder="Zoekwoord(en)" style="flex:2" onkeydown="if(event.key=='Enter')srch()"><input id="sp" placeholder="Speler" style="flex:1"><select id="sk">${KINDS.map(k=>`<option>${k}</option>`).join('')}</select>
 <input id="sf" type="date" title="Van"><input id="st" type="date" title="Tot"><button class="pri" onclick="srch()">Zoek</button></div><div class="mut" style="font-size:12px" id="sinfo">Doorzoekt latest.log en alle oude logs, ook de gecomprimeerde.</div></div>
 <div class="con" style="flex:1"><div class="log" id="sres"></div></div>`}
async function srch(){$('sinfo').textContent='Zoeken…';const j=await go('/api/logsearch',{q:$('sq').value,player:$('sp').value,kind:$('sk').value,from:$('sf').value,to:$('st').value});if(!j)return;
 $('sres').innerHTML=j.rows.map(r=>`<div><span class="mut">${esc(r[0])} ${esc(r[1])}</span>  ${esc(r[2].replace(/^\[[\d:]+\]\s*/,''))}</div>`).join('')||'<div class="mut">Niets gevonden.</div>';
 $('sinfo').textContent=`${j.rows.length}${j.limit?'+':''} regels gevonden in ${j.files} logbestand${j.files==1?'':'en'}${j.limit?' (maximaal 500 getoond, maak je zoekopdracht specifieker)':''}.`}
/* ---------- Spelers ---------- */
function plDlg(n,t){const acts=[['kick','Kick'],['ban','Ban'],['pardon','Pardon'],['op','Op'],['deop','Deop'],['whitelist_add','Whitelist +'],['whitelist_remove','Whitelist −'],['gm','Gamemode'],['tp','Tp naar speler'],['msg','Bericht']];
 $('dmsg').textContent='Speler: '+n;$('dbtn').innerHTML='';
 for(const [a,tt] of acts){const b=document.createElement('button');b.className='sm';b.textContent=tt;b.onclick=async()=>{let arg='';
  if(['kick','ban'].includes(a))arg=prompt('Reden (mag leeg):')||'';else if(a=='gm'){arg=prompt('survival, creative, adventure of spectator:','survival')||''}else if(a=='tp'){arg=prompt('Naar welke speler?')||'';if(!arg)return}else if(a=='msg'){arg=prompt('Bericht:')||'';if(!arg)return}
  if(['ban','kick','op','deop'].includes(a)&&!await ask(tt+' '+n+'?'))return;$('dlg').style.display='none';go('/api/player',{name:n,action:a,arg},tt+' '+n)};$('dbtn').appendChild(b)}
 const c=document.createElement('button');c.className='sm ghost';c.textContent='Sluiten';c.onclick=()=>$('dlg').style.display='none';$('dbtn').appendChild(c);$('dlg').style.display='flex'}
V.pl=()=>{$('view').innerHTML=`<div class="two"><div style="display:flex;flex-direction:column;gap:14px"><div class="card"><h3>Online nu <span class="mut" id="pn"></span></h3><div id="plOn"></div></div>
 <div class="card"><h3>Speelstatistieken <button class="sm" onclick="behP()">↻</button></h3><div id="bp" class="mut">Laden…</div></div></div>
 <div style="display:flex;flex-direction:column;gap:14px"><div class="card"><h3>Whitelist <span class="sp"></span><label class="mut" style="font-weight:400;display:flex;gap:6px;align-items:center;font-size:13px">Whitelist actief<input type="checkbox" id="wlOn" onchange="wlToggle(this.checked)"></label></h3><div id="L-whitelist"></div></div>
 <div class="card"><h3>Gebande spelers</h3><div id="L-bans"></div></div><div class="card"><h3>Gebande IP-adressen</h3><div id="L-ips"></div></div><div class="card"><h3>Operators</h3><div id="L-ops"></div></div></div></div>`;
 behP();listsLoad()};
function plOnline(){const e=$('plOn');if(!e)return;$('pn').textContent='('+S.players.length+')';e.innerHTML=S.players.length?'':'<span class="mut">Niemand online.</span>';
 for(const p of S.players){const d=document.createElement('div');d.className='pl';d.appendChild(skin(p.name,p.type));const n=document.createElement('span');n.className='n';n.innerHTML=`<b>${esc(p.name)}</b><small>${esc(p.type||'Java')}${p.since?' · '+esc(p.since):''}</small>`;d.appendChild(n);
  const b=document.createElement('button');b.className='sm';b.textContent='Beheren';b.onclick=()=>plDlg(p.name,p.type);d.appendChild(b);e.appendChild(d)}}
async function listsLoad(){const j=await go('/api/lists');if(!j||!$('L-bans'))return;cur.lists=j;if($('wlOn'))$('wlOn').checked=!!j.whitelist_on;
 const mk=(k,ph,rsn)=>{const arr=j[k]||[];const key=e=>k=='ips'?e.ip:e.name;
  return (arr.length?arr.map(e=>`<div class="li">${k=='ips'?'':skinHtml(e.name,'','sm')}<div><b>${esc(key(e))}</b>${k=='bans'||k=='ips'?`<small>${esc(e.reason||'')}${e.created?' · '+esc(String(e.created).slice(0,10)):''}</small>`:''}</div><button class="sm ghost" onclick="listRm('${k}','${esc(key(e)).replace(/'/g,"\\'")}')">Verwijderen</button></div>`).join(''):'<span class="mut">Leeg.</span>')+
  `<div class="row" style="margin-top:8px"><input id="a-${k}" placeholder="${ph}" style="flex:1" onkeydown="if(event.key=='Enter')listAdd('${k}')">${rsn?`<input id="r-${k}" placeholder="Reden (optioneel)" style="flex:1">`:''}<button class="sm pri" onclick="listAdd('${k}')">Toevoegen</button></div>`};
 $('L-whitelist').innerHTML=mk('whitelist','Spelersnaam');$('L-bans').innerHTML=mk('bans','Spelersnaam',1);$('L-ips').innerHTML=mk('ips','IP-adres',1);$('L-ops').innerHTML=mk('ops','Spelersnaam')}
async function listAdd(k){const n=$('a-'+k).value.trim();if(!n)return;const r=$('r-'+k);const j=await go('/api/lists/add',{list:k,name:n,reason:r?r.value:''});if(j&&j.ok!==false){setTimeout(listsLoad,S.state=='online'?900:100)}}
async function listRm(k,n){if(!await ask(n+' uit deze lijst halen?'))return;await go('/api/lists/remove',{list:k,name:n});setTimeout(listsLoad,S.state=='online'?900:100)}
async function wlToggle(on){const j=await go('/api/props',{key:'white-list',value:on});if(S.state=='online')go('/api/cmd',{cmd:'whitelist '+(on?'on':'off')})}
async function behP(){const dur=s=>{s=Math.round(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return h?`${h}u ${m}m`:`${m}m`};const j=await go('/api/stats');if(!j||!$('bp'))return;j.rows.sort((a,b)=>b.online-a.online||b.time-a.time);
 $('bp').innerHTML=j.rows.length?`<table><tr><th>Speler</th><th class="n">Tijd</th><th class="n">Dood</th><th class="n">Kills</th><th class="n">km</th></tr>`+j.rows.map(r=>`<tr><td style="display:flex;align-items:center;gap:8px">${skinHtml(r.name,'','sm')}${esc(r.name)}${r.online?' <span class="ok">●</span>':''}</td><td class="n">${dur(r.time)}</td><td class="n">${r.deaths}</td><td class="n">${r.kills}</td><td class="n">${(r.dist/1000).toFixed(1)}</td></tr>`).join('')+'</table>':'Geen spelersgegevens gevonden.'}
/* ---------- Plugins ---------- */
V.plug=async()=>{$('view').innerHTML=`<div class="card"><h3>Plugins <button class="sm" onclick="V.plug()">↻</button></h3><div id="pls" class="mut">Laden…</div></div>
<div class="card"><h3>Zoeken en installeren</h3><form onsubmit="return psearch()" style="margin-top:0"><input id="pq" placeholder="Zoek een plugin, bijv. chunky of 'wereld bewerken'"><button class="pri">Zoek</button></form>
<label class="row mut" style="margin-top:8px;gap:8px;font-size:13px"><input type="checkbox" id="pcompat" checked>Alleen compatibel met mijn Minecraft-versie</label><div id="pres" style="margin-top:8px"></div></div>`;
 const j=await go('/api/plugins');if(!j)return;cur.pl=j.items;cur.sel=new Set();renderPl(j)};
function renderPl(j){const items=j.items;$('pls').innerHTML=items.length?`<div class="row" style="margin-bottom:6px"><button class="sm go" onclick="plAct(true)">Aanzetten</button><button class="sm warn" onclick="plAct(false)">Uitzetten</button><button class="sm bad" onclick="plRm()">Verwijderen</button>${j.plm?'<button class="sm" onclick="plLoad()">PLM laden</button><button class="sm" onclick="plLoad(true)">PLM uitladen</button>':''}</div>`+
 items.map(i=>`<label class="li"><input type="checkbox" onchange="plSel('${esc(i.file)}',this.checked)" ${cur.sel.has(i.file)?'checked':''}><div><b class="${i.enabled?'':'mut'}">${esc(i.name)}${i.version?`<span class="tag">${esc(i.version)}</span>`:''}${i.enabled?'':'<span class="tag">uit</span>'}${i.missing.length?`<span class="tag yel">mist ${esc(i.missing.join(', '))}</span>`:''}</b><small>${esc(i.desc)}</small></div></label>`).join(''):'Geen plugins gevonden.'}
function plSel(f,on){on?cur.sel.add(f):cur.sel.delete(f)}
async function plAct(en,force,stop_ok){const files=[...cur.sel];if(!files.length)return toast('Vink eerst plugins aan');
 const j=await go('/api/plugins/toggle',{files,enable:en,force:!!force,stop_ok:!!stop_ok,restart:true});if(!j)return;
 if(j.confirm){if(await ask(j.confirm))return plAct(en,true,true);return}setTimeout(V.plug,1500)}
async function plRm(){const files=[...cur.sel];if(!files.length)return toast('Vink eerst plugins aan');if(!await ask(files.length+' plugin(s) verwijderen?\nZe gaan naar een aparte map en kunnen worden teruggezet. Een draaiende server wordt eerst veilig gestopt en daarna weer gestart.'))return;
 await go('/api/plugins/remove',{files});setTimeout(V.plug,2000)}
async function plLoad(u){await go('/api/plugins/plm',{files:[...cur.sel],unload:!!u},'Verstuurd')}
async function psearch(){const t=$('pq').value.trim();if(!t)return false;$('pres').innerHTML='<span class="mut">Zoeken…</span>';
 const j=await go('/api/plugins/search',{q:t,compat:$('pcompat').checked});if(!j){$('pres').innerHTML='';return false}
 $('pres').innerHTML=(j.info?`<div class="mut" style="font-size:12px;margin-bottom:6px">${esc(j.info)}</div>`:'')+(j.results.length?j.results.map(r=>`<div class="li"><div><b>${esc(r.name)}${r.installed?'<span class="tag">geïnstalleerd</span>':''}${r.compat===false?'<span class="tag yel">niet voor jouw versie</span>':''}</b><small style="white-space:normal">${esc(r.desc)}</small><small>${esc((r.sources||[]).join(', '))}${r.downloads?' • '+r.downloads.toLocaleString('nl')+' downloads':''}</small></div><button class="sm pri" onclick="pInst(${r.idx})">Installeer</button></div>`).join(''):'Niets gevonden.');return false}
async function pInst(idx){const j=await go('/api/plugins/install',{idx});if(!j||!j.plan_id)return;
 if(!await ask('Dit wordt geïnstalleerd:\n\n'+j.lines.join('\n')+(j.running?'\n\nDe server draait. Na het installeren kun je hem herstarten.':'')))return;
 let restart=false;if(j.running)restart=await ask('Server nu herstarten zodat de plugin geladen wordt?','Ja, herstart','Later');
 await go('/api/plugins/install',{plan_id:j.plan_id,restart});setTimeout(()=>V.plug(),1500)}
/* ---------- Updates ---------- */
V.upd=async()=>{$('view').innerHTML='<div class="card" id="u1">Laden…</div><div class="card" id="u2"></div>';cur.t=setInterval(updRender,3000);cur.stop=()=>clearInterval(cur.t);updRender()};
async function updRender(){const j=await go('/api/updates');if(!j||!$('u1'))return;
 $('u1').innerHTML=`<h3>Paper (Minecraft ${esc(j.mc)}, build ${esc(j.build)})</h3><div style="color:${j.paper.color||'inherit'}">${esc(j.paper.text)}</div>
 <div class="row" style="margin-top:10px"><button class="sm" onclick="uCheck('all')">Alles controleren</button><button class="sm go" onclick="uInst('paper')">Paper updaten</button></div>
 <label class="lab"><span>Ook bèta/alpha-versies</span><input type="checkbox" ${j.unstable?'checked':''} onchange="go('/api/updates/opt',{unstable:this.checked})"></label>
 <label class="lab"><span>Gedownloade bestanden in map 'updates' bewaren</span><input type="checkbox" ${j.updfolder?'checked':''} onchange="go('/api/updates/opt',{updfolder:this.checked})"></label>`;
 const n=j.rows.filter(r=>r.tag=='update').length;
 $('u2').innerHTML=`<h3>Plugins <span>${n?`<button class="sm go" onclick="uInst('plugins')">Alle ${n} updaten</button>`:''}</span></h3>`+j.rows.map(r=>`<div class="li"><div><b>${esc(r.name)}</b><small>${esc(r.cur)} → ${esc(r.latest)} • ${esc(r.source)}</small></div><span class="${r.tag=='update'?'yel':r.tag=='ok'?'ok':r.tag=='error'?'err':'mut'}" style="font-size:12px;max-width:40%;text-align:right">${esc(r.status)}</span></div>`).join('')+
 `<div class="row" style="margin-top:10px"><button class="sm" onclick="uCheck('plugins')">Plugins controleren</button></div>
 <h3 style="margin-top:16px">Dit programma (versie ${esc(j.version)})</h3>${j.selfupd?`<div>Nieuwe versie ${esc(j.selfupd)} beschikbaar.</div><div class="row" style="margin-top:8px"><button class="go" onclick="selfUpd()">Installeren</button></div>`:'<div class="mut">Je hebt de nieuwste versie (voor zover bekend).</div><div class="row" style="margin-top:8px"><button class="sm" onclick="go(\'/api/selfupdate\',{action:\'check\'},\'Zoeken…\')">Zoek updates</button></div>'}`}
async function uCheck(w){await go('/api/updates/check',{what:w},'Controleren…');setTimeout(updRender,4000)}
async function uInst(w){if(!await ask(w=='paper'?'Paper updaten? De server wordt veilig gestopt en weer gestart.':'Alle plugin-updates installeren? De server wordt zo nodig veilig gestopt en weer gestart.'))return;await go('/api/updates/install',{what:w},'Bezig…')}
async function selfUpd(){if(!await ask('Het programma op de pc updaten? Als een herstart nodig is, wordt de server eerst veilig gestopt en kun je hier niets meer bedienen tot het programma terug is.'))return;await go('/api/selfupdate',{action:'install'},'Bezig…')}
/* ---------- Kaart ---------- */
V.map=async()=>{$('view').innerHTML=`<div class="card"><div class="row"><select id="mw" style="flex:2" onchange="mapWorld(this.value)"></select><button class="sm" id="msel" onclick="mapSel()">▭ Gebied kiezen</button></div>
<div id="mapbox" style="margin-top:8px"><canvas id="mc"></canvas><div class="mapbtn" style="top:8px"><button onclick="mapZoom(1)">＋</button><button onclick="mapZoom(-1)">－</button><button onclick="mapHome()">⌂</button></div></div>
<div class="mut" id="mmsg" style="font-size:12px;margin-top:6px"></div></div><div class="card hide" id="mgen"></div>`;
 const m=cur.m={worlds:[],players:[],w:null,zl:2,zt:2,cx:0,cz:0,imgs:new Map(),sel:null,selmode:false,gen:{},dirty:true};
 mapInit(m);cur.stop=()=>{m.dead=1;clearInterval(m.t)};await mapLoad(true);m.t=setInterval(()=>mapLoad(false),3000);mapLoop(m)};
async function mapLoad(first){const m=cur.m;if(!m||m.dead)return;let j;try{j=await api('/map/info')}catch(e){return}if(!j||m.dead)return;
 m.players=j.players||[];m.gen=j.gen||{};m.info=j.gen_info;m.chunky=j.chunky;m.ap=j.autopause;
 if(first||!m.worlds.length){m.worlds=j.worlds;$('mw').innerHTML=j.worlds.map(w=>`<option value="${esc(w.name)}">${esc(w.display)}</option>`).join('');
  if(j.worlds.length){const w=j.worlds.find(w=>w.type=='normal')||j.worlds[0];mapWorld(w.name)}$('mmsg').textContent=j.msg||''}
 if(j.disk)$('mmsg').textContent='Server uit: opgeslagen kaart';else if(!j.msg)$('mmsg').textContent='';
 m.dirty=true;genUI()}
function mapWorld(n){const m=cur.m,w=m.worlds.find(w=>w.name==n);if(!w)return;m.w=w;m.zl=m.zt=Math.min(w.def,w.max+w.extra);m.anc=null;m.cx=w.spawn.x||0;m.cz=w.spawn.z||0;m.imgs.clear();$('mw').value=n;m.dirty=true}
function mapHome(){const m=cur.m;if(m.w){m.cx=m.w.spawn.x||0;m.cz=m.w.spawn.z||0;m.dirty=true}}
function mapZoom(d,px,py){const m=cur.m;if(!m.w)return;const top=m.w.max+m.w.extra,nt=Math.max(0,Math.min(top,Math.round(m.zt)+d));if(nt==m.zt)return;const cv=$('mc'),W=cv.clientWidth,H=cv.clientHeight;
 if(px==null){px=W/2;py=H/2}const s=2**(m.zl-m.w.max);m.anc=[px,py,m.cx+(px-W/2)/s,m.cz+(py-H/2)/s];m.zt=nt;m.dirty=true}
function mapAnim(m){if(!m.w||Math.abs(m.zl-m.zt)<0.002)return;const cv=$('mc'),W=cv.clientWidth,H=cv.clientHeight;m.zl+=(m.zt-m.zl)*0.18;if(Math.abs(m.zl-m.zt)<0.01)m.zl=m.zt;
 if(m.anc){const s=2**(m.zl-m.w.max);m.cx=m.anc[2]-(m.anc[0]-W/2)/s;m.cz=m.anc[3]-(m.anc[1]-H/2)/s}m.dirty=true}
function mapSel(){const m=cur.m;if(['running','paused','waiting','rendering'].includes(m.gen.state))return toast('Er loopt al een taak');m.selmode=!m.selmode;$('msel').classList.toggle('pri',m.selmode);
 $('mmsg').textContent=m.selmode?'Sleep over de kaart om een gebied te kiezen':''}
function mapInit(m){const cv=$('mc');const pts=new Map();let last=null,start=null;
 const wpt=(x,y)=>{const s=2**(m.zl-m.w.max);return [m.cx+(x-cv.clientWidth/2)/s,m.cz+(y-cv.clientHeight/2)/s]};
 cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);pts.set(e.pointerId,[e.offsetX,e.offsetY]);if(pts.size==1){last=[e.offsetX,e.offsetY];if(m.selmode&&m.w){start=wpt(e.offsetX,e.offsetY);m.tmp=[start[0],start[1],start[0],start[1]]}}else{start=null;m.tmp=null;last=null}});
 cv.addEventListener('pointermove',e=>{if(!pts.has(e.pointerId))return;const old=pts.get(e.pointerId);pts.set(e.pointerId,[e.offsetX,e.offsetY]);if(!m.w)return;
  if(pts.size==2){const [a,b]=[...pts.values()];const d=Math.hypot(a[0]-b[0],a[1]-b[1]);if(m.pd){const top=m.w.max+m.w.extra,W=cv.clientWidth,H=cv.clientHeight,px=(a[0]+b[0])/2,py=(a[1]+b[1])/2,s0=2**(m.zl-m.w.max),wx=m.cx+(px-W/2)/s0,wz=m.cz+(py-H/2)/s0;m.zl=Math.max(0,Math.min(top,m.zl+Math.log2(d/m.pd)));m.zt=m.zl;const s1=2**(m.zl-m.w.max);m.cx=wx-(px-W/2)/s1;m.cz=wz-(py-H/2)/s1;m.dirty=true}m.pd=d;return}
  if(m.selmode&&start){const p=wpt(e.offsetX,e.offsetY);m.tmp=[start[0],start[1],p[0],p[1]];m.dirty=true;return}
  const s=2**(m.zl-m.w.max);m.anc=null;m.cx-=(e.offsetX-old[0])/s;m.cz-=(e.offsetY-old[1])/s;m.dirty=true});
 const up=e=>{pts.delete(e.pointerId);m.pd=0;if(m.selmode&&start&&m.tmp){const t=m.tmp;m.tmp=null;start=null;m.selmode=false;$('msel').classList.remove('pri');
   const a=[Math.round(Math.min(t[0],t[2])),Math.round(Math.min(t[1],t[3])),Math.round(Math.max(t[0],t[2])),Math.round(Math.max(t[1],t[3]))];
   if(a[2]-a[0]<32||a[3]-a[1]<32){toast('Gebied te klein');m.dirty=true;return}
   go('/map/area',{world:m.w.name,area:a}).then(()=>mapLoad(false))}};
 cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
 cv.addEventListener('wheel',e=>{e.preventDefault();mapZoom(e.deltaY<0?1:-1,e.offsetX,e.offsetY)},{passive:false})}
function mapLoop(m){if(m.dead)return;const cv=$('mc');if(cv)mapAnim(m);if(cv&&m.dirty){m.dirty=false;mapDraw(m,cv)}requestAnimationFrame(()=>mapLoop(m))}
function tileImg(m,key){let t=m.imgs.get(key);if(!t){t={img:new Image(),ok:false};t.img.onload=()=>{t.ok=true;m.dirty=true};t.img.onerror=()=>{t.bad=true};t.img.src='/map/tile/'+key+'.png';m.imgs.set(key,t);
  if(m.imgs.size>300){const k=m.imgs.keys().next().value;m.imgs.delete(k)}}return t}
function mapDraw(m,cv){const dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;if(cv.width!=W*dpr||cv.height!=H*dpr){cv.width=W*dpr;cv.height=H*dpr}
 const x=cv.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);x.fillStyle='#0b1220';x.fillRect(0,0,W,H);if(!m.w){x.fillStyle='#94a3b8';x.fillText('Kaart laden…',14,24);return}
 const w=m.w,nat=Math.min(Math.ceil(m.zl-1e-6),w.max),span=512*2**(w.max-nat),s=2**(m.zl-w.max),P=512*2**(m.zl-nat);
 const x0=m.cx-W/2/s,x1=m.cx+W/2/s,z0=m.cz-H/2/s,z1=m.cz+H/2/s;x.imageSmoothingEnabled=P<511;
 for(let ty=Math.floor(z0/span);ty<=Math.floor(z1/span);ty++)for(let tx=Math.floor(x0/span);tx<=Math.floor(x1/span);tx++){
  const t=tileImg(m,`${w.name}/${nat}/${tx}_${ty}`);if(t.ok)x.drawImage(t.img,Math.floor(W/2+(tx*span-m.cx)*s),Math.floor(H/2+(ty*span-m.cz)*s),Math.ceil(P)+1,Math.ceil(P)+1)}
 const c=(a,b)=>[W/2+(a-m.cx)*s,H/2+(b-m.cz)*s];
 const g=m.gen||{};const area=m.tmp?[Math.min(m.tmp[0],m.tmp[2]),Math.min(m.tmp[1],m.tmp[3]),Math.max(m.tmp[0],m.tmp[2]),Math.max(m.tmp[1],m.tmp[3])]:(g.area&&g.world==w.name?g.area:null);
 if(area){const [ax,ay]=c(area[0],area[1]),[bx,by]=c(area[2],area[3]);const col={running:'#22c55e',paused:'#f59e0b',rendering:'#38bdf8',done:'#22c55e'}[g.state]||'#c084fc';
  x.fillStyle=col+'33';x.strokeStyle=col;x.lineWidth=2;x.setLineDash([6,3]);x.fillRect(ax,ay,bx-ax,by-ay);x.strokeRect(ax,ay,bx-ax,by-ay);x.setLineDash([])}
 const sp=w.spawn;if(sp){const [a,b]=c(sp.x||0,sp.z||0);x.fillStyle='#fde047';x.font='bold 18px sans-serif';x.fillText('⌂',a-6,b+6)}
 for(const p of m.players){if(p.world!=w.name)continue;const [a,b]=c(p.x,p.z);x.fillStyle=pcol(p.name);x.strokeStyle='#fff';x.lineWidth=2;const hi=headImg(m,p.name);
  if(hi&&hi.ok){x.fillRect(a-14,b-14,28,28);x.strokeRect(a-14,b-14,28,28);x.imageSmoothingEnabled=false;x.drawImage(hi.img,a-12,b-12,24,24)}else{x.beginPath();x.arc(a,b,7,0,7);x.fill();x.stroke()}
  x.font='bold 12px sans-serif';const tw=x.measureText(p.name).width;x.fillStyle='#111827cc';x.fillRect(a-tw/2-4,b-34,tw+8,16);x.fillStyle='#fff';x.fillText(p.name,a-tw/2,b-22)}}
function headImg(m,n){m.heads=m.heads||{};let t=m.heads[n];if(!t){t={img:new Image(),ok:false};t.img.onload=()=>{t.ok=true;m.dirty=true};t.img.src=hd(n,'');m.heads[n]=t}return t}
function pcol(n){let h=0;for(const ch of n)h=(h*31+ch.charCodeAt(0))>>>0;return['#ef4444','#3b82f6','#22c55e','#eab308','#a855f7','#f97316','#14b8a6','#ec4899'][h%8]}
function genUI(){const m=cur.m,g=m.gen||{},e=$('mgen');if(!e)return;const st=g.state||'idle';e.classList.toggle('hide',st=='idle');if(st=='idle')return;
 const fmt=n=>Math.round(n||0).toLocaleString('nl'),a=g.area,size=a?`${a[2]-a[0]} × ${a[3]-a[1]} blokken (${fmt(g.chunks)} chunks)`:'';let t='',btn='';
 if(st=='ready'){t='Gebied: '+size;btn=m.chunky?`<button class="go" onclick="genAct('start')">Genereren</button>`:'<span class="yel">Chunky staat niet in de plugins</span>';btn+=`<button onclick="genAct('clear')">Wissen</button>`}
 else if(st=='waiting'){t='⏳ Wacht tot de server leeg is • '+size;btn='<button class="bad" onclick="genAct(\'cancel\')">Annuleren</button>'}
 else if(st=='running'||st=='paused'){t=st=='paused'&&g.reason?'⏸ Gepauzeerd: '+g.reason:(st=='running'?'Chunks genereren':'⏸ Gepauzeerd')+' • '+size;btn=`<button class="warn" onclick="genAct('pause')">${st=='running'?'⏸ Pauze':'▶ Hervat'}</button><button class="bad" onclick="genAct('cancel')">■ Stop</button>`}
 else if(st=='rendering')t='✔ Chunks klaar • kaart wordt bijgewerkt…';else if(st=='done'){t='✔ Klaar • '+size;btn='<button onclick="genAct(\'clear\')">Sluiten</button>'}
 e.innerHTML=`<h3>Gebied genereren</h3><div>${esc(t)}</div><div class="bar" style="margin:8px 0"><i style="width:${st=='done'||st=='rendering'?100:(g.pct||0)}%"></i></div><div class="mut" style="font-size:12px">${esc(m.info||'')}${st=='paused'&&g.auto?' • hervat vanzelf als de server leeg is':''}</div><div class="row" style="margin-top:8px">${btn}</div>`}
async function genAct(a){await go('/map/gen',{action:a});mapLoad(false)}

/* ---------- Plugins en updates samen ---------- */
V.plug=async()=>{$('view').innerHTML=`<div class="two"><div style="display:flex;flex-direction:column;gap:14px"><div class="card"><h3>Plugins <span class="sp"></span><button class="sm" onclick="V.plug()">↻</button></h3><div id="pls" class="mut">Laden…</div></div>
 <div class="card"><h3>Zoeken en installeren</h3><form onsubmit="return psearch()" class="row"><input id="pq" style="flex:1" placeholder="Zoek een plugin, bijv. chunky"><button class="pri">Zoek</button></form>
 <label class="row mut" style="gap:8px;font-size:13px"><input type="checkbox" id="pcompat" checked>Alleen compatibel met mijn Minecraft-versie</label><div id="pres"></div></div></div>
 <div style="display:flex;flex-direction:column;gap:14px"><div class="card" id="u1">Laden…</div><div class="card" id="u2"></div></div></div>`;
 cur.t=setInterval(updRender,5000);cur.stop=()=>clearInterval(cur.t);updRender();
 const j=await go('/api/plugins');if(!j)return;cur.pl=j.items;cur.sel=new Set();renderPl(j)};
async function behB(){const j=await go('/api/backuper');if(!j||!$('bb'))return;cur.bk=j;cur.bsel=new Set();
 if(!j.jar){$('bb').innerHTML='Backuper staat niet in de plugins-map.';return}
 const tot=j.backups.reduce((a,b)=>a+b.size,0);
 $('bb').innerHTML=`<div>${esc(j.jar)}${j.disabled?' <span class="tag">uit</span>':''}</div><div class="mut" style="margin:4px 0">${j.backups.length} backups, ${fb2(tot)}${j.backups.length?' • laatste '+dt(j.backups[0].mtime):''}</div>
 <div class="row" style="margin:8px 0"><button class="go sm" onclick="bkNow()">💾 Nu backup maken</button><button class="bad sm" onclick="bkDel()">Geselecteerde verwijderen</button></div>`+
 j.backups.slice(0,40).map((b,i)=>`<label class="li"><input type="checkbox" onchange="this.checked?cur.bsel.add(${i}):cur.bsel.delete(${i})"><div><b>${esc(b.name)}</b><small>${esc(b.storage)} • ${dt(b.mtime)} • ${fb2(b.size)}</small></div></label>`).join('')+
 (j.has_config?`<h3 style="margin-top:14px">Instellingen van Backuper</h3>`+bkForm(j)+`<div class="row" style="margin-top:8px"><button class="sm pri" onclick="bkSave(false)">Opslaan</button><button class="sm warn" onclick="bkSave(true)">Opslaan en herstarten</button></div>`:'<div class="mut">Nog geen config.yml: start de server één keer.</div>')+
 `<h3 style="margin-top:14px">Backups van dit programma</h3>`+j.own.map(o=>`<div class="lab"><span>${esc(o.label)}</span><span class="mut" style="flex:none">${o.count} • ${fb2(o.size)}</span></div>`).join('')}
const BKG={autoBackup:['bool','Automatisch backups maken'],autoBackupPeriod:['int','Interval (minuten)'],autoBackupCron:['str','Cron-planning']};
const BKS={enabled:['bool','Opslag gebruiken'],autoBackup:['bool','Automatisch hierheen'],backupsFolder:['str','Map'],maxBackupsNumber:['int','Max. aantal (0 = onbeperkt)'],maxBackupsWeight:['int','Max. grootte in MB (0 = onbeperkt)'],zipArchive:['bool','Als zip bewaren'],zipCompressionLevel:['int','Zip-compressie (0-9)']};
function bkRow(path,def,val){const id='bk|'+path.join('|');return def[0]=='bool'?`<label class="lab"><span>${def[1]}</span><input type="checkbox" data-k="${esc(id)}" data-t="bool" ${val?'checked':''}></label>`:`<label class="lab"><span>${def[1]}</span><input data-k="${esc(id)}" data-t="${def[0]}" value="${esc(val)}" ${def[0]=='int'?'inputmode="numeric"':''}></label>`}
function bkForm(j){let h='<div class="mut" style="font-size:12px">Planning</div>';for(const k in BKG)if(k in j.global)h+=bkRow(['backup',k],BKG[k],j.global[k]);
 for(const s of j.storages){h+=`<div class="mut" style="font-size:12px;margin-top:8px">Opslag ${esc(s.id)} (${esc(s.type||'?')})</div>`;for(const k in BKS)if(k in s)h+=bkRow(['storages',s.id,k],BKS[k],s[k])}return h}
async function bkSave(restart){const changes=[];document.querySelectorAll('[data-k]').forEach(e=>{const path=e.dataset.k.split('|').slice(1);const v=e.dataset.t=='bool'?e.checked:e.value;changes.push({path,value:v})});
 if(restart&&!await ask('Opslaan en de server herstarten?'))return;await go('/api/backuper/config',{changes,restart});setTimeout(behB,1500)}
async function bkNow(){const j=cur.bk;await go('/api/backuper/now',{cmd:j.cmd});setTimeout(behB,20000)}
async function bkDel(){const j=cur.bk,items=[...cur.bsel].map(i=>j.backups[i]).filter(Boolean);if(!items.length)return toast('Vink eerst backups aan');if(!await ask(items.length+' backup(s) definitief verwijderen?'))return;await go('/api/backuper/delete',{items:items.map(b=>({storage:b.storage,name:b.name}))});behB()}
async function behT(){const j=await go('/api/tuning');if(!j||!$('bt'))return;const fx=j.rows.filter(r=>r.fix);
 $('bt').innerHTML=j.rows.map(r=>`<div class="li"><div><b class="${r.warn?'yel':''}">${esc(r.what)}: ${esc(r.now)}</b><small style="white-space:normal">${esc(r.adv)}</small></div></div>`).join('')+(fx.length?`<div class="row" style="margin-top:8px"><button class="go" onclick='behFix(${JSON.stringify(fx.map(r=>r.fix.split("=")[0]))})'>Alle ${fx.length} adviezen toepassen</button></div>`:'')}
async function behFix(keys){if(!await ask('Adviezen toepassen in server.properties? Je moet de server daarna herstarten.'))return;await go('/api/tuning/apply',{keys});behT()}
async function behW(){const j=await go('/api/world');if(!j||!$('bw'))return;const tot=j.items.reduce((a,b)=>a+b.size,0)||1,fb=n=>n>1e9?(n/1e9).toFixed(1)+' GB':n>1e6?(n/1e6).toFixed(0)+' MB':Math.round(n/1e3)+' kB';
 $('bw').innerHTML=j.items.map(i=>`<div class="li"><div><b>${esc(i.name)}</b><div class="bar" style="margin-top:4px"><i style="width:${i.size/tot*100}%"></i></div></div><span>${fb(i.size)}</span></div>`).join('')+(j.disk?`<div class="mut" style="margin-top:6px">Schijf: ${fb(j.disk.free)} vrij van ${fb(j.disk.total)}</div>`:'')+
 `<div class="row" style="margin-top:10px"><button onclick="behLogs()">Oude logs opruimen</button></div><div class="mut" style="font-size:12px;margin-top:8px">Regio's buiten een gebied wegzetten: kies op de kaart een gebied en gebruik dat op de pc (de server moet uit staan).</div>`}
async function behLogs(){if(!await ask('Logs ouder dan 7 dagen en crash-reports ouder dan 14 dagen verwijderen?'))return;await go('/api/world/logs',{},'Opgeruimd');setTimeout(behW,1500)}

V.bk=()=>{$('view').innerHTML=`<div class="two"><div class="card"><h3>Backups (Backuper) <span class="sp"></span><button class="sm" onclick="behB()">↻</button></h3><div id="bb" class="mut">Laden…</div></div>
 <div style="display:flex;flex-direction:column;gap:14px"><div class="card"><h3>Wereldgrootte <span class="sp"></span><button class="sm" onclick="behW()">↻</button></h3><div id="bw" class="mut">Laden…</div></div></div></div>`;behB();behW()};
/* ---------- Programma-updates ---------- */
V.upd=()=>{$('view').innerHTML='<div class="two"><div class="card" id="pu1">Laden…</div><div class="card" id="pu2"></div></div>';cur.t=setInterval(progLoad,4000);cur.stop=()=>clearInterval(cur.t);progLoad()};
async function progLoad(){const j=await go('/api/program');if(!j||!$('pu1'))return;
 $('pu1').innerHTML=`<h3>MC Server Manager</h3><div style="font-size:28px;font-weight:600">Versie ${esc(j.version)}</div>`+
  (j.new?`<div class="att"><span class="ic y">${WARNI}</span><span class="tx">Versie <b>${esc(j.new)}</b> is beschikbaar${j.hot?' (zonder herstart)':' (het programma herstart)'}</span></div>
   <div class="mut" style="white-space:pre-wrap;font-size:13px">${esc(j.notes)}</div><div class="row" style="margin-top:6px"><button class="pri" onclick="progInst()">Nu installeren</button></div>`:
   `<div class="att"><span class="ic">${OKI}</span><span class="tx">Je hebt de nieuwste versie${j.last?' (gecontroleerd '+ago(j.last)+')':''}</span></div>`)+
  `<div class="row" style="margin-top:6px"><button onclick="progCheck()" ${j.busy?'disabled':''}>${j.busy?'Controleren…':'Zoek naar updates'}</button></div>`+
  (j.frozen?'<div class="mut" style="font-size:12px">Je draait de .exe: automatisch bijwerken werkt alleen met het .py-bestand.</div>':'')+
  (j.url?'':'<div class="yel" style="font-size:13px;margin-top:6px">Er is nog geen update-link ingesteld (klassiek scherm: Instellingen, Programma-update).</div>');
 $('pu2').innerHTML=`<h3>Instellingen</h3><label class="lab"><span>Automatisch zoeken naar updates</span><input type="checkbox" ${j.check?'checked':''} onchange="setSet('selfupdate_check',this.checked)"></label>
  <label class="lab"><span>Updates automatisch installeren</span><input type="checkbox" ${j.auto?'checked':''} onchange="setSet('selfupdate_auto',this.checked)"></label>
  <div class="mut" style="font-size:12px;word-break:break-all">${j.url?'Bron: '+esc(j.url):''}</div><h3 style="margin-top:14px">Recent veranderd</h3>`+j.hist.map(l=>`<div class="li"><div style="white-space:normal;font-size:13px">${esc(l)}</div></div>`).join('')}
async function progCheck(){await go('/api/selfupdate',{action:'check'},'Controleren…');setTimeout(progLoad,2500);setTimeout(progLoad,6000)}
async function progInst(){if(!await ask('Het programma updaten? Als een herstart nodig is, wordt de server eerst veilig gestopt en kun je hier niets meer bedienen tot het programma terug is.'))return;await go('/api/selfupdate',{action:'install'},'Bezig…')}
/* ---------- Instellingen ---------- */
async function sleepAuto(){const on=!$('swSleep').classList.contains('on');$('swSleep').classList.toggle('on',on);await go('/api/sleep',{action:'auto',on});setTimeout(poll,300)}
async function sleepNow(){if(!await ask('De server veilig stoppen en vanzelf weer starten zodra iemand probeert te joinen? Spelers die nog online zijn worden van de server gezet.'))return;await go('/api/sleep',{action:'now'});setTimeout(poll,800)}
async function ramDlg(){const v=prompt('Maximaal geheugen voor Java (bijv. 4G):');if(!v)return;const r=await ask('Toepassen? De server moet herstarten om het nieuwe geheugen te gebruiken. Nu herstarten als hij draait?','Ja, herstart','Alleen opslaan');await go('/api/ram',{value:v,restart:r},'Opgeslagen')}
const PROPL={'motd':'Bericht in serverlijst (MOTD)','max-players':'Maximaal aantal spelers','difficulty':'Moeilijkheid (peaceful, easy, normal, hard)','gamemode':'Standaard spelmodus','pvp':'PvP','white-list':'Whitelist','online-mode':'Online modus (Mojang-login)','allow-flight':'Vliegen toestaan','view-distance':'Zichtafstand','simulation-distance':'Simulatieafstand','spawn-protection':'Spawn-bescherming (blokken)'};
V.set=()=>{$('view').innerHTML=`<div class="two"><div style="display:flex;flex-direction:column;gap:14px"><div class="card"><h3>Server (server.properties)</h3><div id="props" class="mut">Laden…</div></div>
 <div class="card"><h3>Prestaties en geheugen</h3><div class="row"><button onclick="ramDlg()">Geheugen (RAM) instellen…</button><button class="warn" onclick="act('kill')">Geforceerd stoppen</button></div><div id="bt" class="mut" style="margin-top:6px">Laden…</div></div>
 <div class="card"><h3>Bereikbaarheid</h3><div id="net" class="mut">Laden…</div></div></div>
 <div style="display:flex;flex-direction:column;gap:14px"><div class="card"><h3>Programma</h3><div id="set" class="mut">Laden…</div></div>
 <div class="card"><h3>Logboek van het programma</h3><div class="con" style="border:0"><div class="log" id="alog" style="height:220px;flex:none"></div></div><div class="mut" style="font-size:12px" id="ver"></div></div></div></div>`;
 propsLoad();behT();netLoad();setLoad();LOG2.forEach(addAlog);$('ver').textContent='Programmaversie '+(S.version||'')};
async function propsLoad(){const j=await go('/api/props');if(!j||!$('props'))return;$('props').innerHTML=Object.keys(PROPL).map(k=>{const t=j.kinds[k],v=j.props[k];return `<label class="lab"><span>${PROPL[k]}</span>${t=='bool'?`<input type="checkbox" ${String(v).toLowerCase()=='true'?'checked':''} onchange="propSet('${k}',this.checked)">`:`<input value="${esc(v)}" ${t=='int'?'inputmode="numeric"':''} onchange="propSet('${k}',this.value)">`}</label>`}).join('')+(j.running?'<div class="mut" style="font-size:12px;margin-top:6px">De server draait: wijzigingen werken na een herstart.</div>':'')}
const propSet=(key,value)=>go('/api/props',{key,value});
const addAlog=l=>{const c=$('alog');if(!c)return;const d=document.createElement('div');d.className={error:'e',warn:'w',ok:'o'}[l[3]]||'';d.textContent=`[${l[1]}] ${l[2]}`;c.appendChild(d);c.scrollTop=c.scrollHeight};
async function netLoad(){const j=await go('/api/net');if(!j||!$('net'))return;
 $('net').innerHTML=`<div style="color:${j.status.color||'inherit'}">${esc(j.status.text)}</div><div class="mut" style="margin:4px 0">${esc(j.motd)} ${esc(j.info)}</div><div style="color:${j.bedrock.color||'inherit'}">${esc(j.bedrock.text)}</div><div class="mut" style="font-size:12px;margin-top:4px;white-space:pre-wrap">${esc(j.diag)}</div>
 <div class="row" style="margin-top:8px"><input id="nh" value="${esc(j.host)}" placeholder="Adres/IP" style="flex:1"><input id="np" value="${esc(j.jport)}" style="width:90px" inputmode="numeric"></div>
 <div class="row" style="margin-top:8px"><button onclick="netChk(false)" ${j.busy?'disabled':''}>Controleer</button><button onclick="netChk(true)" ${j.busy?'disabled':''}>Alleen lokaal</button></div>`}
async function netChk(local){await go('/api/net/check',{host:$('nh').value,jport:$('np').value,local},'Controleren…');setTimeout(netLoad,3500);setTimeout(netLoad,8000)}
async function setLoad(){const j=await go('/api/settings');if(!j||!$('set'))return;
 $('set').innerHTML=j.items.map(i=>`<label class="lab"><span>${esc(i.label)}</span>${i.type=='bool'?`<input type="checkbox" ${i.value?'checked':''} onchange="setSet('${i.key}',this.checked)">`:`<input value="${esc(i.value)}" ${i.type=='int'?'inputmode="numeric"':''} onchange="setSet('${i.key}',this.value)">`}</label>`).join('')}
const setSet=(key,value)=>go('/api/settings',{key,value},'Opgeslagen');
/* ---------- Server-acties ---------- */
async function act(a){const t={start:'Server starten?',restart:'Server herstarten?',stop:'Server stoppen?',kill:'Geforceerd stoppen? Dit kan de wereld beschadigen als er net opgeslagen wordt.'}[a];if(a!='start'&&!await ask(t))return;go('/api/action',{name:a});setTimeout(poll,500)}
/* ---------- Tekenen met live gegevens ---------- */
function draw(){const j=S;if(!j.stats)return;const st=j.state,sl=j.sleep&&j.sleep.sleeping;
 const m=sl?['Slaapstand','b']:{online:['Online','' ],starting:['Opstarten…','y'],stopping:['Stoppen…','y'],stopped:['Gestopt','r']}[st]||[st,'y'];
 $('pill').className='pill '+(m[1]||'');$('pillTx').textContent=m[0]+(st=='online'&&j.stats.uptime&&j.stats.uptime!='-'?' · '+j.stats.uptime:'');
 $('bStart').classList.toggle('hide',st!='stopped'||sl);$('bRestart').classList.toggle('hide',st!='online');$('bStop').classList.toggle('hide',!(st=='online'||st=='starting'));
 $('sname').textContent=j.folder||'Server';$('sver').textContent=[j.mc,j.build?'build '+j.build:''].filter(Boolean).join(' · ')||'Paper';
 $('swSleep').classList.toggle('on',!!(j.sleep&&j.sleep.on));$('btnSleep').disabled=st!='online'||sl;
 $('sleepTx').textContent=j.stats.sleep&&j.stats.sleep!='-'?j.stats.sleep:'Server stopt na een tijd zonder spelers en start vanzelf bij de eerste join.';
 const bz=$('busy');bz.classList.toggle('hide',!j.busy);if(j.busy){const p=j.progress||[0,1,'determinate'];bz.classList.toggle('ind',p[2]=='indeterminate');bz.firstChild.style.width=(p[2]=='indeterminate'?40:Math.min(100,p[0]/(p[1]||1)*100))+'%'}
 const bp=$('bd-plug'),n=(j.pupd||0)+(j.paperupd?1:0);if(bp){bp.classList.toggle('hide',!n);bp.textContent=n}const bu=$('bd-upd');if(bu){bu.classList.toggle('hide',!j.selfupd);bu.textContent='1'}
 const g=j.graphs||{};
 if($('vTps')){const cpu=num(j.stats.cpu),tps=num(j.stats.tps),tmp=num(j.stats.temp);const ram=num(j.stats.ram);
  $('vTps').textContent=j.stats.tps&&j.stats.tps!='-'?j.stats.tps:'-';
  $('lgRam').textContent=ram==null?'':(ram/1024).toFixed(1).replace('.',',')+(j.xmx?' / '+(j.xmx/1024).toFixed(0):'')+' GB';
  $('lgCpu').textContent=cpu==null?'':Math.round(cpu)+'%';
  const pc=num(j.stats.players),pm=String(j.stats.players||'').split('/')[1];$('vPl').innerHTML=pc==null?'-':pc+(pm?` <small>/ ${esc(pm.trim())}</small>`:'');
  $('vTmp').innerHTML=tmp==null?'<small>niet beschikbaar</small>':Math.round(tmp)+' <small>°C</small>';
  spark('sTps',g.tps,'#3ddc97',0,20);spark('sTmp',g.temp,'#f87171',null,null);
  const ramPct=(g.ram||[]).map(v=>j.xmx?v/j.xmx*100:v);bigChart('cBig',[[ramPct,'#6ea8fe'],[g.cpu,'#f5a524']]);
  const e=$('ovPl');if(e){e.innerHTML=j.players.length?'':'<span class="mut">Niemand online.</span>';for(const p of j.players){const d=document.createElement('div');d.className='pl';d.appendChild(skin(p.name,p.type));
   const nn=document.createElement('span');nn.className='n';nn.innerHTML=`<b>${esc(p.name)}</b><small>${esc(p.type||'Java')}${p.since?' · '+esc(p.since):''}</small>`;d.appendChild(nn);e.appendChild(d)}}
  $('cleanTx').textContent=j.clean?'Schoon':'';drawAtt()}
 if(tab=='pl')plOnline();
 if($('clean')&&document.activeElement!==$('clean'))$('clean').checked=!!j.clean}
/* ---------- poll ---------- */
async function poll(){if(busy)return;busy=1;try{const j=await api(`/api/state?since=${since}&nsince=${nsince}&asince=${asince}`);S=j;fails=0;$('off').style.display='none';
 j.lines.forEach(l=>{since=Math.max(since,l[0]);LOG.push(l);if(LOG.length>600)LOG.shift();addLine(l)});
 j.notes.forEach(n=>{nsince=Math.max(nsince,n[0]);toast(n[2],7000)});j.alog.forEach(l=>{asince=Math.max(asince,l[0]);LOG2.push(l);if(LOG2.length>200)LOG2.shift();if(tab=='set')addAlog(l)});
 draw();if(tab=='map'&&cur.m&&j.gen){cur.m.gen=Object.assign({},cur.m.gen,j.gen);cur.m.info=j.gen_info;genUI();cur.m.dirty=true}}catch(e){if(e!==0&&++fails>2){$('off').style.display='flex';$('off').firstChild.textContent='Verbinding met het programma is weg.'}}busy=0}
build();poll();setInterval(poll,2000);window.addEventListener('resize',()=>{if(S.stats)draw()});
</script></body></html>
"""
# DESK_PAGE>>


REMOTE_PAGE = r"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111827"><link rel="manifest" href="/manifest.json"><link rel="icon" href="/icon.png"><link rel="apple-touch-icon" href="/icon.png">
<title>MC Server</title><style>
:root{--bg:#0f172a;--card:#1e293b;--in:#0b1220;--b:#334155;--t:#e2e8f0;--m:#94a3b8;--g:#22c55e;--r:#ef4444;--y:#f59e0b;--a:#3b82f6}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}html,body{margin:0}
body{background:var(--bg);color:var(--t);font:15px system-ui,sans-serif;padding-top:env(safe-area-inset-top);padding-bottom:calc(66px + env(safe-area-inset-bottom))}
header{position:sticky;top:0;background:#111827;padding:11px 14px;display:flex;align-items:center;gap:10px;z-index:5;border-bottom:1px solid var(--b)}
header b{font-size:16px;flex:1}.dot{width:12px;height:12px;border-radius:50%;background:var(--m)}
nav{position:fixed;left:0;right:0;bottom:0;background:#111827;border-top:1px solid var(--b);display:flex;z-index:6;padding-bottom:env(safe-area-inset-bottom);overflow-x:auto}
nav a{flex:1;min-width:62px;text-align:center;padding:8px 2px 7px;font-size:11px;color:var(--m);position:relative}nav a i{display:block;font-style:normal;font-size:20px}
nav a.on{color:#fff;background:#1e293b}nav a .bd{position:absolute;top:3px;right:12px;background:var(--r);color:#fff;border-radius:9px;font-size:10px;padding:0 5px}
main{padding:12px;max-width:820px;margin:auto;display:grid;gap:12px}.card{background:var(--card);border:1px solid var(--b);border-radius:14px;padding:12px;min-width:0}
h3{margin:0 0 8px;font-size:12px;color:var(--m);text-transform:uppercase;letter-spacing:.05em;display:flex;justify-content:space-between;align-items:center;gap:8px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.s{background:var(--in);border-radius:10px;padding:8px;text-align:center}
.s b{display:block;font-size:18px}.s span{font-size:11px;color:var(--m)}
button,.btn{background:var(--b);color:var(--t);border:0;border-radius:10px;padding:11px 13px;font-size:14px;font-weight:600;font-family:inherit}
button:active{opacity:.7}button:disabled{opacity:.4}.sm{padding:7px 10px;font-size:13px}.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.row>button{flex:1}
.go{background:#15803d}.warn{background:#b45309}.bad{background:#b91c1c}.pri{background:#1d4ed8}
input,select{background:var(--in);border:1px solid var(--b);color:var(--t);border-radius:10px;padding:11px;font-size:16px;min-width:0;font-family:inherit}
input[type=checkbox]{width:22px;height:22px;accent-color:#3b82f6;flex:none;padding:0}
.con{background:#020617;border-radius:10px;padding:8px;height:44vh;overflow:auto;font:12px ui-monospace,Consolas,monospace;white-space:pre-wrap;word-break:break-word}
.e{color:#fca5a5}.w{color:#fcd34d}.o{color:#5eead4}.c{color:#93c5fd}.mut{color:var(--m)}.ok{color:var(--g)}.err{color:var(--r)}.yel{color:var(--y)}
form,.f{display:flex;gap:8px;margin-top:8px}form input,.f input{flex:1}canvas.sp{width:100%;height:56px;display:block}
.chip{display:inline-block;background:var(--in);border-radius:20px;padding:6px 12px;margin:0 6px 6px 0}
.li{display:flex;gap:10px;align-items:center;padding:10px 0;border-top:1px solid var(--b)}.li:first-child{border-top:0}.li>div{flex:1;min-width:0}
.li b{display:block;overflow:hidden;text-overflow:ellipsis}.li small{color:var(--m);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tag{font-size:11px;border-radius:6px;padding:1px 6px;background:var(--b);margin-left:6px;font-weight:400}
.bar{height:10px;background:var(--in);border-radius:6px;overflow:hidden}.bar i{display:block;height:100%;background:var(--g);transition:width .5s}
.hd{width:22px;height:22px;image-rendering:pixelated;border-radius:4px;vertical-align:middle;margin-right:7px;background:#0b1220}
.hide{display:none!important}#login{max-width:340px;margin:20vh auto;padding:16px}#login input{width:100%;margin:10px 0}
#toast{position:fixed;left:12px;right:12px;bottom:calc(76px + env(safe-area-inset-bottom));background:#475569;padding:12px;border-radius:12px;display:none;z-index:9;box-shadow:0 4px 20px #0008}
#dlg{position:fixed;inset:0;background:#000a;z-index:20;display:none;align-items:center;justify-content:center;padding:20px}#dlg .card{max-width:420px;width:100%;white-space:pre-wrap}
#mapbox{position:relative;height:62vh;min-height:320px;background:#0b1220;border-radius:12px;overflow:hidden;touch-action:none}#mapbox canvas{width:100%;height:100%;display:block}
.mapbtn{position:absolute;right:8px;display:flex;flex-direction:column;gap:6px}.mapbtn button{width:42px;height:42px;padding:0;font-size:20px;background:#1e293bdd}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:6px 4px;border-top:1px solid var(--b);text-align:left}th{color:var(--m);font-weight:600;border:0}td.n,th.n{text-align:right}
.lab{display:flex;gap:10px;align-items:center;justify-content:space-between;padding:9px 0;border-top:1px solid var(--b)}.lab:first-child{border-top:0}.lab span{flex:1}.lab input:not([type=checkbox]){width:46%;flex:none}
</style></head><body>
<div id="login" class="card hide"><h3>MC Server Manager</h3><input id="pw" type="password" placeholder="Wachtwoord" autocomplete="current-password"><button class="go" style="width:100%" onclick="login()">Inloggen</button><div id="lerr" class="err" style="margin-top:8px"></div></div>
<div id="app" class="hide"><header><span class="dot" id="dot"></span><b id="st">…</b><span id="up" class="mut"></span></header><main id="main"></main>
<nav id="nav"></nav></div><div id="toast"></div><div id="dlg"><div class="card"><div id="dmsg"></div><div class="row" style="margin-top:14px" id="dbtn"></div></div></div>
<script>
const $=i=>document.getElementById(i);let S={},since=0,nsince=0,asince=0,busy=0,tab=localStorage.getItem('tab')||'srv',LOG=[],cur={};
const hd=(n,t)=>'/head/'+encodeURIComponent(n)+'?t='+encodeURIComponent(t||'');
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
function toast(t,ms=4000){const e=$('toast');e.textContent=t;e.style.display='block';clearTimeout(toast.t);toast.t=setTimeout(()=>e.style.display='none',ms)}
function ask(msg,yes='Ja',no='Annuleren'){return new Promise(r=>{$('dmsg').textContent=msg;$('dbtn').innerHTML='';
 for(const [t,v,c] of [[no,false,''],[yes,true,'pri']]){const b=document.createElement('button');b.textContent=t;b.className=c;b.onclick=()=>{$('dlg').style.display='none';r(v)};$('dbtn').appendChild(b)}$('dlg').style.display='flex'})}
async function api(p,b){let r;try{r=await fetch(p,b?{method:'POST',headers:{'Content-Type':'application/json','X-MC':'1'},body:JSON.stringify(b)}:{headers:{'X-MC':'1'}})}catch(e){toast('Geen verbinding met de pc');throw e}
 if(r.status==401){show(false);throw 0}let j={};try{j=await r.json()}catch(e){}if(!r.ok&&j.error){toast(j.error);throw j.error}return j}
const go=async(p,b,msg)=>{try{const j=await api(p,b);if(msg||j.msg)toast(msg||j.msg);return j}catch(e){return null}};
function show(on){$('app').classList.toggle('hide',!on);$('login').classList.toggle('hide',on)}
async function login(){const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json','X-MC':'1'},body:JSON.stringify({password:$('pw').value})});
 const j=await r.json();if(j.ok){$('pw').value='';show(true);since=nsince=asince=0;LOG=[];build();poll()}else $('lerr').textContent=j.error||'Mislukt'}
$('pw').addEventListener('keydown',e=>{if(e.key=='Enter')login()});
const TABS=[['srv','🖥️','Server'],['plug','🧩','Plugins'],['upd','🔧','Updates'],['map','🗺️','Kaart'],['beh','👥','Beheer'],['more','⚙️','Meer']];
function build(){$('nav').innerHTML=TABS.map(t=>`<a data-t="${t[0]}" onclick="setTab('${t[0]}')"><i>${t[1]}</i>${t[2]}<span class="bd hide" id="bd-${t[0]}"></span></a>`).join('');setTab(tab)}
function setTab(t){if(cur.stop)cur.stop();cur={};tab=t;try{localStorage.setItem('tab',t)}catch(e){}
 document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('on',a.dataset.t==t));$('main').innerHTML='';window.scrollTo(0,0);(V[t]||V.srv)()}
const V={};
/* ---------- Server ---------- */
V.srv=()=>{$('main').innerHTML=`<div class="card"><div class="grid"><div class="s"><b id="cpu">-</b><span>CPU</span></div><div class="s"><b id="ram">-</b><span>Geheugen</span></div><div class="s"><b id="tps">-</b><span>TPS</span></div></div>
<div class="grid" style="margin-top:8px"><div class="s"><canvas class="sp" id="g1"></canvas><span>CPU</span></div><div class="s"><canvas class="sp" id="g2"></canvas><span>Geheugen</span></div><div class="s"><canvas class="sp" id="g3"></canvas><span>TPS</span></div></div>
<div class="mut" style="margin-top:8px;font-size:12px" id="stline"></div></div>
<div class="card"><h3>Server</h3><div class="row"><button class="go" onclick="act('start')">Starten</button><button class="warn" onclick="act('restart')">Herstarten</button><button class="bad" onclick="act('stop')">Stoppen</button></div>
<div id="busy" class="hide" style="margin-top:10px"><div class="mut" id="busytx" style="font-size:12px;margin-bottom:4px"></div><div class="bar"><i id="busybar" style="width:0"></i></div></div>
<div class="row" style="margin-top:8px"><button class="sm" onclick="act('kill')">Geforceerd stoppen</button><button class="sm" onclick="ramDlg()">Geheugen (RAM)…</button></div></div>
<div class="card"><h3><span>Spelers online (<span id="pn">0</span>)</span></h3><div id="pl"></div></div>
<div class="card"><h3>Console <label class="mut" style="text-transform:none;font-weight:400;display:flex;gap:6px;align-items:center"><input type="checkbox" id="clean" onchange="go('/api/clean',{on:this.checked})">schoon</label></h3><div class="con" id="con"></div>
<form onsubmit="return send()"><input id="cmd" placeholder="Commando…" autocapitalize="off" autocomplete="off" enterkeyhint="send"><button class="pri">Stuur</button></form>
<div class="row" style="margin-top:8px"><button class="sm" onclick="q('list')">list</button><button class="sm" onclick="q('save-all')">save-all</button><button class="sm" onclick="q('tps')">tps</button></div></div>`;
 cur.con=1;LOG.forEach(addLine);draw()};
function addLine(l){const c=$('con');if(!c)return;const bot=c.scrollHeight-c.scrollTop-c.clientHeight<40;const d=document.createElement('div');d.className=l[2];d.textContent=l[1];c.appendChild(d);
 while(c.childElementCount>400)c.removeChild(c.firstChild);if(bot)c.scrollTop=c.scrollHeight}
function spark(id,d,col){const c=$(id);if(!c)return;const x=c.getContext('2d');c.width=c.clientWidth*2;c.height=c.clientHeight*2;x.clearRect(0,0,c.width,c.height);
 d=(d||[]).filter(v=>v!=null);if(d.length<2)return;let lo=Math.min(...d),hi=Math.max(...d);if(hi-lo<1e-6){hi+=1;lo-=1}
 x.strokeStyle=col;x.lineWidth=3;x.lineJoin='round';x.beginPath();d.forEach((v,i)=>{const X=i/(d.length-1)*c.width,Y=c.height-(v-lo)/(hi-lo)*(c.height-8)-4;i?x.lineTo(X,Y):x.moveTo(X,Y)});x.stroke()}
function draw(){const j=S;if(!j.stats||!$('cpu'))return;$('cpu').textContent=j.stats.cpu;$('ram').textContent=(j.stats.ram||'-').split(' / ')[0];$('tps').textContent=j.stats.tps;
 spark('g1',j.graphs.cpu,'#38bdf8');spark('g2',j.graphs.ram,'#a78bfa');spark('g3',j.graphs.tps,'#4ade80');
 $('pn').textContent=j.players.length;$('pl').innerHTML=j.players.length?j.players.map(p=>`<span class="chip" onclick="plDlg('${esc(p.name)}')"><img class="hd" src="${hd(p.name,p.type)}">${esc(p.name)}${p.type?` <span class="mut" style="font-size:11px">${esc(p.type)}</span>`:''}</span>`).join(''):'<span class="mut">niemand</span>';
 $('stline').textContent=[j.stats.temp&&j.stats.temp!='-'?'Temperatuur '+j.stats.temp:'',j.status].filter(Boolean).join('  •  ');
 const b=$('busy');b.classList.toggle('hide',!j.busy);if(j.busy){$('busytx').textContent=j.status||'Bezig…';const p=j.progress||[0,1,'determinate'];$('busybar').style.width=(p[2]=='indeterminate'?100:Math.min(100,p[0]/(p[1]||1)*100))+'%'}
 if($('clean')&&document.activeElement!==$('clean'))$('clean').checked=!!j.clean}
async function act(a){const t={start:'Server starten?',restart:'Server herstarten?',stop:'Server stoppen?',kill:'Geforceerd stoppen? Dit kan de wereld beschadigen als er net opgeslagen wordt.'}[a];if(!await ask(t))return;go('/api/action',{name:a});setTimeout(poll,500)}
async function q(c){await go('/api/cmd',{cmd:c});setTimeout(poll,600)}
function send(){const v=$('cmd').value.trim();if(v){q(v);$('cmd').value=''}return false}
async function ramDlg(){const v=prompt('Maximaal geheugen voor Java (bijv. 4G):');if(!v)return;const r=await ask('Toepassen? De server moet herstarten om het nieuwe geheugen te gebruiken. Nu herstarten als hij draait?','Ja, herstart','Alleen opslaan');await go('/api/ram',{value:v,restart:r},'Opgeslagen')}
function plDlg(n){const acts=[['kick','Kick'],['ban','Ban'],['pardon','Pardon'],['op','Op'],['deop','Deop'],['whitelist_add','Whitelist +'],['whitelist_remove','Whitelist −'],['gm','Gamemode'],['tp','Tp naar speler'],['msg','Bericht']];
 $('dmsg').textContent='Speler: '+n;$('dbtn').innerHTML='';
 for(const [a,t] of acts){const b=document.createElement('button');b.className='sm';b.textContent=t;b.onclick=async()=>{let arg='';
  if(['kick','ban'].includes(a))arg=prompt('Reden (mag leeg):')||'';else if(a=='gm'){arg=prompt('survival, creative, adventure of spectator:','survival')||''}else if(a=='tp'){arg=prompt('Naar welke speler?')||'';if(!arg)return}else if(a=='msg'){arg=prompt('Bericht:')||'';if(!arg)return}
  if(['ban','kick','op','deop'].includes(a)&&!await ask(t+' '+n+'?'))return;$('dlg').style.display='none';go('/api/player',{name:n,action:a,arg},t+' '+n)};$('dbtn').appendChild(b)}
 const c=document.createElement('button');c.className='sm';c.textContent='Sluiten';c.onclick=()=>$('dlg').style.display='none';$('dbtn').appendChild(c);$('dlg').style.display='flex'}
/* ---------- Plugins ---------- */
V.plug=async()=>{$('main').innerHTML=`<div class="card"><h3>Plugins <button class="sm" onclick="V.plug()">↻</button></h3><div id="pls" class="mut">Laden…</div></div>
<div class="card"><h3>Zoeken en installeren</h3><form onsubmit="return psearch()" style="margin-top:0"><input id="pq" placeholder="Zoek een plugin, bijv. chunky of 'wereld bewerken'"><button class="pri">Zoek</button></form>
<label class="row mut" style="margin-top:8px;gap:8px;font-size:13px"><input type="checkbox" id="pcompat" checked>Alleen compatibel met mijn Minecraft-versie</label><div id="pres" style="margin-top:8px"></div></div>`;
 const j=await go('/api/plugins');if(!j)return;cur.pl=j.items;cur.sel=new Set();renderPl(j)};
function renderPl(j){const items=j.items;$('pls').innerHTML=items.length?`<div class="row" style="margin-bottom:6px"><button class="sm go" onclick="plAct(true)">Aanzetten</button><button class="sm warn" onclick="plAct(false)">Uitzetten</button><button class="sm bad" onclick="plRm()">Verwijderen</button>${j.plm?'<button class="sm" onclick="plLoad()">PLM laden</button><button class="sm" onclick="plLoad(true)">PLM uitladen</button>':''}</div>`+
 items.map(i=>`<label class="li"><input type="checkbox" onchange="plSel('${esc(i.file)}',this.checked)" ${cur.sel.has(i.file)?'checked':''}><div><b class="${i.enabled?'':'mut'}">${esc(i.name)}${i.version?`<span class="tag">${esc(i.version)}</span>`:''}${i.enabled?'':'<span class="tag">uit</span>'}${i.missing.length?`<span class="tag yel">mist ${esc(i.missing.join(', '))}</span>`:''}</b><small>${esc(i.desc)}</small></div></label>`).join(''):'Geen plugins gevonden.'}
function plSel(f,on){on?cur.sel.add(f):cur.sel.delete(f)}
async function plAct(en,force,stop_ok){const files=[...cur.sel];if(!files.length)return toast('Vink eerst plugins aan');
 const j=await go('/api/plugins/toggle',{files,enable:en,force:!!force,stop_ok:!!stop_ok,restart:true});if(!j)return;
 if(j.confirm){if(await ask(j.confirm))return plAct(en,true,true);return}setTimeout(V.plug,1500)}
async function plRm(){const files=[...cur.sel];if(!files.length)return toast('Vink eerst plugins aan');if(!await ask(files.length+' plugin(s) verwijderen?\nZe gaan naar een aparte map en kunnen worden teruggezet. Een draaiende server wordt eerst veilig gestopt en daarna weer gestart.'))return;
 await go('/api/plugins/remove',{files});setTimeout(V.plug,2000)}
async function plLoad(u){await go('/api/plugins/plm',{files:[...cur.sel],unload:!!u},'Verstuurd')}
async function psearch(){const t=$('pq').value.trim();if(!t)return false;$('pres').innerHTML='<span class="mut">Zoeken…</span>';
 const j=await go('/api/plugins/search',{q:t,compat:$('pcompat').checked});if(!j){$('pres').innerHTML='';return false}
 $('pres').innerHTML=(j.info?`<div class="mut" style="font-size:12px;margin-bottom:6px">${esc(j.info)}</div>`:'')+(j.results.length?j.results.map(r=>`<div class="li"><div><b>${esc(r.name)}${r.installed?'<span class="tag">geïnstalleerd</span>':''}${r.compat===false?'<span class="tag yel">niet voor jouw versie</span>':''}</b><small style="white-space:normal">${esc(r.desc)}</small><small>${esc((r.sources||[]).join(', '))}${r.downloads?' • '+r.downloads.toLocaleString('nl')+' downloads':''}</small></div><button class="sm pri" onclick="pInst(${r.idx})">Installeer</button></div>`).join(''):'Niets gevonden.');return false}
async function pInst(idx){const j=await go('/api/plugins/install',{idx});if(!j||!j.plan_id)return;
 if(!await ask('Dit wordt geïnstalleerd:\n\n'+j.lines.join('\n')+(j.running?'\n\nDe server draait. Na het installeren kun je hem herstarten.':'')))return;
 let restart=false;if(j.running)restart=await ask('Server nu herstarten zodat de plugin geladen wordt?','Ja, herstart','Later');
 await go('/api/plugins/install',{plan_id:j.plan_id,restart});setTimeout(()=>V.plug(),1500)}
/* ---------- Updates ---------- */
V.upd=async()=>{$('main').innerHTML='<div class="card" id="u1">Laden…</div><div class="card" id="u2"></div>';cur.t=setInterval(updRender,3000);cur.stop=()=>clearInterval(cur.t);updRender()};
async function updRender(){const j=await go('/api/updates');if(!j||!$('u1'))return;
 $('u1').innerHTML=`<h3>Paper (Minecraft ${esc(j.mc)}, build ${esc(j.build)})</h3><div style="color:${j.paper.color||'inherit'}">${esc(j.paper.text)}</div>
 <div class="row" style="margin-top:10px"><button class="sm" onclick="uCheck('all')">Alles controleren</button><button class="sm go" onclick="uInst('paper')">Paper updaten</button></div>
 <label class="lab"><span>Ook bèta/alpha-versies</span><input type="checkbox" ${j.unstable?'checked':''} onchange="go('/api/updates/opt',{unstable:this.checked})"></label>
 <label class="lab"><span>Gedownloade bestanden in map 'updates' bewaren</span><input type="checkbox" ${j.updfolder?'checked':''} onchange="go('/api/updates/opt',{updfolder:this.checked})"></label>`;
 const n=j.rows.filter(r=>r.tag=='update').length;
 $('u2').innerHTML=`<h3>Plugins <span>${n?`<button class="sm go" onclick="uInst('plugins')">Alle ${n} updaten</button>`:''}</span></h3>`+j.rows.map(r=>`<div class="li"><div><b>${esc(r.name)}</b><small>${esc(r.cur)} → ${esc(r.latest)} • ${esc(r.source)}</small></div><span class="${r.tag=='update'?'yel':r.tag=='ok'?'ok':r.tag=='error'?'err':'mut'}" style="font-size:12px;max-width:40%;text-align:right">${esc(r.status)}</span></div>`).join('')+
 `<div class="row" style="margin-top:10px"><button class="sm" onclick="uCheck('plugins')">Plugins controleren</button></div>
 <h3 style="margin-top:16px">Dit programma (versie ${esc(j.version)})</h3>${j.selfupd?`<div>Nieuwe versie ${esc(j.selfupd)} beschikbaar.</div><div class="row" style="margin-top:8px"><button class="go" onclick="selfUpd()">Installeren</button></div>`:'<div class="mut">Je hebt de nieuwste versie (voor zover bekend).</div><div class="row" style="margin-top:8px"><button class="sm" onclick="go(\'/api/selfupdate\',{action:\'check\'},\'Zoeken…\')">Zoek updates</button></div>'}`}
async function uCheck(w){await go('/api/updates/check',{what:w},'Controleren…');setTimeout(updRender,4000)}
async function uInst(w){if(!await ask(w=='paper'?'Paper updaten? De server wordt veilig gestopt en weer gestart.':'Alle plugin-updates installeren? De server wordt zo nodig veilig gestopt en weer gestart.'))return;await go('/api/updates/install',{what:w},'Bezig…')}
async function selfUpd(){if(!await ask('Het programma op de pc updaten? Als een herstart nodig is, wordt de server eerst veilig gestopt en kun je hier niets meer bedienen tot het programma terug is.'))return;await go('/api/selfupdate',{action:'install'},'Bezig…')}
/* ---------- Kaart ---------- */
V.map=async()=>{$('main').innerHTML=`<div class="card"><div class="row"><select id="mw" style="flex:2" onchange="mapWorld(this.value)"></select><button class="sm" id="msel" onclick="mapSel()">▭ Gebied kiezen</button></div>
<div id="mapbox" style="margin-top:8px"><canvas id="mc"></canvas><div class="mapbtn" style="top:8px"><button onclick="mapZoom(1)">＋</button><button onclick="mapZoom(-1)">－</button><button onclick="mapHome()">⌂</button></div></div>
<div class="mut" id="mmsg" style="font-size:12px;margin-top:6px"></div></div><div class="card hide" id="mgen"></div>`;
 const m=cur.m={worlds:[],players:[],w:null,zl:2,zt:2,cx:0,cz:0,imgs:new Map(),sel:null,selmode:false,gen:{},dirty:true};
 mapInit(m);cur.stop=()=>{m.dead=1;clearInterval(m.t)};await mapLoad(true);m.t=setInterval(()=>mapLoad(false),3000);mapLoop(m)};
async function mapLoad(first){const m=cur.m;if(!m||m.dead)return;let j;try{j=await api('/map/info')}catch(e){return}if(!j||m.dead)return;
 m.players=j.players||[];m.gen=j.gen||{};m.info=j.gen_info;m.chunky=j.chunky;m.ap=j.autopause;
 if(first||!m.worlds.length){m.worlds=j.worlds;$('mw').innerHTML=j.worlds.map(w=>`<option value="${esc(w.name)}">${esc(w.display)}</option>`).join('');
  if(j.worlds.length){const w=j.worlds.find(w=>w.type=='normal')||j.worlds[0];mapWorld(w.name)}$('mmsg').textContent=j.msg||''}
 if(j.disk)$('mmsg').textContent='Server uit: opgeslagen kaart';else if(!j.msg)$('mmsg').textContent='';
 m.dirty=true;genUI()}
function mapWorld(n){const m=cur.m,w=m.worlds.find(w=>w.name==n);if(!w)return;m.w=w;m.zl=m.zt=Math.min(w.def,w.max+w.extra);m.anc=null;m.cx=w.spawn.x||0;m.cz=w.spawn.z||0;m.imgs.clear();$('mw').value=n;m.dirty=true}
function mapHome(){const m=cur.m;if(m.w){m.cx=m.w.spawn.x||0;m.cz=m.w.spawn.z||0;m.dirty=true}}
function mapZoom(d,px,py){const m=cur.m;if(!m.w)return;const top=m.w.max+m.w.extra,nt=Math.max(0,Math.min(top,Math.round(m.zt)+d));if(nt==m.zt)return;const cv=$('mc'),W=cv.clientWidth,H=cv.clientHeight;
 if(px==null){px=W/2;py=H/2}const s=2**(m.zl-m.w.max);m.anc=[px,py,m.cx+(px-W/2)/s,m.cz+(py-H/2)/s];m.zt=nt;m.dirty=true}
function mapAnim(m){if(!m.w||Math.abs(m.zl-m.zt)<0.002)return;const cv=$('mc'),W=cv.clientWidth,H=cv.clientHeight;m.zl+=(m.zt-m.zl)*0.18;if(Math.abs(m.zl-m.zt)<0.01)m.zl=m.zt;
 if(m.anc){const s=2**(m.zl-m.w.max);m.cx=m.anc[2]-(m.anc[0]-W/2)/s;m.cz=m.anc[3]-(m.anc[1]-H/2)/s}m.dirty=true}
function mapSel(){const m=cur.m;if(['running','paused','waiting','rendering'].includes(m.gen.state))return toast('Er loopt al een taak');m.selmode=!m.selmode;$('msel').classList.toggle('pri',m.selmode);
 $('mmsg').textContent=m.selmode?'Sleep over de kaart om een gebied te kiezen':''}
function mapInit(m){const cv=$('mc');const pts=new Map();let last=null,start=null;
 const wpt=(x,y)=>{const s=2**(m.zl-m.w.max);return [m.cx+(x-cv.clientWidth/2)/s,m.cz+(y-cv.clientHeight/2)/s]};
 cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);pts.set(e.pointerId,[e.offsetX,e.offsetY]);if(pts.size==1){last=[e.offsetX,e.offsetY];if(m.selmode&&m.w){start=wpt(e.offsetX,e.offsetY);m.tmp=[start[0],start[1],start[0],start[1]]}}else{start=null;m.tmp=null;last=null}});
 cv.addEventListener('pointermove',e=>{if(!pts.has(e.pointerId))return;const old=pts.get(e.pointerId);pts.set(e.pointerId,[e.offsetX,e.offsetY]);if(!m.w)return;
  if(pts.size==2){const [a,b]=[...pts.values()];const d=Math.hypot(a[0]-b[0],a[1]-b[1]);if(m.pd){const top=m.w.max+m.w.extra,W=cv.clientWidth,H=cv.clientHeight,px=(a[0]+b[0])/2,py=(a[1]+b[1])/2,s0=2**(m.zl-m.w.max),wx=m.cx+(px-W/2)/s0,wz=m.cz+(py-H/2)/s0;m.zl=Math.max(0,Math.min(top,m.zl+Math.log2(d/m.pd)));m.zt=m.zl;const s1=2**(m.zl-m.w.max);m.cx=wx-(px-W/2)/s1;m.cz=wz-(py-H/2)/s1;m.dirty=true}m.pd=d;return}
  if(m.selmode&&start){const p=wpt(e.offsetX,e.offsetY);m.tmp=[start[0],start[1],p[0],p[1]];m.dirty=true;return}
  const s=2**(m.zl-m.w.max);m.anc=null;m.cx-=(e.offsetX-old[0])/s;m.cz-=(e.offsetY-old[1])/s;m.dirty=true});
 const up=e=>{pts.delete(e.pointerId);m.pd=0;if(m.selmode&&start&&m.tmp){const t=m.tmp;m.tmp=null;start=null;m.selmode=false;$('msel').classList.remove('pri');
   const a=[Math.round(Math.min(t[0],t[2])),Math.round(Math.min(t[1],t[3])),Math.round(Math.max(t[0],t[2])),Math.round(Math.max(t[1],t[3]))];
   if(a[2]-a[0]<32||a[3]-a[1]<32){toast('Gebied te klein');m.dirty=true;return}
   go('/map/area',{world:m.w.name,area:a}).then(()=>mapLoad(false))}};
 cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
 cv.addEventListener('wheel',e=>{e.preventDefault();mapZoom(e.deltaY<0?1:-1,e.offsetX,e.offsetY)},{passive:false})}
function mapLoop(m){if(m.dead)return;const cv=$('mc');if(cv)mapAnim(m);if(cv&&m.dirty){m.dirty=false;mapDraw(m,cv)}requestAnimationFrame(()=>mapLoop(m))}
function tileImg(m,key){let t=m.imgs.get(key);if(!t){t={img:new Image(),ok:false};t.img.onload=()=>{t.ok=true;m.dirty=true};t.img.onerror=()=>{t.bad=true};t.img.src='/map/tile/'+key+'.png';m.imgs.set(key,t);
  if(m.imgs.size>300){const k=m.imgs.keys().next().value;m.imgs.delete(k)}}return t}
function mapDraw(m,cv){const dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;if(cv.width!=W*dpr||cv.height!=H*dpr){cv.width=W*dpr;cv.height=H*dpr}
 const x=cv.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);x.fillStyle='#0b1220';x.fillRect(0,0,W,H);if(!m.w){x.fillStyle='#94a3b8';x.fillText('Kaart laden…',14,24);return}
 const w=m.w,nat=Math.min(Math.ceil(m.zl-1e-6),w.max),span=512*2**(w.max-nat),s=2**(m.zl-w.max),P=512*2**(m.zl-nat);
 const x0=m.cx-W/2/s,x1=m.cx+W/2/s,z0=m.cz-H/2/s,z1=m.cz+H/2/s;x.imageSmoothingEnabled=P<511;
 for(let ty=Math.floor(z0/span);ty<=Math.floor(z1/span);ty++)for(let tx=Math.floor(x0/span);tx<=Math.floor(x1/span);tx++){
  const t=tileImg(m,`${w.name}/${nat}/${tx}_${ty}`);if(t.ok)x.drawImage(t.img,Math.floor(W/2+(tx*span-m.cx)*s),Math.floor(H/2+(ty*span-m.cz)*s),Math.ceil(P)+1,Math.ceil(P)+1)}
 const c=(a,b)=>[W/2+(a-m.cx)*s,H/2+(b-m.cz)*s];
 const g=m.gen||{};const area=m.tmp?[Math.min(m.tmp[0],m.tmp[2]),Math.min(m.tmp[1],m.tmp[3]),Math.max(m.tmp[0],m.tmp[2]),Math.max(m.tmp[1],m.tmp[3])]:(g.area&&g.world==w.name?g.area:null);
 if(area){const [ax,ay]=c(area[0],area[1]),[bx,by]=c(area[2],area[3]);const col={running:'#22c55e',paused:'#f59e0b',rendering:'#38bdf8',done:'#22c55e'}[g.state]||'#c084fc';
  x.fillStyle=col+'33';x.strokeStyle=col;x.lineWidth=2;x.setLineDash([6,3]);x.fillRect(ax,ay,bx-ax,by-ay);x.strokeRect(ax,ay,bx-ax,by-ay);x.setLineDash([])}
 const sp=w.spawn;if(sp){const [a,b]=c(sp.x||0,sp.z||0);x.fillStyle='#fde047';x.font='bold 18px sans-serif';x.fillText('⌂',a-6,b+6)}
 for(const p of m.players){if(p.world!=w.name)continue;const [a,b]=c(p.x,p.z);x.fillStyle=pcol(p.name);x.strokeStyle='#fff';x.lineWidth=2;const hi=headImg(m,p.name);
  if(hi&&hi.ok){x.fillRect(a-14,b-14,28,28);x.strokeRect(a-14,b-14,28,28);x.imageSmoothingEnabled=false;x.drawImage(hi.img,a-12,b-12,24,24)}else{x.beginPath();x.arc(a,b,7,0,7);x.fill();x.stroke()}
  x.font='bold 12px sans-serif';const tw=x.measureText(p.name).width;x.fillStyle='#111827cc';x.fillRect(a-tw/2-4,b-34,tw+8,16);x.fillStyle='#fff';x.fillText(p.name,a-tw/2,b-22)}}
function headImg(m,n){m.heads=m.heads||{};let t=m.heads[n];if(!t){t={img:new Image(),ok:false};t.img.onload=()=>{t.ok=true;m.dirty=true};t.img.src=hd(n,'');m.heads[n]=t}return t}
function pcol(n){let h=0;for(const ch of n)h=(h*31+ch.charCodeAt(0))>>>0;return['#ef4444','#3b82f6','#22c55e','#eab308','#a855f7','#f97316','#14b8a6','#ec4899'][h%8]}
function genUI(){const m=cur.m,g=m.gen||{},e=$('mgen');if(!e)return;const st=g.state||'idle';e.classList.toggle('hide',st=='idle');if(st=='idle')return;
 const fmt=n=>Math.round(n||0).toLocaleString('nl'),a=g.area,size=a?`${a[2]-a[0]} × ${a[3]-a[1]} blokken (${fmt(g.chunks)} chunks)`:'';let t='',btn='';
 if(st=='ready'){t='Gebied: '+size;btn=m.chunky?`<button class="go" onclick="genAct('start')">Genereren</button>`:'<span class="yel">Chunky staat niet in de plugins</span>';btn+=`<button onclick="genAct('clear')">Wissen</button>`}
 else if(st=='waiting'){t='⏳ Wacht tot de server leeg is • '+size;btn='<button class="bad" onclick="genAct(\'cancel\')">Annuleren</button>'}
 else if(st=='running'||st=='paused'){t=st=='paused'&&g.reason?'⏸ Gepauzeerd: '+g.reason:(st=='running'?'Chunks genereren':'⏸ Gepauzeerd')+' • '+size;btn=`<button class="warn" onclick="genAct('pause')">${st=='running'?'⏸ Pauze':'▶ Hervat'}</button><button class="bad" onclick="genAct('cancel')">■ Stop</button>`}
 else if(st=='rendering')t='✔ Chunks klaar • kaart wordt bijgewerkt…';else if(st=='done'){t='✔ Klaar • '+size;btn='<button onclick="genAct(\'clear\')">Sluiten</button>'}
 e.innerHTML=`<h3>Gebied genereren</h3><div>${esc(t)}</div><div class="bar" style="margin:8px 0"><i style="width:${st=='done'||st=='rendering'?100:(g.pct||0)}%"></i></div><div class="mut" style="font-size:12px">${esc(m.info||'')}${st=='paused'&&g.auto?' • hervat vanzelf als de server leeg is':''}</div><div class="row" style="margin-top:8px">${btn}</div>`}
async function genAct(a){await go('/map/gen',{action:a});mapLoad(false)}
/* ---------- Beheer ---------- */
V.beh=()=>{$('main').innerHTML=`<div class="card"><h3>Spelers <button class="sm" onclick="behP()">↻</button></h3><div id="bp" class="mut">Laden…</div></div>
<div class="card"><h3>Server-tuning <button class="sm" onclick="behT()">↻</button></h3><div id="bt" class="mut">Laden…</div></div>
<div class="card"><h3>Wereldgrootte <button class="sm" onclick="behW()">↻</button></h3><div id="bw" class="mut">Laden…</div></div>
<div class="card"><h3>Backups (Backuper) <button class="sm" onclick="behB()">↻</button></h3><div id="bb" class="mut">Laden…</div></div>`;behP();behT();behW();behB()};
const dt=t=>new Date(t*1000).toLocaleString('nl',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'});
const fb2=n=>n>1e9?(n/1e9).toFixed(1)+' GB':n>1e6?(n/1e6).toFixed(0)+' MB':Math.round(n/1e3)+' kB';
async function behB(){const j=await go('/api/backuper');if(!j||!$('bb'))return;cur.bk=j;cur.bsel=new Set();
 if(!j.jar){$('bb').innerHTML='Backuper staat niet in de plugins-map.';return}
 const tot=j.backups.reduce((a,b)=>a+b.size,0);
 $('bb').innerHTML=`<div>${esc(j.jar)}${j.disabled?' <span class="tag">uit</span>':''}</div><div class="mut" style="margin:4px 0">${j.backups.length} backups, ${fb2(tot)}${j.backups.length?' • laatste '+dt(j.backups[0].mtime):''}</div>
 <div class="row" style="margin:8px 0"><button class="go sm" onclick="bkNow()">💾 Nu backup maken</button><button class="bad sm" onclick="bkDel()">Geselecteerde verwijderen</button></div>`+
 j.backups.slice(0,40).map((b,i)=>`<label class="li"><input type="checkbox" onchange="this.checked?cur.bsel.add(${i}):cur.bsel.delete(${i})"><div><b>${esc(b.name)}</b><small>${esc(b.storage)} • ${dt(b.mtime)} • ${fb2(b.size)}</small></div></label>`).join('')+
 (j.has_config?`<h3 style="margin-top:14px">Instellingen van Backuper</h3>`+bkForm(j)+`<div class="row" style="margin-top:8px"><button class="sm pri" onclick="bkSave(false)">Opslaan</button><button class="sm warn" onclick="bkSave(true)">Opslaan en herstarten</button></div>`:'<div class="mut">Nog geen config.yml: start de server één keer.</div>')+
 `<h3 style="margin-top:14px">Backups van dit programma</h3>`+j.own.map(o=>`<div class="lab"><span>${esc(o.label)}</span><span class="mut" style="flex:none">${o.count} • ${fb2(o.size)}</span></div>`).join('')}
const BKG={autoBackup:['bool','Automatisch backups maken'],autoBackupPeriod:['int','Interval (minuten)'],autoBackupCron:['str','Cron-planning']};
const BKS={enabled:['bool','Opslag gebruiken'],autoBackup:['bool','Automatisch hierheen'],backupsFolder:['str','Map'],maxBackupsNumber:['int','Max. aantal (0 = onbeperkt)'],maxBackupsWeight:['int','Max. grootte in MB (0 = onbeperkt)'],zipArchive:['bool','Als zip bewaren'],zipCompressionLevel:['int','Zip-compressie (0-9)']};
function bkRow(path,def,val){const id='bk|'+path.join('|');return def[0]=='bool'?`<label class="lab"><span>${def[1]}</span><input type="checkbox" data-k="${esc(id)}" data-t="bool" ${val?'checked':''}></label>`:`<label class="lab"><span>${def[1]}</span><input data-k="${esc(id)}" data-t="${def[0]}" value="${esc(val)}" ${def[0]=='int'?'inputmode="numeric"':''}></label>`}
function bkForm(j){let h='<div class="mut" style="font-size:12px">Planning</div>';for(const k in BKG)if(k in j.global)h+=bkRow(['backup',k],BKG[k],j.global[k]);
 for(const s of j.storages){h+=`<div class="mut" style="font-size:12px;margin-top:8px">Opslag ${esc(s.id)} (${esc(s.type||'?')})</div>`;for(const k in BKS)if(k in s)h+=bkRow(['storages',s.id,k],BKS[k],s[k])}return h}
async function bkSave(restart){const changes=[];document.querySelectorAll('[data-k]').forEach(e=>{const path=e.dataset.k.split('|').slice(1);const v=e.dataset.t=='bool'?e.checked:e.value;changes.push({path,value:v})});
 if(restart&&!await ask('Opslaan en de server herstarten?'))return;await go('/api/backuper/config',{changes,restart});setTimeout(behB,1500)}
async function bkNow(){const j=cur.bk;await go('/api/backuper/now',{cmd:j.cmd});setTimeout(behB,20000)}
async function bkDel(){const j=cur.bk,items=[...cur.bsel].map(i=>j.backups[i]).filter(Boolean);if(!items.length)return toast('Vink eerst backups aan');if(!await ask(items.length+' backup(s) definitief verwijderen?'))return;await go('/api/backuper/delete',{items:items.map(b=>({storage:b.storage,name:b.name}))});behB()}
const dur=s=>{s=Math.round(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return h?`${h}u ${m}m`:`${m}m`};
async function behP(){const j=await go('/api/stats');if(!j||!$('bp'))return;j.rows.sort((a,b)=>b.online-a.online||b.time-a.time);
 $('bp').innerHTML=j.rows.length?`<table><tr><th>Speler</th><th class="n">Tijd</th><th class="n">Dood</th><th class="n">Kills</th><th class="n">km</th></tr>`+j.rows.map(r=>`<tr><td>${r.online?'🟢 ':''}<img class="hd" src="${hd(r.name,'')}">${esc(r.name)}</td><td class="n">${dur(r.time)}</td><td class="n">${r.deaths}</td><td class="n">${r.kills}</td><td class="n">${(r.dist/1000).toFixed(1)}</td></tr>`).join('')+'</table>':'Geen spelersgegevens gevonden.'}
async function behT(){const j=await go('/api/tuning');if(!j||!$('bt'))return;const fx=j.rows.filter(r=>r.fix);
 $('bt').innerHTML=j.rows.map(r=>`<div class="li"><div><b class="${r.warn?'yel':''}">${esc(r.what)}: ${esc(r.now)}</b><small style="white-space:normal">${esc(r.adv)}</small></div></div>`).join('')+(fx.length?`<div class="row" style="margin-top:8px"><button class="go" onclick='behFix(${JSON.stringify(fx.map(r=>r.fix.split("=")[0]))})'>Alle ${fx.length} adviezen toepassen</button></div>`:'')}
async function behFix(keys){if(!await ask('Adviezen toepassen in server.properties? Je moet de server daarna herstarten.'))return;await go('/api/tuning/apply',{keys});behT()}
async function behW(){const j=await go('/api/world');if(!j||!$('bw'))return;const tot=j.items.reduce((a,b)=>a+b.size,0)||1,fb=n=>n>1e9?(n/1e9).toFixed(1)+' GB':n>1e6?(n/1e6).toFixed(0)+' MB':Math.round(n/1e3)+' kB';
 $('bw').innerHTML=j.items.map(i=>`<div class="li"><div><b>${esc(i.name)}</b><div class="bar" style="margin-top:4px"><i style="width:${i.size/tot*100}%"></i></div></div><span>${fb(i.size)}</span></div>`).join('')+(j.disk?`<div class="mut" style="margin-top:6px">Schijf: ${fb(j.disk.free)} vrij van ${fb(j.disk.total)}</div>`:'')+
 `<div class="row" style="margin-top:10px"><button onclick="behLogs()">Oude logs opruimen</button></div><div class="mut" style="font-size:12px;margin-top:8px">Regio's buiten een gebied wegzetten: kies op de kaart een gebied en gebruik dat op de pc (de server moet uit staan).</div>`}
async function behLogs(){if(!await ask('Logs ouder dan 7 dagen en crash-reports ouder dan 14 dagen verwijderen?'))return;await go('/api/world/logs',{},'Opgeruimd');setTimeout(behW,1500)}
/* ---------- Meer ---------- */
V.more=()=>{$('main').innerHTML=`<div class="card"><h3>Bereikbaarheid</h3><div id="net" class="mut">Laden…</div></div><div class="card"><h3>Instellingen van het programma</h3><div id="set" class="mut">Laden…</div></div>
<div class="card"><h3>Logboek van het programma</h3><div class="con" id="alog" style="height:30vh"></div></div>
<div class="card"><h3>Telefoon</h3><div class="row"><button onclick="logout()">Uitloggen</button></div><div class="mut" style="font-size:12px;margin-top:8px" id="ver"></div></div>`;
 netLoad();setLoad();LOG2.forEach(addAlog);$('ver').textContent='Programmaversie '+(S.version||'')};
const LOG2=[];function addAlog(l){const c=$('alog');if(!c)return;const d=document.createElement('div');d.className={error:'e',warn:'w',ok:'o'}[l[3]]||'';d.textContent=`[${l[1]}] ${l[2]}`;c.appendChild(d);c.scrollTop=c.scrollHeight}
async function netLoad(){const j=await go('/api/net');if(!j||!$('net'))return;
 $('net').innerHTML=`<div style="color:${j.status.color||'inherit'}">${esc(j.status.text)}</div><div class="mut" style="margin:4px 0">${esc(j.motd)} ${esc(j.info)}</div><div style="color:${j.bedrock.color||'inherit'}">${esc(j.bedrock.text)}</div><div class="mut" style="font-size:12px;margin-top:4px;white-space:pre-wrap">${esc(j.diag)}</div>
 <div class="f"><input id="nh" value="${esc(j.host)}" placeholder="Adres/IP"><input id="np" value="${esc(j.jport)}" style="max-width:90px" inputmode="numeric"></div>
 <div class="row" style="margin-top:8px"><button onclick="netChk(false)" ${j.busy?'disabled':''}>Controleer</button><button onclick="netChk(true)" ${j.busy?'disabled':''}>Alleen lokaal</button></div>`}
async function netChk(local){await go('/api/net/check',{host:$('nh').value,jport:$('np').value,local},'Controleren…');setTimeout(netLoad,3500);setTimeout(netLoad,8000)}
async function setLoad(){const j=await go('/api/settings');if(!j||!$('set'))return;
 $('set').innerHTML=j.items.map(i=>`<label class="lab"><span>${esc(i.label)}</span>${i.type=='bool'?`<input type="checkbox" ${i.value?'checked':''} onchange="setSet('${i.key}',this.checked)">`:`<input value="${esc(i.value)}" ${i.type=='int'?'inputmode="numeric"':''} onchange="setSet('${i.key}',this.value)">`}</label>`).join('')}
const setSet=(key,value)=>go('/api/settings',{key,value},'Opgeslagen');
async function logout(){document.cookie='mcsess=;Max-Age=0;path=/';show(false)}
/* ---------- poll ---------- */
async function poll(){if(busy)return;busy=1;try{const j=await api(`/api/state?since=${since}&nsince=${nsince}&asince=${asince}`);S=j;
 const m={online:['Online','var(--g)'],starting:['Opstarten…','var(--y)'],stopping:['Stoppen…','var(--y)'],stopped:['Gestopt','var(--r)']}[j.state]||[j.state,'var(--m)'];
 $('st').textContent=m[0];$('dot').style.background=m[1];$('up').textContent=j.stats.uptime&&j.stats.uptime!='-'?j.stats.uptime:'';
 j.lines.forEach(l=>{since=Math.max(since,l[0]);LOG.push(l);if(LOG.length>400)LOG.shift();if(tab=='srv')addLine(l)});
 j.notes.forEach(n=>{nsince=Math.max(nsince,n[0]);toast(n[2],7000)});j.alog.forEach(l=>{asince=Math.max(asince,l[0]);LOG2.push(l);if(LOG2.length>200)LOG2.shift();if(tab=='more')addAlog(l)});
 const bd=$('bd-upd');if(bd){bd.classList.toggle('hide',!j.selfupd);bd.textContent='!'}
 if(tab=='srv')draw();if(tab=='map'&&cur.m&&j.gen){cur.m.gen=Object.assign({},cur.m.gen,j.gen);cur.m.info=j.gen_info;genUI();cur.m.dirty=true}}catch(e){}busy=0}
fetch('/api/state?since=0',{headers:{'X-MC':'1'}}).then(r=>{show(r.status!=401);if(r.status!=401){build();poll()}});setInterval(poll,2000);
</script></body></html>
"""


class RemoteServer:
    """Webserver voor de telefoon. Alles wat het programma zelf aanraakt gebeurt in de hoofdthread (call_main)."""

    SETTINGS = {  # sleutel -> (soort, label, min, max)
        "confirm": ("bool", "Bevestiging vragen voor updates"), "auto_restart": ("bool", "Automatisch herstarten na een crash"),
        "keep_server_backups": ("bool", "Backups van server.jar bewaren"), "server_backups_max": ("int", "Aantal server.jar-backups", 1, 99),
        "keep_plugin_backups": ("bool", "Backups van plugins bewaren"), "plugin_backups_max": ("int", "Aantal plugin-backups", 1, 99),
        "stop_timeout": ("int", "Wachttijd bij stoppen (sec)", 10, 600), "poll_secs": ("int", "Spelers/TPS verversen (sec, 0 = uit)", 0, 600),
        "graph_minutes": ("int", "Grafiek-tijdvenster (min)", 1, 180), "java_xms": ("str", "Java min. geheugen (bijv. 1G)"),
        "java_xmx": ("str", "Java max. geheugen (bijv. 4G)"), "java_extra": ("str", "Extra Java-opties"),
        "selfupdate_check": ("bool", "Automatisch zoeken naar programma-updates"), "selfupdate_auto": ("bool", "Updates automatisch installeren"),
        "desk_main": ("bool", "Nieuwe interface als hoofdscherm (bij opstarten)"),
        "clean_console": ("bool", "Schone console"), "console_max_lines": ("int", "Maximaal aantal consoleregels", 500, 50000),
        "temp_enabled": ("bool", "Temperatuur tonen"), "temp_warn": ("int", "Temperatuurwaarschuwing (°C)", 50, 110),
        "notify_crash": ("bool", "Melding bij crash"), "notify_start": ("bool", "Melding als de server klaar is met starten"),
        "notify_join": ("bool", "Melding als een speler binnenkomt"), "notify_leave": ("bool", "Melding als een speler weggaat"),
        "notify_chunky": ("bool", "Melding als genereren klaar is"), "notify_update": ("bool", "Melding bij programma-update"),
        "notify_ignore": ("str", "Namen zonder melding (komma's)"),
    }

    def __init__(self, app):
        self.app = app
        self.httpd = None
        self.thread = None
        self.lines = deque(maxlen=400)
        self.lid = 0
        self.notes = deque(maxlen=100)
        self.nid = 0
        self.alog = deque(maxlen=200)
        self.alid = 0
        self.snap = {"state": "stopped", "stats": {}, "players": [], "graphs": {"cpu": [], "ram": [], "tps": []}}
        self.rpcs = queue.Queue()
        self.auto_until = 0.0
        self.answer = True
        self.sessions = {}
        self.desk_only, self.port = False, 0
        self.desk_token = secrets.token_urlsafe(18)
        self.fails = {}
        self.error = ""
        self.lock = threading.Lock()
        self.results = []
        self.plans = {}
        self._shim_done = False

    # ================= hoofdthread =================
    def push(self, e):
        kind = {"error": "e", "warn": "w", "ok": "o", "cmd": "c"}.get(e.get("tag"), "")
        text = e.get("raw") if e.get("kind") == "own" else (e.get("raw") or "")
        with self.lock:
            self.lid += 1
            self.lines.append((self.lid, str(text)[:600], kind))

    def push_log(self, text, level):
        with self.lock:
            self.alid += 1
            self.alog.append((self.alid, datetime.now().strftime("%H:%M:%S"), str(text)[:500], level))

    def note(self, text, level="info"):
        with self.lock:
            self.nid += 1
            self.notes.append((self.nid, level, str(text)[:1500]))

    def _install_shim(self):
        """Vensters van het programma worden automatisch beantwoord als de opdracht van de telefoon komt."""
        if self._shim_done:
            return
        self._shim_done = True
        me = self

        def msg_of(a, k):
            return str(a[1] if len(a) > 1 else k.get("message", ""))

        for name in ("askyesno", "askokcancel", "askretrycancel"):
            orig = getattr(messagebox, name)

            def mk(orig):
                def f(*a, **k):
                    if time.time() < me.auto_until:
                        me.note(msg_of(a, k).strip(), "ask")
                        return me.answer
                    return orig(*a, **k)
                return f
            setattr(messagebox, name, mk(orig))
        for name, lvl in (("showinfo", "info"), ("showwarning", "warn"), ("showerror", "error")):
            orig = getattr(messagebox, name)

            def mk2(orig, lvl):
                def f(*a, **k):
                    if time.time() < me.auto_until:
                        me.note(msg_of(a, k).strip(), lvl)
                        return "ok"
                    return orig(*a, **k)
                return f
            setattr(messagebox, name, mk2(orig, lvl))

    def call_main(self, fn, timeout=60, auto=False, answer=True):
        ev, box = threading.Event(), {}
        self.rpcs.put((fn, ev, box, auto, answer))
        if not ev.wait(timeout):
            raise TimeoutError("Het programma reageert niet")
        if "err" in box:
            raise box["err"]
        return box.get("val")

    def pump(self):
        while True:
            try:
                fn, ev, box, auto, answer = self.rpcs.get_nowait()
            except queue.Empty:
                return
            if auto:
                self.auto_until = time.time() + 60
                self.answer = answer
            try:
                box["val"] = fn()
            except Exception as e:  # noqa
                box["err"] = e
            if auto:
                self.auto_until = time.time() + 2   # korte nasleep voor vensters die direct na de opdracht komen
            ev.set()

    def update(self):
        a = self.app
        try:
            def series(sk):
                pts = [v for _t, v in list(sk.data)[-150:] if v is not None]
                return pts[::max(1, len(pts) // 60)]
            pl = []
            for iid in a.ptree.get_children():
                v = a.ptree.item(iid, "values")
                pl.append({"name": iid, "type": v[1] if len(v) > 1 else "", "since": v[2] if len(v) > 2 else ""})
            g = a.tab_map.gen
            pb = a.pbar
            snap = {"state": a.srv_state, "stats": {k: a.sv[k].get() for k in ("uptime", "cpu", "ram", "tps", "players", "temp")},
                    "players": pl, "graphs": {"cpu": series(a.spark_cpu), "ram": series(a.spark_ram), "tps": series(a.spark_tps)},
                    "busy": bool(a.busy), "status": a.status_var.get(), "clean": bool(a.clean_var.get()),
                    "progress": [float(pb.cget("value") or 0), float(pb.cget("maximum") or 1), str(pb.cget("mode"))],
                    "selfupd": (a._upd or {}).get("version") if getattr(a, "_upd", None) else None,
                    "gen": {k: (list(g[k]) if isinstance(g.get(k), tuple) else g.get(k)) for k in ("state", "pct", "done", "chunks", "area", "world", "reason", "auto")},
                    "gen_info": a.tab_map.gen_info.cget("text") if g.get("state") != "idle" else "",
                    "version": APP_VERSION}
            snap["graphs"]["temp"] = series(a.spark_temp)
            snap["stats"]["sleep"] = a.sv["sleep"].get()
            try:
                free = shutil.disk_usage(a.folder_var.get().strip() or ".").free / 1e9
            except OSError:
                free = None
            snap.update(sleep={"on": bool(a.cfg.get("sleep_enabled")), "sleeping": bool(getattr(a, "_sleeping", False))},
                        xmx=a.srv_xmx, mc=a.mc_var.get(), build=a.build_var.get(), disk=free,
                        folder=os.path.basename(a.folder_var.get().strip().rstrip("/\\")) if a.folder_var.get().strip() else "",
                        pupd=sum(1 for r in a.rows.values() if r.get("state") == "update"),
                        paperupd=str(a.paper_label.cget("text")).startswith("⬆"))
            with self.lock:
                self.snap = snap
        except Exception:
            pass

    def folder(self):
        return self.call_main(lambda: self.app.folder_var.get().strip())

    # ================= API (draaien in de serverthread) =================
    def api_state(self, q, body):
        def n(k):
            try:
                return int(q.get(k, ["0"])[0])
            except ValueError:
                return 0
        since, ns, asn = n("since"), n("nsince"), n("asince")
        with self.lock:
            snap = dict(self.snap)
            snap["lines"] = [l for l in self.lines if l[0] > since][-300:]
            snap["notes"] = [x for x in self.notes if x[0] > ns]
            snap["alog"] = [x for x in self.alog if x[0] > asn][-100:]
        return 200, snap

    def api_action(self, q, body):
        n = body.get("name")
        a = self.app
        if n not in ("start", "stop", "restart", "kill"):
            return 400, {"error": "onbekend"}

        def go():
            if n == "start":
                if not a.srv_running():
                    a.srv_start()
            elif n == "stop" and a.srv_running():
                a.srv_stop()
            elif n == "restart" and a.srv_running():
                a.srv_stop(restart=True)
            elif n == "kill" and a.srv_running():
                a.srv_kill()
            a.log(f"Telefoon: {n}", "info")
        self.call_main(go, auto=True)
        return 200, {"ok": True, "msg": {"start": "Starten…", "stop": "Stoppen…", "restart": "Herstarten…", "kill": "Gestopt (geforceerd)"}[n]}

    def api_cmd(self, q, body):
        c = str(body.get("cmd", "")).strip()
        if not c or len(c) > 400 or "\n" in c or "\r" in c:
            return 400, {"error": "ongeldig commando"}
        ok = self.call_main(lambda: self.app.srv_send(c))
        return 200, {"ok": bool(ok), "msg": "" if ok else "De server draait niet"}

    def api_player(self, q, body):
        name, act, arg = str(body.get("name", "")), body.get("action"), str(body.get("arg", "")).replace("\n", " ").strip()[:200]
        if not re.fullmatch(r"[\w.\-]{1,40}", name):
            return 400, {"error": "ongeldige naam"}
        cmds = {"kick": f"kick {name} {arg}", "ban": f"ban {name} {arg}", "pardon": f"pardon {name}", "op": f"op {name}",
                "deop": f"deop {name}", "msg": f"msg {name} {arg}", "whitelist_add": f"whitelist add {name}",
                "whitelist_remove": f"whitelist remove {name}", "gm": f"gamemode {arg if arg in ('survival', 'creative', 'adventure', 'spectator') else 'survival'} {name}",
                "tp": f"tp {name} {arg}" if re.fullmatch(r"[\w.\-]{1,40}", arg) else ""}
        c = cmds.get(act, "").strip()
        if not c:
            return 400, {"error": "ongeldige actie"}
        ok = self.call_main(lambda: self.app.srv_send(c))
        return 200, {"ok": bool(ok), "msg": c if ok else "De server draait niet"}

    def api_clean(self, q, body):
        self.call_main(lambda: self.app.clean_var.set(bool(body.get("on"))))
        return 200, {"ok": True}

    def api_ram(self, q, body):
        v = str(body.get("value", ""))[:10]

        def go():
            self.app.ram_var.set(v)
            self.app.ram_apply()
        self.call_main(go, auto=True, answer=bool(body.get("restart", False)))
        return 200, {"ok": True}

    # --- plugins ---
    def _pitem(self, i):
        return {"file": i["file"], "name": i["name"], "version": i.get("version") or "", "enabled": i["enabled"],
                "desc": (i.get("desc") or "")[:200], "missing": i.get("missing", []), "needed_by": i.get("needed_by", []),
                "size": i.get("size", 0)}

    def api_plugins(self, q, body):
        folder = self.folder()
        items = scan_plugins(os.path.join(folder, "plugins")) if folder else []
        return 200, {"items": [self._pitem(i) for i in items], "folder": bool(folder),
                     "plm": bool(self.call_main(lambda: plugman_name(items)))}

    def _items_for(self, files):
        t = self.app.tab_plug
        t.refresh()
        return [t.items[f] for f in files if f in t.items]

    def api_plugins_toggle(self, q, body):
        files, enable, force = list(body.get("files") or []), bool(body.get("enable")), bool(body.get("force"))
        self.call_main(lambda: self.app.tab_plug.refresh())
        t = self.app.tab_plug
        sel = [t.items[f] for f in files if f in t.items and t.items[f]["enabled"] != enable]
        if not sel:
            return 200, {"ok": True, "msg": "Niets te doen"}
        warn = ""
        if not enable:
            names = {i["name"].lower() for i in sel}
            broken = sorted({o["name"] for o in t.items.values() if o["enabled"] and o["name"].lower() not in names
                             and any(d.lower() in names for d in o["depend"])})
            if broken:
                warn = f"{', '.join(broken)} heeft deze plugin nodig en start dan niet meer goed."
        else:
            missing = sorted({m for i in sel for m in i["missing"]})
            if missing:
                warn = f"Deze plugin heeft {', '.join(missing)} nodig, en dat staat niet aan."
        if warn and not force:
            return 200, {"confirm": warn + " Toch doorgaan?"}
        running = self.call_main(lambda: self.app.srv_running())
        if not enable and running and not body.get("stop_ok"):
            return 200, {"confirm": "De server draait. Om plugins uit te zetten moet hij even stoppen en daarna weer starten. Doorgaan?",
                         "needs": "stop_ok"}
        self.call_main(lambda: t._toggle(enable, only=[t.items[i["file"]] for i in sel]), auto=True, answer=bool(body.get("restart", True)))
        return 200, {"ok": True, "msg": ("Aangezet" if enable else "Uitgezet") + f": {', '.join(i['name'] for i in sel)}"}

    def api_plugins_remove(self, q, body):
        files = list(body.get("files") or [])
        t = self.app.tab_plug
        self.call_main(lambda: t.refresh())
        sel = [t.items[f] for f in files if f in t.items]
        if not sel:
            return 400, {"error": "niet gevonden"}
        self.call_main(lambda: t._remove(only=sel), auto=True)
        return 200, {"ok": True, "msg": f"{len(sel)} plugin(s) verwijderd (naar de map verwijderde_plugins)"}

    def api_plugins_plm(self, q, body):
        files = [f for f in (body.get("files") or []) if isinstance(f, str) and f.lower().endswith(".jar")]
        if body.get("unload"):
            def un():
                t = self.app.tab_plug
                names = [t.items[f]["name"] for f in files if f in t.items and t.items[f]["enabled"]
                         and not norm_name(t.items[f]["name"]).startswith("plugman")]
                if names:
                    t._plm_unload(names)
            self.call_main(un, auto=True)
        else:
            self.call_main(lambda: self.app.tab_plug._plm_load([f[:-4] for f in files]), auto=True)
        return 200, {"ok": True}

    def api_plugins_search(self, q, body):
        text = str(body.get("q", "")).strip()[:200]
        if not text:
            return 400, {"error": "Typ iets om te zoeken"}
        t = self.app.tab_plug
        mc, loaders, names, folder = self.call_main(lambda: (t._mc(), t._loaders(), t._installed_names() or [], self.app.folder_var.get().strip()))
        if not names and folder:
            names = [x["name"] for x in scan_plugins(os.path.join(folder, "plugins"))]
        only = bool(body.get("compat")) and bool(mc)
        results, info = search_plugins(text, mc, loaders, names, only_compat=only)
        self.results = results
        out = []
        for idx, r in enumerate(results):
            out.append({"idx": idx, "name": r["name"], "desc": (r.get("desc") or "")[:300], "exact": bool(r.get("exact")),
                        "compat": r.get("compat"), "installed": bool(r.get("installed")), "downloads": r.get("downloads", 0),
                        "updated": r["updated"].strftime("%d-%m-%Y") if r.get("updated") else "", "sources": r.get("sources", []),
                        "why": r.get("why") or "", "page": r.get("page") or "", "versions": (r.get("versions") or [])[-1:]})
        msg = ("Ik snap dit als: " + " / ".join(info["concepts"]) + ".") if info.get("concepts") else ""
        return 200, {"results": out, "mc": mc, "info": msg + ((" (let op: " + "; ".join(info["errors"]) + ")") if info.get("errors") else "")}

    def api_plugins_install(self, q, body):
        t = self.app.tab_plug
        folder = self.folder()
        pdir = os.path.join(folder, "plugins")
        if body.get("plan_id"):
            plan = self.plans.pop(body["plan_id"], None)
            if not plan:
                return 400, {"error": "Plan verlopen, begin opnieuw"}
            done = install_plan(plan, pdir)
            self.call_main(lambda: (self.app.log("Geïnstalleerd (telefoon): " + ", ".join(done), "ok"), t.refresh()))
            run = self.call_main(lambda: self.app.srv_running())
            if run:
                self.call_main(lambda: t._apply_changes(done), auto=True, answer=bool(body.get("restart", False)))
            return 200, {"ok": True, "msg": "Geïnstalleerd: " + ", ".join(done), "running": run}
        try:
            r = self.results[int(body.get("idx"))]
        except (TypeError, ValueError, IndexError):
            return 400, {"error": "Zoek eerst opnieuw"}
        mc, loaders, names, unstable = self.call_main(lambda: (t._mc(), t._loaders(), t._installed_names() or [], self.app.unstable_var.get()))
        plan, notes = plan_install(r, mc, loaders, names, unstable)
        pid = secrets.token_urlsafe(8)
        self.plans[pid] = plan
        lines = []
        for p in plan:
            lines.append(f"{p.get('title', r['name'])} {p['version']} [{p['source']}]" + (" (verplichte afhankelijkheid)" if p.get("dep") else "")
                         + (" ⚠ niet bevestigd voor jouw Minecraft-versie" if mc and not p.get("verified", True) else ""))
        if any(p.get("vtype") not in (None, "release") for p in plan):
            lines.append("Let op: er is alleen een bèta/alpha-versie.")
        return 200, {"plan_id": pid, "lines": lines + notes, "running": self.call_main(lambda: self.app.srv_running())}

    # --- updates ---
    def api_updates(self, q, body):
        a = self.app

        def get():
            rows = []
            for iid in a.tree.get_children():
                v = a.tree.item(iid, "values")
                tag = (a.tree.item(iid, "tags") or [""])[0]
                rows.append({"id": iid, "name": v[0], "file": v[1], "cur": v[2], "latest": v[3], "source": v[4], "status": v[5], "tag": tag})
            return {"paper": {"text": a.paper_label.cget("text"), "color": a.paper_label.cget("fg")}, "mc": a.mc_var.get(),
                    "build": a.build_var.get(), "rows": rows, "unstable": bool(a.unstable_var.get()),
                    "updfolder": bool(a.updfolder_var.get()), "selfupd": (a._upd or {}).get("version") if getattr(a, "_upd", None) else None,
                    "version": APP_VERSION}
        return 200, self.call_main(get)

    def api_updates_check(self, q, body):
        a = self.app
        what = body.get("what", "all")
        fn = {"all": a.on_check_all, "paper": a.on_paper_check, "plugins": a.on_plugins_check}.get(what)
        if not fn:
            return 400, {"error": "onbekend"}
        self.call_main(fn, auto=True)
        return 200, {"ok": True}

    def api_updates_install(self, q, body):
        a = self.app
        what, ids = body.get("what"), list(body.get("ids") or [])
        if what == "paper":
            self.call_main(a.on_paper_update, auto=True)
        elif what == "plugins":
            def go():
                if ids:
                    a.tree.selection_set([i for i in ids if a.tree.exists(i)])
                    a.on_plugins_update(False)
                else:
                    a.on_plugins_update(True)
            self.call_main(go, auto=True)
        else:
            return 400, {"error": "onbekend"}
        return 200, {"ok": True}

    def api_updates_opt(self, q, body):
        a = self.app

        def go():
            if "unstable" in body:
                a.unstable_var.set(bool(body["unstable"]))
            if "updfolder" in body:
                a.updfolder_var.set(bool(body["updfolder"]))
            a._save_cfg()
        self.call_main(go)
        return 200, {"ok": True}

    def api_selfupdate(self, q, body):
        a = self.app
        if body.get("action") == "check":
            self.call_main(lambda: a.selfupdate_check(True), auto=True)
        elif body.get("action") == "install":
            self.call_main(a.selfupdate_install, auto=True, answer=True)
        return 200, {"ok": True}

    # --- bereikbaarheid ---
    def api_net(self, q, body):
        a = self.app

        def get():
            return {"host": a.reach_host_var.get(), "jport": a.reach_port_var.get(), "bed": bool(a.reach_bed_var.get()),
                    "bport": a.reach_bport_var.get(), "lport": a.reach_lport_var.get(), "auto": bool(a.reach_auto_var.get()),
                    "status": {"text": a.net_status.cget("text"), "color": a.net_status.cget("fg")},
                    "motd": a.net_motd.cget("text"), "info": a.net_info.cget("text"), "diag": a.net_diag.cget("text"),
                    "bedrock": {"text": a.net_bed.cget("text"), "color": a.net_bed.cget("fg")}, "busy": bool(a._net_busy)}
        return 200, self.call_main(get)

    def api_net_check(self, q, body):
        a = self.app

        def go():
            for key, var in (("host", a.reach_host_var), ("jport", a.reach_port_var), ("bport", a.reach_bport_var),
                             ("lport", a.reach_lport_var)):
                if key in body:
                    try:
                        var.set(str(body[key]).strip() if key == "host" else int(body[key]))
                    except (ValueError, tk.TclError):
                        pass
            if "bed" in body:
                a.reach_bed_var.set(bool(body["bed"]))
            if "auto" in body:
                a.reach_auto_var.set(bool(body["auto"]))
            a._save_cfg()
            a.net_check(local_only=bool(body.get("local")))
        self.call_main(go, auto=True)
        return 200, {"ok": True}

    # --- beheer ---
    def api_stats(self, q, body):
        rows = self.call_main(self.app.tab_beheer._collect_players)
        return 200, {"rows": [{"name": r["name"], "online": bool(r["online"]), "time": r["time"], "sessions": r["sessions"], "last": r["last"],
                               "deaths": r["deaths"], "kills": r["kills"], "dist": r["dist"]} for r in rows]}

    def api_tuning(self, q, body):
        b = self.app.tab_beheer

        def get():
            b.refresh_tuning()
            fixes = {k[0] for k in b.tu_fix.values()}
            out = []
            for iid in b.tu_tree.get_children():
                v = b.tu_tree.item(iid, "values")
                tag = (b.tu_tree.item(iid, "tags") or [""])[0]
                fx = b.tu_fix.get(iid)
                out.append({"what": v[0], "now": v[1], "adv": v[2], "warn": tag == "warn", "fix": f"{fx[0]}={fx[1]}" if fx else ""})
            return out
        return 200, {"rows": self.call_main(get)}

    def api_tuning_apply(self, q, body):
        b = self.app.tab_beheer
        keys = set(body.get("keys") or [])

        def go():
            b.refresh_tuning()
            ids = [i for i, fx in b.tu_fix.items() if fx[0] in keys]
            if not ids:
                return False
            b.tu_tree.selection_set(ids)
            b.apply_tuning()
            return True
        ok = self.call_main(go, auto=True)
        return 200, {"ok": bool(ok), "msg": "Aangepast. Herstart de server om het te laten werken." if ok else "Niets aan te passen"}

    def api_world(self, q, body):
        folder = self.folder()
        out, du = measure_world(folder)
        return 200, {"items": [{"name": n, "size": s, "files": f} for n, s, f in out],
                     "disk": {"free": du.free, "total": du.total} if du else None}

    def api_world_logs(self, q, body):
        self.call_main(self.app.tab_beheer.clean_logs, auto=True)
        return 200, {"ok": True}

    def api_world_trim(self, q, body):
        try:
            area = tuple(int(x) for x in body.get("area"))
            dim = body.get("dim", "overworld")
            if len(area) != 4 or dim not in ("overworld", "nether", "end"):
                raise ValueError
        except (TypeError, ValueError):
            return 400, {"error": "ongeldig gebied"}
        b = self.app.tab_beheer
        running = self.call_main(lambda: self.app.srv_running())
        if body.get("confirm"):
            def go():
                self.app.tab_map.sel = area
                b.trim_world.set(dim)
                b.trim_regions()
            self.call_main(go, auto=True)
            return 200, {"ok": True}
        move, keep = b.plan_trim(area, dim)
        return 200, {"move": len(move), "keep": keep, "size": sum(s for _p, s in move), "running": running}

    # --- instellingen ---
    def api_settings(self, q, body):
        a = self.app

        def get():
            out = []
            for k, spec in self.SETTINGS.items():
                out.append({"key": k, "type": spec[0], "label": spec[1], "value": a.cfg.get(k, DEFAULTS.get(k)),
                            "min": spec[2] if len(spec) > 2 else None, "max": spec[3] if len(spec) > 3 else None})
            return out
        return 200, {"items": self.call_main(get)}

    def api_settings_set(self, q, body):
        a = self.app
        k, v = body.get("key"), body.get("value")
        spec = self.SETTINGS.get(k)
        if not spec:
            return 400, {"error": "onbekende instelling"}
        try:
            if spec[0] == "bool":
                v = bool(v)
            elif spec[0] == "int":
                v = min(max(int(v), spec[2]), spec[3])
            else:
                v = str(v).strip()[:300]
        except (TypeError, ValueError):
            return 400, {"error": "ongeldige waarde"}

        def go():
            a.cfg[k] = v
            if k == "clean_console":
                a.clean_var.set(v)
            a._save_cfg()
            a.apply_settings()
        self.call_main(go)
        return 200, {"ok": True}

    # ================= HTTP =================
    def start(self, port, host="0.0.0.0", desk_only=False):
        self.stop()
        self.desk_only = desk_only
        outer = self
        self._install_shim()
        routes = {
            ("GET", "/api/state"): outer.api_state, ("POST", "/api/action"): outer.api_action, ("POST", "/api/cmd"): outer.api_cmd,
            ("POST", "/api/player"): outer.api_player, ("POST", "/api/clean"): outer.api_clean, ("POST", "/api/ram"): outer.api_ram,
            ("GET", "/api/plugins"): outer.api_plugins, ("POST", "/api/plugins/toggle"): outer.api_plugins_toggle,
            ("POST", "/api/plugins/remove"): outer.api_plugins_remove, ("POST", "/api/plugins/plm"): outer.api_plugins_plm,
            ("POST", "/api/plugins/search"): outer.api_plugins_search, ("POST", "/api/plugins/install"): outer.api_plugins_install,
            ("GET", "/api/updates"): outer.api_updates, ("POST", "/api/updates/check"): outer.api_updates_check,
            ("POST", "/api/updates/install"): outer.api_updates_install, ("POST", "/api/updates/opt"): outer.api_updates_opt,
            ("POST", "/api/selfupdate"): outer.api_selfupdate,
            ("GET", "/api/net"): outer.api_net, ("POST", "/api/net/check"): outer.api_net_check,
            ("GET", "/api/stats"): outer.api_stats, ("GET", "/api/tuning"): outer.api_tuning, ("POST", "/api/tuning/apply"): outer.api_tuning_apply,
            ("GET", "/api/world"): outer.api_world, ("POST", "/api/world/logs"): outer.api_world_logs, ("POST", "/api/world/trim"): outer.api_world_trim,
            ("GET", "/api/settings"): outer.api_settings, ("POST", "/api/settings"): outer.api_settings_set,
        }
        routes.update(outer.extra_routes())

        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "MCM"

            def log_message(self, *a):
                pass

            def _ip_ok(self):
                if not outer.app.cfg.get("remote_lan_only", True):
                    return True
                try:
                    ip = ipaddress.ip_address(self.client_address[0].split("%")[0])
                    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or
                                (ip.version == 4 and ip in ipaddress.ip_network("100.64.0.0/10")))
                except ValueError:
                    return False

            def _send(self, code, body, ctype="application/json", extra=()):
                if isinstance(body, (dict, list)):
                    body = json.dumps(body).encode("utf-8")
                elif isinstance(body, str):
                    body = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") or "json" in ctype else ""))
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store" if not ctype.startswith("image/") else "max-age=30")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                for k, v in extra:
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def _authed(self):
                m = re.search(r"mcsess=([A-Za-z0-9_-]+)", self.headers.get("Cookie", ""))
                t = outer.sessions.get(m.group(1)) if m else None
                return bool(t and t > time.time())

            def _json_body(self):
                try:
                    n = min(int(self.headers.get("Content-Length") or 0), 20000)
                    return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
                except (ValueError, OSError):
                    return {}

            def _dispatch(self, method):
                if not self._ip_ok():
                    return self._send(403, "Alleen op je eigen netwerk", "text/plain")
                u = urllib.parse.urlsplit(self.path)
                path, query = u.path, urllib.parse.parse_qs(u.query)
                if method == "POST":
                    if self.headers.get("X-MC") != "1":
                        return self._send(400, {"error": "ongeldig"})
                    body = self._json_body()
                else:
                    body = {}
                if method == "GET":
                    if path == "/desk":
                        tok = (query.get("t") or [""])[0]
                        if tok and self.client_address[0] in ("127.0.0.1", "::1") and hmac.compare_digest(tok, outer.desk_token):
                            st = secrets.token_urlsafe(32)
                            outer.sessions[st] = time.time() + 30 * 86400
                            return self._send(200, DESK_PAGE, "text/html",
                                              extra=[("Set-Cookie", f"mcsess={st}; Max-Age={30 * 86400}; Path=/; HttpOnly; SameSite=Strict")])
                        if self._authed():
                            return self._send(200, DESK_PAGE, "text/html")
                        return self._send(401, "Open dit scherm via de knop 'Nieuwe interface' in het programma.", "text/plain")
                    if path == "/":
                        return self._send(200, REMOTE_PAGE, "text/html")
                    if path == "/icon.png":
                        return self._send(200, app_icon_png(192), "image/png")
                    if path == "/manifest.json":
                        return self._send(200, {"name": "MC Server Manager", "short_name": "MC Server", "start_url": "/",
                                                "display": "standalone", "background_color": "#0f172a", "theme_color": "#111827",
                                                "icons": [{"src": "/icon.png", "sizes": "192x192", "type": "image/png"}]},
                                          "application/manifest+json")
                if method == "POST" and path == "/api/login":
                    return self._login(body)
                if not path.startswith(("/api/", "/map/", "/head/")):
                    return self._send(404, {"error": "niet gevonden"})
                if not self._authed():
                    return self._send(401, {"error": "login"})
                fn = routes.get((method, path))
                if not fn:
                    fn = outer.dynamic_route(method, path)
                if not fn:
                    return self._send(404, {"error": "niet gevonden"})
                try:
                    res = fn(query, body)
                except TimeoutError as e:
                    return self._send(504, {"error": str(e)})
                except Exception as e:  # noqa
                    return self._send(500, {"error": f"{type(e).__name__}: {e}"[:300]})
                if len(res) == 3:
                    return self._send(res[0], res[2], res[1])
                return self._send(res[0], res[1])

            def _login(self, body):
                ip = self.client_address[0]
                now = time.time()
                f = [t for t in outer.fails.get(ip, []) if now - t < 300]
                if len(f) >= 5:
                    return self._send(429, {"ok": False, "error": "Te veel pogingen. Probeer het over 5 minuten opnieuw."})
                real = str(outer.app.cfg.get("remote_pass", ""))
                if real and hmac.compare_digest(str(body.get("password", "")).encode(), real.encode()):
                    tok = secrets.token_urlsafe(32)
                    outer.sessions[tok] = now + 30 * 86400
                    outer.fails.pop(ip, None)
                    return self._send(200, {"ok": True}, extra=[("Set-Cookie", f"mcsess={tok}; Max-Age={30 * 86400}; Path=/; HttpOnly; SameSite=Strict")])
                f.append(now)
                outer.fails[ip] = f
                time.sleep(1)
                return self._send(200, {"ok": False, "error": "Verkeerd wachtwoord"})

            def do_GET(self):
                self._dispatch("GET")

            def do_POST(self):
                self._dispatch("POST")

        try:
            self.httpd = http.server.ThreadingHTTPServer((host, int(port)), H)
            self.port = self.httpd.server_address[1]
        except OSError as e:
            self.error = f"Poort {port} is niet beschikbaar ({e})."
            self.httpd = None
            return False
        self.error = ""
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return True

    # --- kaart ---
    def extra_routes(self):
        return {("GET", "/api/backuper"): self.api_backuper, ("POST", "/api/backuper/config"): self.api_backuper_config,
                ("POST", "/api/backuper/delete"): self.api_backuper_delete, ("POST", "/api/backuper/now"): self.api_backuper_now,
                ("GET", "/map/info"): self.api_map_info, ("POST", "/map/area"): self.api_map_area, ("POST", "/map/gen"): self.api_map_gen,
                ("POST", "/api/sleep"): self.api_sleep, ("GET", "/api/lists"): self.api_lists, ("POST", "/api/lists/add"): self.api_lists_add,
                ("POST", "/api/lists/remove"): self.api_lists_remove, ("POST", "/api/logsearch"): self.api_logsearch,
                ("GET", "/api/program"): self.api_program, ("POST", "/api/classic"): self.api_classic,
                ("GET", "/api/props"): self.api_props, ("POST", "/api/props"): self.api_props_set}

    # --- nieuwe interface: slaapstand, lijsten, logboek, server.properties ---
    def api_sleep(self, q, body):
        a = self.app
        act = body.get("action")
        if act == "now":
            if not self.call_main(lambda: a.srv_state == "online" and not getattr(a, "_sleeping", False)):
                return 200, {"ok": False, "msg": "De server draait niet (of slaapt al)"}
            self.call_main(a.sleep_now, auto=True)
            return 200, {"ok": True, "msg": "Slaapstand gestart"}
        if act == "auto":
            def go():
                a.sleep_var.set(bool(body.get("on")))
                a._sleep_toggle()
            self.call_main(go)
            return 200, {"ok": True}
        return 400, {"error": "onbekend"}

    def api_lists(self, q, body):
        folder = self.folder()
        if not folder:
            return 200, {"folder": False}
        out = {"folder": True, "whitelist_on": read_properties(folder).get("white-list", "false").lower() == "true"}
        for k in LIST_FILES:
            out[k] = lists_read(folder, k)
        return 200, out

    def api_lists_add(self, q, body):
        key, name, reason = body.get("list"), str(body.get("name", "")).strip(), str(body.get("reason", "")).replace("\n", " ")[:200]
        if key not in LIST_FILES or not re.fullmatch(r"[\w.\-: ]{1,45}", name):
            return 400, {"error": "ongeldige invoer"}
        if self.call_main(lambda: self.app.srv_running()):
            cmd = {"whitelist": f"whitelist add {name}", "bans": f"ban {name} {reason}".strip(), "ips": f"ban-ip {name} {reason}".strip(),
                   "ops": f"op {name}"}[key]
            self.call_main(lambda: self.app.srv_send(cmd))
            return 200, {"ok": True, "msg": cmd}
        ok, msg = lists_file_add(self.folder(), key, name, reason)
        return 200, {"ok": ok, "msg": msg}

    def api_lists_remove(self, q, body):
        key, name = body.get("list"), str(body.get("name", "")).strip()
        if key not in LIST_FILES or not re.fullmatch(r"[\w.\-: ]{1,45}", name):
            return 400, {"error": "ongeldige invoer"}
        if self.call_main(lambda: self.app.srv_running()):
            cmd = {"whitelist": f"whitelist remove {name}", "bans": f"pardon {name}", "ips": f"pardon-ip {name}", "ops": f"deop {name}"}[key]
            self.call_main(lambda: self.app.srv_send(cmd))
            return 200, {"ok": True, "msg": cmd}
        lists_file_remove(self.folder(), key, {name})
        return 200, {"ok": True, "msg": "Verwijderd"}

    def api_logsearch(self, q, body):
        folder = self.folder()
        if not folder:
            return 200, {"rows": [], "files": 0}
        terms = [t for t in str(body.get("q", "")).split() if t][:6]
        kinds = dict(LOG_KINDS)
        kind = kinds.get(body.get("kind") or "Alles")
        d_from, d_to = str(body.get("from", ""))[:10], str(body.get("to", ""))[:10]
        rows = []
        files = search_logs(folder, terms, str(body.get("player", ""))[:40], kind, d_from or None, d_to or None, 500,
                            lambda r: rows.append(r), lambda: False)
        return 200, {"rows": [list(r) for r in rows], "files": files, "limit": len(rows) >= 500, "kinds": [k for k, _ in LOG_KINDS]}

    def api_program(self, q, body):
        a = self.app

        def get():
            u = getattr(a, "_upd", None)
            notes = changelog_since(u["text"], APP_VERSION) if u else ""
            cur = re.search(r'^CHANGELOG\s*=\s*"""(.*?)"""', open(os.path.abspath(__file__), encoding="utf-8").read(), re.M | re.S)
            hist = [l.strip() for l in (cur.group(1).strip().splitlines() if cur else [])][:12]
            return {"version": APP_VERSION, "new": u["version"] if u else None, "hot": bool(getattr(a, "_upd_hot", False)), "notes": notes,
                    "hist": hist, "url": (a.cfg.get("update_url") or "").strip(), "busy": bool(a._upd_busy),
                    "check": bool(a.cfg.get("selfupdate_check", True)), "auto": bool(a.cfg.get("selfupdate_auto")),
                    "frozen": bool(getattr(sys, "frozen", False)), "last": getattr(a, "_upd_last", 0) or 0}
        return 200, self.call_main(get)

    def api_classic(self, q, body):
        def go():
            self.app.deiconify()
            self.app.lift()
        self.call_main(go)
        return 200, {"ok": True, "msg": "Het klassieke scherm staat op de taakbalk"}

    PROPS = {"motd": "str", "max-players": "int", "difficulty": "str", "gamemode": "str", "pvp": "bool", "white-list": "bool",
             "online-mode": "bool", "allow-flight": "bool", "view-distance": "int", "simulation-distance": "int", "spawn-protection": "int"}

    def api_props(self, q, body):
        folder = self.folder()
        pr = read_properties(folder) if folder else {}
        return 200, {"props": {k: pr.get(k, "") for k in self.PROPS}, "kinds": self.PROPS,
                     "running": bool(self.call_main(lambda: self.app.srv_running()))}

    def api_props_set(self, q, body):
        k, v = body.get("key"), body.get("value")
        kind = self.PROPS.get(k)
        if not kind:
            return 400, {"error": "onbekende instelling"}
        if kind == "bool":
            v = "true" if v else "false"
        elif kind == "int":
            try:
                v = str(min(max(int(v), 0), 100000))
            except (TypeError, ValueError):
                return 400, {"error": "ongeldige waarde"}
        else:
            v = str(v).replace("\n", " ").strip()[:200]
            if k in ("difficulty", "gamemode") and not re.fullmatch(r"[a-z]{3,12}", v):
                return 400, {"error": "ongeldige waarde"}
        set_property(self.folder(), k, v)
        return 200, {"ok": True, "msg": "Opgeslagen. Werkt na een herstart van de server."}

    def dynamic_route(self, method, path):
        if method == "GET" and path.startswith("/map/tile/"):
            return lambda q, b: self.map_tile(path[len("/map/tile/"):])
        if method == "GET" and path.startswith("/head/"):
            nm = urllib.parse.unquote(path[len("/head/"):])
            if not re.fullmatch(r"[\w.\- ]{1,40}", nm):
                return lambda q, b: (400, {"error": "ongeldig"})
            return lambda q, b: (200, "image/png", self.app.heads.png_bytes(nm, (q.get("t") or [""])[0]))
        return None

    # --- backups ---
    def api_backuper(self, q, body):
        folder = self.folder()
        st = backuper_state(folder) if folder else {}
        bks = []
        for sd in st.get("storages", []):
            if sd.get("path"):
                for b in list_backups(sd["path"]):
                    bks.append({"storage": sd["id"], "name": b["name"], "size": b["size"], "mtime": b["mtime"], "dir": b["dir"]})
        bks.sort(key=lambda b: -b["mtime"])
        own = []
        for label, d in self.call_main(lambda: own_backup_dirs(self.app)):
            n = sz = 0
            if os.path.isdir(d):
                for fn in os.listdir(d):
                    n += 1
                    pth = os.path.join(d, fn)
                    sz += dir_size_n(pth)[0] if os.path.isdir(pth) else (os.path.getsize(pth) if os.path.exists(pth) else 0)
            own.append({"label": label, "count": n, "size": sz})
        cfg = self.call_main(lambda: {k: self.app.cfg.get(k, DEFAULTS.get(k)) for k in
                                      ("keep_server_backups", "server_backups_max", "keep_plugin_backups", "plugin_backups_max")})
        return 200, {"jar": st.get("jar"), "disabled": bool(st.get("disabled")), "has_config": bool(st.get("has_config")),
                     "global": st.get("global", {}), "storages": [{k: v for k, v in sd.items() if k != "path"} for sd in st.get("storages", [])],
                     "backups": bks, "own": own, "own_cfg": cfg,
                     "cmd": self.call_main(lambda: self.app.cfg.get("backuper_cmd", "backuper backup local"))}

    def api_backuper_config(self, q, body):
        ch = {}
        for it in body.get("changes") or []:
            path, val = it.get("path"), it.get("value")
            if not isinstance(path, list) or not (2 <= len(path) <= 3) or not all(isinstance(x, str) for x in path):
                return 400, {"error": "ongeldig"}
            known = {("backup", k): kd for k, kd, _l in BK_GLOBAL}
            if len(path) == 3 and path[0] == "storages":
                known.update({tuple(path[:2]) + (k,): kd for k, kd, _l in BK_STORAGE})
            kd = known.get(tuple(path))
            if not kd:
                return 400, {"error": "onbekende instelling"}
            try:
                val = bool(val) if kd == "bool" else (int(val) if kd == "int" else str(val).strip()[:300])
            except (TypeError, ValueError):
                return 400, {"error": "ongeldige waarde"}
            ch[tuple(path)] = val
        n = backuper_save(self.folder(), ch) if ch else 0
        running = self.call_main(lambda: self.app.srv_running())
        if body.get("restart") and running and n:
            self.call_main(lambda: self.app.srv_stop(restart=True), auto=True)
        return 200, {"ok": True, "n": n, "msg": (f"{n} instelling(en) opgeslagen" if n else "Niets veranderd")
                     + (". Herstart de server om ze te gebruiken." if n and running and not body.get("restart") else "")}

    def api_backuper_delete(self, q, body):
        st = backuper_state(self.folder())
        paths = {sd["id"]: sd.get("path") for sd in st.get("storages", [])}
        gone = 0
        for it in body.get("items") or []:
            try:
                delete_backup(paths[it["storage"]], it["name"])
                gone += 1
            except (OSError, ValueError, KeyError, TypeError):
                pass
        self.call_main(lambda: self.app.log(f"{gone} backup(s) verwijderd (telefoon).", "ok"))
        return 200, {"ok": True, "msg": f"{gone} backup(s) verwijderd"}

    def api_backuper_now(self, q, body):
        c = str(body.get("cmd") or "").strip().lstrip("/")
        if not re.fullmatch(r"backuper( [\w.\-]{1,30}){0,4}", c):
            return 400, {"error": "Dit is geen Backuper-commando"}
        ok = self.call_main(lambda: self.app.srv_send(c))
        return 200, {"ok": bool(ok), "msg": f"/{c} verstuurd, kijk in de console" if ok else "De server draait niet"}

    def map_tile(self, rest):
        m = re.fullmatch(r"([\w.\-]{1,60})/(\d{1,2})/(-?\d{1,6})_(-?\d{1,6})\.png", rest)
        if not m:
            return 400, {"error": "ongeldig"}
        data = self.app.tab_map._get(f"tiles/{m.group(1)}/{m.group(2)}/{m.group(3)}_{m.group(4)}.png")
        if not data:
            return 404, "text/plain", b""
        return 200, "image/png", data

    def api_map_info(self, q, body):
        mt = self.app.tab_map
        self.call_main(mt._upd_webdir)
        raw = mt._get("tiles/settings.json")
        if not raw:
            return 200, {"worlds": [], "msg": "Geen kaart gevonden. Start de server met squaremap en laat hem eerst renderen."}
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            return 200, {"worlds": [], "msg": "Kaartinstellingen onleesbaar"}
        worlds = []
        for w in sorted(data.get("worlds") or [], key=lambda w: w.get("order", 0)):
            try:
                st = json.loads((mt._get(f"tiles/{w['name']}/settings.json") or b"{}").decode("utf-8"))
            except ValueError:
                st = {}
            z = st.get("zoom") or {}
            worlds.append({"name": w["name"], "display": w.get("display_name") or w["name"], "type": w.get("type", ""),
                           "max": int(z.get("max", 3)), "extra": int(z.get("extra", 1)), "def": int(z.get("def", 2)),
                           "spawn": st.get("spawn") or {"x": 0, "z": 0}})
        pl = []
        try:
            pr = mt._get("tiles/players.json")
            pl = [p for p in (json.loads(pr.decode("utf-8")).get("players") or []) if "x" in p and "z" in p] if pr else []
        except ValueError:
            pass
        g = mt.gen
        return 200, {"worlds": worlds, "players": [{"name": p.get("name", "?"), "x": p["x"], "z": p["z"], "world": p.get("world"),
                                                    "yaw": p.get("yaw")} for p in pl],
                     "disk": bool(getattr(mt, "_from_disk", False)), "chunky": bool(self.call_main(mt._chunky_installed)),
                     "gen": {k: (list(v) if isinstance(v, tuple) else v) for k, v in g.items() if k in
                             ("state", "pct", "done", "chunks", "area", "world", "reason", "auto", "cur")},
                     "gen_info": self.snap.get("gen_info", ""),
                     "autopause": bool(mt.autopause_var.get()), "autoresume": bool(mt.autoresume_var.get())}

    def api_map_area(self, q, body):
        mt = self.app.tab_map
        try:
            ar = [int(v) for v in body.get("area")]
            world = str(body.get("world", ""))
            if len(ar) != 4 or not re.fullmatch(r"[\w.\-]{1,60}", world):
                raise ValueError
        except (TypeError, ValueError):
            return 400, {"error": "ongeldig gebied"}
        if mt.gen.get("state") in ("running", "paused", "waiting", "rendering"):
            return 400, {"error": "Er loopt al een taak. Stop die eerst."}

        def go():
            r = mt._snap((ar[0], ar[1]), (ar[2], ar[3]))
            if (r[2] - r[0]) < 32 or (r[3] - r[1]) < 32:
                return "Gebied is te klein (minimaal 2 × 2 chunks)"
            if (r[2] - r[0]) > 20000 or (r[3] - r[1]) > 20000:
                return "Gebied is te groot (maximaal 20.000 blokken)"
            mt.cur = world
            mt.sel = r
            mt.gen = {"state": "ready", "world": world, "area": r, "chunks": ((r[2] - r[0]) // 16) * ((r[3] - r[1]) // 16)}
            mt._gen_refresh_ui()
            mt._draw_overlay_only()
            if body.get("start"):
                mt.gen_begin()
            return ""
        err = self.call_main(go, auto=True)
        if err:
            return 400, {"error": err}
        return 200, {"ok": True}

    def api_map_gen(self, q, body):
        mt = self.app.tab_map
        act = body.get("action")

        def go():
            if act == "start" and mt.gen.get("state") == "ready":
                mt.gen_begin()
            elif act == "pause" and mt.gen.get("state") in ("running", "paused"):
                mt.gen_toggle_pause()
            elif act == "cancel" and mt.gen.get("state") in ("running", "paused", "waiting"):
                mt.gen_cancel()
            elif act == "clear":
                mt.gen = {"state": "idle"}
                mt.sel = None
                mt.gen_hide()
                mt._draw_overlay_only()
        self.call_main(go, auto=True)
        return 200, {"ok": True}

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        self.httpd = None
        self.sessions.clear()

    @property
    def running(self):
        return self.httpd is not None


def measure_world(folder):
    """Grootte van werelden, kaart, logs en plugins. Geeft (lijst van (naam, bytes, bestanden), schijfgebruik of None)."""
    out = []
    try:
        for root in world_roots(folder):
            s, n = dir_size_n(root)
            out.append((os.path.basename(root), s, n))
        sqd = os.path.join(folder, "plugins", "squaremap")
        for label, sub in (("Squaremap-kaart", os.path.join("plugins", "squaremap")), ("Logs", "logs"),
                           ("Crash-reports", "crash-reports"), ("Plugins", "plugins")):
            p = os.path.join(folder, sub)
            if os.path.isdir(p):
                s, n = dir_size_n(p)
                if label == "Plugins" and os.path.isdir(sqd):
                    s -= dir_size_n(sqd)[0]
                out.append((label, s, n))
        try:
            du = shutil.disk_usage(folder)
        except OSError:
            du = None
    except Exception:
        out, du = [], None
    return out, du


# --------------------------------------------------------------------------
# Tabblad Beheer: spelersstatistieken, meldingen, server-tuning, wereldgrootte
# --------------------------------------------------------------------------
STATS_PATH = os.path.join(app_dir(), "mc_server_manager_spelers.json")


def toast(title, text):
    """Windows-melding (rechtsonder). Op andere systemen of bij een fout gebeurt er niets."""
    if os.name != "nt":
        return

    def work():
        try:
            from xml.sax.saxutils import escape
            xml = ('<toast><visual><binding template="ToastGeneric"><text>%s</text><text>%s</text></binding></visual></toast>'
                   % (escape(title), escape(text)))
            ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null\n"
                  "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null\n"
                  "$x = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
                  "$x.LoadXml(@'\n" + xml + "\n'@)\n"
                  "$t = [Windows.UI.Notifications.ToastNotification]::new($x)\n"
                  "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                  "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($t)\n")
            enc = base64.b64encode(ps.encode("utf-16-le")).decode("ascii")
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc], timeout=20,
                           capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            pass

    threading.Thread(target=work, daemon=True).start()


def fmt_dur_short(sec):
    sec = int(sec or 0)
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    return (f"{d}d " if d else "") + (f"{h}u " if (h or d) else "") + f"{m}m"


def fmt_bytes(n):
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u in ("B", "KB") else f"{n:.1f} {u}"
        n /= 1024


def dir_size_n(path):
    tot = n = 0
    for root, _d, files in os.walk(path):
        for f in files:
            try:
                tot += os.path.getsize(os.path.join(root, f))
                n += 1
            except OSError:
                pass
    return tot, n


def level_name(folder):
    return read_properties(folder).get("level-name", "world") or "world"


def world_roots(folder):
    """Mappen die een wereld bevatten (overworld, nether, end), op basis van level-name."""
    lvl = level_name(folder)
    out = []
    for suffix in ("", "_nether", "_the_end"):
        p = os.path.join(folder, lvl + suffix)
        if os.path.isdir(p):
            out.append(p)
    return out


def dim_of(path):
    low = path.replace("\\", "/").lower()
    if "nether" in low or "/dim-1" in low:
        return "nether"
    if "the_end" in low or "/dim1" in low:
        return "end"
    return "overworld"


def find_data_dirs(folder, kinds=("region", "entities", "poi")):
    """Alle region/entities/poi-mappen in de wereldmappen: lijst van (pad, soort, dimensie)."""
    out = []
    for root in world_roots(folder):
        for r, dirs, _f in os.walk(root):
            for d in dirs:
                if d in kinds:
                    p = os.path.join(r, d)
                    out.append((p, d, dim_of(p)))
    return out


def find_stats_dirs(folder):
    out = []
    for root in world_roots(folder):
        for sub in ("stats", os.path.join("players", "stats")):
            p = os.path.join(root, sub)
            if os.path.isdir(p):
                out.append(p)
    return out


def set_property(folder, key, value):
    path = os.path.join(folder, "server.properties")
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines(True)
    bak = path + ".mcupdater.bak"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    done = False
    for i, ln in enumerate(lines):
        if ln.split("=", 1)[0].strip() == key and not ln.lstrip().startswith("#"):
            lines[i] = f"{key}={value}\n"
            done = True
    if not done:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"{key}={value}\n")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)


class BeheerTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.q = queue.Queue()
        self.visible = False
        self.stats = self._load_stats()
        self.sort = ("time", True)
        self._build()

    # ---------- opslag eigen log (sessies) ----------
    def _load_stats(self):
        try:
            with open(STATS_PATH, encoding="utf-8") as fh:
                d = json.load(fh)
                return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_stats(self):
        try:
            tmp = STATS_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.stats, fh)
            os.replace(tmp, STATS_PATH)
        except OSError:
            pass

    def event(self, kind, name):
        """Aangeroepen vanuit de console: speler komt binnen of vertrekt."""
        now = time.time()
        s = self.stats.setdefault(name, {"first": now, "last": now, "sessions": 0, "seconds": 0.0, "since": None})
        if kind == "join":
            s["sessions"] += 1
            s["since"] = now
        elif s.get("since"):
            s["seconds"] += max(0, now - s["since"])
            s["since"] = None
        s["last"] = now
        self._save_stats()
        if self.visible and self.sub.select() == str(self.pg_pl):
            self.after(400, self.refresh_players)

    def close_all(self):
        now = time.time()
        for s in self.stats.values():
            if s.get("since"):
                s["seconds"] += max(0, now - s["since"])
                s["since"] = None
                s["last"] = now
        self._save_stats()

    # ---------- opbouw ----------
    def _build(self):
        self.sub = ttk.Notebook(self)
        self.sub.pack(fill="both", expand=True)
        self.pg_pl = ttk.Frame(self.sub, padding=8)
        self.pg_nf = ttk.Frame(self.sub, padding=12)
        self.pg_tu = ttk.Frame(self.sub, padding=8)
        self.pg_wd = ttk.Frame(self.sub, padding=8)
        self.pg_rm = ttk.Frame(self.sub, padding=12)
        for pg, t in ((self.pg_pl, "📊  Spelers"), (self.pg_nf, "🔔  Meldingen"), (self.pg_tu, "⚙  Tuning"), (self.pg_wd, "💾  Wereld"),
                      (self.pg_rm, "📱  Telefoon")):
            self.sub.add(pg, text=t)
        self._build_players()
        self._build_notify()
        self._build_tuning()
        self._build_world()
        self._build_remote()
        self.sub.bind("<<NotebookTabChanged>>", lambda e: self.on_show())

    def _btn(self, parent, text, cmd, bg="#e5e7eb", fg="#111827"):
        return make_btn(parent, text, cmd, bg, fg, 8, 2)

    def on_show(self):
        self.visible = True
        cur = self.sub.select()
        if cur == str(self.pg_pl):
            self.refresh_players()
        elif cur == str(self.pg_tu):
            self.refresh_tuning()
        elif cur == str(self.pg_wd):
            self.refresh_world()
        elif cur == str(self.pg_rm):
            self.refresh_remote()

    def on_hide(self):
        self.visible = False

    # ---------- spelers ----------
    def _build_players(self):
        f = self.pg_pl
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Speeltijd en activiteit per speler (uit de wereldmap van je server en het logboek van dit programma).",
                  foreground="#6b7280").pack(side="left")
        self._btn(top, "↻  Vernieuwen", self.refresh_players).pack(side="right")
        cols = ("name", "online", "time", "sessions", "last", "deaths", "kills", "dist")
        self.pl_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="browse")
        self.app.heads.watch_tree(self.pl_tree, lambda iid: iid)
        heads = {"name": ("Speler", 170), "online": ("Nu", 60), "time": ("Speeltijd", 110), "sessions": ("Keer online", 90),
                 "last": ("Laatst gezien", 150), "deaths": ("Doden", 70), "kills": ("Mobs gedood", 100), "dist": ("Afgelegd", 100)}
        for c in cols:
            self.pl_tree.heading(c, text=heads[c][0], command=lambda c=c: self._sort_players(c))
            self.pl_tree.column(c, width=heads[c][1], anchor="w" if c in ("name", "last") else "e")
        self.pl_tree.pack(fill="both", expand=True)
        self.pl_tree.tag_configure("on", background="#dcfce7")
        self.pl_info = ttk.Label(f, text="", foreground="#6b7280")
        self.pl_info.pack(anchor="w", pady=(6, 0))

    def _sort_players(self, c):
        self.sort = (c, not self.sort[1] if self.sort[0] == c else c != "name")
        self.refresh_players()

    def _collect_players(self):
        folder = self.app.folder_var.get().strip()
        names = {}
        try:
            with open(os.path.join(folder, "usercache.json"), encoding="utf-8") as fh:
                for x in json.load(fh):
                    if isinstance(x, dict) and x.get("uuid") and x.get("name"):
                        names[x["uuid"].lower()] = x["name"]
        except (OSError, ValueError):
            pass
        rows = {}
        for d in find_stats_dirs(folder):
            try:
                files = os.listdir(d)
            except OSError:
                continue
            for fn in files:
                if not fn.endswith(".json"):
                    continue
                uid = fn[:-5].lower()
                nm = names.get(uid) or uid[:8]
                try:
                    p = os.path.join(d, fn)
                    with open(p, encoding="utf-8") as fh:
                        st = json.load(fh).get("stats", {})
                    cu = st.get("minecraft:custom", {})
                    ticks = cu.get("minecraft:play_time", cu.get("minecraft:play_one_minute", 0))
                    kills = sum((st.get("minecraft:killed") or {}).values())
                    dist = sum(cu.get(k, 0) for k in ("minecraft:walk_one_cm", "minecraft:sprint_one_cm", "minecraft:swim_one_cm",
                                                       "minecraft:aviate_one_cm", "minecraft:boat_one_cm", "minecraft:horse_one_cm",
                                                       "minecraft:minecart_one_cm", "minecraft:crouch_one_cm"))
                    r = rows.setdefault(nm, dict(name=nm, time=0, sessions=0, last=0, deaths=0, kills=0, dist=0, online=False))
                    r["time"] += ticks / 20.0
                    r["deaths"] += cu.get("minecraft:deaths", 0)
                    r["kills"] += kills
                    r["dist"] += dist / 100.0
                    r["last"] = max(r["last"], os.path.getmtime(p))
                except (OSError, ValueError, AttributeError):
                    continue
        for nm, s in self.stats.items():
            r = rows.setdefault(nm, dict(name=nm, time=s.get("seconds", 0), sessions=0, last=0, deaths=0, kills=0, dist=0, online=False))
            r["sessions"] = s.get("sessions", 0)
            r["last"] = max(r["last"], s.get("last", 0))
            if not any(True for d in find_stats_dirs(folder)) or r["time"] == 0:
                r["time"] = max(r["time"], s.get("seconds", 0))
        online = set(self.app.players) if isinstance(self.app.players, dict) else set()
        for nm in online:
            if nm in rows:
                rows[nm]["online"] = True
        return list(rows.values())

    def refresh_players(self):
        rows = self._collect_players()
        key, desc = self.sort
        rows.sort(key=lambda r: (str(r["name"]).lower() if key == "name" else (1 if r.get(key) else 0, r.get(key, 0))), reverse=desc)
        self.pl_tree.delete(*self.pl_tree.get_children())
        for r in rows:
            last = "nu online" if r["online"] else (datetime.fromtimestamp(r["last"]).strftime("%d-%m-%Y %H:%M") if r["last"] else "-")
            self.pl_tree.insert("", "end", iid=str(r["name"]), tags=("on",) if r["online"] else (), values=(
                r["name"], "●" if r["online"] else "", fmt_dur_short(r["time"]) if r["time"] else "-", r["sessions"] or "-", last,
                int(r["deaths"]) or "-", int(r["kills"]) or "-", f"{r['dist'] / 1000:.1f} km" if r["dist"] else "-"))
        tot = sum(r["time"] for r in rows)
        self.pl_info.config(text=f"{len(rows)} spelers  •  samen {fmt_dur_short(tot)} gespeeld" if rows else
                            "Nog geen spelers gevonden. Kies je servermap (Instellingen) of wacht tot er iemand is binnengekomen.")

    # ---------- meldingen ----------
    NOTIFY = (("notify_crash", "Als de server onverwacht stopt (crash)"), ("notify_start", "Als de server klaar is met opstarten"),
              ("notify_join", "Als een speler binnenkomt"), ("notify_leave", "Als een speler weggaat"),
              ("notify_chunky", "Als het genereren van een gebied klaar is"), ("notify_update", "Als er een update van het programma is"))

    def _build_notify(self):
        f = self.pg_nf
        ttk.Label(f, text="Laat een melding van Windows zien (rechtsonder) bij:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.nv = {}
        for key, text in self.NOTIFY:
            v = tk.BooleanVar(value=bool(self.app.cfg.get(key, DEFAULTS.get(key, False))))
            self.nv[key] = v
            ttk.Checkbutton(f, text=text, variable=v, command=lambda k=key: self._nsave(k)).pack(anchor="w", pady=2)
        ttk.Label(f, text="Namen waarvoor je geen meldingen wilt (bijv. bots), gescheiden door komma's:",
                  foreground="#6b7280").pack(anchor="w", pady=(12, 2))
        self.ign_var = tk.StringVar(value=self.app.cfg.get("notify_ignore", ""))
        e = ttk.Entry(f, textvariable=self.ign_var, width=60)
        e.pack(anchor="w")
        e.bind("<FocusOut>", lambda ev: self._nsave("notify_ignore"))
        e.bind("<Return>", lambda ev: self._nsave("notify_ignore"))
        self._btn(f, "Test: toon een melding", lambda: toast(APP_NAME, "Zo ziet een melding eruit.")).pack(anchor="w", pady=(14, 0))
        self.nf_note = ttk.Label(f, text="", foreground="#6b7280")
        self.nf_note.pack(anchor="w", pady=(6, 0))
        if os.name != "nt":
            self.nf_note.config(text="Meldingen werken alleen op Windows.")

    def _nsave(self, key):
        self.app.cfg[key] = self.ign_var.get().strip() if key == "notify_ignore" else bool(self.nv[key].get())
        save_config(self.app.cfg)

    def notify(self, key, title, text, name=None):
        if not self.app.cfg.get(key, DEFAULTS.get(key, False)):
            return
        ign = {x.strip().lower() for x in str(self.app.cfg.get("notify_ignore", "")).split(",") if x.strip()}
        if name and name.lower() in ign:
            return
        toast(title, text)

    # ---------- tuning ----------
    def _build_tuning(self):
        f = self.pg_tu
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Controle van je serverinstellingen, Java-geheugen en de huidige belasting.",
                  foreground="#6b7280").pack(side="left")
        self._btn(top, "↻  Opnieuw controleren", self.refresh_tuning).pack(side="right")
        self.tu_tree = ttk.Treeview(f, columns=("what", "now", "adv"), show="headings", selectmode="extended")
        for c, t, w in (("what", "Onderdeel", 190), ("now", "Nu", 160), ("adv", "Beoordeling", 560)):
            self.tu_tree.heading(c, text=t)
            self.tu_tree.column(c, width=w, anchor="w")
        self.tu_tree.pack(fill="both", expand=True)
        self.tu_tree.tag_configure("warn", background="#fff3e0", foreground="#e65100")
        self.tu_tree.tag_configure("ok", foreground="#166534")
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(6, 0))
        self.tu_apply = self._btn(bar, "Pas geselecteerde regels toe", self.apply_tuning, "#059669", "white")
        self.tu_apply.pack(side="left")
        ttk.Label(bar, text="  (wijzigt server.properties; een kopie blijft bewaard; herstart de server daarna)",
                  foreground="#6b7280").pack(side="left")
        self.tu_fix = {}

    def refresh_tuning(self):
        a = self.app
        folder = a.folder_var.get().strip()
        pr = read_properties(folder)
        t = self.tu_tree
        t.delete(*t.get_children())
        self.tu_fix = {}

        def add(what, now, adv, warn=False, fix=None):
            iid = t.insert("", "end", values=(what, now, ("⚠ " if warn else "✔ ") + adv), tags=("warn" if warn else "ok",))
            if fix:
                self.tu_fix[iid] = fix

        if not pr:
            add("server.properties", "niet gevonden", "Kies je servermap in Instellingen.", True)
        else:
            def num(k, d):
                try:
                    return int(pr.get(k, d))
                except ValueError:
                    return d
            vd, sd = num("view-distance", 10), num("simulation-distance", 10)
            add("view-distance", f"{vd} chunks", "Hoog: kost veel geheugen en netwerk. 8–10 is genoeg voor de meeste servers." if vd > 10
                else "Prima.", vd > 10, ("view-distance", "10") if vd > 10 else None)
            add("simulation-distance", f"{sd} chunks", "Hoog: mobs en machines rekenen in een groot gebied. 6 is een goede balans." if sd > 8
                else "Prima.", sd > 8, ("simulation-distance", "6") if sd > 8 else None)
            mp = num("max-players", 20)
            add("max-players", str(mp), "Zeer hoog ten opzichte van wat je server aankan." if mp > 100 else "Prima.", mp > 100)
            om = pr.get("online-mode", "true").lower()
            add("online-mode", om, "Staat uit: iedereen kan met een willekeurige naam binnen. Alleen veilig achter een proxy met "
                                   "eigen controle." if om == "false" else "Aan (aanbevolen).", om == "false")
            ct = num("network-compression-threshold", 256)
            add("network-compression-threshold", str(ct), "Uitgeschakeld (-1): meer netwerkverkeer, tenzij je dat bewust doet."
                if ct == -1 else "Prima.", ct == -1)
        # Java-geheugen
        xmx = a.cfg.get("java_xmx") or ""
        extra = a.cfg.get("java_extra") or ""
        mb = parse_mem_mb(xmx) if xmx else None
        sp = (a.cfg.get("start_script") or "").strip()
        if sp and os.path.isfile(sp):
            try:
                txt = open(sp, encoding="utf-8", errors="replace").read(20000)
                m = re.search(r"-Xmx(\d+\s*[GgMm])", txt)
                mb = parse_mem_mb(m.group(1)) if m else mb
                extra = txt
            except OSError:
                pass
        total = None
        if psutil is not None:
            try:
                total = psutil.virtual_memory().total // (1024 * 1024)
            except Exception:
                pass
        if mb:
            if total:
                pct = mb * 100 // total
                add("Geheugen voor Java (-Xmx)", f"{mb / 1024:.1f} GB van {total / 1024:.0f} GB",
                    f"Meer dan 75% van je werkgeheugen ({pct}%): Windows en andere programma's kunnen dan vastlopen." if pct > 75
                    else ("Erg weinig voor een server met plugins." if mb < 2048 else "Prima."), pct > 75 or mb < 2048)
            else:
                add("Geheugen voor Java (-Xmx)", f"{mb / 1024:.1f} GB", "Installeer 'psutil' voor een vergelijking met je werkgeheugen.")
        else:
            add("Geheugen voor Java (-Xmx)", "onbekend", "Niet gevonden in de instellingen of het startbestand.")
        has_g1 = "UseG1GC" in extra or "UseZGC" in extra or "UseShenandoah" in extra
        add("Garbage collector", "G1/ZGC aanwezig" if has_g1 else "standaard", "Java kiest zelf; dat is prima voor kleine servers."
            if not has_g1 else "Eigen opstartopties gevonden.")
        # Live
        try:
            tps = next((v for _t, v in reversed(a.spark_tps.data) if v is not None), None)
            ram = next((v for _t, v in reversed(a.spark_ram.data) if v is not None), None)
        except Exception:
            tps = ram = None
        if a.srv_running():
            if tps is not None:
                add("TPS (nu)", f"{tps:.1f}", "Server loopt achter: minder view-distance/simulation-distance of minder plugins."
                    if tps < 18 else "Soepel (20 is perfect).", tps < 18)
            if ram is not None and mb:
                p = ram / mb * 100
                add("Geheugengebruik (nu)", f"{ram / 1024:.1f} GB ({p:.0f}%)", "Bijna vol: geef Java meer geheugen of verlaag de afstanden."
                    if p > 90 else "Prima.", p > 90)
        else:
            add("Belasting", "server uit", "Start de server om TPS en geheugen te zien.")

    def apply_tuning(self):
        a = self.app
        sel = [i for i in self.tu_tree.selection() if i in self.tu_fix] or list(self.tu_fix)
        if not sel:
            messagebox.showinfo(APP_NAME, "Er zijn geen aanpassingen om toe te passen.")
            return
        txt = "\n".join(f"{self.tu_fix[i][0]} → {self.tu_fix[i][1]}" for i in sel)
        if not messagebox.askyesno(APP_NAME, f"Deze instellingen aanpassen in server.properties?\n\n{txt}\n\n"
                                             "De server moet daarna opnieuw starten. Een kopie van het bestand blijft bewaard."):
            return
        try:
            for i in sel:
                set_property(a.folder_var.get().strip(), *self.tu_fix[i])
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Aanpassen mislukt: {e}")
            return
        a.log("server.properties aangepast: " + ", ".join(f"{k}={v}" for k, v in (self.tu_fix[i] for i in sel)) +
              ". Herstart de server om het te laten werken.", "ok")
        self.refresh_tuning()

    # ---------- telefoon ----------
    def _build_remote(self):
        f, c = self.pg_rm, self.app.cfg
        ttk.Label(f, text="Bedien je server vanaf je telefoon (status, console, spelers, starten en stoppen).",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.rm_on = tk.BooleanVar(value=bool(c.get("remote_enabled")))
        ttk.Checkbutton(f, text="Toegang vanaf telefoon aanzetten", variable=self.rm_on, command=self._rm_save).pack(anchor="w", pady=(10, 2))
        self.rm_lan = tk.BooleanVar(value=bool(c.get("remote_lan_only", True)))
        ttk.Checkbutton(f, text="Alleen vanaf je eigen netwerk of VPN (aanbevolen)", variable=self.rm_lan,
                        command=self._rm_save).pack(anchor="w", pady=2)
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(8, 2))
        ttk.Label(row, text="Poort:").pack(side="left")
        self.rm_port = tk.IntVar(value=int(c.get("remote_port", 8765)))
        sp = ttk.Spinbox(row, from_=1024, to=65535, width=7, textvariable=self.rm_port, command=self._rm_save)
        sp.pack(side="left", padx=(4, 16))
        sp.bind("<FocusOut>", lambda e: self._rm_save())
        ttk.Label(row, text="Wachtwoord:").pack(side="left")
        self.rm_pw = tk.StringVar(value=c.get("remote_pass", ""))
        self.rm_pw_e = ttk.Entry(row, textvariable=self.rm_pw, width=22, show="•")
        self.rm_pw_e.pack(side="left", padx=4)
        self.rm_pw_e.bind("<FocusOut>", lambda e: self._rm_save())
        self._btn(row, "👁", lambda: self.rm_pw_e.config(show="" if self.rm_pw_e.cget("show") else "•")).pack(side="left", padx=2)
        self._btn(row, "Nieuw wachtwoord", self._rm_newpw).pack(side="left", padx=4)
        self.rm_status = tk.Label(f, text="", font=("Segoe UI", 10, "bold"), anchor="w", justify="left")
        self.rm_status.pack(anchor="w", pady=(12, 2))
        self.rm_urls = tk.Label(f, text="", font=("Consolas", 12, "bold"), fg="#2563eb", anchor="w", justify="left", cursor="hand2")
        self.rm_urls.pack(anchor="w")
        ttk.Label(f, justify="left", foreground="#6b7280", wraplength=900, text=(
            "Zo gebruik je het:\n"
            "1. Zet je telefoon op hetzelfde wifi als deze pc, open het adres hierboven in Chrome en log in.\n"
            "2. Chrome-menu (⋮) → ‘Toevoegen aan startscherm’: dan heb je een app-icoon.\n"
            "3. Windows vraagt bij de eerste keer om toestemming in de firewall: kies ‘Privénetwerken’.\n\n"
            "Buiten je wifi? Gebruik een VPN zoals Tailscale (gratis): installeer het op pc en telefoon en open het Tailscale-adres "
            "van deze pc. Zet de poort NIET open in je router: de verbinding is niet versleuteld en wie het wachtwoord raadt, "
            "kan je server bedienen.")).pack(anchor="w", pady=(14, 0))
        self.rm_urls.bind("<Button-1>", lambda e: self._rm_copy())

    def _rm_newpw(self):
        self.rm_pw.set(secrets.token_urlsafe(9).replace("-", "x").replace("_", "y"))
        self.rm_pw_e.config(show="")
        self._rm_save()

    def _rm_copy(self):
        u = self.rm_urls.cget("text").split("\n")[0]
        if u.startswith("http"):
            self.clipboard_clear()
            self.clipboard_append(u)
            self.rm_status.config(text="Adres gekopieerd.", fg="#6b7280")

    def _rm_save(self):
        a, c = self.app, self.app.cfg
        c["remote_enabled"] = bool(self.rm_on.get())
        c["remote_lan_only"] = bool(self.rm_lan.get())
        try:
            c["remote_port"] = min(max(int(self.rm_port.get()), 1024), 65535)
        except (tk.TclError, ValueError):
            c["remote_port"] = 8765
        c["remote_pass"] = self.rm_pw.get().strip()
        if c["remote_enabled"] and not c["remote_pass"]:
            self._rm_newpw()
            return
        a._save_cfg()
        a.remote_apply()

    def refresh_remote(self):
        a, c = self.app, self.app.cfg
        if a.remote.running:
            ips = lan_ips() or ["jouw-pc-adres"]
            self.rm_status.config(text="● Aan: open dit adres op je telefoon (klik om te kopiëren)", fg="#059669")
            self.rm_urls.config(text="\n".join(f"http://{ip}:{c.get('remote_port', 8765)}" for ip in ips))
        else:
            err = a.remote.error
            self.rm_status.config(text=("✖ " + err) if err else "○ Uit", fg="#b91c1c" if err else "#6b7280")
            self.rm_urls.config(text="")

    # ---------- wereld ----------
    def _build_world(self):
        f = self.pg_wd
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        self.wd_status = ttk.Label(top, text="", foreground="#6b7280")
        self.wd_status.pack(side="left")
        self._btn(top, "↻  Opnieuw meten", self.refresh_world).pack(side="right")
        self.wd_tree = ttk.Treeview(f, columns=("what", "size", "files", "share"), show="headings", height=9, selectmode="browse")
        for c, t, w, an in (("what", "Onderdeel", 300, "w"), ("size", "Grootte", 110, "e"), ("files", "Bestanden", 100, "e"),
                            ("share", "Aandeel", 300, "w")):
            self.wd_tree.heading(c, text=t)
            self.wd_tree.column(c, width=w, anchor=an)
        self.wd_tree.pack(fill="x")
        self.wd_disk = ttk.Label(f, text="", foreground="#374151", font=("Segoe UI", 10, "bold"))
        self.wd_disk.pack(anchor="w", pady=(8, 8))
        box = ttk.LabelFrame(f, text="Opruimen", padding=8)
        box.pack(fill="x")
        r1 = ttk.Frame(box)
        r1.pack(fill="x", pady=2)
        self._btn(r1, "🧹  Oude logs en crash-reports opruimen", self.clean_logs).pack(side="left")
        ttk.Label(r1, text="  logs ouder dan 7 dagen en crash-reports ouder dan 14 dagen", foreground="#6b7280").pack(side="left")
        r2 = ttk.Frame(box)
        r2.pack(fill="x", pady=(8, 2))
        self.trim_world = tk.StringVar()
        ttk.Label(r2, text="Regio's buiten een gebied wegzetten voor:").pack(side="left")
        self.trim_cb = ttk.Combobox(r2, textvariable=self.trim_world, state="readonly", width=20,
                                    values=["overworld", "nether", "end"])
        self.trim_cb.pack(side="left", padx=6)
        self.trim_cb.set("overworld")
        self._btn(r2, "✂  Buiten gekozen gebied wegzetten…", self.trim_regions, "#b45309", "white").pack(side="left")
        ttk.Label(box, text="Kies eerst op het tabblad Kaart een gebied dat je wilt BEHOUDEN (Gebied genereren → slepen). Alles daarbuiten "
                            "gaat naar een map _opgeruimd in je servermap (niet verwijderd). De server moet uit staan.",
                  foreground="#6b7280", wraplength=900, justify="left").pack(anchor="w", pady=(4, 0))

    def refresh_world(self):
        if getattr(self, "_measuring", False):
            return
        self._measuring = True
        self.wd_status.config(text="Meten…")
        folder = self.app.folder_var.get().strip()

        def work():
            self.q.put(measure_world(folder))

        threading.Thread(target=work, daemon=True).start()
        self.after(200, self._poll)

    def _poll(self):
        try:
            out, du = self.q.get_nowait()
        except queue.Empty:
            self.after(200, self._poll)
            return
        self._measuring = False
        t = self.wd_tree
        t.delete(*t.get_children())
        tot = sum(s for _l, s, _n in out) or 1
        for label, s, n in out:
            bar = "█" * max(1, round(s / tot * 30)) if s else ""
            t.insert("", "end", values=(label, fmt_bytes(s), n, f"{bar}  {s / tot * 100:.0f}%"))
        self.wd_status.config(text=f"Totaal {fmt_bytes(sum(s for _l, s, _n in out))}" if out else
                              "Geen servermap gevonden. Kies je servermap in Instellingen.")
        if du:
            self.wd_disk.config(text=f"Schijf: {fmt_bytes(du.free)} vrij van {fmt_bytes(du.total)}")

    def clean_logs(self):
        folder = self.app.folder_var.get().strip()
        now = time.time()
        targets = []
        for sub, days, keep in (("logs", 7, ("latest.log",)), ("crash-reports", 14, ())):
            d = os.path.join(folder, sub)
            if os.path.isdir(d):
                for fn in os.listdir(d):
                    p = os.path.join(d, fn)
                    if fn in keep or not os.path.isfile(p):
                        continue
                    try:
                        if now - os.path.getmtime(p) > days * 86400:
                            targets.append((p, os.path.getsize(p)))
                    except OSError:
                        pass
        if not targets:
            messagebox.showinfo(APP_NAME, "Er is niets om op te ruimen.")
            return
        size = sum(s for _p, s in targets)
        if not messagebox.askyesno(APP_NAME, f"{len(targets)} oude bestanden verwijderen ({fmt_bytes(size)})?"):
            return
        gone = 0
        for p, _s in targets:
            try:
                os.remove(p)
                gone += 1
            except OSError:
                pass
        self.app.log(f"{gone} oude logbestanden opgeruimd ({fmt_bytes(size)}).", "ok")
        self.refresh_world()

    def plan_trim(self, area, dim):
        """Welke region-bestanden liggen volledig buiten het gebied? Geeft (lijst van (pad, grootte), regio's-behouden)."""
        x1, z1, x2, z2 = area
        rx = range(math.floor(x1 / 512), math.floor((x2 - 1) / 512) + 1)
        rz = range(math.floor(z1 / 512), math.floor((z2 - 1) / 512) + 1)
        keep_n, move = 0, []
        for path, _kind, d in find_data_dirs(self.app.folder_var.get().strip()):
            if d != dim:
                continue
            for fn in os.listdir(path):
                m = re.match(r"^r\.(-?\d+)\.(-?\d+)\.mca$", fn)
                if not m:
                    continue
                if int(m.group(1)) in rx and int(m.group(2)) in rz:
                    keep_n += 1
                else:
                    p = os.path.join(path, fn)
                    try:
                        move.append((p, os.path.getsize(p)))
                    except OSError:
                        pass
        return move, keep_n

    def trim_regions(self):
        a = self.app
        mt = a.tab_map
        if a.srv_running():
            messagebox.showinfo(APP_NAME, "Stop eerst de server: regio's wegzetten terwijl hij draait kan de wereld beschadigen.")
            return
        area = mt.sel or (mt.gen.get("area") if mt.gen.get("area") else None)
        if not area:
            messagebox.showinfo(APP_NAME, "Kies eerst op het tabblad Kaart een gebied dat je wilt behouden: klik op "
                                          "'Gebied genereren' en sleep een rechthoek.")
            return
        dim = self.trim_world.get() or "overworld"
        move, keep_n = self.plan_trim(area, dim)
        if not move:
            messagebox.showinfo(APP_NAME, f"Er liggen geen regio's van de {dim} buiten dit gebied.")
            return
        size = sum(s for _p, s in move)
        msg = (f"Gebied dat blijft: X {area[0]}..{area[2]}, Z {area[1]}..{area[3]}\n"
               f"Regio-bestanden die blijven: {keep_n}\n"
               f"Regio-bestanden die worden weggezet: {len(move)} ({fmt_bytes(size)})\n\n"
               "Ze gaan naar de map _opgeruimd in je servermap en kunnen terug worden gezet. Doorgaan?")
        if not messagebox.askyesno(APP_NAME, msg):
            return
        folder = a.folder_var.get().strip()
        dest = os.path.join(folder, "_opgeruimd", datetime.now().strftime("%Y%m%d-%H%M%S"))
        moved = 0
        for p, _s in move:
            rel = os.path.relpath(p, folder)
            tgt = os.path.join(dest, rel)
            try:
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                shutil.move(p, tgt)
                moved += 1
            except OSError:
                pass
        a.log(f"{moved} regio-bestanden ({fmt_bytes(size)}) weggezet naar {dest}.", "ok")
        messagebox.showinfo(APP_NAME, f"{moved} regio-bestanden weggezet ({fmt_bytes(size)}).\nMap: {dest}")
        self.refresh_world()



# --------------------------------------------------------------------------
# Backuper-plugin (DVDishka) beheren + backups van dit programma
# --------------------------------------------------------------------------
def _yml_split(val):
    """Splitst 'waarde  # commentaar' in (waarde, commentaar) met respect voor aanhalingstekens."""
    v = val.strip()
    if v[:1] in ("'", '"'):
        q = v[0]
        i = 1
        while i < len(v):
            if v[i] == q and not (q == "'" and v[i + 1:i + 2] == "'"):
                break
            i += 2 if (q == "'" and v[i:i + 2] == "''") else 1
        return v[:i + 1], v[i + 1:]
    m = re.search(r"\s+#", v)
    return (v[:m.start()], v[m.start():]) if m else (v, "")


def yml_unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1].replace("''", "'") if v[0] == "'" else v[1:-1]
    return v


def yml_scan(text):
    """Leest een simpele yml (alleen sleutel: waarde, geneste secties) en geeft {pad-tuple: (regelnummer, ruwe waarde of None)}."""
    out, stack = {}, []
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("-"):
            continue
        m = re.match(r"^(\s*)([^\s:#][^:]*?):(?:\s+(.*))?$", line.rstrip())
        if not m:
            continue
        ind = len(m.group(1).replace("\t", "    "))
        while stack and stack[-1][0] >= ind:
            stack.pop()
        path = tuple(k for _i, k in stack) + (m.group(2).strip(),)
        raw = _yml_split(m.group(3))[0] if m.group(3) else ""
        if raw == "" and not (m.group(3) or "").strip():
            out[path] = (i, None)
            stack.append((ind, m.group(2).strip()))
        else:
            out[path] = (i, raw)
    return out


def yml_set(text, path, value):
    """Zet één waarde en laat de rest (ook commentaar) ongemoeid. Geeft nieuwe tekst of None als de sleutel niet bestaat."""
    sc = yml_scan(text)
    if path not in sc or sc[path][1] is None:
        return None
    lines = text.splitlines(keepends=True)
    ln = lines[sc[path][0]]
    eol = ln[len(ln.rstrip("\r\n")):]
    body = ln.rstrip("\r\n")
    m = re.match(r"^(\s*[^\s:#][^:]*?:\s+)(.*)$", body)
    if not m:
        return None
    _v, cm = _yml_split(m.group(2))
    if isinstance(value, bool):
        nv = "true" if value else "false"
    elif isinstance(value, int):
        nv = str(value)
    else:
        nv = "'" + str(value).replace("'", "''") + "'"
    lines[sc[path][0]] = m.group(1) + nv + cm + eol
    return "".join(lines)


def yml_val(raw, kind):
    if raw is None:
        return None
    v = yml_unquote(raw)
    if kind == "bool":
        return v.lower() in ("true", "yes", "on")
    if kind == "int":
        try:
            return int(float(v))
        except ValueError:
            return 0
    return v


BK_GLOBAL = (("autoBackup", "bool", "Automatisch backups maken"), ("autoBackupPeriod", "int", "Interval (minuten, 1440 = elke dag)"),
             ("autoBackupCron", "str", "Cron-planning (leeg = interval gebruiken)"))
BK_STORAGE = (("enabled", "bool", "Deze opslag gebruiken"), ("autoBackup", "bool", "Automatische backups hierheen"),
              ("backupsFolder", "str", "Map voor de backups"), ("maxBackupsNumber", "int", "Maximaal aantal backups (0 = onbeperkt)"),
              ("maxBackupsWeight", "int", "Maximale totale grootte in MB (0 = onbeperkt)"), ("zipArchive", "bool", "Als zip bewaren (anders als map)"),
              ("zipCompressionLevel", "int", "Zip-compressie (0-9)"))


def backuper_paths(folder):
    pl = os.path.join(folder, "plugins")
    jar = None
    off = False
    try:
        for fn in sorted(os.listdir(pl)):
            low = fn.lower()
            if low.startswith("backuper") and (low.endswith(".jar") or low.endswith(".jar.disabled")):
                jar, off = fn, low.endswith(".disabled")
                break
    except OSError:
        pass
    return jar, off, os.path.join(pl, "Backuper"), os.path.join(pl, "Backuper", "config.yml")


def backuper_state(folder):
    """Alles wat we van Backuper weten, uit de bestanden op schijf (werkt ook als de server uit staat)."""
    jar, off, pdir, cfgp = backuper_paths(folder)
    st = {"jar": jar, "disabled": off, "dir": pdir, "config": cfgp, "has_config": os.path.isfile(cfgp), "global": {}, "storages": []}
    if not st["has_config"]:
        return st
    try:
        with open(cfgp, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return st
    st["text"] = text
    sc = yml_scan(text)
    for k, kind, _l in BK_GLOBAL:
        if ("backup", k) in sc:
            st["global"][k] = yml_val(sc[("backup", k)][1], kind)
    ids = []
    for p, (_ln, raw) in sc.items():
        if len(p) == 2 and p[0] == "storages" and raw is None:
            ids.append(p[1])
    for sid in ids:
        d = {"id": sid, "type": yml_unquote(sc.get(("storages", sid, "type"), (0, ""))[1] or "")}
        for k, kind, _l in BK_STORAGE:
            if ("storages", sid, k) in sc:
                d[k] = yml_val(sc[("storages", sid, k)][1], kind)
        if d["type"] == "local":  # bij ftp/sftp/webdav is backupsFolder een map op de andere computer, geen lokale map
            bf = d.get("backupsFolder") or "./plugins/Backuper/Backups"
            d["path"] = os.path.normpath(bf if os.path.isabs(bf) else os.path.join(folder, bf))
        st["storages"].append(d)
    return st


def backuper_save(folder, changes):
    """changes: {pad-tuple: waarde}. Maakt een kopie van config.yml (.mcm.bak) en schrijft de wijzigingen. Geeft aantal gewijzigde sleutels."""
    _j, _o, _d, cfgp = backuper_paths(folder)
    with open(cfgp, encoding="utf-8", newline="") as fh:
        text = fh.read()
    n = 0
    for path, val in changes.items():
        new = yml_set(text, tuple(path), val)
        if new is not None and new != text:
            text, n = new, n + 1
    if n:
        shutil.copy2(cfgp, cfgp + ".mcm.bak")
        tmp = cfgp + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, cfgp)
    return n


def list_backups(path):
    """Backups in een map: lijst van dicts(name, size, mtime, dir). Grootte van mappen wordt echt gemeten."""
    out = []
    try:
        names = os.listdir(path)
    except OSError:
        return out
    for fn in names:
        p = os.path.join(path, fn)
        try:
            if os.path.isdir(p):
                size, _n = dir_size_n(p)
                out.append({"name": fn, "size": size, "mtime": os.path.getmtime(p), "dir": True})
            else:
                out.append({"name": fn, "size": os.path.getsize(p), "mtime": os.path.getmtime(p), "dir": False})
        except OSError:
            continue
    out.sort(key=lambda b: b["mtime"], reverse=True)
    return out


def delete_backup(base, name):
    """Verwijdert één backup uit de backupmap (alleen een naam, nooit een pad)."""
    if not name or name != os.path.basename(name) or name in (".", ".."):
        raise ValueError("ongeldige naam")
    p = os.path.join(base, name)
    if not os.path.exists(p):
        raise OSError("bestaat niet meer")
    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)


def open_path(p):
    try:
        os.startfile(p)
    except AttributeError:
        webbrowser.open(p)
    except OSError as e:
        messagebox.showerror(APP_NAME, f"Openen mislukt: {e}")


def own_backup_dirs(app):
    root = app.backup_root()
    return [("Server.jar-backups (Paper)", os.path.join(root, "server")), ("Plugin-backups bij updates", os.path.join(root, "plugins")),
            ("Verwijderde plugins", os.path.join(root, "verwijderde_plugins")),
            ("Backups van dit programma", os.path.join(app_dir(), "programma_backups"))]


class BackupTab(ttk.Frame):
    """Tabblad Backups: beheert de plugin Backuper (instellingen, backups, bestanden) en de backups van dit programma."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.q = queue.Queue()
        self.st = {}
        self.vars = {}
        self._busy = False
        self._build()

    def _btn(self, parent, text, cmd, bg="#e5e7eb", fg="#111827"):
        return make_btn(parent, text, cmd, bg, fg, 8, 2)

    def folder(self):
        return self.app.folder_var.get().strip()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 6))
        self.head = ttk.Label(top, text="", font=("Segoe UI", 10, "bold"))
        self.head.pack(side="left")
        self._btn(top, "↻  Vernieuwen", self.refresh).pack(side="right")
        self._btn(top, "❓", lambda: self.app.srv_running() and self.app.srv_send("help backuper")).pack(side="right", padx=(6, 0))
        self._btn(top, "💾  Nu backup maken", self.backup_now, "#15803d", "white").pack(side="right", padx=6)
        self.cmd_var = tk.StringVar(value=self.app.cfg.get("backuper_cmd", "backuper backup local"))
        ttk.Entry(top, textvariable=self.cmd_var, width=26).pack(side="right")
        ttk.Label(top, text="commando:", foreground="#6b7280").pack(side="right", padx=(0, 4))
        self.sub = ttk.Notebook(self)
        self.sub.pack(fill="both", expand=True)
        self.pg_bk = ttk.Frame(self.sub, padding=8)
        self.pg_cf = ttk.Frame(self.sub, padding=8)
        self.pg_fl = ttk.Frame(self.sub, padding=8)
        self.pg_ow = ttk.Frame(self.sub, padding=8)
        for pg, t in ((self.pg_bk, "💾  Backups"), (self.pg_cf, "⚙  Instellingen van Backuper"), (self.pg_fl, "📁  Bestanden van de plugin"),
                      (self.pg_ow, "🧰  Backups van dit programma")):
            self.sub.add(pg, text=t)
        # backups
        f = self.pg_bk
        self.bk_info = ttk.Label(f, text="", foreground="#374151")
        self.bk_info.pack(anchor="w", pady=(0, 6))
        self.bk_tree = ttk.Treeview(f, columns=("st", "name", "date", "size"), show="headings", height=12, selectmode="extended")
        for c, t, w, an in (("st", "Opslag", 90, "w"), ("name", "Naam", 380, "w"), ("date", "Datum", 150, "w"), ("size", "Grootte", 100, "e")):
            self.bk_tree.heading(c, text=t)
            self.bk_tree.column(c, width=w, anchor=an)
        self.bk_tree.pack(fill="both", expand=True)
        r = ttk.Frame(f)
        r.pack(fill="x", pady=(8, 0))
        self._btn(r, "📂  Map openen", self.open_backup_dir).pack(side="left")
        self._btn(r, "🗑  Geselecteerde verwijderen…", self.del_selected, "#b91c1c", "white").pack(side="left", padx=6)
        ttk.Label(r, text="Terugzetten doe je met de hand: stop de server, pak de zip uit in de wereldmap. Zo kan er niets misgaan.",
                  foreground="#6b7280").pack(side="left", padx=8)
        # instellingen
        _o, self.cf_box = make_scroll_frame(self.pg_cf)
        _o.pack(fill="both", expand=True)
        # bestanden
        f = self.pg_fl
        r = ttk.Frame(f)
        r.pack(fill="x", pady=(0, 6))
        self._btn(r, "📝  config.yml openen", lambda: self._open_cfg()).pack(side="left")
        self._btn(r, "📂  Pluginmap openen", lambda: open_path(self.st.get("dir", ""))).pack(side="left", padx=6)
        self.fl_tree = ttk.Treeview(f, columns=("name", "date", "size"), show="tree headings", height=14, selectmode="browse")
        self.fl_tree.heading("#0", text="Bestand of map")
        self.fl_tree.column("#0", width=380)
        for c, t, w, an in (("name", "Soort", 80, "w"), ("date", "Gewijzigd", 150, "w"), ("size", "Grootte", 100, "e")):
            self.fl_tree.heading(c, text=t)
            self.fl_tree.column(c, width=w, anchor=an)
        self.fl_tree.pack(fill="both", expand=True)
        self.fl_tree.bind("<Double-1>", self._fl_open)
        # eigen backups
        f = self.pg_ow
        self.ow_tree = ttk.Treeview(f, columns=("what", "count", "size", "where"), show="headings", height=5, selectmode="browse")
        for c, t, w, an in (("what", "Onderdeel", 240, "w"), ("count", "Aantal", 70, "e"), ("size", "Grootte", 100, "e"), ("where", "Map", 420, "w")):
            self.ow_tree.heading(c, text=t)
            self.ow_tree.column(c, width=w, anchor=an)
        self.ow_tree.pack(fill="x")
        r = ttk.Frame(f)
        r.pack(fill="x", pady=(8, 8))
        self._btn(r, "📂  Openen", self.ow_open).pack(side="left")
        self._btn(r, "🗑  Leegmaken…", self.ow_clear, "#b91c1c", "white").pack(side="left", padx=6)
        box = ttk.LabelFrame(f, text="Instellingen van dit programma voor backups", padding=8)
        box.pack(fill="x")
        self.ov = {}
        for row, (key, kind, label) in enumerate((("keep_server_backups", "bool", "Bij elke Paper-update een backup van server.jar bewaren"),
                                                  ("server_backups_max", "int", "Aantal server.jar-backups"),
                                                  ("keep_plugin_backups", "bool", "Bij elke plugin-update een backup van de plugin bewaren"),
                                                  ("plugin_backups_max", "int", "Aantal plugin-backups"))):
            if kind == "bool":
                v = tk.BooleanVar(value=bool(self.app.cfg.get(key, DEFAULTS.get(key))))
                ttk.Checkbutton(box, text=label, variable=v, command=lambda k=key, v=v: self._own_set(k, bool(v.get()))).grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
            else:
                v = tk.StringVar(value=str(self.app.cfg.get(key, DEFAULTS.get(key))))
                ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", pady=2)
                sp = ttk.Spinbox(box, from_=1, to=99, width=5, textvariable=v, command=lambda k=key, v=v: self._own_set(k, int_var(v, 3)))
                sp.grid(row=row, column=1, sticky="w", padx=8)
                sp.bind("<FocusOut>", lambda _e, k=key, v=v: self._own_set(k, int_var(v, 3)))
            self.ov[key] = v
        r = ttk.Frame(box)
        r.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(r, text="Backupmap:").pack(side="left")
        self.bd_var = tk.StringVar(value=self.app.cfg.get("backup_dir", ""))
        e = ttk.Entry(r, textvariable=self.bd_var, width=50)
        e.pack(side="left", padx=6)
        e.bind("<FocusOut>", lambda _e: self._own_set("backup_dir", self.bd_var.get().strip()))
        ttk.Label(r, text="(leeg = updater_backups in je servermap)", foreground="#6b7280").pack(side="left")

    def _own_set(self, key, val):
        self.app.cfg[key] = val
        self.app._save_cfg()
        try:
            self.app.apply_settings()
        except Exception:
            pass

    def on_show(self):
        self.refresh()

    # ---------- inlezen ----------
    def refresh(self):
        if self._busy:
            return
        self._busy = True
        self.head.config(text="Laden…")
        folder = self.folder()

        def work():
            st = backuper_state(folder) if folder else {"jar": None, "global": {}, "storages": []}
            bks = []
            for s in st["storages"]:
                if s.get("path"):
                    for b in list_backups(s["path"]):
                        b["storage"] = s["id"]
                        bks.append(b)
            bks.sort(key=lambda b: b["mtime"], reverse=True)
            files = []
            pd = st.get("dir")
            skip = {os.path.normcase(s["path"]) for s in st["storages"] if s.get("path")}
            if pd and os.path.isdir(pd):
                for fn in sorted(os.listdir(pd)):
                    p = os.path.join(pd, fn)
                    try:
                        if os.path.isdir(p):
                            sz = dir_size_n(p)[0]
                            files.append((fn, "map", os.path.getmtime(p), sz, os.path.normcase(p) in skip))
                        else:
                            files.append((fn, "bestand", os.path.getmtime(p), os.path.getsize(p), False))
                    except OSError:
                        pass
            own = []
            for label, d in own_backup_dirs(self.app):
                n, sz = 0, 0
                if os.path.isdir(d):
                    for fn in os.listdir(d):
                        n += 1
                        p = os.path.join(d, fn)
                        sz += dir_size_n(p)[0] if os.path.isdir(p) else (os.path.getsize(p) if os.path.exists(p) else 0)
                own.append((label, n, sz, d))
            try:
                du = shutil.disk_usage(folder)
            except OSError:
                du = None
            self.q.put((st, bks, files, own, du))
        threading.Thread(target=work, daemon=True).start()
        self.after(150, self._poll)

    def _poll(self):
        try:
            st, bks, files, own, du = self.q.get_nowait()
        except queue.Empty:
            self.after(150, self._poll)
            return
        self._busy = False
        self.st = st
        self.bks = bks
        self._fill(st, bks, files, own, du)

    def _fill(self, st, bks, files, own, du):
        if not st.get("jar"):
            self.head.config(text="Backuper staat niet in je plugins-map. Installeer hem via het tabblad Plugins (zoeken: Backuper).")
        else:
            state = "uitgezet (.disabled)" if st.get("disabled") else "aan"
            self.head.config(text=f"Backuper: {st['jar']}  •  {state}" + ("" if st.get("has_config") else "  •  nog geen config.yml (start de server één keer)"))
        t = self.bk_tree
        t.delete(*t.get_children())
        for i, b in enumerate(bks):
            t.insert("", "end", iid=str(i), values=(b["storage"], b["name"] + ("  (map)" if b["dir"] else ""),
                                                     datetime.fromtimestamp(b["mtime"]).strftime("%d-%m-%Y %H:%M"), fmt_bytes(b["size"])))
        tot = sum(b["size"] for b in bks)
        loc = next((s for s in st.get("storages", []) if s.get("path")), {})
        lim = []
        if loc.get("maxBackupsNumber"):
            lim.append(f"max {loc['maxBackupsNumber']} backups")
        if loc.get("maxBackupsWeight"):
            lim.append(f"max {fmt_bytes(loc['maxBackupsWeight'] * 1024 * 1024)}")
        last = f"laatste backup {fmt_dur_short(time.time() - bks[0]['mtime'])} geleden" if bks else "nog geen backups gevonden"
        per = (st.get("global") or {}).get("autoBackupPeriod")
        warn = ""
        if bks and per and (st.get("global") or {}).get("autoBackup") and time.time() - bks[0]["mtime"] > per * 60 * 2.5:
            warn = "  ⚠ Dit is veel ouder dan het ingestelde interval: controleer of Backuper nog draait."
        self.bk_info.config(text=f"{len(bks)} backups, samen {fmt_bytes(tot)}  •  {last}" + (f"  •  limiet: {', '.join(lim)}" if lim else "")
                            + (f"  •  schijf: {fmt_bytes(du.free)} vrij" if du else "") + warn)
        self._fill_cfg(st)
        ft = self.fl_tree
        ft.delete(*ft.get_children())
        for fn, kind, mt, sz, isbk in files:
            ft.insert("", "end", iid=fn, text=("📁 " if kind == "map" else "📄 ") + fn + ("   (hier staan je backups)" if isbk else ""),
                      values=(kind, datetime.fromtimestamp(mt).strftime("%d-%m-%Y %H:%M"), fmt_bytes(sz)))
        ot = self.ow_tree
        ot.delete(*ot.get_children())
        for label, n, sz, d in own:
            ot.insert("", "end", iid=d, values=(label, n, fmt_bytes(sz), d))

    def _fill_cfg(self, st):
        for w in self.cf_box.winfo_children():
            w.destroy()
        self.vars = {}
        if not st.get("has_config"):
            ttk.Label(self.cf_box, text="Er is nog geen config.yml van Backuper. Start de server een keer met de plugin aan; daarna kun je hem hier instellen.",
                      foreground="#6b7280").pack(anchor="w")
            return
        def section(title, rows, base, data):
            box = ttk.LabelFrame(self.cf_box, text=title, padding=8)
            box.pack(fill="x", pady=(0, 8))
            for r, (key, kind, label) in enumerate(rows):
                if key not in data:
                    continue
                if kind == "bool":
                    v = tk.BooleanVar(value=bool(data[key]))
                    ttk.Checkbutton(box, text=label, variable=v).grid(row=r, column=0, columnspan=2, sticky="w", pady=2)
                else:
                    v = tk.StringVar(value=str(data[key]))
                    ttk.Label(box, text=label).grid(row=r, column=0, sticky="w", pady=2)
                    ttk.Entry(box, textvariable=v, width=48 if key == "backupsFolder" else 14).grid(row=r, column=1, sticky="w", padx=8)
                self.vars[base + (key,)] = (v, kind, data[key])
        section("Planning", BK_GLOBAL, ("backup",), st["global"])
        for s in st["storages"]:
            title = f"Opslag '{s['id']}'  ({s.get('type') or '?'})"
            section(title, BK_STORAGE, ("storages", s["id"]), s)
        r = ttk.Frame(self.cf_box)
        r.pack(fill="x")
        self._btn(r, "💾  Opslaan", lambda: self.save_cfg(False), "#2563eb", "white").pack(side="left")
        self._btn(r, "💾  Opslaan en server herstarten", lambda: self.save_cfg(True), "#b45309", "white").pack(side="left", padx=6)
        ttk.Label(r, text="Er wordt een kopie bewaard als config.yml.mcm.bak. Wachtwoorden en logins van FTP/Google Drive blijven ongemoeid.",
                  foreground="#6b7280").pack(side="left", padx=8)

    # ---------- acties ----------
    def save_cfg(self, restart):
        ch = {}
        for path, (v, kind, old) in self.vars.items():
            if kind == "int":
                try:
                    nv = int(str(v.get()).strip())
                except ValueError:
                    messagebox.showerror(APP_NAME, f"'{path[-1]}' moet een getal zijn.")
                    return
            elif kind == "bool":
                nv = bool(v.get())
            else:
                nv = str(v.get()).strip()
            if nv != old:
                ch[path] = nv
        if not ch:
            messagebox.showinfo(APP_NAME, "Er is niets veranderd.")
            return
        try:
            n = backuper_save(self.folder(), ch)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Opslaan mislukt: {e}")
            return
        self.app.log(f"Backuper-instellingen opgeslagen ({n} gewijzigd).", "ok")
        running = self.app.srv_running()
        if restart and running:
            self.app.srv_stop(restart=True)
        elif running:
            messagebox.showinfo(APP_NAME, "Opgeslagen. Backuper leest zijn instellingen pas na een herstart van de server.")
        self.refresh()

    def backup_now(self):
        c = self.cmd_var.get().strip().lstrip("/")
        if not c:
            return
        if not self.app.srv_running() or self.app.srv_state != "online":
            messagebox.showinfo(APP_NAME, "De server draait niet. Backuper maakt zelf backups terwijl de server aan staat.")
            return
        self.app.cfg["backuper_cmd"] = c
        self.app._save_cfg()
        self.app.srv_send(c)
        self.app.log(f"Backup gevraagd: /{c}. Kijk in de console of Backuper hem accepteert.", "info")
        self.after(20000, self.refresh)

    def open_backup_dir(self):
        s = next((s for s in self.st.get("storages", []) if s.get("path")), None)
        if s and os.path.isdir(s["path"]):
            open_path(s["path"])
        else:
            messagebox.showinfo(APP_NAME, "De backupmap bestaat nog niet.")

    def del_selected(self):
        sel = [self.bks[int(i)] for i in self.bk_tree.selection()]
        if not sel:
            messagebox.showinfo(APP_NAME, "Selecteer eerst backups in de lijst.")
            return
        if not messagebox.askyesno(APP_NAME, f"{len(sel)} backup(s) definitief verwijderen ({fmt_bytes(sum(b['size'] for b in sel))})?\n\n"
                                             + "\n".join(b["name"] for b in sel[:8]) + ("\n…" if len(sel) > 8 else "")):
            return
        paths = {s["id"]: s.get("path") for s in self.st.get("storages", [])}
        gone = 0
        for b in sel:
            try:
                delete_backup(paths[b["storage"]], b["name"])
                gone += 1
            except (OSError, ValueError, KeyError) as e:
                messagebox.showerror(APP_NAME, f"{b['name']}: {e}")
        self.app.log(f"{gone} backup(s) verwijderd.", "ok")
        self.refresh()

    def _open_cfg(self):
        if os.path.isfile(self.st.get("config", "")):
            open_path(self.st["config"])

    def _fl_open(self, _e):
        iid = self.fl_tree.focus()
        if iid and self.st.get("dir"):
            open_path(os.path.join(self.st["dir"], iid))

    def ow_open(self):
        sel = self.ow_tree.selection()
        if sel:
            if os.path.isdir(sel[0]):
                open_path(sel[0])
            else:
                messagebox.showinfo(APP_NAME, "Deze map bestaat nog niet.")

    def ow_clear(self):
        sel = self.ow_tree.selection()
        if not sel or not os.path.isdir(sel[0]):
            return
        d = sel[0]
        label = self.ow_tree.item(d, "values")[0]
        if not messagebox.askyesno(APP_NAME, f"Alles in '{label}' verwijderen?\n\n{d}\n\nDit kan niet ongedaan worden gemaakt."):
            return
        gone = 0
        for fn in os.listdir(d):
            try:
                delete_backup(d, fn)
                gone += 1
            except (OSError, ValueError):
                pass
        self.app.log(f"{gone} item(s) uit '{label}' verwijderd.", "ok")
        self.refresh()


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
        try:
            with open(os.path.abspath(__file__), encoding="utf-8") as fh:
                self._src = fh.read()          # de code die nu draait, om een update mee te vergelijken
        except OSError:
            self._src = None
        if self.cfg.get("dark_mode"):
            install_dark(self)
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
        self._crash_times, self.cmd_hist, self.hist_idx = [], [str(x) for x in (self.cfg.get("cmd_history") or [])][-200:], 0
        self.hist_idx = len(self.cmd_hist)
        self._bad = set()
        self._learn_until, self._learn_topics = 0.0, []
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

        self.heads = Heads(self)
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
        if DARK_ON:
            self.after(50, lambda: dark_titlebar(self))
        self.after(200, self._startup)

    # ---------------- UI opbouw ----------------
    def _style(self):
        style = ttk.Style(self)
        flat_style(style, DARK if DARK_ON else LIGHT)
        if not DARK_ON:
            for pat in ("*Frame.background", "*Toplevel.background", "*Label.background", "*Checkbutton.background",
                        "*Radiobutton.background"):
                self.option_add(pat, LIGHT["bg"], 20)
            self.configure(bg=LIGHT["bg"])

        def fixed_map(option):  # workaround voor kleuren in Tk 8.6.9
            return [e for e in style.map("Treeview", query_opt=option) if e[:2] != ("!disabled", "!selected")]

        style.map("Treeview", foreground=fixed_map("foreground"), background=fixed_map("background"))
        style.configure("Heads.Treeview", rowheight=max(28, round(28 * max(1.0, self.winfo_fpixels("1i") / 96.0))))

    def _build(self):
        header = tk.Frame(self, bg="#1f2937")
        header.pack(fill="x")
        tk.Label(header, text="⛏  MC Server Manager", bg="#1f2937", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(header, text="Beheer je Minecraft-server: starten, plugins, kaart en backups", bg="#1f2937", fg="#9ca3af",
                 font=("Segoe UI", 10)).pack(side="left", padx=4)

        self.btn_settings = tk.Button(header, text="⚙  Instellingen", command=self.open_settings, bg="#374151",
                                      fg="white", activebackground="#4b5563", activeforeground="white",
                                      relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 10), cursor="hand2")
        self.btn_settings.pack(side="right", padx=14, pady=10)
        self.btn_desk = tk.Button(header, text="✨  Nieuwe interface", command=self.open_desk, bg="#2563eb",
                                  fg="white", activebackground="#1d4ed8", activeforeground="white",
                                  relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 10), cursor="hand2")
        self.btn_desk.pack(side="right", padx=0, pady=10)
        self.btn_start = tk.Button(header, text="▶  Server starten", command=self.start_server, bg="#059669",
                                   fg="white", activebackground="#047857", activeforeground="white",
                                   relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 10), cursor="hand2")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.btn_selfupd = tk.Button(header, text="⬆  Update", command=self._selfupd_ask, bg="#d97706", fg="white",
                                     activebackground="#b45309", activeforeground="white", relief="flat", bd=0,
                                     padx=12, pady=5, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.tab_srv = ttk.Frame(self.nb, padding=10)
        self.tab_net = ttk.Frame(self.nb, padding=10)
        self.tab_plug = PluginsTab(self.nb, self)
        body = ttk.Frame(self.tab_plug.sub, padding=10)      # Updates zit als subtabblad in Plugins
        self.tab_plug.sub.insert(1, body, text="🔧  Updates")
        self.remote = RemoteServer(self)
        self.desk = RemoteServer(self)      # eigen scherm op dit adres (alleen deze computer)
        self.tab_map = MapTab(self.nb, self)
        self.tab_beheer = BeheerTab(self.nb, self)
        self.tab_backup = BackupTab(self.nb, self)
        self.nb.add(self.tab_srv, text="🖥  Server")
        self.nb.add(self.tab_plug, text="🧩  Plugins")
        self.nb.add(self.tab_map, text="🗺  Kaart")
        self.nb.add(self.tab_beheer, text="🛠  Beheer")
        self.nb.add(self.tab_backup, text="💾  Backups")
        self.tab_upd = body
        self.nb.add(self.tab_net, text="🌐  Netwerk")
        self._build_server_tab(self.tab_srv)
        self._build_net_tab(self.tab_net)
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)
        self.after(300, self._spark_anim)
        self.after(1500, self.remote_apply)
        self.after(1000, self._remote_tick)
        self.after(700, self._upd_tab_blink)
        self.after(800, self._heads_tick)

        ttk.Label(body, text="Controleer en installeer updates voor Paper (de server zelf) en voor je plugins. "
                             "Er wordt eerst een backup gemaakt, zodat je altijd terug kunt.",
                  style="Muted.TLabel", wraplength=1000, justify="left").pack(anchor="w", pady=(0, 8))
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
        try:
            self.heads.pump()
        except Exception:
            pass
        self.after(80, self._poll)

    def _handle(self, m):
        k = m[0]
        if k == "log":
            try:
                self.remote.push_log(m[1], m[2])
                self.desk.push_log(m[1], m[2])
            except Exception:
                pass
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
        elif k == "wake":
            self._wake(m[1])
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

    GRAPHS_PATH = os.path.join(app_dir(), "mc_server_manager_grafieken.json")

    def _sparks(self):
        return {"cpu": self.spark_cpu, "ram": self.spark_ram, "tps": self.spark_tps, "temp": self.spark_temp}

    def _graphs_load(self):
        """De grafieken lopen door na een herstart van de server of van het programma."""
        try:
            with open(self.GRAPHS_PATH, encoding="utf-8") as fh:
                d = json.load(fh)
            lim = time.time() - 6 * 3600
            for k, sk in self._sparks().items():
                for t, v in d.get(k, []):
                    if t >= lim:
                        sk.data.append((float(t), None if v is None else float(v)))
                sk.gap()
        except (OSError, ValueError, TypeError):
            pass

    def _graphs_save(self):
        try:
            lim = time.time() - 6 * 3600
            out = {k: [[round(t, 1), None if v is None else round(v, 2)] for t, v in sk.data if t >= lim][-6000:]
                   for k, sk in self._sparks().items()}
            tmp = self.GRAPHS_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(out, fh)
            os.replace(tmp, self.GRAPHS_PATH)
        except (OSError, ValueError):
            pass

    def _graphs_tick(self):
        self._graphs_save()
        self.after(60000, self._graphs_tick)

    def _save_cfg(self):
        self.cfg.update(folder=self.folder_var.get().strip(), jar=self.jar_var.get().strip(),
                        unstable=self.unstable_var.get(), update_folder=self.updfolder_var.get(),
                        reach_host=self.reach_host_var.get().strip(), reach_port=int_var(self.reach_port_var, 25565),
                        reach_check_bedrock=bool(self.reach_bed_var.get()),
                        reach_bedrock_port=int_var(self.reach_bport_var, 19132),
                        reach_auto=bool(self.reach_auto_var.get()))
        save_config(self.cfg)

    def _startup(self):
        self.after(60000, self._graphs_tick)
        self.after(15000, self._sleep_tick)
        self.after(4000, self.tab_map.prewarm)
        self.after(20000, self._health_tick)
        self.after(2000, self._sleep_stats_show)
        if self.cfg.get("desk_main", True):
            self.after(1500, self._open_desk_main)
        self._console_add("Welkom! Klik op 'Starten' om je server te starten. Wat de server meldt verschijnt hier; "
                          "typ onderaan een commando en druk op Enter (Tab vult aan, pijltje omhoog haalt het vorige terug).", own=True)
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
            self.sleep_var.set(bool(c.get("sleep_enabled")))
            self._sleep_stats_show()
        except (AttributeError, tk.TclError):
            pass
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
                                          ("temp", "Laptop-temp."), ("sleep", "Slaapstand"))):
            self.sv[key] = tk.StringVar(value="-")
            ttk.Label(st, text=label + ":").grid(row=i, column=0, sticky="w", pady=1)
            self.sv_lbl[key] = ttk.Label(st, textvariable=self.sv[key], font=("Segoe UI", 10, "bold"))
            self.sv_lbl[key].grid(row=i, column=1, sticky="w", padx=(10, 0))
        self.psutil_frame = None
        if psutil is None:
            hf = ttk.Frame(st)
            hf.grid(row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))
            self.psutil_frame = hf
            self.psutil_lbl = ttk.Label(hf, text="CPU/geheugen heeft 'psutil' nodig", foreground="#b45309")
            self.psutil_lbl.pack(anchor="w")
            self.btn_psutil = ttk.Button(hf, text="psutil installeren", command=self.install_psutil)
            self.btn_psutil.pack(anchor="w", pady=(2, 0))

        ttk.Separator(st).grid(row=9, column=0, columnspan=2, sticky="ew", pady=6)
        self.sleep_var = tk.BooleanVar(value=bool(self.cfg.get("sleep_enabled")))
        ttk.Checkbutton(st, text="😴  Auto slaapstand", variable=self.sleep_var, command=self._sleep_toggle).grid(
            row=10, column=0, columnspan=2, sticky="w")
        self.btn_sleep_now = make_btn(st, "😴  Nu in slaapstand", self.sleep_now)
        self.btn_sleep_now.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        make_btn(st, "👥  Whitelist en bans", self.open_lists).grid(row=12, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        make_btn(st, "🔎  Logboek doorzoeken", self.open_logsearch).grid(row=13, column=0, columnspan=2, sticky="ew", pady=(4, 0))

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
        self._graphs_load()
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
        self.pmenu.add_command(label="Bannen…", command=self.player_ban)
        self.pmenu.add_command(label="Op de whitelist zetten", command=lambda: self._player_cmd("whitelist add {}"))
        self.pmenu.add_command(label="Operator maken", command=lambda: self._player_cmd("op {}"))
        self.ptree.bind("<Button-3>", self._player_menu)
        self.heads.watch_tree(self.ptree, lambda iid: iid, lambda iid: (self.ptree.item(iid, "values") or ("", ""))[1] if len(self.ptree.item(iid, "values") or ()) > 1 else "")

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
        try:
            self.btn_sleep_now.config(state="normal" if st == "online" else "disabled")
        except AttributeError:
            pass
        for w in [self.cmd_entry, self.btn_send] + self.quick_btns:
            w.config(state="normal" if st in ("starting", "online") else "disabled")
        self.btn_start.config(text="▶  Server starten" if st == "stopped" else "🖥  Naar server")
        if st == "stopped" and getattr(self, "_sleeping", False):
            self.srv_state_lbl.config(text="😴  Slaapstand", fg="#7c3aed")

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
        self._wake_stop()
        self._mcm_install(folder)
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

    # ---- Slaapstand: server stoppen als er niemand is, wakker maken zodra iemand probeert te joinen ----
    def _sleep_tick(self):
        try:
            self._sleep_stats_show()
            if self.cfg.get("sleep_enabled") and self.srv_state == "online" and not getattr(self, "_sleeping", False):
                busy = bool(self.players) or self.tab_map.gen["state"] in ("running", "paused")
                now = time.time()
                if busy or not getattr(self, "_idle_since", None) or not sleep_allowed(self.cfg, now):
                    self._idle_since = now
                else:
                    mins = max(1, int(self.cfg.get("sleep_minutes", 10) or 10))
                    if now - self._idle_since >= mins * 60:
                        self._go_sleep(mins)
        finally:
            self.after(15000, self._sleep_tick)

    def _sleep_stats(self):
        st = self.cfg.get("sleep_stats")
        if not isinstance(st, dict):
            st = self.cfg["sleep_stats"] = {}
        return st

    def _sleep_stats_show(self):
        st = self._sleep_stats()
        secs = st.get("secs", 0) + (time.time() - self._sleep_t0 if getattr(self, "_sleeping", False) and getattr(self, "_sleep_t0", None) else 0)
        if not st.get("count"):
            txt = "nog niet geslapen" if self.cfg.get("sleep_enabled") else "uit"
        else:
            txt = f"{st['count']}x, {fmt_dur_short(secs)}"
            if st.get("wakes"):
                txt += f", {st['wakes']}x gewekt"
        if getattr(self, "_sleeping", False):
            txt = "😴 slaapt: " + txt
        self.sv["sleep"].set(txt)

    def _sleep_toggle(self):
        self.cfg["sleep_enabled"] = bool(self.sleep_var.get())
        self._idle_since = time.time()
        self._save_cfg()
        self._sleep_stats_show()

    # ---- gezondheidscontrole ----
    def _health_warn(self, kind, title, text):
        now = time.time()
        last = getattr(self, "_health_last", None)
        if last is None:
            last = self._health_last = {}
        if now - last.get(kind, 0) < 1800:
            return
        last[kind] = now
        self.log("⚠ " + text, "warn")
        toast(title, text)

    def _health_tps_check(self, tps):
        c = self.cfg
        thr = float(c.get("health_tps_min", 15))
        if not c.get("health_tps", True) or tps >= thr:
            self._tps_low_since = None
            return
        now = time.time()
        if not getattr(self, "_tps_low_since", None):
            self._tps_low_since = now
        mins = max(1, int(c.get("health_tps_mins", 5)))
        if now - self._tps_low_since >= mins * 60:
            self._health_warn("tps", "Server loopt achter", f"De TPS zit al {int((now - self._tps_low_since) / 60)} minuten onder {thr:g} (nu {tps:.1f}). "
                              "Tips: verlaag view-distance of simulation-distance, pauzeer Chunky, of controleer zware plugins met /spark profiler.")

    def _health_ram_check(self, ram):
        c = self.cfg
        if not c.get("health_ram", True) or not ram or not self.srv_xmx:
            self._ram_hi_since = None
            return
        pct = ram / float(self.srv_xmx) * 100
        if pct < int(c.get("health_ram_pct", 90)):
            self._ram_hi_since = None
            return
        now = time.time()
        if not getattr(self, "_ram_hi_since", None):
            self._ram_hi_since = now
        if now - self._ram_hi_since >= 180:
            self._health_warn("ram", "Geheugen bijna op", f"De server gebruikt {ram:.0f} van {self.srv_xmx} MB ({pct:.0f}%) en zit al 3 minuten zo hoog. "
                              "Verhoog 'Max. RAM' bovenin het tabblad Server (herstart nodig) als dit blijft gebeuren.")

    def _health_tick(self):
        try:
            folder = self.folder_var.get().strip()
            if self.cfg.get("health_disk", True) and os.path.isdir(folder):
                free = shutil.disk_usage(folder).free / 1e9
                lim = float(self.cfg.get("health_disk_gb", 5))
                if free < lim:
                    self._health_warn("disk", "Schijf bijna vol", f"Er is nog maar {free:.1f} GB vrij op de schijf van de server (grens {lim:g} GB). "
                                      "Ruim oude backups of logs op (tabblad Backups), anders kan de wereld niet meer opgeslagen worden.")
        except Exception:
            pass
        self.after(60000, self._health_tick)

    def sleep_now(self):
        """Knop: de server nu zelf in slaapstand zetten, ook als de automatische slaapstand uit staat."""
        if self.srv_state != "online" or getattr(self, "_sleeping", False):
            return
        n = len(self.players)
        gen = self.tab_map.gen["state"] in ("running", "paused")
        msg = "De server wordt veilig gestopt en start vanzelf weer zodra iemand probeert te joinen."
        if n:
            msg = f"Er {'is' if n == 1 else 'zijn'} nog {n} speler{'' if n == 1 else 's'} online; die word{'t' if n == 1 else 'en'} van de server gezet.\n\n" + msg
        if gen:
            msg = "Chunky is nog bezig met genereren; dat stopt en kan later worden hervat.\n\n" + msg
        if not messagebox.askyesno(APP_NAME, msg + "\n\nNu in slaapstand zetten?"):
            return
        self._go_sleep(None)

    def _go_sleep(self, mins):
        self.log(f"Slaapstand: al {mins} minuten niemand online. De server wordt veilig gestopt en start vanzelf weer zodra iemand probeert te joinen."
                 if mins else "Slaapstand: handmatig gestart. De server wordt veilig gestopt en start vanzelf weer zodra iemand probeert te joinen.", "info")
        self._sleeping = True
        self._sleep_t0 = time.time()
        st = self._sleep_stats()
        st["count"] = st.get("count", 0) + 1
        self._save_cfg()
        self.srv_stop(after=self._sleep_enter)

    def _wake_ports(self):
        folder = self.folder_var.get().strip()
        props = read_properties(folder)
        try:
            jport = int(props.get("server-port") or 25565)
        except ValueError:
            jport = 25565
        try:
            maxp = int(props.get("max-players") or 20)
        except ValueError:
            maxp = 20
        bport = 0
        try:
            if any("geyser" in f.lower() and f.lower().endswith(".jar") for f in os.listdir(os.path.join(folder, "plugins"))):
                bport = int_var(self.reach_bport_var, 19132)
        except OSError:
            pass
        return jport, bport, maxp

    def _sleep_enter(self):
        if not getattr(self, "_sleeping", False):
            return
        jport, bport, maxp = self._wake_ports()
        self._wake_stop(keep=True)
        lis = WakeListener(jport, bport, "💤 Server slaapt: verbind om hem wakker te maken", maxp,
                           lambda who: self.q.put(("wake", who)), self.log)
        errs = lis.start()
        self._wake_lis = lis
        if errs:
            self.log("Slaapstand: kon niet luisteren op " + "; ".join(errs) + ". Start de server zelf met de knop.", "warn")
        else:
            self.log(f"Slaapstand: wacht op spelers (poort {jport}" + (f", Bedrock {bport}" if bport else "") + ").", "ok")
        self._set_state("stopped")

    def _wake_stop(self, keep=False):
        lis = getattr(self, "_wake_lis", None)
        if lis is not None:
            lis.stop()
            self._wake_lis = None
        if not keep:
            if getattr(self, "_sleeping", False) and getattr(self, "_sleep_t0", None):
                st = self._sleep_stats()
                st["secs"] = st.get("secs", 0) + max(0, time.time() - self._sleep_t0)
                self._sleep_t0 = None
                self._save_cfg()
            self._sleeping = False

    def _wake(self, who):
        if not getattr(self, "_sleeping", False) or self.srv_running():
            return
        st = self._sleep_stats()
        st["wakes"] = st.get("wakes", 0) + 1
        st["last_who"], st["last_at"] = who, time.strftime("%d-%m %H:%M")
        self.tab_beheer.notify("notify_join", "Slaapstand voorbij", f"{who} wekt de server.", who)
        self.log(f"Slaapstand: {who} probeert te joinen. De server wordt gestart…", "ok")
        self._wake_stop()
        self._set_state("stopped")
        self.after(1200, self.srv_start)

    def _mcm_install(self, folder):
        """Zet (eenmalig) het kleine hulpplugin MCMTab in de plugins-map. Daarmee geeft de server zijn eigen Tab-aanvullingen door."""
        try:
            pdir = os.path.join(folder, "plugins")
            dst = os.path.join(pdir, "MCMTab.jar")
            if not os.path.isdir(pdir) or os.path.exists(dst) or self.cfg.get("mcmtab_done"):
                return
            with open(dst, "wb") as fh:
                fh.write(base64.b64decode("".join(MCMTAB_JAR_B64)))
            self.cfg["mcmtab_done"] = True
            self._save_cfg()
            self.log("Hulpplugin MCMTab geïnstalleerd (plugins/MCMTab.jar). Na een herstart van de server geeft Tab dezelfde aanvullingen als de echte console.", "ok")
        except OSError as e:
            self.log(f"MCMTab kon niet worden geplaatst: {e}", "warn")

    # ---- Tab-aanvulling via het hulpplugin ----
    def _mcm_ask(self, rid, line=None):
        arg = ""
        if line is not None:
            arg = " " + base64.urlsafe_b64encode(line.encode("utf-8")).decode("ascii").rstrip("=")
        self.srv_send(f"mcmtab {rid}{arg}", echo=False)

    def _mcm_reply(self, rid, body):
        items = [x for x in body.split("\t") if x]
        if rid.startswith("c"):
            self._mcm_ok = True
            if not body.startswith("!"):
                cur = self.cfg.setdefault("learned_cmds", [])
                new = [x.lower() for x in items if re.fullmatch(r"[A-Za-z0-9_\-.]{1,40}", x) and x.lower() not in cur]
                if new:
                    cur.extend(new)
                    self._save_cfg()
            return
        w = getattr(self, "_mcm_wait", None)
        if not w or w[0] != rid:
            return
        self._mcm_wait = None
        _, text, direction = w
        if self.cmd_var.get() != text:
            return
        head, sp, last = text.rpartition(" ")
        pre = head + sp
        cands = []
        for it in items:
            if not sp:
                it = it.lstrip("/")
                it = ("/" if text.startswith("/") else "") + it
                if ":" in it and ":" not in text:
                    continue
                cands.append(it)
            else:
                cands.append(pre + it)
        cands = sorted(set(c for c in cands if c.lower().startswith(text.lower())), key=str.lower)
        if not cands:
            cands = self._tab_local(text)
        if cands:
            self._tab_show(text, cands, direction)

    def _mcm_timeout(self, rid):
        w = getattr(self, "_mcm_wait", None)
        if w and w[0] == rid:
            self._mcm_wait = None
            self._mcm_ok = False
            cands = self._tab_local(w[1])
            if cands and self.cmd_var.get() == w[1]:
                self._tab_show(w[1], cands, w[2])

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
        self._tps_low_since = self._ram_hi_since = None
        self._cleanup_tmp()
        self._set_state("stopped")
        self.players.clear()
        self._refresh_players()
        for key in ("uptime", "pid", "cpu", "ram", "tps", "players"):
            self.sv[key].set("-")
        self.tab_beheer.close_all()
        if code not in (0, None) and not self._user_stop:
            self.tab_beheer.notify("notify_crash", "Server gestopt!", f"De server is onverwacht gestopt (exitcode {code}).")
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
        self.remote.push(e)
        self.desk.push(e)
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
            self._last_sent = (cmd, time.time())
            self.hist_idx = len(self.cmd_hist)
            self.cfg["cmd_history"] = list(dict.fromkeys(reversed(self.cmd_hist)))[::-1][-200:]
            self._save_cfg()
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

    def _learn_commands(self):
        """Vraagt de server stil om zijn commandolijst: eerst /help (lijst met plugins), dan /help <plugin> voor elk (daar staan de commando's)."""
        if self.srv_state != "online":
            return
        self._learn_topics, self._learn_dirty = [], False
        self._mcm_ok = False
        self._learn_until = time.time() + 6
        self._mcm_ask("c0")
        self.after(2500, self._learn_fallback)

    def _learn_fallback(self):
        if getattr(self, "_mcm_ok", False) or self.srv_state != "online":
            return
        self._learn_until = time.time() + 6
        self.srv_send("help", echo=False)
        self.after(2000, self._learn_topics_next)

    def _learn_topics_next(self, i=0):
        tops = self._learn_topics
        if self.srv_state != "online":
            return
        if i < len(tops) and i < 60:
            self._learn_until = time.time() + 3
            self.srv_send(f"help {tops[i]}", echo=False)
            self.after(350, lambda: self._learn_topics_next(i + 1))
            return
        if getattr(self, "_learn_dirty", False):
            self._save_cfg()
            self.log(f"{len(self.cfg.get('learned_cmds') or [])} commando's geleerd voor Tab-aanvulling.", "info")

    def _tab_local(self, text):
        cmds, plugs = self._plugin_cmds()
        cmds = set(cmds) | {x.lower() for x in plugs if re.fullmatch(r"[a-z0-9_\-]{2,30}", x.lower())} | set(self.cfg.get("learned_cmds") or [])
        return complete_command(text, sorted(set(VANILLA_CMDS) | cmds),
                                sorted(self.player_names, key=str.lower), plugs, [h for h in self.cmd_hist if h not in self._bad], cmds)

    def _tab_complete(self, direction=1):
        text = self.cmd_var.get()
        st = self._tab_state
        if st and text == st["cur"]:
            st["i"] = (st["i"] + direction) % len(st["cands"])
            return self._tab_apply(st)
        if getattr(self, "_mcm_ok", False) and self.srv_state == "online":
            self._mcm_seq = getattr(self, "_mcm_seq", 0) + 1
            rid = f"t{self._mcm_seq}"
            self._mcm_wait = (rid, text, direction)
            self._mcm_ask(rid, text[1:] if text.startswith("/") else text)
            self.after(1200, lambda: self._mcm_timeout(rid))
            return "break"
        cands = self._tab_local(text)
        if cands:
            self._tab_show(text, cands, direction)
        return "break"

    def _tab_show(self, text, cands, direction):
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
        return self._tab_apply(st)

    def _tab_apply(self, st):
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
                        sk.tick()
        except tk.TclError:
            pass
        self.after(50, self._spark_anim)

    def remote_apply(self):
        """Zet de telefoon-webserver aan of uit volgens de instellingen."""
        c = self.cfg
        if c.get("remote_enabled") and c.get("remote_pass"):
            if not self.remote.running or getattr(self, "_remote_port", None) != int(c.get("remote_port", 8765)):
                self._remote_port = int(c.get("remote_port", 8765))
                if self.remote.start(self._remote_port):
                    self.log(f"Telefoon-toegang aan op poort {self._remote_port}.", "ok")
                else:
                    self.log("Telefoon-toegang: " + self.remote.error, "warn")
        elif self.remote.running:
            self.remote.stop()
            self.log("Telefoon-toegang uitgezet.", "info")
        try:
            self.tab_beheer.refresh_remote()
        except Exception:
            pass

    def _heads_tick(self):
        try:
            self.heads.sync()
        except Exception:
            pass
        self.after(1000, self._heads_tick)

    def _remote_tick(self):
        self._rt = getattr(self, "_rt", 0) + 1
        for r in (self.remote, self.desk):
            if r.running:
                r.pump()
                if self._rt % 7 == 0:
                    r.update()
        self.after(100, self._remote_tick)

    def open_desk(self):
        """Opent de nieuwe interface in een eigen venster (alleen bereikbaar vanaf deze computer)."""
        if not self.desk.running and not (self.desk.start(8799, "127.0.0.1", True) or self.desk.start(0, "127.0.0.1", True)):
            messagebox.showerror(APP_NAME, "De nieuwe interface kon niet starten: " + self.desk.error)
            return False
        self.desk.update()
        open_app_window(f"http://127.0.0.1:{self.desk.port}/desk?t={self.desk.desk_token}")
        return True

    def _open_desk_main(self):
        if self.open_desk():
            self.iconify()     # het klassieke scherm blijft op de taakbalk; via "Klassiek scherm" in de nieuwe interface terug te halen

    def _upd_tab_blink(self):
        """Updates-tabje valt op (knippert + aantal) zodra er een plugin- of Paper-update is."""
        try:
            n = sum(1 for r in self.rows.values() if r.get("state") == "update")
            if str(self.paper_label.cget("text")).startswith("⬆"):
                n += 1
            if n:
                self._blink = not getattr(self, "_blink", False)
                txt = f"{'🔴' if self._blink else '🟠'}  Updates ({n})"
                main = f"{'🔴' if self._blink else '🟠'}  Plugins ({n})"
            else:
                txt, main = "🔧  Updates", "🧩  Plugins"
            if txt != getattr(self, "_upd_txt", None):
                self._upd_txt = txt
                self.tab_plug.sub.tab(self.tab_upd, text=txt)
                self.nb.tab(self.tab_plug, text=main)
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
            if cur == str(self.tab_backup):
                self.tab_backup.on_show()
            if cur == str(self.tab_beheer):
                self.tab_beheer.on_show()
            else:
                self.tab_beheer.on_hide()
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
        if self.tab_map.gen["state"] in ("running", "paused") and self.tab_map.on_chunky(msg):
            suppress = True
        ls = getattr(self, "_last_sent", None)
        if ls and now - ls[1] < 3 and ("Incorrect argument for command" in msg or "Unknown or incomplete command" in msg or "Unknown command" in msg):
            # een fout commando blijft wel met pijltje-omhoog terug te halen (om te verbeteren), maar komt niet in de Tab-aanvulling
            self._bad.add(ls[0])
            self._last_sent = None
        mm = re.search(r"MCMTAB\|(\w+)\|(.*)$", msg)
        if mm:
            suppress = True
            self._mcm_reply(mm.group(1), mm.group(2))
        if now < self._learn_until and ("Unknown or incomplete command" in msg or "<--[HERE]" in msg or "Unknown command" in msg):
            suppress = True
        if now < self._learn_until:
            lc = re.match(r"^/([A-Za-z0-9_:.\-]{1,40}):", msg)
            tp = re.match(r"^([A-Za-z0-9_.\-]{1,40}): (All commands for |[A-Z])", msg)
            if tp:
                suppress = True
                if tp.group(1) not in self._learn_topics:
                    self._learn_topics.append(tp.group(1))
            elif lc or re.match(r"^-{3,}\s*Help:", msg) or re.match(r"^Below is a list of all .* commands:", msg) or msg.startswith("Help:") or msg.startswith("Use /help"):
                suppress = True
                if lc:
                    nm = lc.group(1).split(":")[-1].lower()
                    cur = self.cfg.setdefault("learned_cmds", [])
                    if nm and nm not in cur and len(cur) < 3000:
                        cur.append(nm)
                        self._learn_dirty = True
        gm = re.search(r"Started Geyser on (?:UDP )?port (\d+)", msg)
        if gm and gm.group(1).isdigit() and 0 < int(gm.group(1)) < 65536:
            if int(gm.group(1)) != int_var(self.reach_bport_var, 19132):
                self.reach_bport_var.set(int(gm.group(1)))
                self.log(f"Geyser luistert op UDP-poort {gm.group(1)}: Bedrock-poort bij Bereikbaarheid aangepast.", "info")
        jm = JOIN_RE.match(msg)
        if jm:
            self.tab_beheer.event("join", jm.group(1))
            self.tab_beheer.notify("notify_join", "Speler online", f"{jm.group(1)} is binnengekomen.", jm.group(1))
            self.players.setdefault(jm.group(1), now)
            self._add_name(jm.group(1))
            self._refresh_players()
            self.tab_map.players_changed(jm.group(1))
        lv = LEAVE_RE.match(msg)
        if lv:
            self.tab_beheer.event("leave", lv.group(1))
            self.tab_beheer.notify("notify_leave", "Speler weg", f"{lv.group(1)} heeft de server verlaten.", lv.group(1))
            self.players.pop(lv.group(1), None)
            self._refresh_players()
            self.tab_map.players_changed()
        if DONE_RE.search(msg) and self.srv_state == "starting":
            self.tab_beheer.notify("notify_start", "Server is online", "De Minecraft-server is klaar met opstarten.")
            self._set_state("online")
            self._idle_since = time.time()
            self.after(30000, self.tab_map.prewarm)   # squaremap is dan klaar: kaart alvast laden
            self.after(12000, self._learn_commands)
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
        self._health_tps_check(tps)

    def _auto_poll(self):
        self._last_poll = time.time()
        until = self._last_poll + 4
        self._sup = {"list": until, "tps": until, "any": until}
        self.srv_send("list", echo=False)
        self.srv_send("tps", echo=False)

    # ---------- spelers ----------
    def _refresh_players(self):
        tree = self.ptree
        now = time.time()
        names = sorted(self.players, key=str.lower)
        for iid in tree.get_children():          # alleen wat weg is verwijderen: bestaande rijen blijven staan (geen geknipper van de kop)
            if iid not in self.players:
                tree.delete(iid)
        for i, name in enumerate(names):
            kind = "Bedrock" if name.startswith(".") else "Java"
            vals = (name, kind, fmt_dur(now - self.players[name])[-8:])
            if tree.exists(name):
                if tuple(str(v) for v in tree.item(name, "values")) != vals:
                    tree.item(name, values=vals)
                if tree.index(name) != i:
                    tree.move(name, "", i)
            else:
                try:
                    im = self.heads.photo(name, kind)
                except Exception:
                    im = None
                tree.insert("", i, iid=name, values=vals, **({"image": im} if im is not None else {}))
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

    def player_ban(self):
        sel = self.ptree.selection()
        if sel:
            reason = simpledialog.askstring(APP_NAME, f"Reden voor het bannen van {sel[0]}:", parent=self)
            if reason is not None:
                self.srv_send(f"ban {sel[0]} {reason}".strip())

    def _player_cmd(self, tpl):
        sel = self.ptree.selection()
        if sel:
            self.srv_send(tpl.format(sel[0]))

    def open_lists(self):
        if not self._need_folder():
            return
        d = getattr(self, "_lists_dlg", None)
        if d is not None:
            try:
                if d.winfo_exists():
                    d.lift()
                    d.reload()
                    return
            except tk.TclError:
                pass
        self._lists_dlg = ListsDialog(self)

    def open_logsearch(self):
        if not self._need_folder():
            return
        d = getattr(self, "_logs_dlg", None)
        if d is not None:
            try:
                if d.winfo_exists():
                    d.lift()
                    return
            except tk.TclError:
                pass
        self._logs_dlg = LogSearchDialog(self)

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
            for sk in (self.spark_cpu, self.spark_ram, self.spark_tps):   # server uit of in slaapstand: de lijn zakt gewoon naar 0
                sk.add(0)
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
            self._health_ram_check(ram)
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
        ttk.Label(a, text="Test of vrienden via internet kunnen verbinden. Vul je publieke IP-adres of domeinnaam in "
                          "(of klik op 'Mijn IP opzoeken') en klik op 'Controleer van buitenaf'.",
                  style="Muted.TLabel", wraplength=900, justify="left").grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
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
        self._upd_hot = self._hot_ok(info)
        self.btn_selfupd.config(text=f"⬆  Update {info['version']}" + ("  (zonder herstart)" if self._upd_hot else ""))
        self.btn_selfupd.pack(side="right", padx=(0, 6), pady=10)
        self.log(f"Nieuwe versie van het programma beschikbaar: {info['version']} (jij hebt {APP_VERSION}).", "warn")
        if getattr(self, "_upd_notified", None) != info["version"]:
            self._upd_notified = info["version"]
            self.tab_beheer.notify("notify_update", "Update beschikbaar", f"MC Server Manager {info['version']} is beschikbaar.")
        if self.cfg.get("selfupdate_auto") and not manual:
            self.selfupdate_install()
        elif manual or self._upd_prompted != info["version"]:
            self._selfupd_ask()

    def _hot_ok(self, info):
        """Kan deze update zonder herstart? (alleen als het .py-bestand draait en de code-vergelijking dat toestaat)"""
        if getattr(sys, "frozen", False) or not getattr(self, "_src", None):
            return False
        try:
            ok, why = hot_check(self._src, info["text"])
        except Exception as e:  # noqa
            ok, why = False, str(e)
        self._hot_why = why
        return ok

    def _selfupd_ask(self):
        info = self._upd
        if not info:
            return
        self._upd_prompted = info["version"]
        notes = changelog_since(info["text"], APP_VERSION)
        hot = getattr(self, "_upd_hot", False)
        tail = ("Deze update kan direct worden toegepast, zonder herstart. De server blijft gewoon draaien.\n\n" if hot else
                "Voor deze update moet het programma herstarten" + (f" ({getattr(self, '_hot_why', '')})" if getattr(self, "_hot_why", "") else "") +
                ". De server wordt dan eerst veilig gestopt.\n\n" if self.srv_running() else "")
        if messagebox.askyesno(APP_NAME, f"Nieuwe versie {info['version']} beschikbaar (jij hebt {APP_VERSION}).\n\n"
                                         + (notes + "\n\n" if notes else "") + tail + "Nu installeren?"):
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
        if getattr(self, "_upd_hot", False) and self._src:
            try:
                stale = hot_apply(info["text"], self._src)
                self._src = info["text"]
                self.title(f"{APP_NAME} {APP_VERSION}")
                self.log(f"Versie {APP_VERSION} is direct toegepast, zonder herstart." + (
                    f" ({stale} onderdelen werken pas na een herstart.)" if stale else ""), "ok")
                messagebox.showinfo(APP_NAME, f"Versie {APP_VERSION} is toegepast, zonder herstart.\n\n"
                                              + (f"Wat is er nieuw:\n{notes}\n\n" if notes else "")
                                              + "De server is niet gestopt.")
                return
            except Exception as e:  # noqa
                self.log(f"Direct toepassen mislukt ({e}); herstart het programma om de nieuwe versie te gebruiken.", "warn")
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
        self._wake_stop()
        self._cleanup_tmp()
        self._graphs_save()
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
                    self.row(fn, name, cur or "?", latest_txt, src, "✔ Up-to-date", "ok")
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
                     "reach_bedrock_port", "reach_auto", "plm_load", "plm_ack", "plugins_only_compat", "squaremap_url",
                     "notify_crash", "notify_start", "notify_join", "notify_leave", "notify_chunky", "notify_update", "notify_ignore",
                     "chunky_autopause", "chunky_autoresume", "remote_enabled", "remote_port", "remote_pass", "remote_lan_only",
                     "cmd_history", "learned_cmds", "pil_asked", "mcmtab_done", "sleep_days", "sleep_stats"):
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
        self._tab_gedrag(nb)
        self._tab_server(nb)
        self._tab_beheer(nb)
        self._tab_updates(nb)
        self._tab_backups(nb)
        self._tab_health(nb)
        self._tab_grafiek(nb)
        self._tab_console(nb)
        self._tab_update(nb)

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
        try:
            self._update_info()
        except Exception:
            self.info_lbl.config(text="")

    def _tab_updates(self, nb):
        f = self._frame(nb, "Zoeken naar updates")
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
        f = self._frame(nb, "Starten & Java")
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
        self._sep(f, 12)
        self._check(f, "😴  Slaapstand: server stoppen als er niemand online is, en weer starten zodra iemand probeert te joinen",
                    self.v["sleep_enabled"], 13)
        self._spin(f, "Slapen na:", "sleep_minutes", 14, 1, 600, "minuten zonder spelers")
        self._hint(f, "Tijdens de slaapstand luistert dit programma op de serverpoort; in de serverlijst staat dan 'Server slaapt'. "
                      "De speler die probeert te joinen krijgt de melding dat de server start en kan het na ongeveer een minuut opnieuw proberen. "
                      "Niet tijdens het genereren van de kaart.", 15)
        self._check(f, "Slaapstand alleen op bepaalde tijden toestaan", self.v["sleep_sched"], 16)
        rf = ttk.Frame(f)
        rf.grid(row=17, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(rf, text="Van").pack(side="left")
        ttk.Entry(rf, textvariable=self.v["sleep_from"], width=6).pack(side="left", padx=4)
        ttk.Label(rf, text="tot").pack(side="left")
        ttk.Entry(rf, textvariable=self.v["sleep_to"], width=6).pack(side="left", padx=4)
        ttk.Label(rf, text="uur   op:").pack(side="left", padx=(6, 4))
        days = str(self.app.cfg.get("sleep_days", "1234567"))
        self.sleep_day_vars = {}
        for i, nm in enumerate(("ma", "di", "wo", "do", "vr", "za", "zo"), 1):
            self.sleep_day_vars[str(i)] = tk.BooleanVar(value=str(i) in days)
            ttk.Checkbutton(rf, text=nm, variable=self.sleep_day_vars[str(i)]).pack(side="left")
        self._hint(f, "Buiten deze tijden blijft de server altijd aan. Een tijdvak over middernacht (22:00 tot 08:00) mag.", 18)

    def _pick_java(self):
        f = filedialog.askopenfilename(parent=self, title="Kies java.exe",
                                       filetypes=[("Java", "java.exe javaw.exe"), ("Alle bestanden", "*.*")])
        if f:
            self.v["java_path"].set(os.path.normpath(f))

    def _tab_health(self, nb):
        f = self._frame(nb, "Gezondheid")
        ttk.Label(f, text="Het programma waarschuwt (logboek en Windows-melding) als er iets mis dreigt te gaan.",
                  foreground="#6b7280").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self._check(f, "Waarschuw als de schijf bijna vol is", self.v["health_disk"], 1)
        self._spin(f, "Waarschuwen onder:", "health_disk_gb", 2, 1, 5000, "GB vrije ruimte")
        self._sep(f, 3)
        self._check(f, "Waarschuw als de server te traag loopt (lage TPS)", self.v["health_tps"], 4)
        self._spin(f, "TPS onder:", "health_tps_min", 5, 1, 19, "(20 is normaal)")
        self._spin(f, "Gedurende minstens:", "health_tps_mins", 6, 1, 120, "minuten")
        self._sep(f, 7)
        self._check(f, "Waarschuw als het geheugen bijna op is", self.v["health_ram"], 8)
        self._spin(f, "Geheugen boven:", "health_ram_pct", 9, 50, 100, "% van Max. RAM, gedurende 3 minuten")
        self._hint(f, "Dezelfde waarschuwing komt hooguit één keer per half uur.", 10)

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
        f = self._frame(nb, "Dit programma")
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
        f = self._frame(nb, "Algemeen")
        self._check(f, "Vraag bevestiging voor updates en het starten van de server", self.v["confirm"], 0)
        self._check(f, "Speel een geluidje af als een taak klaar is", self.v["sound"], 1)
        self._check(f, "Venster altijd bovenop andere vensters", self.v["topmost"], 2)
        self._check(f, "Compacte lijst (kleinere rijen, meer plugins in beeld)", self.v["compact"], 3)
        self._check(f, "Donker thema (het programma herstart na het opslaan)", self.v["dark_mode"], 4)
        self._check(f, "Log bewaren in bestand (mc_server_manager.log naast het programma)", self.v["log_to_file"], 5)
        self._hint(f, "Tip: met F5 start je een controle op alles.", 6)

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
        old_dark = bool(c.get("dark_mode"))
        for k, var in self.v.items():
            try:
                c[k] = var.get()
            except tk.TclError:
                c[k] = DEFAULTS[k]
        c["server_backups_max"] = min(max(int(c["server_backups_max"]), 1), 999)
        c["plugin_backups_max"] = min(max(int(c["plugin_backups_max"]), 1), 999)
        c["net_timeout"] = min(max(int(c["net_timeout"]), 5), 180)
        c["sleep_minutes"] = min(max(int(c["sleep_minutes"]), 1), 600)
        for k, dflt in (("sleep_from", "22:00"), ("sleep_to", "08:00")):
            m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*", str(c[k]))
            c[k] = f"{int(m.group(1)):02d}:{m.group(2)}" if m and int(m.group(1)) < 24 and int(m.group(2)) < 60 else dflt
        c["sleep_days"] = "".join(d for d, v in getattr(self, "sleep_day_vars", {}).items() if v.get()) or "1234567"
        c["health_disk_gb"] = min(max(int(c["health_disk_gb"]), 1), 5000)
        c["health_tps_min"] = min(max(int(c["health_tps_min"]), 1), 19)
        c["health_tps_mins"] = min(max(int(c["health_tps_mins"]), 1), 120)
        c["health_ram_pct"] = min(max(int(c["health_ram_pct"]), 50), 100)
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
        if bool(c.get("dark_mode")) != old_dark:
            if messagebox.askyesno(APP_NAME, "Het thema verandert na een herstart van het programma.\n\nNu herstarten?"):
                app._restart_self()


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
