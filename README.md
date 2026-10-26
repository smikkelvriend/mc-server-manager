# MC Server Manager

Een Windows-programma (één Python-bestand) om je eigen Minecraft-server (Paper, met eventueel Geyser/Floodgate)
te beheren, zonder meerdere vensters of commando's.

## Wat kan het?
- **Server:** starten, stoppen, herstarten en afsluiten, met console (met schone modus en commando's),
  CPU/geheugen/TPS, spelerslijst, RAM aanpassen, grafieken en de temperatuur van je laptop.
- **Plugins:** beheren (aan/uit/verwijderen) en zoeken op naam of beschrijving, met installeren inclusief afhankelijkheden.
- **Kaart:** wereldkaart met alle spelers live erop (naam, richting, spoor, coördinaten), zonder extra plugin.
  Optioneel direct laden met `/plm load` (op eigen risico).
- **Updates:** plugins controleren en bijwerken via Modrinth (met Hangar, GitHub en GeyserMC als reserve) en
  `server.jar` via PaperMC. Back-ups worden bewaard, het aantal stel je zelf in.
- **Bereikbaarheid:** controleert of je server van buitenaf bereikbaar is, voor Java en Bedrock (Geyser),
  met servernaam, icoon en spelers.
- **Instellingen:** één venster (⚙) voor back-ups, gedrag, console, grafieken en updates.

## Installeren
1. Installeer [Python 3.8 of nieuwer](https://www.python.org/downloads/) (vink "Add Python to PATH" aan).
2. Download `mc_server_manager.py` en zet het in een eigen map.
3. Optioneel, voor CPU en geheugen: `pip install psutil`.
4. Dubbelklik op het bestand, of start het met `python mc_server_manager.py`.
5. Kies bovenaan je server-map. Instellingen worden naast het programma opgeslagen in
   `mc_server_manager_config.json`.

Wil je een `.exe`? `pip install pyinstaller` en dan
`pyinstaller --onefile --windowed --name MCServerManager mc_server_manager.py`.
Een `.exe` kan zichzelf niet automatisch bijwerken.

## Automatisch bijwerken
Open Instellingen → **Programma-update** en vul `https://github.com/smikkelvriend/mc-server-manager` in.
Het programma controleert bij het opstarten en daarna elke 6 uur. Is er een nieuwere versie, dan verschijnt de knop
**⬆ Update** met wat er nieuw is. Daarna wordt het bestand vervangen, de vorige versie komt in `programma_backups`
en het programma herstart op jouw verzoek.

Alleen `mc_server_manager.py` in de hoofdmap telt mee. Een versie wordt alleen geïnstalleerd als het geldige
Python is met een hoger versienummer. Gebruik alleen een link van een repository die je zelf vertrouwt, want wie die
beheert bepaalt welke code er draait.

## Temperatuur
Zonder extra software leest het programma de thermal zone van Windows. Niet elke laptop levert die, en het is niet
altijd de CPU-temperatuur. Voor de echte CPU-temperatuur: laat
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) als beheerder openstaan.

## Bereikbaarheid
De controle van buitenaf gebruikt mcstatus.io, mcsrvstat.us en minetools.eu, en api.ipify.org voor "Mijn IP opzoeken".
Die diensten bewaren soms een oud resultaat; één dienst die "online" meldt is genoeg.

## Versies
Zie [CHANGELOG.md](CHANGELOG.md). Oude versies staan in [`oude_versies/`](oude_versies/).
