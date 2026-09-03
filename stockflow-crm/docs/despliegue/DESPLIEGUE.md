# Guía de despliegue — StockFlow CRM

Guía completa para desplegar StockFlow CRM en producción y para **regenerar la
infraestructura desde cero**. Documenta la arquitectura actual (Supabase + Brevo +
Azure), cada variable de entorno, y los problemas concretos que aparecen en el
camino con sus soluciones.

> ⚠️ **Los valores sensibles (contraseñas, API keys) nunca van en este archivo ni
> en el repositorio.** Se cargan en el `.env` local (que está en `.gitignore`) y
> en las *App settings* de Azure. Acá se usan solo marcadores como `[TU-PASSWORD]`.

---

## Arquitectura

El sistema se reparte en tres proveedores, cada uno con su capa gratuita o de
bajo costo:

| Capa | Proveedor | Servicio | Región |
|---|---|---|---|
| Frontend (React + Vite) | **Azure** | Static Web Apps (Free) | East US 2 |
| Backend (FastAPI) | **Azure** | App Service (Basic B1, Linux) | Canada Central |
| Base de datos (PostgreSQL 17) | **Supabase** | Postgres gestionado (Free) | South America (São Paulo) |
| Correo transaccional | **Brevo** | Relay SMTP (Free, 300/día) | — |
| IA de facturas | **Google AI Studio** | Gemini 2.5 Flash (Free) | — |

```
   Navegador
      │  HTTPS
      ▼
 ┌──────────────────────┐        ┌───────────────────────────┐
 │  Static Web App       │  API   │  App Service (FastAPI)     │
 │  (frontend React)     │ ─────► │  stockflow-backend         │
 │  proud-smoke-…        │  CORS  │  …canadacentral-01…        │
 └──────────────────────┘        └────────────┬──────────────┘
                                               │
                          ┌────────────────────┼─────────────────────┐
                          ▼                     ▼                     ▼
                 ┌─────────────────┐   ┌────────────────┐   ┌────────────────┐
                 │ Supabase        │   │ Brevo (SMTP)   │   │ Gemini 2.5     │
                 │ PostgreSQL      │   │ verificación / │   │ Flash          │
                 │ (pooler IPv4)   │   │ notificaciones │   │ (facturas IA)  │
                 └─────────────────┘   └────────────────┘   └────────────────┘
```

### URLs de producción

| Componente | URL |
|---|---|
| Frontend | https://proud-smoke-07bfb670f.7.azurestaticapps.net |
| Backend | https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net |
| Docs API (Swagger) | https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net/docs |

### Recursos de Azure (grupo `StockFlow`)

| Recurso | Tipo | Región |
|---|---|---|
| `stockflow-backend` | App Service (sitio) | canadacentral |
| `ASP-StockFlow-9650` | Plan de App Service (B1 Linux) | canadacentral |
| `stockflow-frontend` | Static Web App | eastus2 |
| `oidc-msi-b794` | Identidad administrada (despliegue OIDC) | canadacentral |

---

## Requisitos previos

- Cuenta **Azure for Students** (crédito gratuito, sin tarjeta).
- Cuenta en **Supabase** (supabase.com).
- Cuenta en **Brevo** (brevo.com).
- Clave de API de **Google AI Studio** (aistudio.google.com/apikey).
- **Azure CLI** instalado (`az`). En Windows: `winget install Microsoft.AzureCLI`.
- **Python 3.11+** y **Node 20+** para construir backend y frontend.

---

## Parte 1 — Base de datos (Supabase)

### 1.1 Crear el proyecto

1. En Supabase, **New project**. Elegir región **South America (São Paulo)**
   (`sa-east-1`), la más cercana a Argentina.
2. Guardar la **contraseña** de la base que define Supabase (no se vuelve a mostrar).

### 1.2 Las dos cadenas de conexión (¡importante!)

Supabase ofrece dos formas de conectarse, y **cuál usar depende de desde dónde**:

| Cadena | Host | Cuándo usarla |
|---|---|---|
| **Conexión directa** | `db.<ref>.supabase.co:5432` | Solo desde redes con **IPv6**. Sirve para correr migraciones desde tu PC si tenés IPv6. |
| **Session pooler** | `aws-0-sa-east-1.pooler.supabase.com:5432` | **Obligatoria desde Azure**, porque App Service sale por **IPv4** y la conexión directa es solo IPv6. |

> 🔑 **Regla de oro:** en producción (Azure) usá **siempre el Session pooler**.
> La conexión directa fallará desde Azure con un timeout de red.

Ambas requieren **SSL**: agregá `?sslmode=require` al final de la URL. Si la
contraseña tiene caracteres especiales (`^`, `@`, `#`…), hay que **codificarlos
en la URL** (ej. `^` → `%5E`).

Ejemplo de `DATABASE_URL` con el pooler:

```
postgresql://postgres.<ref>:[TU-PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

### 1.3 Crear las tablas (migraciones Alembic)

**No se pega ningún SQL en Supabase.** Las tablas las crea Alembic conectándose a
la base. Desde `backend/`, con el `DATABASE_URL` ya configurado en el `.env`:

```bash
alembic upgrade head
```

Esto aplica las 4 migraciones en orden y crea las 12 tablas (`organizations`,
`users`, `products`, `suppliers`, `customers`, `orders`, `order_items`,
`invoices`, `invoice_items`, `stock_movements`, `product_supplier_mappings`, más
`alembic_version`). En una base vacía funciona directo; la parte de *backfill*
multi-tenant se salta sola si no hay datos previos.

---

## Parte 2 — Correo (Brevo)

El backend envía correos por **SMTP genérico** (`smtplib`), así que sirve
cualquier proveedor. En producción se usa **Brevo** (300 correos/día gratis).

### 2.1 Crear la cuenta y verificar el remitente

1. Registrarse en brevo.com.
2. Verificar el **remitente** (*sender*): el correo desde el que se envía
   (ej. `remitente@tudominio.com`). Brevo rechaza correos de remitentes no
   verificados.

### 2.2 Obtener las credenciales SMTP

En Brevo: **SMTP & API → SMTP**. Ahí figuran:

- **Servidor:** `smtp-relay.brevo.com`
- **Puerto:** `587`
- **Login:** algo tipo `xxxxxx@smtp-brevo.com`
- **Clave SMTP:** generarla con el botón correspondiente.

### 2.3 Desactivar la restricción de IP

⚠️ Por defecto Brevo **bloquea el envío desde IPs no autorizadas**. Como la IP de
Azure (y la de tu casa) cambian, hay que **desactivar esa restricción**:

> **Brevo → Configuración → Seguridad → IPs autorizadas** → apagar la restricción.

Si no se hace, el envío falla con `525 5.7.1 Unauthorized IP address`. La
seguridad la aporta la clave SMTP secreta, no la IP.

---

## Parte 3 — Backend (Azure App Service)

### 3.1 Variables de entorno (*App settings*)

Configurar en Azure (Portal → App Service → Configuración → Variables de entorno,
o por CLI). **Ninguna se guarda en el repo.**

| Variable | Valor / ejemplo |
|---|---|
| `DATABASE_URL` | cadena del **Session pooler** de Supabase + `?sslmode=require` |
| `SECRET_KEY` | clave aleatoria (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `GOOGLE_API_KEY` | clave de Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `SMTP_HOST` | `smtp-relay.brevo.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | login SMTP de Brevo |
| `SMTP_PASSWORD` | clave SMTP de Brevo |
| `SMTP_FROM_EMAIL` | remitente verificado en Brevo |
| `SMTP_FROM_NAME` | `StockFlow CRM` |
| `CORS_ORIGINS` | URL del frontend (ej. `https://proud-smoke-07bfb670f.7.azurestaticapps.net`) |
| `FRONTEND_URL` | misma URL del frontend (para armar el enlace de verificación) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` (instala dependencias al desplegar) |

Ejemplo por CLI:

```bash
az webapp config appsettings set --name stockflow-backend --resource-group StockFlow --settings \
  "SMTP_HOST=smtp-relay.brevo.com" "SMTP_PORT=587" \
  "SMTP_USER=[LOGIN-BREVO]" "SMTP_PASSWORD=[CLAVE-BREVO]" \
  "SMTP_FROM_NAME=StockFlow CRM" \
  "CORS_ORIGINS=https://proud-smoke-07bfb670f.7.azurestaticapps.net" \
  "FRONTEND_URL=https://proud-smoke-07bfb670f.7.azurestaticapps.net"
```

### 3.2 Comando de arranque

El App Service usa este *startup command* (Configuración → Configuración general):

```
pip install -r /home/site/wwwroot/requirements.txt && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3.3 Desplegar el código

El backend se despliega **empaquetando la carpeta `backend/`** (con
`requirements.txt` en la raíz del zip) y subiéndola:

```bash
# 1. Crear un zip con app/, alembic/, requirements.txt y alembic.ini
#    (sin venv/, sin .env, sin __pycache__)
# 2. Desplegar
az webapp deploy --resource-group StockFlow --name stockflow-backend \
  --src-path backend_deploy.zip --type zip

# 3. Asegurarse de que la app esté encendida
az webapp start --name stockflow-backend --resource-group StockFlow
```

> ⏱️ El primer arranque es lento (**arranque en frío**): Azure instala las
> dependencias y levanta el contenedor. Las primeras requests pueden dar timeout
> uno o dos minutos; después responde normal.

---

## Parte 4 — Frontend (Azure Static Web Apps)

El Static Web App está vinculado al repositorio de GitHub (`main`). La variable
de build **`VITE_API_URL`** debe apuntar al backend (Vite la incrusta en tiempo
de compilación):

```bash
az staticwebapp appsettings set --name stockflow-frontend --resource-group StockFlow \
  --setting-names "VITE_API_URL=https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net"
```

Para reconstruir y volver a publicar el frontend, se hace `npm run build` en
`frontend/` y se publica el contenido de `dist/` (vía el flujo de GitHub del
Static Web App o con la SWA CLI).

---

## Parte 5 — Verificación post-despliegue

Checklist para confirmar que todo quedó funcionando:

```bash
BASE="https://stockflow-backend-btczc8eahbaaafd6.canadacentral-01.azurewebsites.net"

# 1. Salud del backend
curl "$BASE/health"                      # → {"status":"ok"}

# 2. Registro (crea org+admin en Supabase y manda correo por Brevo)
curl -X POST "$BASE/auth/signup" -H "Content-Type: application/json" \
  -d '{"organization_name":"Test","full_name":"Test","email":"tu+test@gmail.com","phone":"+540000000000","password":"TuClave123!"}'

# 3. El frontend carga
curl -o /dev/null -w "%{http_code}\n" https://proud-smoke-07bfb670f.7.azurestaticapps.net/

# 4. CORS habilitado para el frontend
curl -s -D - -o /dev/null -X OPTIONS "$BASE/products" \
  -H "Origin: https://proud-smoke-07bfb670f.7.azurestaticapps.net" \
  -H "Access-Control-Request-Method: GET" | grep -i access-control-allow-origin
```

La prueba final humana: entrar al frontend, registrarse, abrir el correo de
verificación real y hacer login.

---

## Solución de problemas (problemas reales encontrados)

| Síntoma | Causa | Solución |
|---|---|---|
| `RequestDisallowedByAzure … set of best available regions` | La suscripción *Azure for Students* restringe las regiones. Brazil South no está permitida. | Usar una región permitida (ej. **East US 2**, canadacentral). |
| Conexión a la base falla desde Azure (timeout) | La **conexión directa** de Supabase es solo **IPv6**; Azure sale por IPv4. | Usar la cadena del **Session pooler** (IPv4). |
| `AADSTS50076 … multi-factor authentication` al hacer `az login` | El tenant exige MFA y el login normal no lo dispara. | `az login --tenant <TENANT_ID>` (fuerza el paso de MFA). |
| `525 5.7.1 Unauthorized IP address` al enviar correo | Brevo bloquea IPs no autorizadas. | Desactivar la restricción de IP en Brevo (Parte 2.3). |
| `"az" no se reconoce` en la terminal de VSCode | La terminal se abrió antes de instalar el CLI (PATH viejo). | Abrir una terminal **fuera de VSCode**, o reiniciar Windows, o usar la ruta completa a `az.cmd`. |
| Primeras requests al backend dan timeout | Arranque en frío del contenedor. | Esperar 1–2 min; después responde normal. |

---

## Modelo de costos y límites

| Servicio | Plan | Límite / costo |
|---|---|---|
| Azure Static Web Apps | Free | 100 GB/mes de ancho de banda, 0,5 GB de almacenamiento |
| Azure App Service | Basic B1 | 1 vCore, 1,75 GB RAM. ~$13 USD/mes (cubierto por el crédito de estudiante) |
| Supabase Postgres | Free | 500 MB de base, se pausa tras inactividad prolongada. **Gratis permanente** |
| Brevo | Free | **300 correos/día**, 1 remitente verificado |
| Gemini 2.5 Flash | Free | 15 req/min, 1.500 req/día |

> Mover la base a Supabase y el correo a Brevo **elimina el costo mensual** de la
> base de datos de Azure y del plan de SendGrid: el único gasto es el App Service
> B1, que el crédito de *Azure for Students* cubre.
