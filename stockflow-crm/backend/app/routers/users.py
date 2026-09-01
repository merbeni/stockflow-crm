"""
Administración de usuarios dentro de una organización.

Todas las rutas exigen rol de administrador y operan exclusivamente sobre la
organización del usuario autenticado.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.errors import DomainError, NotFoundError
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.auth_service import (
    count_active_admins,
    create_user,
    get_user_by_email,
)
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/users", tags=["users"])

_SIN_ADMIN = (
    "La organización tiene que conservar al menos un administrador activo. "
    "Asigná el rol a otra persona antes de aplicar este cambio."
)


def _get_org_user(db: Session, user_id: int, organization_id: int) -> User:
    """
    Busca un usuario dentro de la organización activa.

    Si pertenece a otra organización se responde 404 y no 403: informar que
    existe ya sería filtrar datos de otro cliente.
    """
    user = (
        db.query(User)
        .filter(User.id == user_id, User.organization_id == organization_id)
        .first()
    )
    if not user:
        raise NotFoundError("No encontramos ese usuario en tu organización.")
    return user


@router.get("", response_model=list[UserResponse])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .filter(User.organization_id == admin.organization_id)
        .order_by(User.created_at)
        .all()
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if get_user_by_email(db, payload.email):
        raise DomainError(
            "Ya existe una cuenta con ese correo electrónico.", field="email"
        )

    user, token = create_user(
        db,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        organization_id=admin.organization_id,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    background_tasks.add_task(
        send_verification_email,
        user_email=user.email,
        token=token,
        organization_name=admin.organization.name,
    )
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update(
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _get_org_user(db, user_id, admin.organization_id)
    data = payload.model_dump(exclude_unset=True)

    nuevo_rol = data.get("role", user.role)
    sigue_activo = data.get("is_active", user.is_active)
    deja_de_ser_admin = user.role == UserRole.admin and (
        nuevo_rol != UserRole.admin or not sigue_activo
    )

    # Sin este control, un administrador podría dejar a la organización sin
    # ningún admin y nadie podría volver a gestionar usuarios.
    if deja_de_ser_admin and count_active_admins(
        db, admin.organization_id, exclude_user_id=user.id
    ) == 0:
        raise DomainError(_SIN_ADMIN)

    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _get_org_user(db, user_id, admin.organization_id)

    if user.id == admin.id:
        raise DomainError(
            "No podés eliminar tu propia cuenta. Pedile a otro administrador "
            "que lo haga."
        )

    if user.role == UserRole.admin and count_active_admins(
        db, admin.organization_id, exclude_user_id=user.id
    ) == 0:
        raise DomainError(_SIN_ADMIN)

    db.delete(user)
    db.commit()
