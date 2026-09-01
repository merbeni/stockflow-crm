import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.organization import Organization
from app.models.user import User, UserRole

# Ventana de validez del enlace de verificación de correo.
VERIFICATION_TTL = timedelta(hours=24)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "organizacion"


def generate_unique_slug(db: Session, name: str) -> str:
    """Slug legible y único para la organización."""
    base = _slugify(name)[:100]
    slug = base
    sufijo = 2
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base}-{sufijo}"
        sufijo += 1
    return slug


def issue_verification_token(user: User) -> str:
    """Genera (o renueva) el token de verificación de correo del usuario."""
    token = secrets.token_urlsafe(48)
    user.email_verification_token = token
    user.email_verification_expires_at = datetime.now(timezone.utc) + VERIFICATION_TTL
    return token


def create_organization_with_admin(
    db: Session,
    *,
    organization_name: str,
    email: str,
    password: str,
    full_name: str,
    phone: str | None,
) -> tuple[Organization, User, str]:
    """
    Alta pública: crea la organización y su primer administrador.

    Ambos se insertan en la misma transacción; si algo falla, no queda una
    organización huérfana sin usuarios.
    """
    organization = Organization(
        name=organization_name,
        slug=generate_unique_slug(db, organization_name),
    )
    db.add(organization)
    db.flush()

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=UserRole.admin,
        organization_id=organization.id,
        full_name=full_name,
        phone=phone,
        is_active=True,
        is_email_verified=False,
    )
    token = issue_verification_token(user)
    db.add(user)

    db.commit()
    db.refresh(organization)
    db.refresh(user)
    return organization, user, token


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: UserRole,
    organization_id: int,
    full_name: str | None = None,
    phone: str | None = None,
) -> tuple[User, str]:
    """Alta de un usuario dentro de una organización existente."""
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        organization_id=organization_id,
        full_name=full_name,
        phone=phone,
        is_active=True,
        is_email_verified=False,
    )
    token = issue_verification_token(user)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, token


def verify_email_token(db: Session, token: str) -> User | None:
    """
    Consume un token de verificación.

    Devuelve el usuario si el token es válido y no expiró; ``None`` en cualquier
    otro caso. El token es de un solo uso: se borra al confirmarse.
    """
    user = db.query(User).filter(User.email_verification_token == token).first()
    if not user:
        return None

    expira = user.email_verification_expires_at
    if expira is not None:
        # La columna puede volver sin zona horaria según el motor de base de datos.
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        if expira < datetime.now(timezone.utc):
            return None

    user.is_email_verified = True
    user.email_verification_token = None
    user.email_verification_expires_at = None
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def count_active_admins(db: Session, organization_id: int, exclude_user_id: int | None = None) -> int:
    """Cantidad de administradores activos de la organización."""
    query = db.query(User).filter(
        User.organization_id == organization_id,
        User.role == UserRole.admin,
        User.is_active.is_(True),
    )
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.count()
