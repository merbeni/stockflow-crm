from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _no_autorizado() -> DomainError:
    return DomainError(
        "Tu sesión expiró o no es válida. Iniciá sesión nuevamente.",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        email = decode_token(token)
    except JWTError:
        raise _no_autorizado()

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise _no_autorizado()

    if not user.is_active:
        raise DomainError(
            "Tu cuenta fue desactivada. Contactá al administrador de tu organización.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if not user.is_email_verified:
        raise DomainError(
            "Tenés que verificar tu correo electrónico antes de usar la aplicación.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return user


def get_current_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    """Organización a la que pertenece el usuario autenticado."""
    organization = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )
    if organization is None:
        raise _no_autorizado()
    return organization


def get_current_org_id(current_user: User = Depends(get_current_user)) -> int:
    """
    Identificador de la organización activa.

    Es la dependencia que usan los routers para acotar cada consulta: ningún
    registro de otra organización debe ser accesible, ni siquiera conociendo su ID.
    """
    return current_user.organization_id


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependencia para las rutas que exigen rol de administrador."""
    if current_user.role != UserRole.admin:
        raise DomainError(
            "Necesitás permisos de administrador para realizar esta acción.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user
