from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# El pooler de Supabase cierra las conexiones que quedan un rato sin uso, pero
# el pool de SQLAlchemy las conserva y las vuelve a entregar ya muertas. Sin
# estas dos opciones, la primera acción después de un rato de inactividad
# fallaba con un error 500 —incluido el propio inicio de sesión— y recién el
# segundo intento funcionaba, porque para entonces la conexión rota ya se había
# descartado.
#
#   pool_pre_ping: comprueba la conexión con una consulta mínima antes de
#     entregarla, y la reemplaza sola si está caída.
#   pool_recycle: además descarta las que llevan más de cinco minutos abiertas,
#     por debajo del tiempo de espera del pooler, para no depender solo del
#     reintento.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
