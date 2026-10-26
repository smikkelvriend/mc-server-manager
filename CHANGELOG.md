# Changelog

De nieuwste versie staat bovenaan. De oude bestanden staan in [`oude_versies/`](oude_versies/).

## 2.8.9
- Kaart: chunks die wel bestaan maar helemaal leeg zijn (geen enkel blok, bijvoorbeeld een leegte) worden nu als vlak, iets lichter dan de achtergrond getoond. Zo zie je het verschil tussen 'nooit gegenereerd' en 'leeg'.

## 2.8.8
- Kaart begint nu gecentreerd op de spawn van je wereld (met de wereld uit level.dat) in plaats van op 0,0. Is de spawn onbekend, dan het midden van het getekende gebied.

## 2.8.7
- Kaart-diagnose: bij het aanwijzen van een regio zie je nu de reden waarom chunks niet getekend worden (bijv. oud wereldformaat) en welke wereldmap gebruikt wordt.

## 2.8.6
- Kaart laadt bij het opstarten veel sneller: de bewaarde kaart wordt nu als PNG opgeslagen en direct door Tk geladen. De eerste keer na deze update wordt de kaart nog één keer opnieuw opgebouwd.

## 2.8.5
- Kaart: in- en uitzoomen haperde even. Nu worden de plaatjes voor het volgende en vorige zoomniveau alvast op de achtergrond klaargemaakt en wordt het terrein van het midden naar buiten getekend in kleine happen.

## 2.8.4
- Het zwarte consolevenster dat naast het programma openstond wordt nu automatisch verborgen (en bij herstarten niet meer opnieuw geopend).
- Kaart: als je met de muis boven een regio staat zie je onderaan hoeveel chunks onleesbaar zijn of nog niet klaar, handig om te zien waarom een stuk leeg blijft.

## 2.8.3
- Updatemelding sneller: het programma controleert elke 5 minuten op een nieuwe versie (was elke 6 uur), en ook zodra je terugkeert naar het venster. Er komt maar één melding per nieuwe versie.

## 2.8.2
- **Kaart veel sneller:** slepen verschuift het beeld in één keer, bij nieuwe spelerposities wordt alleen de spelerslaag opnieuw getekend en het inladen van veel regio's blokkeert het venster niet meer.
- **Fout opgelost:** bij veel zichtbare regio's verdwenen stukken van de kaart (en op een ander zoomniveau weer andere stukken), doordat plaatjes te vroeg werden weggegooid.

## 2.8.1
- Temperatuur: ondersteunt ook LibreHardwareMonitor via de ingebouwde webserver (poort 8085), omdat nieuwere versies geen WMI meer aanbieden.

## 2.8
- **Kaart wordt bewaard** (map `map_cache` naast het programma) en staat bij het openen direct klaar.
- De kaart wordt elke paar minuten stil op de achtergrond bijgewerkt (alleen regio's die de server opnieuw heeft opgeslagen), ook als het tabblad dicht is, met weinig processorgebruik.

## 2.7.1
- Plugin-lijst opgeruimd: geen bestandsnaam, commando's of grootte meer, kleinere tellers en kleinere tabbladen.

## 2.7
- **Nieuw tabblad Kaart:** terrein van je wereld (Overworld, Nether, End) uit de opgeslagen wereldbestanden, met alle spelers live erop:
  gekleurde stip, naam, kijkrichting en een spoor van waar ze langs liepen. Slepen om te verschuiven, muiswiel om te zoomen,
  raster met coordinaten, wereldrand en spawn, lijst met X/Y/Z per speler (dubbelklik = ernaartoe, of volg een speler).
- Posities komen uit de server zelf (`data get entity`), dus geen extra plugin nodig; ze worden alleen opgevraagd zolang het tabblad open is.
- Terrein wordt na een autosave van de server ververst; met de knop Kaart opnieuw inlezen kan het ook handmatig.

## 2.6.1
- Scrollen met het muiswiel of de touchpad werkt nu in de hele plugin-lijst, ook als de muis boven een kaart of knop staat.

## 2.6
- **Plugins-tabblad in kaartvorm:** teller-tegels bovenaan (totaal, aan, uit, aandacht), per plugin een kaart met status, versie,
  omschrijving, afhankelijkheden en eigen aan/uit-knop, plus filter op naam, filter op status en sortering.
- Zoekresultaten ook als kaarten, met badges (beste match, past bij jouw Minecraft-versie, geïnstalleerd), de reden waarom het
  past, een eigen installeerknop en sortering op relevantie, downloads, datum, naam of Minecraft-versie.

## 2.5
- **Compatibiliteitsfilter** bij Plugins zoeken: met het vinkje "Alleen plugins die zeker werken met mijn Minecraft-versie" blijven
  alleen plugins over die een versie voor jouw Minecraft-versie hebben. Bij Modrinth gebeurt dat al bij het zoeken (er komen dus
  meer passende resultaten, niet minder); bij Hangar vraagt het programma voor de beste resultaten apart na. De kolom
  "Jouw MC-versie" is nu ook voor Hangar-resultaten ingevuld. Het vinkje wordt onthouden.

## 2.4.2
- Resultaten en geïnstalleerde plugins zijn te sorteren door op een kolomnaam te klikken (nogmaals klikken draait om).
  "Relevantie" zet de slimme volgorde terug.

## 2.4.1
- Zoeken: woorden die Modrinth niet kent (zoals "waardoor", "omhakken", "1x") blokkeerden alle resultaten. Die laat het programma nu
  weg zodra de rest vertaald kan worden, en korte Engelse zoekopdrachten worden altijd erbij gedaan.
- Nieuw onderwerp "bomen omhakken" (tree feller / timber); "farmen / oogsten" is apart gezet.

## 2.4
- **Nieuw tabblad Plugins.**
  - *Geïnstalleerd:* alle plugins in één lijst, aan en uit te zetten (een uitgezette plugin krijgt de extensie `.jar.disabled`,
    die Paper negeert), te verwijderen (naar een map in de back-ups, dus terug te zetten), met waarschuwing als een andere plugin
    de plugin nodig heeft of er een afhankelijkheid mist. Omschrijving, auteur, commando's en afhankelijkheden zijn te zien.
  - *Zoeken en toevoegen:* zoek op naam ("worldedit") of beschrijf wat je zoekt ("als 1 speler slaapt wordt het dag"), in het
    Nederlands of Engels. Het programma herkent ruim 45 onderwerpen, zoekt tegelijk op Modrinth en Hangar, voegt de resultaten
    samen en rangschikt ze op naam, beschrijving, populariteit, recente updates en of ze jouw Minecraft-versie ondersteunen.
    Een exacte naam komt altijd bovenaan. Installeren downloadt met controle van de checksum en haalt verplichte
    afhankelijkheden (Modrinth) mee.
  - *Optioneel, op eigen risico:* na installeren of aanzetten de plugin direct laden met `/plm load` (PlugManX), zonder herstart.
- **Tab-aanvulling in de console:** Tab vult commando's aan (vanilla, Paper en de commando's van je plugins), subcommando's
  (bijv. `whitelist add`, `time set`, `plm load`), spelersnamen en pluginnamen. Meerdere keren Tab bladert door de mogelijkheden,
  Shift+Tab gaat terug.

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
