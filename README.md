# CS2-manager

Web aplikacija za upravljanje CS2 timovima, igračima i prijavama timova na turnire.

- **Admin** kreira turnire i vodi ih kroz statuse (`draft` → `registration_open` → `ongoing` → `finished`).
- **Manager** upravlja svojim timovima i igračima te prijavljuje svoje timove na turnire.

Projekt je jedan git repozitorij: backend je u mapi `api/`, frontend (2. dio) bit će u mapi `web/`.

## Tehnologije

- **Backend:** FastAPI, Pydantic, SQLAlchemy 2.0 (asinkrono, `asyncpg`), Alembic
- **Baza:** PostgreSQL 17 u Dockeru
- **Autentikacija:** bcrypt za lozinke, JWT (access i refresh token)
- **Testovi:** pytest, pytest-asyncio, httpx, freezegun
- **Statička analiza:** Ruff

## Preduvjeti

- Python 3.11 ili noviji
- Docker Desktop (s Docker Compose)
- Git

## Pokretanje na svježem klonu

Sve naredbe osim prve izvode se iz mape `api/`.

### 1. Kloniranje

```bash
git clone https://github.com/mfranicc/CS2-manager.git
cd CS2-manager/api
```

### 2. Varijable okoline

Kopirati predložak u `.env` (datoteka `.env` nije u repozitoriju):

```bash
# Windows (PowerShell)
Copy-Item .env.example .env
# Linux / macOS
cp .env.example .env
```

U `.env` postaviti `SECRET_KEY` na dugačak nasumičan niz, npr. rezultat naredbe:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Baza

```bash
docker compose up -d
```

Pokreće PostgreSQL na portu 5432. Pri prvom pokretanju stvaraju se dvije baze: `cs2manager` za razvoj i `cs2manager_test` za testove.

### 4. Virtualno okruženje i paketi

```bash
# Windows (PowerShell)
py -m venv .venv
.\.venv\Scripts\Activate.ps1
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 5. Migracije

```bash
alembic upgrade head
```

### 6. Početni podaci

```bash
python -m app.seed
```

Skripta je idempotentna: smije se pokrenuti više puta, a ono što već postoji ne stvara se ponovno.

| Korisnik | Lozinka | Uloga | Podaci |
|---|---|---|---|
| `admin` | `admin123` | admin | stvara turnire |
| `manager1` | `manager123` | manager | Team Vitality, Natus Vincere, Falcons |
| `manager2` | `manager123` | manager | Team Spirit, MOUZ, The MongolZ |

Turniri: *Zadar Cup 2026* (`finished`, pun), *IEM Zagreb 2026* (`registration_open`) i *Split Major 2027* (`draft`).

### 7. Poslužitelj

```bash
uvicorn app.main:app --reload
```

Interaktivna dokumentacija API-ja: <http://127.0.0.1:8000/docs>

### 8. Testovi

```bash
pytest
```

Testovi rade nad zasebnom bazom `cs2manager_test`, pa podaci iz razvojne baze ostaju netaknuti. Baza mora biti pokrenuta (korak 3).

Statička analiza:

```bash
ruff check app tests alembic
ruff format --check app tests alembic
```

## Krajnje točke

| Metoda | Putanja | Tko smije |
|---|---|---|
| GET | `/health/` | svi |
| POST | `/auth/login` | svi |
| POST | `/auth/refresh` | svi |
| GET | `/auth/me` | prijavljeni |
| GET | `/teams/?limit&offset` | admin (svi timovi), manager (svoji) |
| POST | `/teams/` | manager |
| GET, PATCH, DELETE | `/teams/{team_id}` | GET: admin i vlasnik; PATCH, DELETE: vlasnik |
| GET | `/teams/{team_id}/players/?role&limit&offset` | admin, vlasnik tima |
| POST | `/teams/{team_id}/players/` | vlasnik tima |
| GET, PATCH, DELETE | `/teams/{team_id}/players/{player_id}` | GET: admin i vlasnik; PATCH, DELETE: vlasnik |
| GET | `/tournaments/?status&limit&offset` | prijavljeni (manager ne vidi draftove) |
| POST | `/tournaments/` | admin |
| GET | `/tournaments/{tournament_id}` | prijavljeni |
| PATCH, DELETE | `/tournaments/{tournament_id}` | admin |
| PATCH | `/tournaments/{tournament_id}/status` | admin |
| GET | `/tournaments/{tournament_id}/registrations/?limit&offset` | admin (sve), manager (svoje) |
| POST | `/tournaments/{tournament_id}/registrations/` | manager |
| GET, DELETE | `/tournaments/{tournament_id}/registrations/{registration_id}` | admin, vlasnik tima |

## Poslovna pravila

Pravila provodi backend; svako kršenje vraća pogrešku s kodom.

| Pravilo | Kod pogreške |
|---|---|
| Prijava i odjava samo dok je turnir u statusu `registration_open` | `409 registration_not_open` |
| Prijava i odjava samo prije roka `registration_deadline` | `409 registration_closed` |
| Broj prijavljenih timova ne smije premašiti `max_teams` | `409 tournament_full` |
| Tim se može prijaviti samo s najmanje 5 igrača | `409 not_enough_players` |
| Tim smije imati najviše 7 igrača | `409 team_full` |
| Status turnira ide samo jedan korak naprijed | `409 invalid_status_transition` |
| Turnir u tijeku ili završen ne mijenja se | `409 tournament_locked` |
| Kapacitet ne smije pasti ispod broja prijavljenih timova | `409 max_teams_too_low` |
| Briše se samo turnir u statusu `draft` | `409 tournament_not_draft` |
| Tim s prijavama na turnire ne briše se | `409 has_registrations` |

Manager ne vidi i ne mijenja tuđe timove, igrače i prijave (`403 forbidden`).

## Format pogrešaka

Sve pogreške imaju isti oblik:

```json
{"code": "tournament_full", "message": "Turnir je popunjen"}
```

Pogreške validacije (422) uz to navode polja:

```json
{
  "code": "validation_error",
  "message": "Neispravni podatci u zahtjevu",
  "errors": [{"field": "name", "message": "String should have at least 1 character"}]
}
```

## Struktura

```
api/
├── app/
│   ├── core/          # postavke, baza, JWT, bcrypt, ovisnosti, pogreške
│   ├── models/        # SQLAlchemy modeli
│   ├── schemas/       # Pydantic sheme za unos, izmjenu i odgovor
│   ├── repositories/  # upiti nad bazom
│   ├── services/      # poslovna pravila
│   ├── routers/       # krajnje točke
│   ├── main.py
│   └── seed.py        # početni podaci
├── alembic/versions/  # migracije 001, 002
├── tests/             # pytest
├── docker-compose.yml
├── requirements.txt
└── .env.example
web/                   # frontend (2. dio)
```

## Česte radnje

Nova migracija nakon promjene modela:

```bash
alembic revision --autogenerate --rev-id 003 -m "opis promjene"
alembic upgrade head
```

Poništavanje zadnje migracije:

```bash
alembic downgrade -1
```

Brisanje svih podataka i ponovno punjenje:

```bash
alembic downgrade base
alembic upgrade head
python -m app.seed
```

Brisanje Docker kontejnera i volumena s podacima:

```bash
docker compose down -v
```
