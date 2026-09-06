"""
Configuración del pool de conexiones.

El pooler de Supabase cierra las conexiones que quedan un rato sin uso, pero el
pool de SQLAlchemy las conserva y las vuelve a entregar ya muertas. Con la
configuración por omisión, la primera acción después de un rato de inactividad
—incluido el propio inicio de sesión— fallaba con un error 500, y recién el
segundo intento funcionaba porque para entonces la conexión rota ya se había
descartado.

Las pruebas de acá abajo son de dos clases. La primera comprueba el
comportamiento con una base de verdad, cerrando la conexión por debajo para
imitar lo que hace el pooler. La segunda mira la configuración del motor real,
que no se puede ejercitar en la suite porque apunta a PostgreSQL y estas
pruebas corren sobre SQLite en memoria.
"""
from sqlalchemy import create_engine, text


class TestConexionesCaidas:
    def test_una_conexion_muerta_se_reemplaza_sola(self, tmp_path):
        motor = create_engine(
            f"sqlite:///{tmp_path / 'prueba.db'}",
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )
        try:
            with motor.connect() as conexion:
                conexion.execute(text("SELECT 1"))
                cruda = conexion.connection.dbapi_connection

            # El servidor corta por su cuenta: la conexión vuelve al pool ya
            # inservible y es la única que hay para entregar.
            cruda.close()

            with motor.connect() as conexion:
                assert conexion.execute(text("SELECT 1")).scalar() == 1
        finally:
            motor.dispose()

    def test_sin_la_comprobacion_previa_la_conexion_muerta_falla(self, tmp_path):
        """Deja a la vista qué pasaba antes, para que el arreglo no parezca de más."""
        motor = create_engine(
            f"sqlite:///{tmp_path / 'prueba.db'}",
            pool_pre_ping=False,
            pool_size=1,
            max_overflow=0,
        )
        try:
            with motor.connect() as conexion:
                conexion.execute(text("SELECT 1"))
                cruda = conexion.connection.dbapi_connection
            cruda.close()

            fallo = None
            try:
                with motor.connect() as conexion:
                    conexion.execute(text("SELECT 1"))
            except Exception as exc:
                fallo = exc
            assert fallo is not None
        finally:
            motor.dispose()


class TestMotorDeLaAplicacion:
    def test_el_motor_comprueba_la_conexion_antes_de_entregarla(self):
        from app.db.session import engine

        assert engine.pool._pre_ping is True

    def test_las_conexiones_se_renuevan_antes_del_corte_del_pooler(self):
        from app.db.session import engine

        # Por debajo del tiempo de espera del pooler, para no depender solo de
        # que la comprobación previa detecte el corte.
        assert 0 < engine.pool._recycle <= 300
