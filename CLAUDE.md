# Projekt: Systém promo kuponů — pravidla pro Claude Code

Tento repozitář staví aplikaci pro správu papírových promo kuponů v síti restaurací (PWA + FastAPI + PostgreSQL + Docker + Caddy).

## Zdroj pravdy
- **`SPECIFIKACE.md`** je závazné technické zadání. Vždy se jím řiď. Pokud něco ve specifikaci není, ZEPTEJ SE, než budeš improvizovat.
- **`docs/DOKUMENTACE.md`** je uživatelská dokumentace pro laika; needituj ji bez výslovné žádosti.
- **`scripts/generate_cards.py`** je hotový skript, needituj ho.

## Fázovaný build (důležité — nestavěj všechno najednou)
Postav v těchto fázích a po každé se zastav a počkej na revizi:
1. **Kostra backendu:** SQLAlchemy modely podle §4, Alembic migrace, FastAPI app skeleton, auth (login, change-password, role dependency), seed master účtu z env. `requirements.txt`, `Dockerfile`.
2. **Operátorské endpointy:** lookup, issue, redeem, redeem-bypass + atomické přechody + audit logging + heuristiky podezřelosti (baseline UA, noční okno, bypass).
3. **Manažerské endpointy:** dashboard/overview, dashboard/suspicious, coupons/{code}/history, retire, CSV import.
4. **Master endpointy:** restaurants CRUD, accounts mgmt, reset-password, toggle-active.
5. **Frontend kostra:** Vue 3 + Vite + Tailwind + Pinia + Router + axios + vite-plugin-pwa + login obrazovka.
6. **Operátorská obrazovka `/scan`** s html5-qrcode skenerem (s torch), barevným status panelem a modalem pro bypass.
7. **Manažerská administrace:** Overview, Suspicious, CardHistory, Import, vyřazení karty.
8. **Master sekce:** Restaurants, Accounts.
9. **Docker & Caddy:** `docker-compose.yml`, frontend multi-stage `Dockerfile` s Caddy, `Caddyfile`, `.env.example`, `README.md`.
10. **Zálohy a finální kontrola:** `scripts/backup.sh`, projetí všech 11 akceptačních kritérií z §11.

## Konvence
- Prózu a komentáře česky. Identifikátory (proměnné, tabulky, sloupce, endpointy) anglicky přesně podle specifikace.
- Časy ukládat v **UTC**, zobrazovat v **Europe/Prague**.
- **Atomické přechody** stavu kuponu (podmíněný UPDATE + zápis logu v jedné transakci) jsou POVINNÉ — bez výjimek.
- **Nikdy nehardcoduj** hesla, `JWT_SECRET` ani žádné jiné tajemství. Vše z `.env`.
- Frontend a API jsou **same-origin** (Caddy proxuje `/api`). Žádné CORS hacky.
- Žádné IP ověřování, žádný device token v LocalStorage.
- Vue komponenty psát s `<script setup>` (Composition API).

## Workflow s uživatelem
- Před implementací fáze: navrhni plán a počkej na schválení (plan mode).
- Po dokončení fáze: shrň, co je hotové, jaké soubory přibyly/změnily se, a co ještě zbývá k akceptačním kritériím dané fáze.
- Pokud narazíš na nejednoznačnost ve specifikaci, zeptej se — neimprovizuj.
