# Driftsättning - Docker/Unraid

Appen paketeras som en single-container Docker-image och publiceras till
GitHub Container Registry (GHCR).

## Bygga och pusha imagen

GitHub Actions (`.github/workflows/docker.yml`) bygger och pushar automatiskt
vid varje push till `main` samt vid taggar `v*`. Imagen hamnar på
`ghcr.io/armandur/systemdeklaration` med taggarna `latest` (endast main),
kort commit-SHA, och semver vid git-tag.

Manuellt bygge/push som alternativ (t.ex. innan Actions körts en första
gång, eller för att testa lokalt):

```sh
docker build -t ghcr.io/armandur/systemdeklaration:latest .
docker login ghcr.io -u <användarnamn>
docker push ghcr.io/armandur/systemdeklaration:latest
```

## Paketsynlighet

När repot är publikt ärver GHCR-paketet i regel den publika synligheten, så
imagen är direkt dragbar av Unraid utan credentials. Är paketet ändå privat
(t.ex. om repot varit privat): gör det publikt under Package settings
(GitHub -> Packages -> systemdeklaration -> Package settings -> Change
visibility), eller lägg pull-credentials (PAT med `read:packages`) i Unraids
registry-inställningar.

## Unraid - Add Container

Lägg till en ny container manuellt (Docker-fliken -> Add Container) med:

| Fält | Värde |
|---|---|
| Repository | `ghcr.io/armandur/systemdeklaration:latest` |
| Network Type | `bridge` |
| Port | `<ledig host-port>` -> `8000` (container) |
| Path | `/mnt/user/appdata/systemdeklaration` -> `/data` (Access Mode: RW) |
| Env | `SYSDEK_DB_PATH=/data/systemdeklaration.db` |

SQLite-databasen skapas automatiskt i den monterade volymen vid första
starten (`init_db()` skapar katalogen och tabellen).

## Drift-noter

- CSRF-cookien (`app/csrf.py`) sätts med `secure=True` - appen nås via NPM
  med ssl_forced (https://dekl.pettersson-vik.se). Körs appen någon gång rakt
  över http (t.ex. lokal dev på ubuntu-ai:8008) skickar webbläsaren inte
  cookien, så CSRF-skyddade sparningar kräver https.
- `data/sample.json` följer INTE med i imagen och läses aldrig i runtime -
  den används bara för demo/tester i utvecklingsmiljön.
