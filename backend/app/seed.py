from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.models import Account, AccountRole


def seed_master(db: Session) -> None:
    """Vytvoří master účet při prvním spuštění. Pokud účty již existují, nic nedělá."""
    if db.query(Account).first():
        return

    master = Account(
        login=settings.MASTER_LOGIN,
        password_hash=hash_password(settings.MASTER_PASSWORD),
        role=AccountRole.master,
        must_change_password=True,
    )
    db.add(master)
    db.commit()
