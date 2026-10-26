<div align="center">

# ⛏ MC Server Manager

**Eén venster om je eigen Minecraft-server (Paper) te beheren.**
Starten, console, plugins, updates, kaart, backups en een webapp voor je telefoon, zonder losse programma's of commando's.

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776ab?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078d6?logo=windows&logoColor=white)
![Eén bestand](https://img.shields.io/badge/installatie-één%20bestand-059669)

<img src="docs/donker_server.png" alt="Server-tabblad met grafieken, spelerslijst en console (donker thema)" width="860">

</div>

---

## Inhoud
[Functies](#functies) · [Installeren](#installeren) · [Eerste keer](#eerste-keer-gebruiken) · [Tab-aanvulling](#tab-aanvulling-in-de-console) · [Telefoon](#webapp-voor-je-telefoon) · [Bijwerken](#het-programma-bijwerken) · [Veelgestelde vragen](#veelgestelde-vragen) · [Privacy](#privacy-en-netwerk) · [Versies](#versies)

## Functies

| Tabblad | Wat je ermee doet |
|---|---|
| **🖥 Server** | Starten, stoppen, herstarten, RAM aanpassen. Console met schone modus, zoeken, Tab-aanvulling en commandogeschiedenis. Live CPU, geheugen, TPS en temperatuur (de grafieken blijven bewaard na een herstart). Spelerslijst met hoofdjes, ook van Bedrock-spelers. |
| **🧩 Plugins** | Aan- en uitzetten, verwijderen, zoeken op naam *of op beschrijving* en installeren, inclusief afhankelijkheden. Per plugin zie je meteen of hij up-to-date is. |
| **🗺 Kaart** | Live kaart van je wereld (via [squaremap](https://github.com/jpenilla/squaremap)) met spelers, soepel zoomen en je ziet ook de opgeslagen kaart als de server uit staat. Teken een gebied om het met Chunky vooraf te genereren; dat pauzeert zelf zodra er een speler binnenkomt. |
| **🛠 Beheer** | Spelers (speeltijd, laatst gezien, doden, afgelegde afstand), meldingen, tuning, de wereld en de telefoon-webapp. |
| **💾 Backups** | Beheert de plugin [Backuper](https://github.com/DVDishka/Backuper): backups bekijken en verwijderen, instellingen aanpassen, bestanden van de plugin, en de backups die dit programma zelf maakt. |
| **🔧 Updates** | Paper (`server.jar`) en plugins controleren en bijwerken via Modrinth, Hangar, GitHub en GeyserMC. Vóór elke update komt er een backup; het aantal stel je zelf in. |
| **🌐 Netwerk** | Controleert of vrienden via internet kunnen verbinden (Java en Bedrock), met servernaam, icoon en spelers. |

<p align="center">
  <img src="docs/licht_plugins.png" alt="Plugins-tabblad (licht thema)" width="48%">
  <img src="docs/licht_backups.png" alt="Backups-tabblad (licht thema)" width="48%">
</p>

**✨ Nieuwe interface:** de knop bovenin opent een moderner scherm (eigen venster) met Overzicht, Console, Spelers, Plugins, Kaart, Backups en Instellingen. Het is alleen bereikbaar vanaf deze computer; de bron staat in [`nieuwe_interface/`](nieuwe_interface/).

Verder: licht en donker thema, een Update-knop voor het programma zelf (zonder herstart als dat veilig kan),
meldingen bij crash, start, spelers en klaar met genereren, en alles in het Nederlands.

## Installeren

1. Installeer [Python 3.8 of nieuwer](https://www.python.org/downloads/) en vink **"Add Python to PATH"** aan.
2. Download [`mc_server_manager.py`](mc_server_manager.py) en zet het in een eigen map.
3. Dubbelklik op het bestand (of `python mc_server_manager.py`).
4. Kies bovenaan je server-map. Klaar.

De instellingen staan naast het programma in `mc_server_manager_config.json`.

**Optioneel** (het programma vraagt er zelf naar wanneer ze nuttig zijn):

| Pakket | Waarvoor | Installeren |
|---|---|---|
| `psutil` | CPU en geheugen in de grafieken | `pip install psutil` |
| `pillow` | Vloeiend zoomen op de kaart | `pip install pillow` |

Liever een `.exe`? `pip install pyinstaller` en dan
`pyinstaller --onefile --windowed --name MCServerManager mc_server_manager.py`.
Een `.exe` kan zichzelf niet bijwerken.

## Eerste keer gebruiken

1. **Server-map kiezen** (Plugins › Updates, bovenaan). Het programma herkent Paper, de Minecraft-versie en je plugins.
2. **Server starten** met de groene knop. De console toont wat de server meldt.
3. **Plugins en updates:** klik op *Alles controleren* bij Updates. Dat kost niets, er wordt pas iets veranderd als jij dat vraagt.
4. Het tabblad **Netwerk** is handig om te testen of vrienden kunnen verbinden.

Staat er een knop of instelling die je niet snapt? Bij de meeste opties in Instellingen (rechtsboven) staat een korte uitleg.

## Tab-aanvulling in de console

Net als in de echte serverconsole: typ een deel van een commando en druk op **Tab**; **↑/↓** haalt eerdere
commando's terug. Zonder extra hulp leert het programma de commando's uit `/help`. Voor *exact* dezelfde
aanvullingen als de server (alle subcommando's en argumenten van plugins) plaatst het programma bij het eerste
starten het kleine hulpplugin **MCMTab** in `plugins/`. Herstart de server daarna één keer.

De broncode en uitleg staan in [`hulpplugin/`](hulpplugin/). Het plugin doet niets anders dan op verzoek van de
console de aanvullingen doorgeven.

## Webapp voor je telefoon

Zet bij **Beheer → Telefoon** de webapp aan en kies een wachtwoord. Open daarna het getoonde adres op je telefoon
(zelfde wifi) en voeg het toe aan je beginscherm. Je ziet en bedient dezelfde dingen als op de computer:
server, plugins, updates, kaart, backups en beheer. De app is standaard alleen bereikbaar vanaf je eigen netwerk.

## Het programma bijwerken

Open Instellingen → **Dit programma** en vul `https://github.com/smikkelvriend/mc-server-manager` in.
Het programma controleert bij het opstarten en daarna elke 6 uur. Is er een nieuwe versie, dan verschijnt
**⬆ Update** met wat er nieuw is. Veilige updates worden direct toegepast; de rest vraagt om een herstart.
De vorige versie wordt bewaard in `programma_backups`.

Alleen `mc_server_manager.py` in de hoofdmap telt mee en wordt eerst gecontroleerd op geldige Python en een hoger
versienummer. Gebruik alleen een repository die je vertrouwt: wie die beheert, bepaalt welke code er draait.

## Veelgestelde vragen

<details><summary><b>De kaart zegt "Squaremap niet bereikbaar"</b></summary>

Het programma kan de webserver van squaremap niet bereiken. Controleer dat de plugin draait en dat het adres onder
het tabblad Kaart klopt (standaard `http://localhost:8080`). Zolang de server uit staat toont het programma de
laatst opgeslagen kaart.
</details>

<details><summary><b>CPU en geheugen blijven leeg</b></summary>

Installeer `psutil` (`pip install psutil`) of klik op de knop op het Server-tabblad.
</details>

<details><summary><b>Wat doet het programma met mijn server-map?</b></summary>

Het leest je configuratie en logs, en schrijft alleen als jij iets doet (starten, een plugin installeren of
verwijderen, een update). Bij updates wordt eerst een backup gemaakt en verwijderde plugins worden eerst verplaatst.
</details>

<details><summary><b>De temperatuur klopt niet</b></summary>

Zonder extra software leest het programma de thermal zone van Windows. Niet elke laptop levert die, en het is niet
altijd de CPU-temperatuur. Voor de echte waarde: laat
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) als beheerder openstaan.
</details>

## Privacy en netwerk

Het programma praat alleen met de diensten die bij een functie horen en stuurt niets door naar de maker.

| Functie | Dienst |
|---|---|
| Updates zoeken | Modrinth, Hangar, GitHub, GeyserMC, PaperMC |
| Netwerkcontrole van buitenaf | mcstatus.io, mcsrvstat.us, minetools.eu; `api.ipify.org` voor "Mijn IP opzoeken" |
| Spelershoofdjes | mc-heads.net; Bedrock-spelers via api.geysermc.org en textures.minecraft.net |
| Programma-update | je eigen GitHub-repository |

Die diensten bewaren soms een oud resultaat; één dienst die "online" meldt is genoeg.

## Versies

Zie [CHANGELOG.md](CHANGELOG.md) voor wat er per versie nieuw is. Oude versies staan in
[`oude_versies/`](oude_versies/).

## Meewerken

Een bug gevonden of een idee? Open een [issue](../../issues). Vermeld je versie (staat in de titelbalk) en wat je
deed vlak voor het misging.
