from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_org, get_current_user
from app.core.errors import DomainError
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import (
    MessageResponse,
    OrganizationResponse,
    ResendVerificationRequest,
    SignupRequest,
    SignupResponse,
    Token,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_organization_with_admin,
    get_user_by_email,
    issue_verification_token,
    verify_email_token,
)
from app.services.email_service import send_verification_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["auth"])

# Mensaje único para el alta y el reenvío: no revela si un correo ya está
# registrado, lo que evitaría enumerar cuentas existentes.
_MENSAJE_VERIFICACION = (
    "Te enviamos un correo para verificar tu dirección. Revisá tu bandeja de "
    "entrada (y la carpeta de spam) y hacé clic en el enlace para activar la cuenta."
)


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Alta pública: crea una organización nueva y su primer administrador.

    Es el único punto donde se puede obtener el rol de administrador, y solo
    sobre la organización recién creada.
    """
    if get_user_by_email(db, payload.email):
        raise DomainError(
            "Ya existe una cuenta con ese correo electrónico. "
            "Probá iniciar sesión o usar otra dirección.",
            field="email",
        )

    organization, user, token = create_organization_with_admin(
        db,
        organization_name=payload.organization_name,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        phone=payload.phone,
    )

    # Solo se envía el correo de verificación. La bienvenida se manda recién
    # cuando el usuario confirma su dirección: hasta entonces no puede iniciar
    # sesión, y recibir los dos correos a la vez resultaba contradictorio.
    background_tasks.add_task(
        send_verification_email,
        user_email=user.email,
        token=token,
        organization_name=organization.name,
    )

    return SignupResponse(
        message=_MENSAJE_VERIFICACION,
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse.model_validate(organization),
    )


@router.get("/verify-email", response_model=MessageResponse)
def verify_email(
    background_tasks: BackgroundTasks,
    token: str = Query(..., min_length=10),
    db: Session = Depends(get_db),
):
    user = verify_email_token(db, token)
    if not user:
        raise DomainError(
            "El enlace de verificación no es válido o ya venció. "
            "Pedí uno nuevo desde la pantalla de inicio de sesión.",
            field="token",
        )

    # Ahora sí la cuenta puede operar, así que la bienvenida es correcta.
    background_tasks.add_task(send_welcome_email, user_email=user.email)

    return MessageResponse(
        message="¡Listo! Tu correo quedó verificado. Ya podés iniciar sesión."
    )


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, payload.email)

    # Se responde siempre lo mismo, exista o no la cuenta.
    if user and not user.is_email_verified:
        token = issue_verification_token(user)
        db.commit()
        background_tasks.add_task(
            send_verification_email, user_email=user.email, token=token
        )

    return MessageResponse(message=_MENSAJE_VERIFICACION)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise DomainError(
            "El correo electrónico o la contraseña no son correctos.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        raise DomainError(
            "Tu cuenta está desactivada. Contactá al administrador de tu organización.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if not user.is_email_verified:
        raise DomainError(
            "Todavía no verificaste tu correo electrónico. Revisá tu bandeja de "
            "entrada o pedí que te reenviemos el enlace.",
            status_code=status.HTTP_403_FORBIDDEN,
            field="email",
        )

    return Token(access_token=create_access_token(user.email))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/my-organization", response_model=OrganizationResponse)
def my_organization(organization: Organization = Depends(get_current_org)):
    return organization
