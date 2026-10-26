# Changelog

De nieuwste versie staat bovenaan. De oude bestanden staan in [`oude_versies/`](oude_versies/).

## 2.3.1
- Programma-update haalt het bestand op via de exacte laatste commit van GitHub, zodat een oude cache de update niet kan
  verbergen.

## 2.3
- **Bedrock-controle met uitleg:** meldt de externe controle "offline", dan pingt het programma Geyser zelf (UDP), lokaal en
  via je domein, en toont wat elke controledienst zei. Zo zie je of Geyser draait en of alleen de poortdoorsturing ontbreekt.

## 2.2
- **Temperatuur van de laptop** op het Server-tabblad, met eigen grafiek en waarschuwing (standaard vanaf 85 °C).
  Leest Windows' thermal zone of, als die draait, LibreHardwareMonitor / OpenHardwareMonitor.
  Instellingen: aan/uit, meetinterval en waarschuwingsgrens.
- **Automatische programma-update** via een GitHub-link (Instellingen → Programma-update): controle bij het opstarten
  en elke 6 uur, knop "⬆ Update", changelog vooraf, back-up van de vorige versie in `programma_backups`.
- **Bereikbaarheid sneller en betrouwbaarder:** vraagt tegelijk mcstatus.io, mcsrvstat.us en minetools.eu
  (één "online" is genoeg), probeert een domein ook via het achterliggende IP en controleert of je domein naar je
  huidige publieke IP wijst. Geen vaste melding over 5 minuten cache meer.

## 2.1
- Nieuw tabblad **Bereikbaarheid**: controleert of je server van buitenaf bereikbaar is (Java en Bedrock/Geyser),
  met servernaam, icoon, versie en spelersaantal.
- Tabbladen Server en Updates omgewisseld: Server staat nu vooraan.
- Speleracties (joinen, leaven, chat, commando's, doodgaan) zijn altijd zichtbaar in de schone console.
- Twee opstartregels (versie/Paper-versie) niet meer in de schone console; de knoppen "list" en "tps" weg.
- Standaard 3 server.jar-back-ups en 3 plugin-rondes.

## 2.0
- Nieuwe naam: **MC Server Manager** (het is meer dan een updater).
- Schone console is veel strenger: bij het opstarten alleen belangrijke berichten, niet de hele reeks gewone regels.

## 1.3
- TPS klopte niet door een decimale komma ("19,9") — opgelost.
- Grafieken hebben een instelbaar tijdvenster en auto-zoom, zodat ze beter bewegen.
- Maximale RAM van de server aanpassen vanuit het programma (`-Xmx`/`-Xms` in je startbestand of Java-instellingen,
  met back-up van het origineel).

## 1.2
- **Server-tabblad:** server starten, stoppen, herstarten en afsluiten als proces van het programma.
- Console met commando's en een "schone console" die overbodige regels verbergt (aan/uit).
- Statistieken (CPU, geheugen, uptime, TPS), grafieken en een lijst met spelers.

## 1.1
- Floodgate werd ten onrechte als update gemeld: "update" wordt nu alleen gemeld als de nieuwere versie met bewijs
  vergelijkbaar is; anders staat er "Versie niet vergelijkbaar".
- GeyserMC-downloads als extra bron voor Geyser en Floodgate.

## 1.0
- Plugins controleren en bijwerken via Modrinth, met Hangar en GitHub als reserve.
- `server.jar` controleren en bijwerken via PaperMC.
- Instellingenpagina (o.a. back-ups van server.jar bewaren en hoeveel).
