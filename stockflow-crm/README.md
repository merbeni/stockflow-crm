# StockFlow CRM

Mini CRM para negocios de ecommerce — gestión de clientes, inventario, proveedores y procesamiento automático de facturas de proveedores con IA (Gemini 2.5 Flash).

> **Proyecto de fin de grado — Técnico en Programación**

---

## Tabla de contenidos

1. [Descripción general](#descripción-general)
2. [Stack tecnológico](#stack-tecnológico)
3. [Requisitos previos](#requisitos-previos)
4. [Configuración del entorno](#configuración-del-entorno)
5. [Base de datos](#base-de-datos)
6. [Levantar el proyecto](#levantar-el-proyecto)
7. [Variables de entorno](#variables-de-entorno)
8. [Ejecutar los tests](#ejecutar-los-tests)
9. [Estructura del proyecto](#estructura-del-proyecto)
10. [Módulos del sistema](#módulos-del-sistema)
11. [Manejo de errores](#manejo-de-errores)
12. [API — resumen de endpoints](#api--resumen-de-endpoints)
13. [Despliegue en Azure](#despliegue-en-azure)

---

## Descripción general

StockFlow CRM permite a un negocio:

- **Crear su propio CRM**: cada registro público da de alta una organización con
  sus datos completamente aislados del resto, y su autor queda como administrador.
- **Gestionar usuarios** de la organización con roles (administrador / operador),
  verificación de correo electrónico y datos de contacto.
- **Gestionar su inventario** de productos con alertas de stock mínimo, y con
  distinción entre artículos por unidad y artículos a granel (que sí admiten
  cantidades con decimales).
- **Registrar proveedores** y aprovechar el historial de SKUs para auto-completar futuras facturas.
- **Procesar facturas** de proveedores con IA: el usuario sube una imagen o PDF → Gemini 2.5 Flash verifica que el documento sea realmente una factura y extrae los ítems → el usuario revisa, corrige y confirma → el stock se actualiza automáticamente.
- **Gestionar clientes y pedidos** con un flujo de estados (pendiente → procesando → enviado → entregado) y notificaciones por correo.
- **Consultar movimientos de stock** con filtros por tipo, producto y fecha.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.13 + FastAPI |
| Base de datos | PostgreSQL 17 — **Supabase** en producción (cualquier PostgreSQL 14+ en local) |
| IA | Gemini 2.5 Flash (Google AI Studio) |
| ORM / Migraciones | SQLAlchemy 2 + Alembic |
| Autenticación | JWT (python-jose + bcrypt) |
| Email | SMTP genérico (`smtplib`) — **Brevo** en producción |
| Tests backend | pytest + httpx + pytest-mock |
| Tests frontend | Vitest + React Testing Library |

---

## Requisitos previos

Instalar las siguientes herramientas antes de continuar:

| Herramienta | Versión mínima | Verificar |
|---|---|---|
| Python | 3.11 | `python --version` |
| Node.js | 20 | `node --version` |
| npm | 9 | `npm --version` |
| PostgreSQL | 16 | `psql --version` |
| Git | cualquiera | `git --version` |

> **Windows:** se recomienda instalar Python desde [python.org](https://www.python.org/downloads/) y marcar la opción *"Add Python to PATH"*.

---

## Configuración del entorno

### 1. Clonar el repositorio

```bash
git clone https://github.com/<tu-usuario>/stockflow-crm.git
cd stockflow-crm
```

### 2. Backend — entorno virtual y dependencias

```bash
cd backend

# Crear y activar el entorno virtual
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows (CMD)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Frontend — dependencias

```bash
cd frontend
npm install
```

---

## Base de datos

> **Local vs. producción.** Para desarrollo podés usar un PostgreSQL local (abajo)
> o directamente una base gratis de **Supabase**. En producción se usa Supabase.
> El detalle (regiones, Session pooler, SSL) está en
> [`docs/despliegue/DESPLIEGUE.md`](docs/despliegue/DESPLIEGUE.md).

### Crear la base de datos en PostgreSQL

```sql
-- Ejecutar en psql como superusuario (ej. postgres)
CREATE DATABASE stockflow;
CREATE USER stockflow_admin WITH PASSWORD 'tu_contraseña_segura';
GRANT ALL PRIVILEGES ON DATABASE stockflow TO stockflow_admin;
```

### Configurar la variable de entorno

Antes de aplicar las migraciones, crear el archivo `.env` en la carpeta `backend/` (ver sección [Variables de entorno](#variables-de-entorno)).

### Aplicar las migraciones (Alembic)

```bash
cd backend
alembic upgrade head
```

Esto creará todas las tablas necesarias en la base de datos.

> **Nota:** cada vez que se agregue un nuevo modelo o columna, se debe generar una migración con:
> ```bash
> alembic revision --autogenerate -m "descripcion del cambio"
> alembic upgrade head
> ```

---

## Levantar el proyecto

### Backend (FastAPI)

```bash
cd backend
# Asegurarse de que el entorno virtual está activo
uvicorn app.main:app --reload
```

El servidor arranca en **`http://localhost:8000`**.
La documentación interactiva de la API queda disponible en **`http://localhost:8000/docs`**.

### Frontend (React + Vite)

```bash
cd frontend
npm run dev
```

La aplicación queda disponible en **`http://localhost:5173`**.

> Tanto el backend como el frontend deben estar corriendo **al mismo tiempo** en terminales separadas.

### Primer uso: crear tu CRM

No hay usuarios precargados. El primer paso es registrarse:

1. Entrar a `http://localhost:5173/signup`.
2. Completar el nombre de la organización y los datos de contacto del administrador.
3. Abrir el enlace de verificación que llega por correo (en desarrollo, sin
   SMTP configurado, el enlace aparece en el log del backend).
4. Iniciar sesión: esa cuenta queda como **administrador de su organización**.

Cada registro crea una organización independiente: sus productos, proveedores,
clientes, pedidos y facturas no son visibles desde ninguna otra. Desde
**Usuarios** el administrador da de alta al resto del equipo dentro de su
organización.

---

## Variables de entorno

### Backend — `backend/.env`

Crear el archivo copiando el ejemplo:

```bash
cp backend/.env.example backend/.env   # Linux / macOS
copy backend\.env.example backend\.env  # Windows
```

Luego editar los valores:

```env
# Conexión a PostgreSQL
DATABASE_URL=postgresql://stockflow_admin:tu_contraseña@localhost:5432/stockflow

# Clave secreta para firmar los JWT — generarla con:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=reemplaza_esto_con_una_clave_aleatoria_larga

# Configuración de JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Clave de API de Google AI Studio (Gemini)
# Obtenerla en: https://aistudio.google.com/apikey
GOOGLE_API_KEY=tu_clave_de_google_ai_studio

# Modelo de Gemini a usar
GEMINI_MODEL=gemini-2.5-flash

# Correo por SMTP (opcional — si SMTP_HOST/USER/PASSWORD quedan vacíos, los
# emails se silencian sin error y el enlace de verificación se escribe en el log).
# Sirve cualquier proveedor; en producción se usa Brevo (300 correos/día gratis).
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=remitente_verificado@tudominio.com
SMTP_FROM_NAME=StockFlow CRM

# Orígenes permitidos por CORS, separados por coma.
# Nunca usar "*" en producción: es incompatible con el envío de credenciales.
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# URL pública del frontend, usada para armar el enlace de verificación de correo.
FRONTEND_URL=http://localhost:5173
```

> **Verificación de correo en desarrollo:** si el SMTP no está configurado
> (`SMTP_HOST`, `SMTP_USER` o `SMTP_PASSWORD` vacíos), el enlace de verificación
> **se escribe en el log del servidor** en lugar de enviarse por mail. Buscá una
> línea que empiece con *"SMTP no está configurado. Enlace de verificación
> para…"* y abrila en el navegador.

### Frontend — `frontend/.env`

```bash
cp frontend/.env.example frontend/.env   # Linux / macOS
copy frontend\.env.example frontend\.env  # Windows
```

```env
# URL del backend FastAPI
VITE_API_URL=http://localhost:8000
```

---

## Ejecutar los tests

### Backend

```bash
cd backend

# Instalar dependencias de test (si no se hizo antes)
pip install -r requirements-test.txt

# Ejecutar todos los tests
python -m pytest tests/ -v

# Ejecutar un archivo específico
python -m pytest tests/test_products.py -v

# Ejecutar un test específico
python -m pytest tests/test_invoices.py::TestConfirmInvoice::test_confirm_invoice_with_existing_product -v
```

Los tests usan una base de datos SQLite en memoria — **no se necesita PostgreSQL** para correrlos.

> **Estado actual: 246 pruebas en verde** (199 de backend + 47 de frontend). La estrategia
> detrás de esa suite, los casos negativos y de límite, y los defectos que se encontraron
> buscándolos a propósito están en
> [`docs/test-plan/PLAN_DE_PRUEBAS.md`](docs/test-plan/PLAN_DE_PRUEBAS.md).

### Frontend

```bash
cd frontend

# Ejecutar una sola vez (modo CI)
npm run test:run

# Ejecutar en modo watch (desarrollo)
npm test
```

---

## Estructura del proyecto

```
stockflow-crm/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # Punto de entrada FastAPI
│   │   ├── core/
│   │   │   ├── config.py            # Configuración (pydantic-settings)
│   │   │   ├── security.py          # Hashing + JWT
│   │   │   ├── errors.py            # Contrato de errores + DomainError
│   │   │   └── deps.py              # Dependencias FastAPI (auth + organización)
│   │   ├── db/
│   │   │   ├── base.py              # Base declarativa SQLAlchemy
│   │   │   └── session.py           # Motor + sesión de DB
│   │   ├── models/                  # Modelos SQLAlchemy
│   │   │   ├── organization.py      # Unidad de aislamiento multi-tenant
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── supplier.py
│   │   │   ├── invoice.py
│   │   │   ├── order.py
│   │   │   ├── customer.py
│   │   │   ├── stock_movement.py
│   │   │   └── product_supplier_mapping.py
│   │   ├── schemas/                 # Schemas Pydantic (request / response)
│   │   │   └── validators.py        # Validadores reutilizables en español
│   │   ├── routers/                 # Endpoints por módulo
│   │   └── services/                # Lógica de negocio
│   │       ├── stock_rules.py       # Reglas de integridad del stock
│   │       └── invoice/
│   │           ├── gemini_service.py   # Llamada a Gemini + control de contenido
│   │           └── invoice_service.py  # Lógica de facturas
│   ├── alembic/                     # Migraciones de base de datos
│   ├── tests/                       # Suite de tests (pytest)
│   ├── requirements.txt
│   ├── requirements-test.txt
│   ├── pytest.ini
│   └── .env                         # No se sube al repositorio
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.js            # Cliente Axios con interceptors JWT
│   │   │   └── errors.js            # Normalización de errores de la API
│   │   ├── utils/
│   │   │   └── validation.js        # Validaciones de formulario
│   │   ├── context/
│   │   │   └── AuthContext.jsx      # Estado global de autenticación
│   │   ├── components/
│   │   │   ├── Layout.jsx           # Sidebar + navegación
│   │   │   ├── PrivateRoute.jsx     # Protección de rutas
│   │   │   ├── AdminRoute.jsx       # Rutas restringidas a administradores
│   │   │   ├── ErrorBoundary.jsx    # Red de seguridad ante fallos de render
│   │   │   └── ui/
│   │   │       ├── Badge.jsx        # Badges de estado
│   │   │       ├── ErrorBanner.jsx  # Aviso de error reutilizable
│   │   │       ├── FormField.jsx    # Campo con error en línea
│   │   │       └── Modal.jsx        # Modal reutilizable
│   │   └── pages/
│   │       ├── Login.jsx
│   │       ├── Signup.jsx           # Alta pública de la organización
│   │       ├── VerifyEmail.jsx      # Confirmación del correo
│   │       ├── Users.jsx            # Gestión de usuarios (admin)
│   │       ├── Products.jsx
│   │       ├── Suppliers.jsx
│   │       ├── Invoices.jsx         # Flujo IA (upload → review → confirm)
│   │       ├── StockMovements.jsx
│   │       ├── Customers.jsx
│   │       └── Orders.jsx
│   ├── package.json
│   └── vite.config.js
│
└── docs/
    ├── der/                         # Modelo de datos (DER.md — Mermaid)
    ├── despliegue/                  # Guía de infraestructura y despliegue
    ├── user-manual/                 # Manual de usuario (Word)
    ├── use-cases/                   # Casos de uso (Excel)
    ├── test-cases/                  # Casos de prueba (Excel)
    ├── test-plan/                   # Plan de pruebas (estrategia y resultados)
    └── flows/                       # Diagramas de flujo
```

### Contenido de `docs/`

| Documento | Archivo | Contenido |
|---|---|---|
| **DER** | [`docs/der/DER.md`](docs/der/DER.md) | Modelo de datos en Mermaid (se renderiza en GitHub): 11 tablas, decisiones de diseño, políticas de borrado y unicidad por organización. Reemplaza al `DER.png` anterior. |
| **Despliegue** | [`docs/despliegue/DESPLIEGUE.md`](docs/despliegue/DESPLIEGUE.md) | Guía de infraestructura (Supabase + Brevo + Azure), variables de entorno, verificación y solución de problemas. |
| **Casos de uso** | `docs/use-cases/` | 28 casos de uso en 10 módulos, redactados en lenguaje de negocio (el *qué*, no el *cómo*). Incluye 4 diagramas UML con actores en [`docs/use-cases/diagramas/`](docs/use-cases/diagramas/). |
| **Diagramas de flujo** | [`docs/flows/DIAGRAMAS_DE_FLUJO.md`](docs/flows/DIAGRAMAS_DE_FLUJO.md) | 12 diagramas de proceso: autenticación, facturas con IA, ABM de productos, proveedores y clientes, pedidos, usuarios y flujos integrales. |
| **Casos de prueba** | `docs/test-cases/` | 182 casos que reflejan la suite automatizada. |
| **Plan de pruebas** | [`docs/test-plan/PLAN_DE_PRUEBAS.md`](docs/test-plan/PLAN_DE_PRUEBAS.md) | Estrategia, técnicas de diseño, casos negativos y de límite por módulo, seguridad y aislamiento multiempresa, usabilidad (heurísticas de Nielsen), accesibilidad WCAG 2.1 AA, gestión de defectos y **registro de los 23 defectos encontrados y corregidos**. |
| **Manual de usuario** | `docs/user-manual/` | Manual funcional (v2.0). Describe **cómo operar** el sistema; la lógica de los procesos vive en los diagramas de flujo. |

---

## Módulos del sistema

### 1. Organizaciones y autenticación
- **Registro público multi-tenant**: cada alta crea una organización con datos
  aislados y deja a su autor como administrador de esa organización.
- **Verificación de correo obligatoria**: el login se bloquea hasta confirmar la
  dirección con un enlace de un solo uso, válido por 24 horas.
- Login con JWT — token válido por 60 minutos (configurable).
- Rutas públicas: `/auth/signup`, `/auth/login`, `/auth/verify-email` y
  `/auth/resend-verification`. Todas las demás requieren token, y solo devuelven
  datos de la organización del usuario autenticado.

### 2. Usuarios (solo administradores)
- Alta de usuarios dentro de la propia organización, con rol `admin` u `operator`.
- Cambio de rol, activación y desactivación de cuentas.
- Datos de contacto (nombre y teléfono) del administrador y del resto del equipo.
- La organización nunca puede quedarse sin administradores activos.

### 3. Inventario (Productos)
- CRUD completo de productos con SKU único **dentro de cada organización**.
- Campos: SKU, nombre, descripción, precio, stock actual, stock mínimo,
  admite stock decimal, estado activo/inactivo.
- Los productos por unidad rechazan cantidades fraccionarias; los artículos a
  granel (kilos, litros, metros) las admiten activando *Admite stock decimal*.
- Alerta visual de stock bajo (`current_stock < minimum_stock`).
- Cada cambio de stock genera automáticamente un movimiento de tipo `adjustment`.
- Un producto puede eliminarse si su stock es 0 y no tiene historial comercial
  (pedidos o movimientos originados en facturas). La respuesta incluye
  `can_delete` y el motivo, para poder avisarlo antes de intentarlo.

### 4. Proveedores
- CRUD de proveedores (razón social, contacto, email, teléfono).
- El sistema aprende la relación proveedor → SKU propio cada vez que se confirma una factura.

### 5. Facturas (pipeline IA)
1. El usuario sube un archivo PDF, JPG, PNG o WEBP (máx. 20 MB). Se verifica el
   contenido real del archivo, no solo la extensión declarada.
2. Gemini 2.5 Flash **primero clasifica el documento**: si no es una factura ni
   un remito, se rechaza con una explicación y no se guarda nada.
3. Si es una factura, devuelve los ítems detectados con niveles de confianza
   (`high / medium / low`).
4. El usuario revisa y **puede corregir** la descripción, la cantidad y el precio
   de cada línea, asignarla a un producto existente, crear uno nuevo u omitirla.
5. Puede volver al listado en cualquier momento: la factura queda pendiente y la
   revisión se retoma después.
6. Al confirmar: el stock se actualiza, se crean movimientos de tipo `entry` y se
   guarda el mapeo SKU del proveedor.

### 6. Movimientos de stock
- Vista de solo lectura con filtros por tipo (`entry / exit / adjustment`), producto y rango de fechas.
- El rango de fechas se valida: un rango invertido devuelve un error explicativo
  en lugar de una lista vacía sin explicación.
- Cada movimiento indica si fue originado por una factura, un pedido o una carga manual.

### 7. Clientes
- CRUD de clientes (nombre, email, teléfono, dirección).
- Vista de historial de pedidos por cliente con totales.

### 8. Pedidos
- Crear pedido para un cliente.
- Agregar/quitar ítems (valida stock disponible y la unidad de medida del producto).
- Avanzar estado: `pending → processing → shipped → delivered`.
  - En el paso `processing` se deduce el stock automáticamente y se crea un movimiento de tipo `exit`.
  - Se envía email de notificación al cliente en cada cambio de estado (si el SMTP está configurado).

---

## Manejo de errores

Toda la API responde con el mismo formato, de modo que la interfaz nunca reciba
estructuras inesperadas:

```json
{
  "detail": "Correo electrónico: No es una dirección de correo válida.",
  "errors": { "email": "No es una dirección de correo válida." }
}
```

- `detail` es **siempre un string** legible en español, listo para mostrarse.
- `errors` mapea cada campo con problemas a su mensaje, para señalar el input exacto.
- Los detalles técnicos (constraints, identificadores internos, respuestas crudas
  del modelo de IA) se registran del lado del servidor y **nunca** viajan al navegador.

---

## API — resumen de endpoints

La documentación completa e interactiva (Swagger UI) está en **`http://localhost:8000/docs`**.

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/auth/signup` | Crear organización + administrador (público) |
| GET | `/auth/verify-email` | Verificar el correo con el token recibido |
| POST | `/auth/resend-verification` | Reenviar el enlace de verificación |
| POST | `/auth/login` | Login — devuelve JWT |
| GET | `/auth/me` | Usuario actual |
| GET | `/auth/my-organization` | Organización del usuario actual |
| GET | `/users` | Listar usuarios de la organización (admin) |
| POST | `/users` | Crear usuario en la organización (admin) |
| PUT | `/users/{id}` | Cambiar rol o activar/desactivar (admin) |
| DELETE | `/users/{id}` | Eliminar usuario (admin) |
| GET | `/products` | Listar productos |
| POST | `/products` | Crear producto |
| PUT | `/products/{id}` | Actualizar producto |
| DELETE | `/products/{id}` | Eliminar producto |
| GET | `/suppliers` | Listar proveedores |
| POST | `/suppliers` | Crear proveedor |
| PUT | `/suppliers/{id}` | Actualizar proveedor |
| DELETE | `/suppliers/{id}` | Eliminar proveedor |
| POST | `/invoices/process` | Subir y procesar factura (IA) |
| POST | `/invoices/{id}/confirm` | Confirmar factura |
| POST | `/invoices/{id}/reject` | Rechazar factura |
| GET | `/invoices` | Listar facturas |
| GET | `/stock-movements` | Listar movimientos (con filtros) |
| GET | `/customers` | Listar clientes |
| POST | `/customers` | Crear cliente |
| GET | `/customers/{id}/orders` | Historial de pedidos del cliente |
| GET | `/orders` | Listar pedidos |
| POST | `/orders` | Crear pedido |
| POST | `/orders/{id}/items` | Agregar ítem al pedido |
| DELETE | `/orders/{id}/items/{item_id}` | Quitar ítem |
| POST | `/orders/{id}/advance` | Avanzar estado del pedido |
| GET | `/health` | Health check |

---

## Despliegue en Azure

El backend y el frontend están en **Azure**; la base de datos en **Supabase** y el
correo en **Brevo**. La guía completa paso a paso (incluida la regeneración desde
cero y la solución de problemas reales) está en
[`docs/despliegue/DESPLIEGUE.md`](docs/despliegue/DESPLIEGUE.md).

### URLs de producción

| Componente | URL |
|---|---|
| Frontend | https://proud-smoke-07bfb670f.7.azurestaticapps.net |
| Backend | https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net |
| Docs API | https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net/docs |

### Servicios utilizados

| Componente | Servicio | Plan |
|---|---|---|
| Frontend | Azure Static Web Apps (vinculado a GitHub `main`) | Free |
| Backend | Azure App Service (Linux, despliegue por zip / `az webapp deploy`) | Basic B1 |
| Base de datos | Supabase (PostgreSQL gestionado) | Free |
| Correo | Brevo (relay SMTP) | Free |

> **Importante — conexión a la base desde Azure:** App Service sale por **IPv4** y
> la conexión directa de Supabase es solo **IPv6**. En producción hay que usar la
> cadena del **Session pooler** de Supabase (IPv4). Ver la guía de despliegue.

Para despliegue local o en otro proveedor, cualquier servidor que soporte Python ASGI y PostgreSQL funciona (Railway, Render, Fly.io, etc.).

### Límites y costos por servicio

> Estos límites aplican a la instancia actualmente desplegada. Si se superan, el servicio correspondiente dejará de funcionar hasta el próximo ciclo o hasta actualizar el plan.

#### Azure Static Web Apps — Free
- 100 GB de ancho de banda por mes.
- 0,5 GB de almacenamiento para la aplicación.
- 2 dominios personalizados por app.
- Sin SLA garantizado.

#### Azure App Service — Basic B1
- 1 vCore, 1,75 GB de RAM, 10 GB de almacenamiento en disco.
- Soporte para dominios personalizados y SSL.
- Sin autoescalado (instancia fija).
- Costo aproximado: **~$13 USD/mes** (canadacentral).

#### Supabase — PostgreSQL (Free)
- **Gratis de forma permanente** (no es un trial): la base no se elimina.
- Hasta 500 MB de base de datos y 5 GB de transferencia por mes.
- El proyecto se pausa tras un período largo de inactividad (se reactiva desde el panel).
- Desde Azure hay que conectarse por el **Session pooler** (IPv4); la conexión
  directa es solo IPv6. Ver [`docs/despliegue/DESPLIEGUE.md`](docs/despliegue/DESPLIEGUE.md).

#### Google AI Studio — Gemini 2.5 Flash (Free)
- **15 solicitudes por minuto (RPM).**
- **1.500 solicitudes por día (RPD).** Si se procesan más de 1.500 facturas en un día, las siguientes llamadas serán rechazadas con error 429 hasta el día siguiente.
- 1.000.000 tokens por minuto (TPM).
- Sin costo mientras se permanezca dentro de estos límites; se puede pagar por uso si se necesita escalar.

#### Brevo — SMTP (Free)
- **300 emails por día.** Límite permanente del plan gratuito.
- Si se superan (entre notificaciones de pedidos, alertas de stock y verificaciones), los excedentes se rechazan hasta el día siguiente.
- 1 remitente verificado en el plan gratuito.
- El backend usa SMTP genérico, así que se puede cambiar de proveedor (Gmail,
  Mailjet, etc.) tocando solo las variables `SMTP_*`, sin cambiar código.

---

## Licencia

Proyecto académico — Técnico en Programación. No destinado a uso comercial.
