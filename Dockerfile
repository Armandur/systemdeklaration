# Systemdeklaration - single-container image för Unraid.
FROM python:3.12-slim

# WeasyPrint 69 renderar via Pango + Pillow (INTE cairo som äldre versioner).
# libpango* drar in harfbuzz/fontconfig/freetype transitivt. poppler-utils
# ger pdftoppm (används av /api/pdf-preview). fonts-dejavu-core krävs för att
# panelernas font-family: "DejaVu Sans" faktiskt ska hittas - saknas den
# faller WeasyPrint tyst tillbaka till serif utan att krascha.
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Python-beroenden i eget lager (cachas så länge requirements.txt är oförändrad).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Appkod. data/ tas medvetet inte med (se .dockerignore) - lokala SQLite-DB:n
# ska aldrig bakas in i en publik image, sample.json behövs inte i runtime.
COPY app/ ./app/

# Volymen monteras på /data i containern (se DEPLOY.md).
ENV SYSDEK_DB_PATH=/data/systemdeklaration.db
EXPOSE 8000

# Körs som root: Unraid-appdata-konventionen mappar värdvolymer utan att
# matcha UID/GID mot en icke-root-användare i imagen, vilket annars ger
# rättighetstrassel på den monterade volymen.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
