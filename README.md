<h1 align="center">Basketball Court Finder & 3x3 Matchmaker</h1>

<p align="center">
  Znajdź boisko, sprawdź jego wyposażenie i umów się na mecz 3x3.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Database-PostgreSQL%20%2B%20PostGIS-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL + PostGIS">
  <img src="https://img.shields.io/badge/Maps-Leaflet-199900?logo=leaflet&logoColor=white" alt="Leaflet">
</p>

---

Aplikacja webowa ułatwiająca wyszukiwanie boisk do koszykówki, sprawdzanie ich parametrów technicznych i organizowanie lokalnych meczów 3x3. Projekt powstał w ramach pracy inżynierskiej.

## Główne funkcje

- **Boiska na mapie** — przeglądaj obiekty w okolicy i filtruj je według dostępnych parametrów.
- **Dane z OpenStreetMap** — wyszukuj boiska za pomocą Overpass API.
- **Check-in** — zamelduj się na boisku, jeśli jesteś w odległości do 75 metrów.
- **Zgłaszanie boisk** — dodaj brakujące boisko ze zdjęciami do weryfikacji.
- **Mecze 3x3** — utwórz spotkanie na wybrany termin lub dołącz do składu.
- **Punkty XP i ranking** — zdobywaj punkty za aktywność i sprawdzaj tabelę graczy.

## Technologie

| Część projektu | Technologie |
|---|---|
| Frontend | React, Vite, Leaflet |
| Backend | Python, FastAPI, asyncpg |
| Baza danych | PostgreSQL, PostGIS |
| Narzędzia | Docker, Docker Compose |

## Baza danych

PostGIS umożliwia przechowywanie lokalizacji boisk i wykonywanie zapytań przestrzennych, takich jak wyszukiwanie obiektów w pobliżu lub sprawdzanie odległości podczas meldunku.

Najważniejsze tabele:

- `courts` — boiska, ich lokalizacja i parametry techniczne.
- `court_images` — zdjęcia boisk.
- `check_ins` — meldunki graczy, wygasające po dwóch godzinach.
- `matches` i `match_participants` — spotkania i zapisani gracze.
- `users` — konta użytkowników i punkty XP.

## Uruchomienie

### Wymagania

- Python 3.11+
- Node.js i npm
- Docker i Docker Compose albo lokalny PostgreSQL z PostGIS

### 1. Pobierz repozytorium i uruchom bazę

```bash
git clone https://github.com/Krupakoo/basketball-court-finder.git
cd basketball-court-finder
docker compose up -d
```

> Docker Compose uruchamia bazę PostGIS. Backend i frontend uruchom osobno, korzystając z instrukcji poniżej.

### 2. Uruchom backend

W nowym terminalu:

```bash
cd backend
python -m venv venv
```

Aktywuj środowisko:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Zainstaluj zależności i uruchom serwer:

```bash
pip install fastapi uvicorn asyncpg python-jose python-multipart "passlib[bcrypt]" httpx
uvicorn main:app --reload --port 8000
```

- API: [http://localhost:8000](http://localhost:8000)
- Dokumentacja Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Uruchom frontend

W kolejnym terminalu:

```bash
cd frontend
npm install
npm run dev
```

Otwórz adres wyświetlony przez Vite — domyślnie [http://localhost:5173](http://localhost:5173).

## Autor

**Dawid Krupski**
