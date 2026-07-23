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

## Viktig not: gör GHCR-paketet publikt

Första push:en till GHCR skapar paketet som **privat by default**. Unraid
kan då inte dra imagen. Antingen:

- gör paketet publikt under Package settings på GitHub (repo -> Packages
  -> systemdeklaration -> Package settings -> Change visibility), eller
- lägg in pull-credentials (personal access token med `read:packages`)
  i Unraids Docker-inställningar för registret.

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

- CSRF-cookien (`app/csrf.py`) sätts med `secure=False` eftersom trafiken
  internt går över http. Ligger appen bakom TLS (reverse proxy) bör detta
  ändras till `True`.
- `data/sample.json` följer INTE med i imagen och läses aldrig i runtime -
  den används bara för demo/tester i utvecklingsmiljön.
