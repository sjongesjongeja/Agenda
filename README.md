# 📅 Agenda Web App

Een complete, eenvoudige en elegante persoonlijke **Agenda Web App** gebouwd met **Python 3**, **Flask**, **SQLite**, **HTML5**, **CSS3** en **Vanilla JavaScript**.

Geen zware frontend-frameworks zoals React of Next.js, geen Node.js vereist. Lichtgewicht, snel en betrouwbaar voor zowel lokaal gebruik als hosting op een Linux (Ubuntu) server.

---

## 🌟 Kenmerken & Functionaliteiten

1. **Kalender Maandoverzicht (`/`)**:
   - Maandnavigatie met `‹` Vorige, `Vandaag` en `›` Volgende maand.
   - Huidige dag direct herkenbaar met mintgroene accentstijl en **Vandaag** badge.
   - Afspraken overzichtelijk in de juiste dagcel getoond inclusief starttijd en kleuraccent.
   - Dagagenda zijpaneel met chronologisch overzicht van alle afspraken voor de geselecteerde dag.
   - Snel toevoegen door op een dag te klikken of op het `+` icoontje.
2. **Afspraken Beheren (CRUD)**:
   - **Toevoegen (`/add`)**: Titel (verplicht), Datum (verplicht), Begintijd (verplicht), Eindtijd, Locatie, Beschrijving en Kleurkeuze.
   - **Bekijken (`/event/<id>`)**: Detailpagina én snelle interactieve preview popup zonder de kalender te verlaten.
   - **Bewerken (`/edit/<id>`)**: Bestaande gegevens direct vooringevuld aanpassen.
   - **Verwijderen (`POST /delete/<id>`)**: Veilig verwijderen met bevestigingsvraag.
3. **Zoekfunctie (`/search?q=...`)**:
   - Zoeken op titel, beschrijving of locatie via de zoekbalk (sneltoets `/`).
4. **Beveiliging & Kwaliteit**:
   - Parameterized SQLite queries tegen SQL-injectie.
   - Ingebouwde CSRF-beveiliging op alle formulieren.
   - Server-side validatie (titel niet leeg, geldige datums/tijden, eindtijd >= begintijd).
   - Nette, vriendelijke foutpagina's voor 404 en 500.
5. **Modern Design**:
   - Rustige, lichte interface met veel witruimte.
   - Mintgroene accentkleur (`#2DD4A8`).
   - Volledig responsive: geoptimaliseerd voor desktop, tablet en smartphone.

---

## 📁 Projectstructuur

```text
Agenda/
├── app.py                     # Flask applicatie met alle routes, validatie en kalenderlogica
├── requirements.txt           # Python dependencies
├── schema.sql                 # SQLite databaseschema
├── agenda.db                  # SQLite database (wordt automatisch aangemaakt)
├── static/
│   ├── css/
│   │   └── style.css          # Design systeem, responsive grid en mintgroene styling
│   └── js/
│       └── script.js          # Modal popup, delete bevestiging en sneltoetsen
└── templates/
    ├── base.html              # Basis-layout met navigatie, zoekbalk en meldingen
    ├── index.html             # Kalender maandoverzicht & dagagenda
    ├── add.html               # Formulier voor nieuwe afspraak
    ├── edit.html              # Formulier voor bewerken van afspraak
    ├── event.html             # Detailweergave van afspraak
    ├── search.html            # Zoekresultatenpagina
    ├── 400.html               # Aangepaste 400 foutpagina
    ├── 404.html               # Aangepaste 404 foutpagina
    └── 500.html               # Aangepaste 500 foutpagina
```

---

## 🚀 Installatie & Lokaal Starten

### 1. Vereisten
- Python 3.8 of hoger.

### 2. Dependencies installeren
```bash
python -m pip install -r requirements.txt
```

### 3. Applicatie starten
```bash
python app.py
```

De applicatie start op alle netwerkinterfaces (`0.0.0.0`) op poort **5000**.

### 4. Openen in je browser
Ga in je browser naar:
```text
http://127.0.0.1:5000
```
Of op je lokale netwerk via het IP-adres van je machine: `http://<jouw-ip>:5000`.

---

## 🐧 Productie Deployment op Linux Ubuntu (als Systemd Service)

Hieronder volgt een beknopte handleiding om de Agenda als permanente achtergrondservice op een Ubuntu-server te draaien.

### 1. Code plaatsen en virtuele omgeving maken
```bash
cd /opt
sudo git clone <jouw-repo-url> agenda
cd agenda
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt gunicorn
```

### 2. Systemd servicebestand aanmaken
Maak het bestand `/etc/systemd/system/agenda.service`:

```ini
[Unit]
Description=Agenda Flask Web App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/agenda
Environment="PATH=/opt/agenda/venv/bin"
Environment="SECRET_KEY=kies-hier-een-sterke-willekeurige-sleutel"
ExecStart=/opt/agenda/venv/bin/gunicorn -w 3 -b 0.0.0.0:5000 app:app

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Service activeren en starten
```bash
sudo systemctl daemon-reload
sudo systemctl enable agenda
sudo systemctl start agenda
sudo systemctl status agenda
```

De agenda draait nu automatisch en herstart vanzelf bij een serverherstart of storing.
