# MCMTab: hulpplugin voor Tab-aanvulling

Klein Paper/Spigot-plugin dat **MC Server Manager** gebruikt om de Tab-aanvullingen van de server zelf op te vragen
(subcommando's en argumenten van alle plugins), zodat de console van het programma net zo aanvult als de echte
serverconsole.

## Hoe het werkt
Het programma stuurt via de console `mcmtab <id>` (lijst met alle commando's) of `mcmtab <id> <base64 van de regel>`
(aanvullingen voor die regel). Het plugin vraagt de commandomap van de server om de aanvullingen en antwoordt met één
regel `MCMTAB|<id>|<opties, gescheiden door tab>`. Het commando werkt **alleen vanuit de console**; spelers kunnen het niet gebruiken.

## Bestanden
| Bestand | Wat |
|---|---|
| `MCMTab.java` | broncode |
| `plugin.yml` | plugin-beschrijving |
| `MCMTab.jar` | het gebouwde plugin (zit ook ingebouwd in `mc_server_manager.py`) |

## Zelf bouwen
Compileren tegen de Paper-/Spigot-API (Java 8 of nieuwer):

```bash
javac --release 8 -cp paper-api.jar -d out MCMTab.java
cp plugin.yml out/ && (cd out && jar cfM ../MCMTab.jar .)
```

Het plugin gebruikt alleen `JavaPlugin`, `CommandSender` en `Command`; de rest gaat via reflectie, zodat het op
verschillende serverversies werkt.
