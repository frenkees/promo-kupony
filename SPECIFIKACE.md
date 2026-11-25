# Specifikace projektu pro Claude Code — Systém promo kuponů

> **Pro Claude Code:** Tento dokument je kompletní zadání. Postav podle něj funkční aplikaci (backend + frontend + Docker deployment) přesně podle popsaného stacku, datového modelu a endpointů. Identifikátory (tabulky, sloupce, endpointy, proměnné) drž přesně tak, jak jsou zde uvedené anglicky. Prózu a komentáře piš česky. Na konci jsou **akceptační kritéria** — hotovo je, když všechna projdou. Soubor `scripts/generate_cards.py` a `docs/DOKUMENTACE.md` jsou dodány zvlášť, zařaď je do repozitáře.

---

## 1. Co aplikace dělá (stručně)
Webová PWA pro síť ~7 restaurací. Spravuje oběh fyzických promo kuponů (laminovaná kartička s QR a 4místným kódem). Kupon se **vydá** zákazníkovi a později **uplatní** (zákazník ho odevzdá za odměnu, kupon se vrací do oběhu). Systém je centrální „bod pravdy", vede nezměnitelný auditní log a hlídá podezřelé akce. Hodnotu nese stav kódu v databázi, ne papír → kopie kuponu je bezcenná, protože uplatnit lze jeden kód jen jednou za cyklus.

**Neměnná pravidla:**
- Kupon se při uplatnění vrací do stavu „volná" (recyklace kódu).
- Žádná expirace.
- Typ odměny je jen na papíru, v systému se neeviduje.
- Časy se ukládají v UTC, zobrazují v `Europe/Prague`.

---

## 2. Technologický stack (závazně)
**Backend**
- Python 3.12, **FastAPI**, Uvicorn
- **SQLAlchemy 2.x** (ORM), **Alembic** (migrace), **Pydantic v2** (schémata)
- `passlib[bcrypt]` (hashování hesel), `PyJWT` (JWT), `python-multipart` (upload CSV)

**Databáze**
- **PostgreSQL 16**

**Frontend**
- **Vue 3** (Composition API, `<script setup>`), **Vite**, JavaScript
- **Vue Router**, **Pinia** (stav), **axios** (API klient, `withCredentials: true`)
- **Tailwind CSS**
- **html5-qrcode** (skenování QR z kamery + ovládání blesku/torch)
- **vite-plugin-pwa** (instalovatelná PWA)

**Infrastruktura**
- **Docker** + **Docker Compose**
- **Caddy 2** — reverse proxy, automatické HTTPS (Let's Encrypt), servírování buildnutého frontendu

**Princip nasazení:** vše běží na jedné doméně. Caddy servíruje statický frontend a proxuje `/api/*` na backend → frontend i API jsou **same-origin** → autentizace přes `httpOnly` cookie funguje bez CORS problémů.

---

## 3. Struktura projektu
```
promo-kupony/
├── docker-compose.yml
├── .env.example
├── README.md                  # krátký, odkáže na docs/DOKUMENTACE.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/               # migrace
│   └── app/
│       ├── main.py            # FastAPI app, startup: migrace + seed
│       ├── config.py          # načítání env (pydantic-settings)
│       ├── database.py        # engine, session
│       ├── models.py          # SQLAlchemy modely
│       ├── schemas.py         # Pydantic schémata
│       ├── auth.py            # hashování, JWT, cookie, dependency na role
│       ├── seed.py            # bootstrap master účtu z env
│       ├── services/
│       │   ├── coupons.py     # atomické přechody stavu
│       │   └── audit.py       # zápis logu + výpočet heuristik
│       └── routers/
│           ├── auth.py
│           ├── coupons.py     # operátorské akce
│           ├── dashboard.py   # manažerské pohledy
│           ├── restaurants.py # master
│           └── accounts.py    # master
├── frontend/
│   ├── Dockerfile             # multi-stage: node build → caddy servíruje dist + proxy
│   ├── Caddyfile
│   ├── package.json
│   ├── vite.config.js         # + dev proxy /api → backend:8000
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router.js
│       ├── api.js             # axios instance
│       ├── stores/auth.js     # Pinia: přihlášený účet, role
│       ├── views/
│       │   ├── Login.vue
│       │   ├── Scan.vue                 # operátor
│       │   └── admin/
│       │       ├── Overview.vue
│       │       ├── Suspicious.vue
│       │       ├── CardHistory.vue
│       │       ├── Import.vue
│       │       ├── Restaurants.vue
│       │       └── Accounts.vue
│       └── components/         # tlačítka, status panel, modal s důvodem bypassu…
├── scripts/
│   ├── generate_cards.py       # dodán zvlášť
│   └── backup.sh               # záloha DB (viz §10)
└── docs/
    └── DOKUMENTACE.md          # dodán zvlášť
```

---

## 4. Datový model (PostgreSQL)

### Enumy
- `account_role`: `operator` | `manager` | `master`
- `coupon_state`: `VOLNA` | `K_UPLATNENI` | `VYRAZENA`
- `log_action`: `VYDANI` | `UPLATNENI` | `VYRAZENI` | `IMPORT`
- `log_result`: `OK` | `ODMITNUTO` | `BYPASS`

### Tabulka `restaurants`
| sloupec | typ | pozn. |
|---|---|---|
| id | serial PK | |
| name | text NOT NULL | |
| created_at | timestamptz DEFAULT now() | |

### Tabulka `accounts`
| sloupec | typ | pozn. |
|---|---|---|
| id | serial PK | |
| login | text UNIQUE NOT NULL | |
| password_hash | text NOT NULL | bcrypt |
| role | account_role NOT NULL | |
| restaurant_id | int FK→restaurants NULL | vyplněno jen u `operator` |
| baseline_user_agent | text NULL | uloží se při 1. přihlášení operátora |
| must_change_password | bool DEFAULT false | |
| active | bool DEFAULT true | |
| created_at | timestamptz DEFAULT now() | |

### Tabulka `coupons`
| sloupec | typ | pozn. |
|---|---|---|
| code | text PK | 4místný, např. `"0473"` |
| state | coupon_state NOT NULL DEFAULT `VOLNA` | |
| retired_reason | text NULL | |
| created_at | timestamptz DEFAULT now() | |
| updated_at | timestamptz DEFAULT now() | |

### Tabulka `coupon_logs` (append-only, nikdy se needituje ani nemaže)
| sloupec | typ | pozn. |
|---|---|---|
| id | bigserial PK | |
| coupon_code | text NOT NULL | (FK→coupons, ale řádek logu zůstává i kdyby…) |
| account_id | int FK→accounts NOT NULL | kdo akci provedl |
| restaurant_id | int FK→restaurants NULL | pobočka (z účtu) |
| action | log_action NOT NULL | |
| result | log_result NOT NULL | |
| is_suspicious | bool DEFAULT false | |
| suspicious_reason | text NULL | může spojovat víc důvodů |
| server_time | timestamptz DEFAULT now() | UTC |
| user_agent | text NULL | |

Indexy: `coupon_logs(coupon_code)`, `coupon_logs(is_suspicious)`, `coupon_logs(server_time)`.

### Stavový automat kupónu
- `VOLNA → K_UPLATNENI` = **vydání**
- `K_UPLATNENI → VOLNA` = **uplatnění** (kupon zpět do oběhu)
- `VOLNA → VOLNA` = **uplatnění přesto (bypass)** — viz §6
- `VOLNA | K_UPLATNENI → VYRAZENA` = **vyřazení** (manažer); `VYRAZENA` je terminální (nereaktivuje se)

---

## 5. Autentizace a autorizace
- **Přihlášení:** `POST /api/auth/login` ověří login+heslo (bcrypt), vytvoří **JWT** (claim: `account_id`, `role`, `restaurant_id`) a nastaví ho jako **`httpOnly`, `SameSite=Lax`, `Secure`** cookie (`Secure` řízeno env `COOKIE_SECURE`). Expirace dlouhá (default 30 dní — restaurace se přihlásí jednou).
- **Hashování hesel:** bcrypt přes passlib.
- **Role-based dependency** v FastAPI: `require_role("operator"|"manager"|"master")`. Hierarchie: `master` smí vše co `manager`; `manager` a `master` smí manažerské endpointy; operátorské akce smí všichni přihlášení (operator i výš pro testování).
- **Baseline UA:** při prvním úspěšném přihlášení operátorského účtu, pokud `baseline_user_agent IS NULL`, ulož aktuální `User-Agent`.
- **Bootstrap master účtu (`seed.py`, volá se při startu nad prázdnou tabulkou `accounts`):** vytvoř účet s rolí `master`, login z env `MASTER_LOGIN`, heslo z env `MASTER_PASSWORD` (zahashuj), `must_change_password=true`. **Nikdy nehardcoduj heslo do kódu.** Pokud už master existuje, nedělej nic.
- **Změna hesla:** `POST /api/auth/change-password`. Pokud má účet `must_change_password=true`, frontend ho po loginu rovnou přesměruje na změnu hesla.
- **Rate-limit** na `/api/auth/login` (např. 5 pokusů / minutu / IP) jako ochrana proti hádání.

---

## 6. Backend — endpointy a logika

**Konvence:** vše pod `/api`. Odpovědi JSON. Chyby standardní HTTP (401 nepřihlášen, 403 špatná role, 404 neexistuje, 409 konflikt stavu). Každá akce měnící stav probíhá v jedné DB transakci spolu se zápisem do `coupon_logs`.

### Auth
| metoda | cesta | role | tělo | chování |
|---|---|---|---|---|
| POST | `/api/auth/login` | — | `{login, password}` | nastaví cookie; vrátí `{role, restaurant_id, must_change_password}` |
| POST | `/api/auth/logout` | přihlášen | — | smaže cookie |
| GET | `/api/auth/me` | přihlášen | — | `{account_id, login, role, restaurant_id, must_change_password}` |
| POST | `/api/auth/change-password` | přihlášen | `{old_password, new_password}` | změní heslo, zruší `must_change_password` |

### Operátorské akce (kupony)
| metoda | cesta | role | tělo | chování |
|---|---|---|---|---|
| GET | `/api/coupons/{code}` | přihlášen | — | **jen čte** stav (neloguje). Vrátí `{code, state, last_issue?}`; 404 pokud kód není v DB |
| POST | `/api/coupons/{code}/issue` | přihlášen | — | atomicky `VOLNA→K_UPLATNENI`; log `VYDANI/OK`. Pokud není `VOLNA` → 409 + aktuální stav |
| POST | `/api/coupons/{code}/redeem` | přihlášen | — | atomicky `K_UPLATNENI→VOLNA`; log `UPLATNENI/OK`. Pokud není `K_UPLATNENI` → 409 + aktuální stav (frontend pak nabídne bypass jen je-li stav `VOLNA`) |
| POST | `/api/coupons/{code}/redeem-bypass` | přihlášen | `{reason}` | povoleno **jen když stav = `VOLNA`**; provede uplatnění (`VOLNA→VOLNA`), log `UPLATNENI/BYPASS`, `is_suspicious=true`, `suspicious_reason` z `reason`. Pokud stav `VYRAZENA` → 409 (zničená karta se neuplatní ani přesto) |

**Atomický přechod (vzor):**
```sql
UPDATE coupons SET state = :new, updated_at = now()
WHERE code = :code AND state = :expected;
-- pokud rowcount = 0 → přechod neproveden (někdo předběhl / špatný stav) → 409
```
Zápis do `coupon_logs` ve stejné transakci. `redeem-bypass` přechod nemění stav fakticky (zůstává `VOLNA`), ale stejně se loguje jako uplatnění.

**Výpočet `is_suspicious` při každé akci měnící stav** (důvody se spojují, oddělené `; `):
- **bypass** → vždy `is_suspicious=true`, důvod = zvolený text z dropdownu.
- **odlišné zařízení** → pokud `account.baseline_user_agent` je nastaven a aktuální UA se materiálně liší → přidej důvod `"odlišné zařízení"`.
- **mimo provozní dobu** → pokud hodina `server_time` (v Europe/Prague) spadá do nočního okna (env `NIGHT_WINDOW_START`/`END`, default 0–6) → přidej důvod `"mimo provozní dobu"`.

### Manažerské pohledy
| metoda | cesta | role | chování |
|---|---|---|---|
| GET | `/api/coupons` | manager | seznam/hledání kupónů (filtr `state`, fulltext `code`) |
| GET | `/api/coupons/{code}/history` | manager | celá časová osa z `coupon_logs` (akce, výsledek, účet, pobočka, čas, podezřelost) |
| POST | `/api/coupons/{code}/retire` | manager | `{reason}` → stav `VYRAZENA`; log `VYRAZENI/OK` |
| POST | `/api/coupons/import` | manager | upload CSV (sloupec `code` povinný); založí chybějící kódy jako `VOLNA`; log `IMPORT`. Vrátí počet přidaných/přeskočených |
| GET | `/api/dashboard/overview` | manager | viz níže |
| GET | `/api/dashboard/suspicious` | manager | seznam `coupon_logs` kde `is_suspicious=true`, filtr dle pobočky/období |

**`/api/dashboard/overview` vrací:**
- `open_liability`: počet kupónů ve stavu `K_UPLATNENI` (celkem) — = nevyplacené odměny v oběhu
- `redemption_rate`: poměr `UPLATNENI` / `VYDANI` za zvolené období
- `fund`: počty `{VOLNA, K_UPLATNENI, VYRAZENA}`
- `by_restaurant`: pole `{restaurant_id, name, issued, redeemed}` za období

### Master (správa)
| metoda | cesta | role | chování |
|---|---|---|---|
| GET/POST | `/api/restaurants` | master | seznam / vytvoření pobočky |
| PUT/DELETE | `/api/restaurants/{id}` | master | úprava / smazání (jen pokud nemá vázané účty/logy; jinak deaktivace) |
| GET/POST | `/api/accounts` | master | seznam / vytvoření účtu (`login`, `role`, `restaurant_id`, počáteční heslo, `must_change_password=true`) |
| POST | `/api/accounts/{id}/reset-password` | master | nastaví nové heslo + `must_change_password=true` |
| POST | `/api/accounts/{id}/toggle-active` | master | aktivace/deaktivace účtu |

---

## 7. Frontend — obrazovky a chování

**Routing podle role** (po loginu `/api/auth/me`):
- nepřihlášen → `/login`
- `must_change_password=true` → `/change-password`
- `operator` → `/scan`
- `manager` / `master` → `/admin` (master navíc vidí sekce Restaurace + Účty)

**PWA:** instalovatelná (manifest, ikony, service worker cachuje app shell). **Akce s kupony jsou vždy online** — service worker necachuje API odpovědi stavů. Při výpadku sítě ukázat jasně „offline, nelze zpracovat".

### `/login`
Login + heslo, velká tlačítka. Po úspěchu přesměrování dle role.

### `/scan` (operátor) — nejdůležitější obrazovka, musí být triviální
- Velké číselné pole (`inputmode="numeric"`) s autofocusem; po dosažení 4 číslic se **automaticky odešle** (`GET /api/coupons/{code}`).
- Tlačítko **„Skenovat"** otevře kameru (html5-qrcode) s **přepínačem blesku (torch)**; po načtení QR vyplní stejné pole a odešle.
- Po načtení stavu zobraz **velký barevný panel** + jedno akční tlačítko:
  - `VOLNA` → neutrální/modrý „VOLNÁ" + tlačítko **VYDAT** (`/issue`).
  - `K_UPLATNENI` → oranžový „K UPLATNĚNÍ" + tlačítko **UPLATNIT** (`/redeem`).
  - po `VYDAT` → zelený „VYDÁNO ✓"; po `UPLATNIT` → zelený „UPLATNĚNO ✓".
  - `VYRAZENA` nebo kód neexistuje → červený „NEPLATNÁ".
  - pokus o uplatnění při stavu `VOLNA` (server vrátí 409) → červený „Nevydáno přes systém" + tlačítko **„Uplatnit přesto"** → otevře **modal s dropdownem důvodů** (povinný výběr) → `/redeem-bypass`.
- Po dokončení akce auto-reset zpět na pole za ~2 s (připraveno na další kartu). Žádné přepínání uživatelů, žádný výběr typu odměny.
- Barvy: **zelená = OK, červená = zamítnuto, oranžová = čeká na uplatnění.**

**Dropdown důvodů bypassu (pevný seznam):** „Jiná pobočka zapomněla vydat", „Technický výpadek při vydání", „Zákazník má platnou kartičku, systém ji nezná", „Jiný důvod".

### `/admin` (manager + master)
- **Overview.vue** — karty s metrikami z `/dashboard/overview`: otevřený závazek (velké číslo), míra uplatnění, stav fondu, tabulka per pobočka.
- **Suspicious.vue** — tabulka podezřelých akcí (`/dashboard/suspicious`): čas, kód, akce, účet, pobočka, důvod. Filtr pobočka/období.
- **CardHistory.vue** — vyhledání kódu → časová osa (`/coupons/{code}/history`).
- **Import.vue** — nahrání CSV (`/coupons/import`), zobrazení výsledku.
- (manager + master) **Retire** — vyřazení karty s důvodem (`/coupons/{code}/retire`), dostupné i z CardHistory.

### Master sekce
- **Restaurants.vue** — CRUD poboček.
- **Accounts.vue** — vytvoření operátorského/manažerského účtu (přiřazení pobočky), reset hesla, aktivace/deaktivace.

---

## 8. Konfigurace (`.env.example`)
```
# Databáze
POSTGRES_USER=promo
POSTGRES_PASSWORD=zmen_me
POSTGRES_DB=promo
DATABASE_URL=postgresql+psycopg://promo:zmen_me@db:5432/promo

# Bezpečnost
JWT_SECRET=vygeneruj_nahodny_dlouhy_retezec
COOKIE_SECURE=true
JWT_EXPIRE_DAYS=30

# Master účet (seed při prvním startu)
MASTER_LOGIN=master
MASTER_PASSWORD=zmen_me_hned

# Heuristika podezřelosti
NIGHT_WINDOW_START=0
NIGHT_WINDOW_END=6

# Doména pro Caddy (automatické HTTPS)
DOMAIN=kupony.tvojedomena.cz

# Volitelné: prefix QR pro ověření formátu
QR_PREFIX=PROMO
```

---

## 9. Docker & nasazení

**`docker-compose.yml`** — tři služby:
- `db`: `postgres:16`, volume `pgdata`, env z `.env`, healthcheck.
- `backend`: build `./backend`, `depends_on: db (healthy)`, env z `.env`. Při startu: spustí Alembic migrace → `seed.py` → Uvicorn na `:8000`.
- `frontend`: build `./frontend` (multi-stage: Node build `dist` → finální stage `caddy:2` který servíruje `dist` a proxuje `/api/*` na `backend:8000`). Porty `80:80`, `443:443`. Volume pro Caddy data (certifikáty).

**`frontend/Caddyfile`:**
```
{$DOMAIN} {
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }
}
```

**`frontend/vite.config.js`** — pro vývoj přidej proxy, ať je dev také same-origin:
```js
server: { proxy: { '/api': 'http://localhost:8000' } }
```

**Kroky nasazení** (detailně a pro laika v `docs/DOKUMENTACE.md`):
1. VPS + A-záznam domény na jeho IP.
2. Instalace Dockeru a Docker Compose.
3. Nahrání projektu, `cp .env.example .env`, vyplnit hesla + doménu.
4. `docker compose up -d --build`.
5. Backend provede migrace a vytvoří master účet.
6. Přihlásit se jako master → změnit heslo → vytvořit pobočky a účty.
7. Vygenerovat karty (`scripts/generate_cards.py`) → importovat CSV v manažerské sekci → vytisknout.
8. Nastavit cron na zálohy (§10).

---

## 10. Zálohy (`scripts/backup.sh`)
- Noční `pg_dump -Fc` přes `docker exec` do `/backups/dump_RRRR-MM-DD.dump`.
- Rotace: ponechat ~14 denních + ~8 týdenních, starší mazat.
- Off-site: dump **zašifrovat** (gpg) a poslat mimo VPS (rclone/rsync do S3-kompatibilního úložiště nebo na druhý stroj).
- Cron: `0 3 * * * /cesta/backup.sh`.
- Dump i **před každou migrací**. Měsíčně otestovat obnovu do dočasné DB.

---

## 11. Akceptační kritéria (hotovo, když platí vše)
1. `docker compose up -d --build` spustí celý systém; web běží na HTTPS na zadané doméně.
2. Master účet se vytvoří ze `.env`, po prvním loginu vynutí změnu hesla.
3. Master vytvoří pobočku a operátorský účet; ten se na telefonu přihlásí jedním loginem a rovnou skenuje.
4. Operátor: zadání/sken kódu → barevný stav → jedno tlačítko; vydání i uplatnění mění stav atomicky; dvě současná uplatnění téhož kódu nezpůsobí dvojí uplatnění.
5. Uplatnění nevydané (`VOLNA`) karty vrátí 409 a nabídne „Uplatnit přesto" s povinným důvodem; akce se zaloguje jako `BYPASS` + `is_suspicious`.
6. Heuristiky `odlišné zařízení` (UA baseline) a `mimo provozní dobu` flagují akce.
7. Manažer vidí přehled (otevřený závazek, míra uplatnění, fond, per pobočka), seznam podezřelých akcí, historii konkrétní karty; umí vyřadit kartu a importovat CSV.
8. Vyřazená karta nejde vydat ani uplatnit (ani přes bypass); historie zůstává.
9. PWA je instalovatelná; skener používá kameru a umí přepnout blesk; bez sítě ukáže „offline".
10. `scripts/backup.sh` vytvoří funkční dump, ze kterého lze obnovit.
11. V repu je `README.md` a `docs/DOKUMENTACE.md`.

---

## 12. Co NEdělat
- Žádné IP ověřování, žádný device token v LocalStorage.
- Žádné přepínání uživatelů na frontendu (jeden účet = jedna pobočka).
- Neukládat typ odměny ani expiraci.
- Nehardcodovat žádná hesla ani `JWT_SECRET` do kódu — vše z env.
- Neblokovat provoz tvrdě — podezřelé akce se logují, ne zakazují (kromě vyřazené karty).
