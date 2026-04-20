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
11. [API — resumen de endpoints](#api--resumen-de-endpoints)
12. [Despliegue en Azure](#despliegue-en-azure)

---

## Descripción general

StockFlow CRM permite a un negocio:

- **Gestionar su inventario** de productos con alertas de stock mínimo.
- **Registrar proveedores** y aprovechar el historial de SKUs para auto-completar futuras facturas.
- **Procesar facturas** de proveedores con IA: el usuario sube una imagen o PDF → Gemini 2.5 Flash extrae todos los ítems → el usuario revisa y confirma → el stock se actualiza automáticamente.
- **Gestionar clientes y pedidos** con un flujo de estados (pendiente → procesando → enviado → entregado) y notificaciones por correo.
- **Consultar movimientos de stock** con filtros por tipo, producto y fecha.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.13 + FastAPI |
| Base de datos | PostgreSQL 16 |
| IA | Gemini 2.5 Flash (Google AI Studio) |
| ORM / Migraciones | SQLAlchemy 2 + Alembic |
| Autenticación | JWT (python-jose + bcrypt) |
| Email | SendGrid |
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

# SendGrid (opcional — si se omite, los emails se silencian sin error)
SENDGRID_API_KEY=
SMTP_FROM_EMAIL=
```

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

Resultado esperado: **117 tests, 0 fallos**.

### Frontend

```bash
cd frontend

# Ejecutar una sola vez (modo CI)
npm run test:run

# Ejecutar en modo watch (desarrollo)
npm test
```

Resultado esperado: **26 tests, 0 fallos**.

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
│   │   │   └── deps.py              # Dependencias FastAPI (auth)
│   │   ├── db/
│   │   │   ├── base.py              # Base declarativa SQLAlchemy
│   │   │   └── session.py           # Motor + sesión de DB
│   │   ├── models/                  # Modelos SQLAlchemy
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── supplier.py
│   │   │   ├── invoice.py
│   │   │   ├── order.py
│   │   │   ├── customer.py
│   │   │   ├── stock_movement.py
│   │   │   └── product_supplier_mapping.py
│   │   ├── schemas/                 # Schemas Pydantic (request / response)
│   │   ├── routers/                 # Endpoints por módulo
│   │   └── services/                # Lógica de negocio
│   │       └── invoice/
│   │           ├── gemini_service.py   # Llamada a Gemini
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
│   │   │   └── client.js            # Cliente Axios con interceptors JWT
│   │   ├── context/
│   │   │   └── AuthContext.jsx      # Estado global de autenticación
│   │   ├── components/
│   │   │   ├── Layout.jsx           # Sidebar + navegación
│   │   │   ├── PrivateRoute.jsx     # Protección de rutas
│   │   │   └── ui/
│   │   │       ├── Badge.jsx        # Badges de estado
│   │   │       └── Modal.jsx        # Modal reutilizable
│   │   └── pages/
│   │       ├── Login.jsx
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
    ├── user-manual/                 # Manual de usuario (Word)
    ├── use-cases/
    ├── flows/
    └── test-cases/
```

---

## Módulos del sistema

### 1. Autenticación
- Registro de usuarios con roles (`admin` / `operator`).
- Login con JWT — token válido por 60 minutos (configurable).
- Todas las rutas de la API requieren token excepto `/auth/login` y `/auth/register`.

### 2. Inventario (Productos)
- CRUD completo de productos con SKU único.
- Campos: SKU, nombre, descripción, precio, stock actual, stock mínimo, estado activo/inactivo.
- Alerta visual de stock bajo (`current_stock < minimum_stock`).
- Cada cambio de stock genera automáticamente un movimiento de tipo `adjustment`.

### 3. Proveedores
- CRUD de proveedores (nombre, contacto, email, teléfono).
- El sistema aprende la relación proveedor → SKU propio cada vez que se confirma una factura.

### 4. Facturas (pipeline IA)
1. El usuario sube un archivo PDF, JPG o PNG (máx. 20 MB).
2. Gemini 2.5 Flash analiza la imagen directamente y devuelve los ítems detectados con niveles de confianza (`high / medium / low`).
3. El usuario revisa, asigna cada ítem a un producto existente o crea uno nuevo, y opcionalmente asigna proveedor.
4. Al confirmar: el stock se actualiza, se crean movimientos de tipo `entry` y se guarda el mapeo SKU del proveedor.
5. La factura puede rechazarse en lugar de confirmarse.

### 5. Movimientos de stock
- Vista de solo lectura con filtros por tipo (`entry / exit / adjustment`), producto y rango de fechas.
- Cada movimiento indica si fue originado por una factura o un pedido.

### 6. Clientes
- CRUD de clientes (nombre, email, teléfono, dirección).
- Vista de historial de pedidos por cliente con totales.

### 7. Pedidos
- Crear pedido para un cliente.
- Agregar/quitar ítems (valida stock disponible en tiempo real).
- Avanzar estado: `pending → processing → shipped → delivered`.
  - En el paso `processing` se deduce el stock automáticamente y se crea un movimiento de tipo `exit`.
  - Se envía email de notificación al cliente en cada cambio de estado (si SendGrid está configurado).

---

## API — resumen de endpoints

La documentación completa e interactiva (Swagger UI) está en **`http://localhost:8000/docs`**.

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/auth/register` | Registrar usuario |
| POST | `/auth/login` | Login — devuelve JWT |
| GET | `/auth/me` | Usuario actual |
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

El proyecto está desplegado en Azure con CI/CD automático vía GitHub Actions: cada push a `main` actualiza el frontend y el backend sin intervención manual.

### URLs de producción

| Componente | URL |
|---|---|
| Frontend | https://proud-smoke-07bfb670f.azurestaticapps.net |
| Backend | https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net |
| Docs API | https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net/docs |

### Servicios y plan utilizado

| Componente | Servicio Azure | Plan |
|---|---|---|
| Frontend | Azure Static Web Apps | Free |
| Backend | Azure App Service | Basic B1 |
| Base de datos | Azure Database for PostgreSQL Flexible Server | Burstable B1ms |

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

#### Azure Database for PostgreSQL Flexible Server
- Las primeras 750 horas/mes de Burstable B1ms y 32 GB de almacenamiento son **gratuitas durante los primeros 12 meses** para cuentas Azure nuevas.
- Vencido ese período, el costo aproximado es **~$13 USD/mes** (B1ms, canadacentral).
- Límites del tier B1ms: 1 vCPU, 2 GB RAM, 32 GB almacenamiento, hasta 396 conexiones.

#### Google AI Studio — Gemini 2.5 Flash (Free)
- **15 solicitudes por minuto (RPM).**
- **1.500 solicitudes por día (RPD).** Si se procesan más de 1.500 facturas en un día, las siguientes llamadas serán rechazadas con error 429 hasta el día siguiente.
- 1.000.000 tokens por minuto (TPM).
- Sin costo mientras se permanezca dentro de estos límites; se puede pagar por uso si se necesita escalar.

#### SendGrid — Free
- **100 emails por día.** Este límite es permanente (no se renueva con más tiempo, es el tope del plan gratuito).
- Si se envían más de 100 emails en un día (entre notificaciones de pedidos, alertas de stock y bienvenidas), los excedentes serán rechazados hasta el día siguiente.
- 1 remitente verificado en el plan gratuito.

---

## Licencia

Proyecto académico — Técnico en Programación. No destinado a uso comercial.
