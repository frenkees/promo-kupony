#!/usr/bin/env bash
# Zálohovací skript pro PostgreSQL databázi přes Docker Compose.
set -euo pipefail

# --- Konfigurace ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
KEEP_DAILY=14
KEEP_WEEKLY=8

# --- Helper ---
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Záloha zahájena ==="

# --- Adresář zálohy ---
mkdir -p "$BACKUP_DIR"

# --- Načtení .env (pro POSTGRES_USER, POSTGRES_DB) ---
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

POSTGRES_USER="${POSTGRES_USER:-promo}"
POSTGRES_DB="${POSTGRES_DB:-promo}"

# --- Dump ---
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
DUMP_FILE="$BACKUP_DIR/dump_${TIMESTAMP}.dump"

log "pg_dump → $(basename "$DUMP_FILE")"
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
    > "$DUMP_FILE"

log "Dump hotov: $(du -h "$DUMP_FILE" | cut -f1)"

# --- Rotace ---
# Seřadit od nejnovějšího
mapfile -t ALL_DUMPS < <(ls -1t "$BACKUP_DIR"/dump_*.dump 2>/dev/null || true)
TOTAL=${#ALL_DUMPS[@]}

if [ "$TOTAL" -gt "$KEEP_DAILY" ]; then
    # Starší než posledních 14 → kandidáti na smazání
    CANDIDATES=("${ALL_DUMPS[@]:$KEEP_DAILY}")
    # Seřadit od nejstaršího (pro výběr týdenních)
    mapfile -t OLDEST_FIRST < <(printf '%s\n' "${CANDIDATES[@]}" | sort)

    WEEKLY_KEPT=0
    for i in "${!OLDEST_FIRST[@]}"; do
        dump="${OLDEST_FIRST[$i]}"
        # Každý 7. soubor (index 0, 7, 14...) uchovat jako týdenní zálohu
        if [ $(( i % 7 )) -eq 0 ] && [ "$WEEKLY_KEPT" -lt "$KEEP_WEEKLY" ]; then
            WEEKLY_KEPT=$(( WEEKLY_KEPT + 1 ))
            log "Týdenní záloha zachována: $(basename "$dump")"
        else
            log "Mazání: $(basename "$dump")"
            rm -f "$dump"
        fi
    done
fi

# --- Volitelný off-site upload (rclone + gpg) ---
if [ -n "${RCLONE_REMOTE:-}" ]; then
    log "Šifruji dump pro off-site upload..."
    GPG_FILE="${DUMP_FILE}.gpg"
    # Passphrase přes stdin, ne přes CLI arg (neviditelné v `ps aux`)
    printf '%s' "${GPG_PASSPHRASE:-}" | gpg --batch --yes --symmetric --cipher-algo AES256 \
        --passphrase-fd 0 -o "$GPG_FILE" "$DUMP_FILE"
    log "Nahrávám do $RCLONE_REMOTE ..."
    rclone copy "$GPG_FILE" "$RCLONE_REMOTE"
    rm -f "$GPG_FILE"
    log "Off-site upload dokončen."
fi

log "=== Záloha dokončena ==="

# Pro denní zálohu ve 3:00 přidej do crontab -e:
# 0 3 * * * cd /cesta/k/projektu && ./scripts/backup.sh >> backups/backup.log 2>&1
