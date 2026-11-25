# Analýza projektu: promo-kupony

> Verze: výstup z Claude Code, dosud nenasazeno, netestováno.  
> Stack: FastAPI · SQLAlchemy 2 · PostgreSQL 16 · Vue 3 · Vite · Caddy · Docker Compose

---

## Shrnutí

Projekt je architekturálně kvalitní a dobře strukturovaný. Klíčová bezpečnostní opatření (JWT httpOnly cookie, bcrypt, atomické DB transakce, auditní log) jsou implementována správně. Většina nalezených problémů jsou drobné chyby UX, nedokončená konfigurovatelnost a malé odchylky od specifikace. Dvě závažné chyby jsou v oblasti nesprávných bypass důvodů a chybějícího loginu uživatele v admin hlavičce.

---

## Kategorizace nálezů

| ID | Oblast | Závažnost | Stručný popis |
|----|--------|-----------|---------------|
| B1 | Frontend | **Závažná** | Bypass důvody v Scan.vue neodpovídají specifikaci |
| B2 | Frontend | **Závažná** | `auth.login()` neplní `account.login` → admin header prázdný |
| B3 | Frontend | **Závažná** | QR prefix hardcoded jako `'PROMO-'`, nereaguje na env |
| B4 | Frontend | Střední | Datum filter na dashboardu nezohledňuje timezone |
| B5 | Frontend | Střední | Po resetu scan input ztratí focus |
| B6 | Frontend | Střední | Chyba při `doIssue()` zobrazí "NEZNÁMÝ KÓD" místo správného hlášení |
| B7 | Frontend | Střední | `CardHistory.vue` má `maxlength=10` místo 4 |
| B8 | Backend | Střední | `GET /coupons` bez stránkování |
| B9 | Backend | Střední | UA porovnání v heuristice je striktní `==`, nikoli "materiálně odlišné" |
| B10 | Backend | Nízká | `config.py` nezahrnuje `QR_PREFIX` z env |
| B11 | Infrastruktura | Nízká | Backend Dockerfile nemá `HEALTHCHECK` |
| B12 | Infrastruktura | Nízká | Frontend v `docker-compose.yml` nečeká na zdraví backendu |
| B13 | Backend | Nízká | `requirements.txt` používá wildcard verzování (`.*`) |
| B14 | Infrastruktura | Nízká | `backup.sh` předává GPG passphrase přes CLI argument |
| B15 | Frontend | Nízká | PWA manifest kombinuje `any` a `maskable` v jedné ikoně |
| B16 | Frontend | Nízká | Scan.vue nezobrazuje `last_issue` operátorovi |
| B17 | Frontend | Nízká | V Accounts.vue nelze vytvořit účet role `master` |

---

## Detailní popis nálezů

---

### B1 — Bypass důvody neodpovídají specifikaci

**Soubor:** `frontend/src/views/Scan.vue`  
**Závažnost:** Závažná  

**Popis:**  
Specifikace (§7) definuje přesný seznam důvodů pro bypass dropdown:
```
"Jiná pobočka zapomněla vydat"
"Technický výpadek při vydání"
"Zákazník má platnou kartičku, systém ji nezná"
"Jiný důvod"
```

Ve Scan.vue jsou ale implementovány zcela jiné texty:
```javascript
const BYPASS_REASONS = [
  'Zákazník prokáže nákup účtenkou',
  'Technická závada skeneru',
  'Operátor ručí za vydání',
  'Jiný důvod (schváleno manažerem)',
]
```

Tím pádem texty v audit logu (sloupec `suspicious_reason`) neodpovídají tomu, co bylo zadáno ve specifikaci. Manažer v přehledu uvidí jiné důvody, než na které byl připraven.

---

### B2 — Admin header nezobrazuje jméno přihlášeného uživatele

**Soubory:** `frontend/src/stores/auth.js`, `frontend/src/views/admin/AdminLayout.vue`  
**Závažnost:** Závažná  

**Popis:**  
Po přihlášení nastaví `login()` v auth store objekt `account` pouze s rolí:
```javascript
account.value = { role: data.role }
```
Přitom `AdminLayout.vue` zobrazuje:
```html
<span class="text-sm text-gray-400">{{ auth.account?.login }}</span>
```
Protože `account.login` neexistuje, hlavička zobrazuje prázdný řetězec místo přihlašovacího jména. Tento stav trvá, dokud router guard nezavolá `auth.init()` znovu — ale `initDone` je již `true`, takže se `fetchMe()` nezavolá automaticky.

---

### B3 — QR prefix hardcoded, env proměnná ignorována

**Soubory:** `frontend/src/views/Scan.vue`, `.env.example`, `frontend/vite.config.js`  
**Závažnost:** Závažná  

**Popis:**  
Soubor `.env.example` deklaruje `QR_PREFIX=PROMO`, ale tato hodnota není nikde předávána do frontendového buildu (chybí `VITE_QR_PREFIX` v `vite.config.js`). Ve `Scan.vue` je prefix hardcoded:
```javascript
const extracted = payload.startsWith('PROMO-') ? payload.slice(6) : payload
```
Kdokoli bude chtít projekt nasadit s jiným prefixem, musí editovat zdrojový kód. Navíc `config.py` (backend) tuto proměnnou vůbec nenačítá — je definována jen v `.env.example`.

---

### B4 — Datum filter v dashboardu ignoruje timezone

**Soubory:** `frontend/src/views/admin/Overview.vue`, `frontend/src/views/admin/Suspicious.vue`, `backend/app/routers/dashboard.py`  
**Závažnost:** Střední  

**Popis:**  
Frontend odesílá datum bez timezone informace:
```javascript
if (dateFrom.value) params.date_from = dateFrom.value + 'T00:00:00'
// výsledek: "2024-06-01T00:00:00" — žádná timezone
```
Backend přijímá `Optional[datetime]` a FastAPI to parsuje jako naive datetime (bez tz). PostgreSQL pak srovnává s `timestamptz` sloupcem `server_time` (který je v UTC). V praxi to znamená, že pro CZ uživatele (UTC+1 nebo UTC+2) bude filtr posunutý o 1–2 hodiny — například filtr "od 1. 6. 2024" ve skutečnosti začíná od 1. 6. 2024 00:00:00 UTC, tedy 2:00 místního času.

---

### B5 — Input pro kód ztratí focus po úspěšném resetu

**Soubor:** `frontend/src/views/Scan.vue`  
**Závažnost:** Střední  

**Popis:**  
Funkce `scheduleReset()` po 2 s vynuluje `status` a `currentCode`, ale explicitně neobnoví focus na input. Atribut `autofocus` funguje jen při prvním načtení stránky. Na mobilním zařízení se po dokončení každé akce musí operátor znovu dotknout vstupního pole — narušuje plynulost operace.

---

### B6 — Chybná chybová zpráva po neúspěšném vydání

**Soubor:** `frontend/src/views/Scan.vue`  
**Závažnost:** Střední  

**Popis:**  
Funkce `doIssue()` má generický `catch` blok:
```javascript
} catch {
    status.value = 'NOT_FOUND'
    loading.value = false
}
```
Pokud server vrátí 409 (karta není ve stavu VOLNA — například je ve stavu K_UPLATNENI a někdo ji vydal dříve), operátor uvidí panel "NEZNÁMÝ KÓD" a červeně "Karta nebyla nalezena v systému" — což je zavádějící. Stejný problém je v `doBypass()`. Správně by se měl parsovat `e.response?.status` a `e.response?.data?.current_state`.

---

### B7 — CardHistory: maxlength vstupu je 10 místo 4

**Soubor:** `frontend/src/views/admin/CardHistory.vue`  
**Závažnost:** Střední  

**Popis:**  
```html
<input maxlength="10" ...>
```
Kódy jsou 4místné. Limit 10 umožní zadání neplatně dlouhých řetězců. Backend sice vrátí 404, ale UX je nekonzistentní. Správná hodnota je `maxlength="4"`.

---

### B8 — GET /coupons bez stránkování

**Soubor:** `backend/app/services/coupons.py`, `backend/app/routers/coupons.py`  
**Závažnost:** Střední  

**Popis:**  
Endpoint `GET /api/coupons` vrátí všechny kupony najednou bez limitu nebo stránkování. Při plném fondu (1000–9999 = max 9000 kódů) vrátí celou tabulku v jednom JSON payloadu. Pro manažerský přehled kartiček to může způsobit pomalé načítání. Doporučeno přidat parametry `limit` + `offset` nebo `page`.

---

### B9 — UA heuristika používá striktní porovnání místo "materiální odlišnosti"

**Soubor:** `backend/app/services/audit.py`  
**Závažnost:** Střední  

**Popis:**  
Specifikace říká: "pokud baseline_user_agent je nastaven a aktuální UA se **materiálně liší**". Implementace:
```python
if (
    account.baseline_user_agent
    and user_agent
    and account.baseline_user_agent != user_agent
):
    reasons.append("odlišné zařízení")
```
Pouhá aktualizace prohlížeče (např. Chrome 124 → Chrome 125) změní User-Agent string a vygeneruje falešně pozitivní "odlišné zařízení" pro každého operátora po každé browserové aktualizaci. Vhodnější by bylo ignorovat verze v UA stringu (parsovat jen prohlížeč + OS, nebo porovnávat přes Levenshteinovu vzdálenost/regex).

---

### B10 — `config.py` nenačítá `QR_PREFIX`

**Soubory:** `backend/app/config.py`, `.env.example`  
**Závažnost:** Nízká  

**Popis:**  
`.env.example` obsahuje `QR_PREFIX=PROMO`, ale třída `Settings` v `config.py` tuto proměnnou nezahrnuje. Backend ji tedy vůbec nepoužívá. Pokud by se v budoucnu mělo validovat QR payload na backendu (např. ověření, že naskenovaný kód odpovídá expected formátu), tato hodnota chybí.

---

### B11 — Backend Dockerfile nemá HEALTHCHECK

**Soubor:** `backend/Dockerfile`  
**Závažnost:** Nízká  

**Popis:**  
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Chybí `HEALTHCHECK` instrukce. Docker tedy nemůže detekovat, zda backend container skutečně odpovídá na požadavky. Problematické při `depends_on` s `condition: service_healthy` — to je sice definováno jen pro `db`, ale bez healthchecku backendu nelze backend správně monitorovat ani restartovat při selhání.

Doporučeno přidat:
```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')"
```
nebo dedikovaný `/health` endpoint.

---

### B12 — `docker-compose.yml`: frontend nečeká na zdraví backendu

**Soubor:** `docker-compose.yml`  
**Závažnost:** Nízká  

**Popis:**  
```yaml
frontend:
    depends_on:
        - backend   # bez condition: service_healthy
```
Narozdíl od `backend`, který čeká na `db: condition: service_healthy`, Caddy (frontend) se spustí ihned jak se backend container spustí — ne až když backend skutečně naslouchá. Při pomalém startu backendu (migrace, seed) může Caddy začít proxovat požadavky na neready backend a první requesty selžou s 502. Doporučeno přidat healthcheck na backend a použít `condition: service_healthy`.

---

### B13 — Wildcard verzování v `requirements.txt`

**Soubor:** `backend/requirements.txt`  
**Závažnost:** Nízká  

**Popis:**  
```
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy==2.0.*
```
Wildcard `.*` povoluje instalaci jakékoli patch verze, ale negarantuje reprodukovatelnost buildu v čase. Při přebuildu za 6 měsíců může pip nainstalovat novější patch verzi s breaking změnou. Pro produkci doporučeno vygenerovat `requirements-lock.txt` přes `pip freeze` a jeho použití v Dockerfile.

---

### B14 — `backup.sh`: GPG passphrase předána přes CLI

**Soubor:** `scripts/backup.sh`  
**Závažnost:** Nízká  

**Popis:**  
```bash
gpg --batch --yes --symmetric --cipher-algo AES256 \
    --passphrase "${GPG_PASSPHRASE:-}" -o "$GPG_FILE" "$DUMP_FILE"
```
Předání passphrase přes CLI argument `--passphrase` ji viditelně vystaví v `ps aux` a v shell historii. Bezpečnější alternativa je `--passphrase-fd 0` s pipe:
```bash
echo "$GPG_PASSPHRASE" | gpg --batch --yes --symmetric --cipher-algo AES256 \
    --passphrase-fd 0 -o "$GPG_FILE" "$DUMP_FILE"
```

---

### B15 — PWA manifest kombinuje `any` a `maskable` v jedné ikoně

**Soubor:** `frontend/vite.config.js`  
**Závažnost:** Nízká  

**Popis:**  
```javascript
{
    src: '/icon.svg',
    sizes: 'any',
    type: 'image/svg+xml',
    purpose: 'any maskable',   // oba purpose na jedné ikoně
}
```
Kombinace `purpose: 'any maskable'` na jednom SVG je technicky přípustná, ale doporučuje se mít separátní ikonu pro maskable (s "safe zone" paddingem), jinak Android home screen může ikonu oříznout nevhodně. Doporučeno vytvořit zvláštní maskable PNG (192×192, 512×512) se safe zone paddingem.

---

### B16 — `last_issue` je fetchováno ale nikde nezobrazeno

**Soubor:** `frontend/src/views/Scan.vue`  
**Závažnost:** Nízká  

**Popis:**  
Backend u `GET /coupons/{code}` vrací `last_issue` (timestamp posledního vydání). Scan.vue tuto hodnotu přijme, ale zobrazuje pouze `data.state` a `last_issue` ignoruje:
```javascript
const { data } = await api.get(`/coupons/${val}`)
status.value = data.state
// data.last_issue není použito
```
Pro operátora by bylo užitečné vidět "Vydáno: 3. 6. 2024 14:23" v panelu K_UPLATNENI. Nebyla implementována žádná informace o době vydání.

---

### B17 — V Accounts.vue nelze vytvořit účet role `master`

**Soubor:** `frontend/src/views/admin/Accounts.vue`  
**Závažnost:** Nízká  

**Popis:**  
Select pro roli v create formuláři nabízí pouze `operator` a `manager`:
```html
<option value="operator">Operátor</option>
<option value="manager">Manažer</option>
```
Backend `POST /api/accounts` je schopen vytvořit i `master` roli (validace `AccountRole(body.role)` to povolí). Pokud by bylo třeba vytvořit druhého master účtu, není to možné přes UI — je třeba to udělat přímo přes API nebo ručně do DB. Specifikace to explicitně nezakazuje. Pokud je záměrem pouze jeden master účet (seed), je to v pořádku, ale mělo by být zdokumentováno.

---

## Co je naopak implementováno správně

- Atomické DB transakce s `WHERE code = :code AND state = :expected` — race condition protection funguje správně
- JWT httpOnly cookie, SameSite=Lax, Secure flag z env — bezpečnostní model je správný
- Alembic migrace spuštěné při startu v `lifespan` — správný přístup
- Role hierarchie (`master ≥ manager ≥ operator`) a `require_role()` dependency — čisté a rozšiřitelné
- Auditní log je append-only, `coupon_code` není FK constraint (log přežije i příp. změny kuponu)
- CORS problém vyřešen elegantně přes same-origin + Caddy proxy
- Service worker správně necachuje API odpovědi, offline banner funguje
- Offline detekce v App.vue přes `navigator.onLine` a event listenery
- `import_csv` správně zvládá UTF-8 BOM (`utf-8-sig`)
- Noční okno heuristika správně zvládá přechod přes půlnoc (NIGHT_WINDOW_START > NIGHT_WINDOW_END)
- `seed_master()` idempotentní — neopakuje se při restartu
- Backup rotace (14 denních + 8 týdenních) správně implementována

---

## Doporučené pořadí oprav

1. **B1** — Bypass důvody (přepsat na texty ze spec)
2. **B2** — Login v admin hlavičce (doplnit `login` do `account.value` po loginu)
3. **B3** — QR prefix (přidat `VITE_QR_PREFIX` do vite.config + env)
4. **B4** — Timezone v datum filtrech
5. **B6** — Chybový stav při neúspěšném vydání
6. **B7** — `maxlength="4"` v CardHistory
7. **B5** — Refocus input po resetu
8. **B9** — UA porovnání (alespoň ignore verze)
9. **B11, B12** — Healthchecky v Docker
10. Ostatní nízké priority dle potřeby

