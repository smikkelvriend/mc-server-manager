# Changelog

De nieuwste versie staat bovenaan. De oude bestanden staan in [`oude_versies/`](oude_versies/).

## 2.53
- Nieuwe interface: het vinkje **Schoon** in de console doet weer iets. Het werd alleen op nieuwe regels toegepast en dus nooit op wat er al stond. Nu worden de regels opnieuw geladen als je het vinkje omzet. Daarvoor bewaart het programma ook de regels die in de schone console verborgen zijn (maximaal 1500 in het geheugen).
- Deze versie vereist een herstart.

## 2.52
- Nieuwe interface: spelerskoppen die traag binnenkomen (vooral Bedrock-spelers) verschijnen nu wel. De spelerslijst werd elke seconde opnieuw opgebouwd, waardoor het laden van een kop steeds werd afgebroken. Nu wordt de lijst alleen opnieuw opgebouwd als er een speler bijkomt of weggaat; alleen de duur wordt bijgewerkt. Per speler wordt een kop ook maar één keer tegelijk gedownload. Mislukt een kop toch, dan staat er de beginletter en probeert het scherm het na 4 seconden nog eens.
- Deze versie vereist een herstart.

## 2.51
- Nieuwe interface: de knop onder Auto slaapstand heet **Uit slaapstand halen** zolang de server slaapt en start dan meteen de server (zonder dat er iemand hoeft te joinen). Draait de server, dan is het weer **Nu in slaapstand**.

## 2.50
- Nieuwe interface, Instellingen: de **Slaapstand** (minuten zonder spelers, alleen op bepaalde tijden, van/tot en dagen) en de **Gezondheidscontrole** (schijf, lage TPS, geheugen) hebben nu eigen kaarten. Die instellingen waren alleen in het oude scherm te vinden, dat niet meer te zien is.
- Deze versie vereist een herstart.

## 2.49
- Nieuwe interface: de grafiek in het Overzicht hapert niet meer. De lijn wordt nu op tijd getekend, een paar seconden achter de werkelijkheid, in plaats van te springen zodra er een nieuwe meting binnenkomt. Het scherm ververst elke seconde.
- Na een update met herstart blijft het bestaande venster nu verbonden met het nieuwe programma (vaste sleutel in `mc_server_manager_scherm.key`), in plaats van dat er een tweede venster opent en het oude blijft staan. Een venster dat het programma na 90 seconden nog niet terugvindt, sluit zichzelf.
- Deze versie vereist een herstart.

## 2.48
- De nieuwe interface is nu de **enige** interface: het klassieke scherm is niet meer te zien (ook niet op de taakbalk). De knop Klassiek scherm en de instelling "Nieuwe interface als hoofdscherm" zijn weggehaald.
- Het programma sluit zodra je het venster sluit, als de server niet draait. Draait de server nog, dan opent het venster weer en sluit je af met de nieuwe knop **Afsluiten** onderin de zijbalk (die de server eerst veilig stopt).
- Lukt het niet om een eigen venster te openen (geen Edge of Chrome), dan opent het scherm in je gewone browser en blijft het klassieke scherm op de taakbalk, zodat je altijd kunt afsluiten.
- Deze versie vereist een herstart.

## 2.47
- Nieuwe interface, Overzicht: alle grafieken (geheugen, processor, TPS en temperatuur) staan nu gecombineerd in één grafiek bovenaan, met de huidige waarden in de legenda. Elke lijn is op zijn eigen schaal getekend (TPS 0 tot 20, temperatuur 0 tot 110 °C), dus de hoogte zegt niets over de waarde zelf.
- Het aantal spelers staat nu tussen haakjes achter "Spelers online"; de losse tegels zijn weg.
- Het Overzicht past op één scherm zonder scrollen; de console krijgt de overgebleven ruimte.
- Deze versie vereist een herstart.

## 2.46
- Nieuwe interface: de grafiek Belasting loopt nu soepel door. De lijn schuift continu mee in plaats van per meting te springen (met 30 beelden per seconde, alleen zolang het Overzicht open staat) en gebruikt de volledige reeks metingen.
- Plugins: elke plugin heeft nu een duidelijk label **Aan** of **Uit**, uitgeschakelde plugins staan gedimd onderaan, en bovenaan staat hoeveel er aan en uit staan.
- Plugins: rechtsonder staat niets meer over het programma zelf; dat staat op het tabblad Updates.
- Deze versie vereist een herstart.

## 2.45
- Nieuwe interface, Overzicht: de losse tegels Processor en Geheugen zijn vervangen door de huidige waarden in de legenda van de grafiek Belasting (de TPS-lijn is uit de grafiek gehaald, TPS heeft zijn eigen tegel). Daarvoor in de plaats staat er een tegel Spelers. De console is groter.
- Deze versie vereist een herstart.

## 2.44
- De nieuwe interface is nu het **hoofdscherm**: hij opent bij het starten van het programma en het klassieke scherm blijft op de taakbalk. Uitzetten kan bij Instellingen ("Nieuwe interface als hoofdscherm"). In de zijbalk staat een knop **Klassiek scherm** om het oude venster terug te halen.
- Nieuw tabblad **Updates** in de nieuwe interface voor het programma zelf: versie, wat er nieuw is, nu installeren, zoeken naar updates en de instellingen voor automatisch bijwerken. Het getal bij Plugins telt alleen nog plugin- en Paper-updates.
- Deze versie vereist een herstart.

## 2.43
- Nieuw: **Nieuwe interface**. De knop ✨ bovenin opent een tweede, moderner scherm (in een eigen venster, zonder adresbalk) met dezelfde functies: Overzicht (TPS, processor, geheugen en temperatuur, belastingsgrafiek, spelers met hun skin, console en aandachtspunten), Console (met commandogeschiedenis, Tab-aanvullen en logboek doorzoeken), Spelers (skins, whitelist, bans, IP-bans en operators), Plugins en updates samen, Kaart, Backups en Instellingen (server.properties, slaapstand, gezondheidscontrole). Het oude scherm blijft gewoon werken.
- Het nieuwe scherm draait op een adres dat alleen deze computer kan bereiken (met een eigen geheime sleutel per start); er is geen wachtwoord of poort-doorsturen voor nodig. Het gebruikt Edge of Chrome als die op de computer staan.
- De bron van het scherm staat in `nieuwe_interface/`.
- Deze versie vereist een herstart.

## 2.42
- Plugins: nieuwe knop **PLM uitladen** (`/plm unload`) naast **PLM laden**, ook in de telefoon-app. PlugManX zelf wordt nooit uitgeladen. De plugin blijft in de map staan en wordt bij de volgende herstart weer geladen.
- De namen van de PLM-knoppen en van het vinkje eronder zijn korter gemaakt.
- Deze versie vereist een herstart.

## 2.41
- Het tabblad Updates is samengevoegd met Plugins. Onder Plugins staan nu drie subtabs: Geïnstalleerd, Updates en Zoeken en toevoegen. Bij beschikbare updates knippert het tabblad Plugins met het aantal.
- Deze versie vereist een herstart.

## 2.40
- De grafieken voor CPU, geheugen en TPS zakken naar 0 zolang de server uit staat of slaapt, in plaats van te stoppen met tekenen. Dit kan zonder herstart worden toegepast.

## 2.39
- Het vinkje voor de slaapstand op het tabblad Server heet nu "Auto slaapstand" (de knop eronder zet de server meteen in slaapstand).
- Deze versie vereist een herstart.

## 2.38
- Nieuwe knop **Nu in slaapstand** op het tabblad Server. De server stopt dan meteen veilig en start weer zodra iemand probeert te joinen. De knop werkt ook als de automatische slaapstand uit staat, en vraagt eerst bevestiging als er spelers online zijn of Chunky bezig is.
- Deze versie vereist een herstart.

## 2.37
- Nieuw: **Whitelist en bans**. Knop op het tabblad Server (en rechtsklik op een speler: Bannen, Op de whitelist zetten, Operator maken). Eén venster voor whitelist, bans, IP-bans en operators met toevoegen en verwijderen; whitelist aan/uit. Draait de server, dan gaat het met server-commando's; staat hij uit, dan rechtstreeks in de bestanden (UUID via Mojang, of de offline-UUID bij `online-mode=false`). Bedrock-spelers kunnen alleen bij een draaiende server.
- Nieuw: **Logboek doorzoeken**. Zoekt in latest.log en alle oude logs (ook .gz), met filters voor speler, soort (joinen, verlaten, chat, commando's, doodgaan, waarschuwingen en fouten) en datumbereik. Maximaal 5000 resultaten.
- Slaapstand uitgebreid: aan/uit-vinkje op het tabblad Server, statistieken (aantal keer geslapen, totale slaaptijd, aantal keer gewekt), een rooster (alleen op bepaalde uren en dagen) en een melding bij wakker worden.
- Nieuw: **Gezondheidscontrole** (Instellingen > Gezondheid). Waarschuwt in het logboek en met een Windows-melding bij een bijna volle schijf, te lage TPS of bijna vol geheugen, hooguit één keer per half uur per soort.
- Deze versie vereist een herstart.

## 2.36
- Fix: in het spelersmenu knipperde af en toe de spelerskop. De lijst werd bij elke verversing leeggemaakt en opnieuw opgebouwd, waardoor de kop even weg was. Bestaande rijen blijven nu staan en worden alleen bijgewerkt; nieuwe spelers krijgen hun kop meteen.
- Deze versie vereist een herstart.

## 2.35
- De kaart wordt op de achtergrond voorgeladen: kort na het starten van het programma en 30 seconden nadat de server online is. Wereldlijst en de tegels rond het startpunt staan dan al klaar als je het tabblad Kaart opent, dat daarna meteen ververst.
- Deze versie vereist een herstart.

## 2.34
- Slaapstand, Bedrock met NetherNet (experimenteel): het programma luistert nu ook op TCP van de Bedrock-poort, schrijft in het logboek wat een Bedrock-client daar vraagt en wekt de server bij een join-verzoek. Het exacte NetherNet-verzoek is nog niet bevestigd; het log helpt om dat vast te stellen.
- Deze versie vereist een herstart.

## 2.33
- Slaapstand: de Bedrock-serverlijst toont nu "💤 Server slaapt" met de uitleg "Join = starten, wacht ±1 min". Een melding op het moment van joinen zelf is bij Bedrock niet gemaakt: daarvoor moet het volledige Bedrock-protocol worden nagebouwd.
- Deze versie vereist een herstart.

## 2.32
- Nieuw: **Slaapstand** (Instellingen > Starten & Java). Staat er X minuten niemand online, dan stopt de server veilig en gaat het programma op de serverpoort luisteren. In de Minecraft-serverlijst staat dan "Server slaapt". Probeert iemand te joinen, dan krijgt die de melding dat de server start en wordt de server automatisch gestart; na ongeveer een minuut kan de speler gewoon joinen.
- De server gaat niet slapen zolang Chunky de kaart genereert. De knop "Server starten" wekt de server ook.
- Bedrock-spelers (Geyser) worden ook herkend, maar dat onderdeel is nog niet met een echte Bedrock-client getest.
- Deze versie vereist een herstart.

## 2.31
- Zuiniger: de grafieken op het Server-tabblad worden alleen nog hertekend als de lijn minstens een halve pixel is opgeschoven. Dat scheelt in rust grofweg driekwart van de processortijd.
- Fix: de knop "Pagina" bij plugin-zoekresultaten deed niets (ontbrekende functie).
- Deze versie vereist een herstart.

## 2.30
- De pagina "Instellingen van Backuper" (tabblad Backups) scrolt nu met het muiswiel en een scrollbalk; eerder werd alles onder de eerste opslagen afgesneden.
- Aanvinkvakjes, keuzerondjes, scrollbalken en rijhoogtes schalen nu mee met de schermschaling van Windows (waren op een scherm met 125-200% erg klein).
- Deze versie vereist een herstart.

## 2.29
- Fix: het tabblad Backups toonde bestanden uit je serverfolder (spigot.yml, ops.json, …) als backups. Bij Backuper-opslag via ftp, sftp of webdav is `backupsFolder` een map op een andere computer; die werd ten onrechte als lokale map gelezen. Alleen lokale opslag wordt nu getoond.
- Deze versie vereist een herstart.

## 2.28
- Opgeschoonde en modernere interface: een vlak, rustig kleurenschema voor licht én donker, dat er op elk systeem hetzelfde uitziet (dus niet meer afhankelijk van het Windows-thema).
- Knoppen hebben nu vaste betekenis: blauw = hoofdactie, groen = starten/aanzetten, rood = verwijderen of wissen, grijs = de rest (geen regenboog meer). Uitgeschakelde knoppen blijven zichtbaar.
- Duidelijkere tabbladen en titels: "Bereikbaarheid" heet nu "Netwerk"; bovenaan de tabbladen Updates en Netwerk staat korte uitleg; de console begint met een welkomsttekst.
- Instellingen: begint bij "Algemeen" en de tabbladen zijn logischer gesorteerd en hernoemd (Starten & Java, Zoeken naar updates, Dit programma).
- Deze versie vereist een herstart.

## 2.27
- Pijltje omhoog/omlaag in het commandovak haalt ook commando's terug die de server afkeurde, zodat je ze kunt verbeteren. Alleen de Tab-aanvulling slaat afgekeurde commando's over. De volgorde van de geschiedenis blijft kloppen na een herstart.
- Deze versie vereist een herstart.

## 2.26
- Fout hersteld: in Instellingen was alleen het tabblad Backups zichtbaar. Twee functies met dezelfde naam (`dir_size`) kwamen in elkaar vast te zitten, waardoor de rest van het venster niet werd opgebouwd.
- Uptime en online-tijd in de spelerslijst hebben weer hun oude notatie (uu:mm:ss); de nieuwe kortere notatie (1u 5m) is alleen voor de Spelers- en Backups-overzichten.
- Instellingen slaan geen interne lijsten (geleerde commando's, commandogeschiedenis) meer als tekst over.
- Deze versie vereist een herstart.

## 2.25
- De grafieken (CPU, geheugen, TPS, temperatuur) worden bewaard (laatste 6 uur) en lopen door na een herstart van de server of van het programma. Wanneer de server uit was, laat de lijn een gat zien in plaats van door te trekken.
- Deze versie vereist een herstart.

## 2.24
- Soepel zoomen werkt nu ook op de diepste zoomniveaus (waar squaremap geen scherpere tegels meer heeft), en het einde van de animatie springt niet meer. Met Pillow worden die niveaus vloeiend vergroot in plaats van blokkerig.
- Deze versie vereist een herstart.

## 2.23
- **Tab-aanvulling zoals in de echte console**: het programma plaatst bij het starten van de server (eenmalig) het kleine hulpplugin `MCMTab` in `plugins/`. Dat vraagt de server zelf om aanvullingen (ook subcommando's en argumenten van plugins). Na één herstart van de server werkt het; zonder plugin blijft de oude, geleerde aanvulling werken. De broncode staat in `hulpplugin/`.
- Soepel zoomen is veel vlotter: elk beeld wordt in één keer opgebouwd en tegels worden alvast in een achtergrondthread uitgepakt.
- De kaart meldt nu "Squaremap niet bereikbaar: opgeslagen kaart" (in plaats van "server uit") en probeert het elke paar seconden opnieuw tot de live kaart er is.
- Resterende helpregels (zoals "Aliases: Lists command aliases") verschijnen niet meer in de console.
- Deze versie vereist een herstart.

## 2.22
- Soepel zoomen op de kaart met echte tussenbeelden: de tegels worden vloeiend geschaald in plaats van korrelig. Dit gebruikt Pillow; het programma vraagt eenmalig of het dat mag installeren (of gebruik de knop "Soepel zoomen aanzetten" op het Kaart-tabblad). Zonder Pillow zoomt de kaart zoals voorheen in stappen.
- De help-regels van de server verschijnen niet meer in de console terwijl het programma commando's leert voor tab-aanvulling.
- Kaart leest het adres niet meer vanuit een achtergrondthread (stabieler).
- Deze versie vereist een herstart.

## 2.21
- Soepel zoomen met veel meer tussenstappen (ongeveer 16 per niveau in plaats van 3).
- Tab-aanvulling leert de commando's via /help en /help <plugin> (de server geeft per plugin een lijst), toont daarna ook plugin-commando's zoals backuper, geeft bij plugin-commando's geen spelersnamen meer als subcommando en vergeet commando's die de server afkeurt.
- Deze versie vereist een herstart.

## 2.20
- Kaart zoomt soepel: tussen twee zoomniveaus loopt een korte animatie, rond de plek waar je zoomt. Op de telefoon ook staploos met twee vingers.
- Deze versie vereist een herstart.

## 2.19
- Tabblad Backups: Backuper-plugin beheren (instellingen uit config.yml met behoud van commentaar, backups bekijken en verwijderen, bestanden van de plugin, nu een backup maken) plus de backups en instellingen van dit programma zelf. Ook op de telefoon (Beheer).
- Spelerskoppen bij alle spelerslijsten, op de kaart en op de telefoon. Java via mc-heads.net, Bedrock via de Geyser-skin-API. Zonder skin een eigen hoofdje. Opslag in de map heads.
- Tab-aanvulling kent nu ook plugin-commando's (de server wordt na het opstarten stil om /help gevraagd) en leert van je eigen commando's.
- Deze versie vereist een herstart.

## 2.18.1
- Plugins die up-to-date zijn tonen overal gewoon "Up-to-date" (zonder toelichting).

## 2.18
- De telefoon-webapp heeft nu dezelfde functies als het programma op Windows: Server (grafieken, console, spelers kicken/bannen/op/gamemode, RAM), Plugins (aan/uit/verwijderen, zoeken en installeren), Updates (Paper, plugins, programma), Kaart (inzoomen en slepen, spelers live, gebied kiezen en Chunky starten/pauzeren/stoppen met voortgang en reden van pauze), Beheer (spelersstatistieken, tuning, wereldgrootte, logs opruimen) en Meer (bereikbaarheid, instellingen, logboek).
- Vensters op de pc die door een opdracht van je telefoon verschijnen, worden automatisch beantwoord (kort tijdvenster), zodat de pc niet blijft wachten.
- Deze versie vereist een herstart.

## 2.17
- Updates zonder herstart: het programma beoordeelt zelf of een update veilig live kan (code-vergelijking plus een vlag per release). Zo ja, dan staat er "(zonder herstart)" bij de updateknop en blijft de server gewoon draaien. Anders herstart het programma zoals voorheen.
- Chunky pauzeert automatisch zodra er een speler online komt en hervat als iedereen weg is; de reden staat in het Kaart-tabblad (was 2.16.1).
- Deze versie zelf vereist nog één herstart.

## 2.16.1
- **Chunky pauzeert bij spelers:** komt er een speler online, dan pauzeert het programma Chunky en toont op de kaart waarom ("Gepauzeerd: Floyd is online gekomen"). Is de server weer leeg, dan gaat Chunky vanzelf verder. Beide zijn uit te zetten onder het voortgangsbalkje. Namen bij Beheer → Meldingen → negeren (bijv. bots) tellen niet mee. Start je een gebied terwijl er spelers online zijn, dan wacht Chunky tot ze weg zijn.

## 2.16
- **Telefoon-app:** in Beheer, tabblad Telefoon zet je een beveiligd webadres aan dat je op je Android opent (en als app-icoon op het startscherm zet): status, CPU/geheugen/TPS-grafieken, spelers, live console, commando's sturen en starten/stoppen/herstarten. Standaard uit, met wachtwoord, begrensd tot je eigen netwerk of VPN.

## 2.15
- **Donker thema:** aan te zetten bij Instellingen, Gedrag (het programma herstart daarna). Geldt voor alle tabbladen, lijsten, knoppen en de titelbalk.

## 2.14.1
- **Kaart offline:** staat de server uit (of is squaremap niet bereikbaar), dan toont de kaart de door squaremap opgeslagen tegels uit `plugins/squaremap/web`. Zodra de server draait, schakelt hij vanzelf terug naar live (met spelers).

## 2.14
- **Tabblad Beheer** met vier onderdelen:
  - *Spelers:* speeltijd, keer online, laatst gezien, doden, gedode mobs en afgelegde afstand per speler (uit de stats van je wereld en het logboek van het programma); sorteerbaar.
  - *Meldingen:* Windows-melding bij een crash, opstarten klaar, speler komt/gaat, gebied klaar of programma-update; namen (bots) negeren.
  - *Tuning:* controle van view/simulation-distance, online-mode, Java-geheugen, TPS en geheugengebruik, met knop om advies toe te passen in server.properties.
  - *Wereld:* grootte per wereld en onderdeel, vrije schijfruimte, oude logs opruimen en regio's buiten een gekozen gebied wegzetten (naar _opgeruimd, niet verwijderd).

## 2.13
- **Gebied genereren op de kaart:** klik op *Gebied genereren*, sleep een rechthoek over de kaart (zoals Knipprogramma) en kies *Start genereren*. Het programma stuurt de Chunky-commando's, toont een voortgangsbalk met percentage, chunks, resterende tijd en snelheid (de Chunky-regels verdwijnen uit de console) en werkt daarna automatisch de kaart bij met squaremap. Pauzeren en stoppen kan ook.

## 2.12.7
- Kaart: de regel onderin toont bij de muis welke tegel het is en of die geladen is of op de server niet bestaat.

## 2.12.6
- Bedrock (NetherNet): bij een werkende poort alleen nog één korte groene regel.

## 2.12.5
- **NetherNet:** staat Geyser op `transport: nethernet`, dan test het programma de TCP-poort (lokaal en via je domein) in plaats van de oude RakNet-ping, en legt uit dat TCP en UDP open moeten voor naam/motd.

## 2.12.4
- Bedrock-check toont een oranje waarschuwing (geen rood kruis) als Java de UDP-poort open heeft maar niet op de ping antwoordt.

## 2.12.3
- Bedrock-check: ping probeert opnieuw en ook via IPv6; als Java de UDP-poort open heeft maar niet op de ping antwoordt, staat er dat Geyser wel luistert.

## 2.12.2
- Bedrock-check pingt Geyser ook op je netwerk-adres, voor het geval Geyser niet aan 127.0.0.1 gebonden is.

## 2.12.1
- **Bedrock-poort automatisch gevonden:** antwoordt Geyser niet op de ingestelde UDP-poort, dan kijkt het programma welke UDP-poorten Java open heeft, probeert die en stelt de werkende in. Lukt dat niet, dan staat er welke poorten open zijn.

## 2.12
- **Soepele grafieken:** de grafieken van CPU, geheugen, TPS en temperatuur lopen nu continu door (ca. 20 keer per seconde) in plaats van elke seconde te springen. De lijn loopt een fractie achter op de werkelijkheid en rekent soepel tussen twee echte metingen door; de getoonde waarde rechtsboven is altijd de echte laatste meting. De schaal beweegt zacht mee. Alleen actief als het tabblad Server in beeld is.
- **Opvallend Updates-tabje:** het tabblad Updates knippert rood/oranje en toont het aantal zodra er een plugin- of Paper-update beschikbaar is.

## 2.11.4
- Kaart: dunne strepen tussen tegels op bepaalde zoomniveaus opgelost (tegels worden op hele pixels getekend, zodat afronden geen kier meer geeft).

## 2.11.3
- **Kaart:** te ver inzoomen gaf een zwart beeld, omdat er voorbij het diepste zoomniveau geen tegels bestaan. Nu worden de tegels van het diepste niveau vergroot.
- **Renderen:** squaremap verwacht in commando's `minecraft:overworld` (met dubbele punt), terwijl de website `minecraft_overworld` gebruikt. Het menu Renderen zet dat nu goed om (dat gaf 'No such world').

## 2.11.2
- Programma-update betrouwbaarder: de laatste versie wordt gevonden via de GitHub-API met ETag (een '304' telt niet mee voor de limiet) en, als de API-limiet toch bereikt is, via het git-protocol. Controle bij terugkeren naar het venster hooguit elke 5 minuten.

## 2.11.1
- Bedrock-controle (Bereikbaarheid): leest de poort van Geyser uit `plugins/Geyser-*/config.yml` (ook `clone-remote-port`) en uit de opstartregel "Started Geyser on UDP port …", in plaats van altijd 19132 te testen.

## 2.11
- **Kaart in het programma zelf, zonder browser:** het programma haalt de tegels op van je squaremap-webserver (`tiles/<wereld>/<zoom>/<x>_<z>.png`) en tekent alleen wat in beeld is. Slepen, in- en uitzoomen, alle werelden, spawn, spelers live met naam, richting en spoor (uit squaremap zelf), en een menu Renderen. Doet niets zolang het tabblad dicht is.
- Wereldnamen worden uit squaremap gelezen (bijv. `minecraft_overworld`), zodat de rendercommando's kloppen.

## 2.10
- **Tabblad Kaart (nieuw, nu met squaremap):** toont of je kaartwebsite online is, opent hem met één klik in je browser (adres instelbaar, met adres voor andere apparaten) en bedient het renderen: hele wereld, alleen rond de spawn met instelbare straal, pauzeren/hervatten, stoppen en instellingen herladen.

## 2.9
- **Het tabblad Kaart is verwijderd.** De wereldkaart werkte niet betrouwbaar genoeg op jouw wereld. De versies 2.7 t/m 2.8.11 hieronder beschrijven de kaart; die code zit er niet meer in. De rest (plugins, temperatuur, snellere updatemeldingen, consolevenster verbergen) blijft.

## 2.8.11
- Kaart: als regiobestanden verdeeld staan over meerdere mappen (bijvoorbeeld `world/region` en `world/dimensions/minecraft/overworld/region`), worden ze nu allemaal gebruikt; bij dubbele regio's telt de nieuwste.

## 2.8.10
- De vraag om te herstarten na een programma-update toont nu ook wat er nieuw is (en het staat in het logboek).

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
