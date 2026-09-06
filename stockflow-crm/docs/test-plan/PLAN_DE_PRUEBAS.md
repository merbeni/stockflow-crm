# Plan de Pruebas — StockFlow CRM

> Documento de planificación y ejecución de pruebas del sistema.
> Complementa a [`docs/test-cases/`](../test-cases/), que contiene el detalle caso por caso
> en planilla; acá está la **estrategia**: qué se prueba, con qué técnica, con qué criterio
> se acepta y qué se encontró al ejecutarlo.

---

## 1. Objetivo

Verificar que StockFlow CRM cumple lo especificado en los casos de uso **y**, sobre todo,
**buscar activamente los puntos donde falla**. Un plan que solo recorre el camino feliz
confirma que el sistema anda cuando lo usa alguien que hace todo bien; no dice nada de qué
pasa cuando el usuario se equivoca, se apura, escribe cualquier cosa o intenta algo que no
le corresponde.

Por eso la mayor parte de este plan está dedicada a **casos negativos, límites, errores de
uso y ataques**, y a la **calidad de la experiencia** (que el sistema sea comprensible,
accesible y perdone errores), no solo a la corrección funcional.

### 1.1 Objetivos concretos

| # | Objetivo | Cómo se mide |
|---|----------|--------------|
| O1 | Ninguna entrada del usuario puede provocar un error 500 | Toda respuesta de error es 4xx con mensaje legible |
| O2 | Una organización nunca ve ni modifica datos de otra | 100 % de los intentos cruzados devuelven 404 |
| O3 | Un operador no puede realizar acciones de administrador | 100 % de los intentos devuelven 403 |
| O4 | Las reglas de negocio de stock no se pueden violar | No existe camino que deje stock negativo |
| O5 | Todo par de colores cumple WCAG 2.1 AA | Contraste ≥ 4.5:1 texto, ≥ 3:1 componentes |
| O6 | El sistema es operable solo con teclado | Foco visible y alcanzable en todo control |

---

## 2. Alcance

### 2.1 Qué se prueba

| Módulo | Componentes cubiertos |
|--------|----------------------|
| Acceso | Alta de organización, verificación de correo, reenvío, login, sesión |
| Usuarios | ABM de usuarios, roles, activación/desactivación |
| Productos | ABM, SKU, precios, stock mínimo, stock decimal, bajo stock |
| Proveedores | ABM, datos de contacto, borrado con dependencias |
| Clientes | ABM, historial de pedidos |
| Pedidos | Creación, líneas, máquina de estados, descuento de stock, aviso por correo |
| Facturas con IA | Carga, extracción, corrección manual, confirmación, rechazo |
| Movimientos | Registro automático de entradas y salidas, trazabilidad |
| Transversal | Autenticación, autorización, aislamiento multiempresa, manejo de errores |
| Interfaz | Usabilidad, accesibilidad, adaptación a pantallas, estados vacío/carga/error |

### 2.2 Qué queda fuera

| Fuera de alcance | Motivo |
|------------------|--------|
| Precisión de la extracción de Gemini | Depende de un servicio externo y de la calidad del PDF; se prueba que el sistema **maneje** cualquier salida, no que la salida sea correcta |
| Entregabilidad real del correo (SPF/DKIM) | Responsabilidad del proveedor SMTP (Brevo) |
| Pruebas de carga y estrés con volúmenes de producción | El proyecto no tiene requisitos de rendimiento definidos; se hace solo una verificación de concurrencia puntual |
| Compatibilidad con navegadores heredados | El alcance declarado es navegadores actuales (Chrome, Firefox, Edge) |

---

## 3. Estrategia

Se sigue una **pirámide de pruebas**: muchas pruebas rápidas y baratas en la base, pocas y
costosas arriba. Encima de la pirámide se agregan dos capas que no son automatizables y que
son las que encuentran los problemas que las otras no ven.

```
                  ┌───────────────────────────────┐
                  │  Exploratorias / adversariales│  ← buscan romper el sistema
                  ├───────────────────────────────┤
                  │  UX, accesibilidad, contraste │  ← calidad percibida
                  ├───────────────────────────────┤
                  │  Integración de la API (HTTP) │  ← 193 pruebas automatizadas
                  ├───────────────────────────────┤
                  │  Unitarias front y componentes│  ← 45 pruebas automatizadas
                  └───────────────────────────────┘
```

| Nivel | Herramienta | Qué verifica | Cuándo se corre |
|-------|-------------|--------------|-----------------|
| Unitario (frontend) | Vitest + Testing Library | Validadores, cliente HTTP, contexto de sesión, componentes | En cada cambio |
| Integración (backend) | pytest + TestClient + SQLite en memoria | Cada endpoint de punta a punta, con base real por prueba | En cada cambio |
| Sistema | Ejecución manual sobre el entorno desplegado | Flujos completos entre módulos | Antes de cada despliegue |
| Adversarial | Script propio contra la API | Inyección, límites, aislamiento, concurrencia | Antes de cada entrega |
| UX / accesibilidad | Inspección guiada por heurísticas + cálculo de contraste | Comprensibilidad y accesibilidad | Ante cambios de interfaz |

### 3.1 Por qué la base de pruebas se recrea en cada caso

Cada prueba de integración levanta una base SQLite en memoria y la destruye al terminar.
Es una decisión deliberada: si las pruebas compartieran datos, el resultado dependería del
orden de ejecución y un caso podría pasar solo porque otro dejó algo preparado. Aislarlas
las hace más lentas pero **confiables**, que es la única propiedad que importa en una prueba.

---

## 4. Entornos

| Entorno | Base de datos | Correo | IA | Uso |
|---------|---------------|--------|----|-----|
| Pruebas automatizadas | SQLite en memoria (efímera) | Simulado (mock) | Simulado (mock) | Suite de CI y desarrollo |
| Desarrollo local | Supabase PostgreSQL 17 | Brevo (real) | Gemini (real) | Pruebas exploratorias y manuales |
| Producción | Supabase PostgreSQL 17 (pooler IPv4) | Brevo (real) | Gemini (real) | Verificación posterior al despliegue |

> **Advertencia sobre los servicios externos.** Las pruebas automatizadas **nunca** llaman a
> Gemini ni envían correos: se sustituyen por dobles de prueba. Depender de un servicio
> externo haría que la suite fallara por motivos ajenos al código y consumiría cuota.

### 4.1 Datos de prueba

Las pruebas construyen sus propios datos mediante *fixtures*, que crean como mínimo **dos
organizaciones distintas**. Esto no es un detalle: sin una segunda organización sería
imposible detectar una fuga de datos entre clientes, que es el riesgo más grave del sistema.

---

## 5. Criterios de entrada y de salida

### 5.1 Criterios de entrada (cuándo se puede empezar a probar)

1. El código compila y la aplicación levanta sin errores.
2. Las migraciones de base de datos se aplican correctamente (`alembic upgrade head`).
3. Las variables de entorno del entorno destino están configuradas.
4. La funcionalidad a probar está documentada en un caso de uso.

### 5.2 Criterios de salida (cuándo se considera aprobado)

| Criterio | Umbral |
|----------|--------|
| Pruebas automatizadas | 100 % en verde, sin pruebas omitidas ni marcadas como esperadas-fallar |
| Defectos críticos y graves | 0 abiertos |
| Defectos medios | Documentados, con decisión explícita de corregir o postergar |
| Contraste de color | Sin pares por debajo del mínimo WCAG AA |
| Verificación posterior al despliegue | Alta, verificación, login y una lectura autenticada correctas en producción |

---

## 6. Técnicas de diseño de casos

No se inventan casos al azar: cada uno sale de aplicar una técnica reconocida. Así se cubre
más con menos casos y se justifica por qué **ese** valor y no otro.

| Técnica | Para qué se usa | Ejemplo concreto en StockFlow |
|---------|-----------------|-------------------------------|
| **Particiones de equivalencia** | Agrupar entradas que el sistema trata igual | Contraseña: `< 8 caracteres` / `≥ 8 sin número` / `≥ 8 con letra y número` |
| **Valores límite** | Los errores se concentran en los bordes | Contraseña de 7 y de 8 caracteres; precio de 99.999.999,99 y de 100.000.000,00 |
| **Tabla de decisión** | Reglas con varias condiciones combinadas | Confirmación de línea de factura: `producto existente` × `producto nuevo` × `omitir` |
| **Transición de estados** | Flujos con máquina de estados | Pedido: pendiente → en preparación → enviado → entregado, y todos los saltos inválidos |
| **Conjetura de errores** | Experiencia sobre dónde suelen romperse los sistemas | Correo con mayúsculas, espacios al inicio, doble clic en Guardar |
| **Pruebas basadas en riesgo** | Concentrar esfuerzo donde el daño sería mayor | Aislamiento entre organizaciones y escalada de privilegios |
| **Heurísticas de usabilidad** | Evaluar la interfaz con criterio, no con gusto | Las 10 heurísticas de Nielsen (sección 10) |

---

## 7. Cobertura automatizada actual

| Suite | Archivos | Casos | Resultado |
|-------|----------|-------|-----------|
| Backend (pytest) | 8 | 193 | ✅ Todos en verde |
| Frontend (Vitest) | 7 | 45 | ✅ Todos en verde |
| **Total** | **15** | **238** | ✅ |

### 7.1 Desglose del backend por módulo

| Archivo | Casos | Foco |
|---------|-------|------|
| `test_auth.py` | 31 | Alta, verificación de correo, login, sesión, roles |
| `test_products.py` | 36 | ABM, SKU único, stock decimal, límites numéricos, borrado |
| `test_invoices.py` | 34 | Procesamiento, confirmación, rechazo, alta desde factura |
| `test_orders.py` | 26 | Líneas, máquina de estados, stock insuficiente, correo |
| `test_customers.py` | 22 | ABM, historial, borrado con pedidos |
| `test_suppliers.py` | 18 | ABM, validaciones de contacto, aislamiento |
| `test_stock_movements.py` | 18 | Registro automático, trazabilidad, filtros |
| `test_security.py` | 8 | Hash de contraseñas y firma de tokens |

### 7.2 Desglose del frontend

| Archivo | Casos | Foco |
|---------|-------|------|
| `ui/Modal.test.jsx` | 11 | Comportamiento y **accesibilidad** del diálogo |
| `ui/Badge.test.jsx` | 10 | Indicadores de estado y de confianza de la IA |
| `context/AuthContext.test.jsx` | 7 | Sesión, persistencia del token, cierre de sesión |
| `api/errors.test.js` | 9 | Traducción de errores del backend a mensajes de campo |
| `api/client.test.js` | 3 | Cliente HTTP, cabeceras, expiración de sesión |
| `PrivateRoute.test.jsx` | 3 | Protección de rutas |
| `ErrorBoundary.test.jsx` | 2 | La aplicación no queda en blanco ante un error |

> **Cómo leer estos números.** La cantidad de pruebas no mide calidad por sí sola: una suite
> puede tener 200 casos y no probar nada relevante. Lo que importa es la **proporción de
> casos negativos**: en esta suite, más de la mitad de los casos verifican rechazos,
> errores y accesos indebidos, no funcionamiento correcto.

---

## 8. Pruebas negativas y de límites por módulo

Estas son las tablas de diseño de casos. La columna **Esperado** describe la respuesta
correcta; cualquier otra cosa —en especial un 500— es un defecto.

La columna **Estado** indica con qué mecanismo se verifica hoy cada caso:

| Símbolo | Significado |
|:-------:|-------------|
| 🤖 | Cubierto por una prueba automatizada de la suite |
| ⚔️ | Verificado en la batería adversarial contra la base real |
| ✋ | Diseñado; se verifica manualmente en la ronda previa a cada entrega |

> Los casos ✋ no son deuda oculta: son los que se dejan fuera de la automatización porque el
> costo de automatizarlos supera lo que aportan (variantes de una regla que ya está probada
> con otro valor). Se listan igual para que quede explícito qué se probó y cómo.

### 8.1 Acceso y verificación de correo

| ID | Caso | Entrada | Esperado | Estado |
|----|------|---------|----------|:------:|
| PN-AUT-01 | Correo sin arroba | `no-es-mail` | 422, mensaje legible sobre el correo | 🤖 |
| PN-AUT-02 | Correo sin dominio | `ana@` | 422 | ✋ |
| PN-AUT-03 | Correo repetido | Un correo ya registrado | 400, indicando que la casilla ya está en uso | 🤖 |
| PN-AUT-04 | Correo repetido con otra caja | `ANA@TEST.COM` sobre `ana@test.com` | 400 — **la casilla es la misma** | 🤖 ⚔️ |
| PN-AUT-05 | Contraseña de 7 caracteres | `Abcdef1` | 422 (límite inferior − 1) | ⚔️ |
| PN-AUT-06 | Contraseña de 8 caracteres | `Abcdefg1` | 201 (límite inferior exacto) | ⚔️ |
| PN-AUT-07 | Contraseña muy corta | `corta` | 422 | 🤖 |
| PN-AUT-08 | Contraseña solo con letras / solo con números | `abcdefgh` / `12345678` | 422, pide una letra y un número | ✋ |
| PN-AUT-09 | Falta la contraseña | Campo ausente | 422 | 🤖 |
| PN-AUT-10 | Nombre con números | `Ana 123` | 422, el nombre de una persona no lleva dígitos | 🤖 |
| PN-AUT-11 | Teléfono con letras | `abc` | 422 | 🤖 |
| PN-AUT-12 | Teléfono con menos de 6 dígitos | `+54 11` | 422 | ✋ |
| PN-AUT-13 | Login sin verificar el correo | Cuenta recién creada | 403, explicando que falta verificar | 🤖 |
| PN-AUT-14 | Contraseña incorrecta | Contraseña equivocada | 401 | 🤖 |
| PN-AUT-15 | Correo inexistente | `nadie@test.com` | 401 — **el mismo código que el anterior** | 🤖 |
| PN-AUT-16 | Usuario desactivado | Cuenta dada de baja | 403, cuenta desactivada | 🤖 |
| PN-AUT-17 | Token de verificación inválido | 40 caracteres cualquiera | 400 | 🤖 |
| PN-AUT-18 | Reutilizar el token de verificación | El mismo token dos veces | 400 la segunda vez (uso único) | 🤖 |
| PN-AUT-19 | Reenvío a una casilla inexistente | `nadie@test.com` | 200 con **la misma respuesta** que una existente | 🤖 |
| PN-AUT-20 | Petición sin token de sesión | Sin cabecera `Authorization` | 401 | 🤖 |
| PN-AUT-21 | Token malformado | `no.es.un.token` | 401 | 🤖 ⚔️ |
| PN-AUT-22 | Token con la firma alterada | JWT con los últimos caracteres cambiados | 401 | 🤖 ⚔️ |
| PN-AUT-23 | Token firmado con otra clave | JWT válido de otro emisor | 401 | 🤖 |
| PN-AUT-24 | Inyección SQL en el login | `' OR '1'='1` | 401 o 422; nunca autentica | ⚔️ |

> **PN-AUT-15 y PN-AUT-19 son casos de seguridad, no de funcionalidad.** Si el sistema
> respondiera «esa casilla no existe», estaría confirmando qué correos están registrados:
> eso permite armar una lista de usuarios válidos para atacar. Por eso la respuesta tiene
> que ser indistinguible.

### 8.2 Productos

| ID | Caso | Entrada | Esperado | Estado |
|----|------|---------|----------|:------:|
| PN-PRO-01 | SKU repetido en la organización | Un SKU existente | 400, indicando el conflicto | 🤖 |
| PN-PRO-02 | Mismo SKU en otra organización | El SKU de otra empresa | 201 — **la unicidad es por organización** | 🤖 |
| PN-PRO-03 | SKU con espacios | `SKU 001` | 422, el SKU no admite espacios | 🤖 |
| PN-PRO-04 | SKU solo con espacios | `"   "` | 422 | ⚔️ |
| PN-PRO-05 | Nombre vacío | `""` | 422 con mensaje legible | 🤖 |
| PN-PRO-06 | Nombre de 5000 caracteres | `"A" × 5000` | 422, excede el máximo | ⚔️ |
| PN-PRO-07 | Precio negativo | `-1.00` | 422 | 🤖 ⚔️ |
| PN-PRO-08 | Precio desmedido | `99999999999999999999.00` | 422 — **no debe llegar a la base** | 🤖 ⚔️ |
| PN-PRO-09 | Stock desmedido | Valor fuera del rango de la columna | 422 | 🤖 |
| PN-PRO-10 | Precio no numérico | `"gratis"` | 422 | ✋ |
| PN-PRO-11 | Stock negativo | `-5` | 422 | ✋ |
| PN-PRO-12 | Stock decimal sin permitirlo | `2.5` con la opción desactivada | 422, con explicación de la opción «a granel» | 🤖 |
| PN-PRO-13 | Stock decimal permitiéndolo | `2.5` con la opción activada | 201 | 🤖 |
| PN-PRO-14 | Quitar la opción de decimales con stock fraccionario | Producto con stock `2.5` | 400, primero hay que ajustar el stock | 🤖 |
| PN-PRO-15 | Producto inexistente | `id` que no existe | 404 | 🤖 |
| PN-PRO-16 | Producto de otra organización | `id` ajeno | 404 — **no 403** | 🤖 ⚔️ |
| PN-PRO-17 | Borrar un producto con stock pendiente | Stock mayor que cero | 400, explicando el motivo | 🤖 |
| PN-PRO-18 | Borrar un producto con historial de pedidos | Producto ya vendido | 400, sugiriendo desactivarlo | 🤖 |
| PN-PRO-19 | Nombre de producto con números | `Coca Cola 500ml` | 201 — **es válido**, a diferencia del nombre de una persona | 🤖 |

> **PN-PRO-16: por qué 404 y no 403.** Un 403 significa «existe pero no podés»; eso ya
> confirma que el recurso existe y permite descubrir cuántos productos tiene la competencia
> probando identificadores. Un 404 no revela nada.
>
> **PN-PRO-19 explica por qué hay dos validadores de nombre distintos.** Un producto puede
> llamarse `Coca Cola 500ml`; una persona no se llama `Ana 123`. Aplicar la misma regla a los
> dos campos sería un error en cualquiera de las dos direcciones.

### 8.3 Proveedores y clientes

| ID | Caso | Entrada | Esperado | Estado |
|----|------|---------|----------|:------:|
| PN-CON-01 | Correo sin formato válido | `mer` | 422, con el error señalado en el campo | 🤖 |
| PN-CON-02 | Correo con espacios alrededor | `" ana@test.com "` | Aceptado y guardado recortado y en minúsculas | ✋ |
| PN-CON-03 | Teléfono con letras | `no tengo` | 422 | 🤖 |
| PN-CON-04 | Nombre de contacto con números | `Juan 22` | 422 | 🤖 |
| PN-CON-05 | Faltan campos obligatorios | Alta sin nombre | 422 | 🤖 |
| PN-CON-06 | Nombre solo con espacios | `"   "` | 422 | 🤖 |
| PN-CON-07 | Razón social con números | `Distribuidora 24 S.A.` | 201 — **es válida** | 🤖 |
| PN-CON-08 | Proveedor o cliente de otra organización | `id` ajeno | 404 | 🤖 |
| PN-CON-09 | Mismo correo de cliente en dos organizaciones | Correo repetido entre empresas | 201 — no hay colisión entre clientes | 🤖 |
| PN-CON-10 | Ver el historial de un cliente ajeno | `id` ajeno | 404 | 🤖 |
| PN-CON-11 | Borrar un cliente con pedidos | Cliente con historial | 400, explicando el motivo | ✋ |

> **PN-CON-01 corresponde a un defecto real.** El formulario de alta rápida de proveedor,
> dentro de la pantalla de facturas, aceptaba `mer` como dirección de correo: el backend sí
> validaba, pero el formulario no avisaba nada hasta enviar. Ver DEF-03 en la sección 13.

### 8.4 Pedidos — transición de estados

La máquina de estados es `pendiente → en preparación → enviado → entregado`. Los saltos y
los retrocesos no existen, y hay operaciones permitidas solo en ciertos estados.

| ID | Caso | Estado de partida | Esperado | Estado |
|----|------|-------------------|----------|:------:|
| PN-PED-01 | Avanzar un pedido sin líneas | Pendiente, sin productos | 400, no se puede confirmar vacío | 🤖 |
| PN-PED-02 | Avanzar con stock insuficiente | Pendiente, pide más de lo que hay | 400, indicando cuánto queda y cuánto se pide | 🤖 |
| PN-PED-03 | Avanzar un pedido ya entregado | Entregado | 400, no quedan estados por avanzar | 🤖 |
| PN-PED-04 | Recorrer la cadena completa | Pendiente | Los cuatro estados en orden, sin saltos | 🤖 |
| PN-PED-05 | Agregar una línea con stock insuficiente | Pendiente | 400 | 🤖 |
| PN-PED-06 | Eliminar un pedido que ya no está pendiente | En preparación | 400, solo se borran los pendientes | 🤖 |
| PN-PED-07 | Agregar un producto desactivado | Pendiente | 400, nombrando el producto | 🤖 |
| PN-PED-08 | Agregar una línea a un pedido inexistente | — | 404 | 🤖 |
| PN-PED-09 | Agregar cantidad cero o negativa | Pendiente | 422, la cantidad debe ser mayor que cero | ✋ |
| PN-PED-10 | Agregar cantidad decimal a un producto por unidad | Pendiente | 422, con la explicación de «a granel» | 🤖 |
| PN-PED-11 | Agregar cantidad decimal a un producto a granel | Pendiente | 200 | 🤖 |
| PN-PED-12 | Pedido con un cliente de otra organización | — | 404 | 🤖 |
| PN-PED-13 | Avanzar un pedido de otra organización | — | 404 | 🤖 |
| PN-PED-14 | Quitar una línea que pertenece a otro pedido | Pendiente | 404 | ✋ |
| PN-PED-15 | Modificar líneas de un pedido ya enviado | Enviado | 400, solo se modifica lo pendiente | ✋ |

> **Verificación asociada al descuento de stock.** Al pasar de pendiente a en preparación se
> descuenta el stock y se registra un movimiento de salida por cada línea. Hay dos pruebas
> separadas —una para el stock y otra para el movimiento— porque un descuento sin movimiento
> registrado rompe la trazabilidad aunque el número quede bien.

### 8.5 Facturas con IA

Este es el módulo con más formas de fallar, porque la entrada la produce un modelo que puede
devolver cualquier cosa. La estrategia es no confiar en nada de lo que llega.

| ID | Caso | Entrada | Esperado | Estado |
|----|------|---------|----------|:------:|
| PN-FAC-01 | Documento que no es una factura | Imagen sin datos de compra | Rechazo con mensaje claro, no 500 | 🤖 |
| PN-FAC-02 | Documento que no es factura, verificación en base | Ídem | **No queda nada guardado** | 🤖 |
| PN-FAC-03 | Tipo de archivo no admitido | MIME no soportado | 415 | 🤖 |
| PN-FAC-04 | Extensión falsificada | `.exe` renombrado a `.pdf` | Rechazado por contenido, no por extensión | 🤖 |
| PN-FAC-05 | Imagen válida de una factura | JPG legible | Procesada correctamente | 🤖 |
| PN-FAC-06 | La IA devuelve una factura sin líneas | Respuesta sin ítems | Rechazo con mensaje, no factura vacía | 🤖 |
| PN-FAC-07 | La IA devuelve algo que no es JSON | Respuesta malformada | 422, no 500 | 🤖 |
| PN-FAC-08 | Confirmar sin resolver una línea | Línea sin producto ni omisión | 400, indicando qué falta en lenguaje de negocio | 🤖 |
| PN-FAC-09 | Confirmar con un producto inexistente | `id` inventado | Error **sin exponer el identificador** | 🤖 |
| PN-FAC-10 | Confirmar con un proveedor inexistente | `id` inventado | 404 sin exponer el identificador | 🤖 |
| PN-FAC-11 | Estado tras un error de confirmación | Confirmación fallida | La factura **sigue pendiente**, no queda a medias | 🤖 |
| PN-FAC-12 | Confirmar una factura ya confirmada | Factura confirmada | 400 | 🤖 |
| PN-FAC-13 | Rechazar una factura ya rechazada | Factura rechazada | 400 | 🤖 |
| PN-FAC-14 | Rechazar una factura inexistente | `id` que no existe | 404 | 🤖 |
| PN-FAC-15 | Corregir a mano la cantidad extraída | Valor distinto al detectado | Se usa el valor corregido, no el de la IA | 🤖 |
| PN-FAC-16 | Corregir a una cantidad decimal inválida | `2.5` en producto unitario | 422 | 🤖 |
| PN-FAC-17 | Factura de otra organización | `id` ajeno | 404 | 🤖 |
| PN-FAC-18 | Sugerencias de producto entre organizaciones | Producto de otra empresa | **No se sugiere nunca** | 🤖 |
| PN-FAC-19 | Producto nuevo con SKU repetido | SKU existente | 400 | ✋ |
| PN-FAC-20 | Proveedor nuevo con correo inválido | `mer` | 422 y aviso en el formulario | ✋ |
| PN-FAC-21 | Confirmar con producto **y** producto nuevo en la misma línea | Ambos completos | 400, hay que elegir uno | ✋ |

> **PN-FAC-11 es el caso más importante del módulo.** Una confirmación toca varias tablas:
> crea productos, actualiza stock y registra movimientos. Si falla a mitad de camino y deja
> parte hecha, el inventario queda corrupto y nadie se entera. La prueba verifica que ante
> un error **no quede nada aplicado** y la factura siga pendiente para reintentar.

### 8.6 Movimientos de stock

| ID | Caso | Entrada | Esperado | Estado |
|----|------|---------|----------|:------:|
| PN-MOV-01 | Rango de fechas invertido | `desde` posterior a `hasta` | 400 con mensaje claro | 🤖 |
| PN-MOV-02 | Fecha `desde` en el futuro | Fecha posterior a hoy | 400 | 🤖 |
| PN-MOV-03 | Rango con ambos extremos iguales | Mismo día | 200, es un rango válido de un día | 🤖 |
| PN-MOV-04 | Fecha `hasta` muy lejana | Año futuro | 200, es válido | 🤖 |
| PN-MOV-05 | Movimiento de otra organización | `id` ajeno | 404 | 🤖 |
| PN-MOV-06 | Alta de producto con stock inicial | Stock mayor que cero | Genera un movimiento de entrada | 🤖 |
| PN-MOV-07 | Alta de producto con stock cero | Stock en cero | **No** genera movimiento | 🤖 |
| PN-MOV-08 | Ajuste manual de stock | Modificación del stock | Genera un movimiento de ajuste, positivo o negativo | 🤖 |

> **PN-MOV-03 y PN-MOV-04 son casos de límite «positivos».** Al agregar la validación de
> rangos es fácil pasarse de restrictivo y rechazar un rango de un solo día. Estas dos
> pruebas existen para que la corrección de un error no introduzca otro.

### 8.7 Usuarios y roles

| ID | Caso | Actor | Esperado | Estado |
|----|------|-------|----------|:------:|
| PN-USU-01 | Listar usuarios | Operador | 403 | ⚔️ |
| PN-USU-02 | Crear un usuario | Operador | 403 | 🤖 |
| PN-USU-03 | Crear un administrador | Operador | 403 — **escalada de privilegios** | ⚔️ |
| PN-USU-04 | Quitarse el rol de administrador siendo el único | Administrador único | 400, la organización no puede quedarse sin administradores | 🤖 |
| PN-USU-05 | Eliminar la propia cuenta | Administrador | 400 | 🤖 |
| PN-USU-06 | Editar un usuario de otra organización | Administrador | 404 | 🤖 |
| PN-USU-07 | Listar usuarios de otra organización | Administrador | Ninguno en común | 🤖 |
| PN-USU-08 | Alta pública eligiendo el rol | Anónimo | 404, el endpoint público de registro no existe | 🤖 |
| PN-USU-09 | Usuario creado por el administrador | Administrador | Queda en su organización y **sin verificar** | 🤖 |

> **PN-USU-08 documenta una vulnerabilidad ya corregida.** Existía un endpoint público que
> permitía registrarse eligiendo el rol: cualquiera podía crearse una cuenta de
> administrador. La prueba se conserva para que no vuelva a aparecer si alguien reintroduce
> la ruta.

---

## 9. Pruebas de seguridad y aislamiento multiempresa

StockFlow es multiempresa: los datos de todos los clientes conviven en la misma base. Una
falla de aislamiento no es un error de funcionamiento, es una **filtración de datos entre
clientes**, así que se prueba con prioridad máxima.

### 9.1 Matriz de aislamiento

Para cada recurso se verifica que la organización B no pueda hacer nada con un objeto de A.
Todas las celdas devuelven 404 (o el objeto no aparece en el listado):

| Recurso | Listado | Detalle | Modificar | Eliminar | Acción propia |
|---------|:-------:|:-------:|:---------:|:--------:|:-------------:|
| Productos | 🤖 | 🤖 ⚔️ | 🤖 ⚔️ | 🤖 ⚔️ | — |
| Proveedores | 🤖 | 🤖 | ✋ | ✋ | — |
| Clientes | 🤖 | 🤖 | ✋ | ✋ | 🤖 historial |
| Pedidos | 🤖 | 🤖 | ✋ | ✋ | 🤖 avanzar |
| Facturas | 🤖 | 🤖 | — | — | 🤖 confirmar |
| Movimientos | 🤖 | 🤖 | — | — | — |
| Usuarios | 🤖 | — | 🤖 | ✋ | — |

Además se verifica el sentido inverso, que es igual de importante y más fácil de olvidar:
**lo que sí debe poder repetirse entre organizaciones.** Dos empresas distintas pueden usar
el mismo SKU (PN-PRO-02) y tener el mismo cliente (PN-CON-09); si el sistema lo impidiera,
una empresa podría deducir qué productos vende otra por los conflictos que recibe al cargar.

### 9.2 Otros controles de seguridad

| ID | Control | Esperado | Estado |
|----|---------|----------|:------:|
| SEG-01 | Inyección SQL en el login (`' OR '1'='1`) | No autentica; 401 o 422 | ⚔️ |
| SEG-02 | `'; DROP TABLE products; --` como nombre de producto | Se guarda como texto; la tabla sigue existiendo | ⚔️ |
| SEG-03 | `<script>` en un campo de texto | Se almacena literal; el navegador lo escapa al mostrarlo | ⚔️ |
| SEG-04 | Token JWT con la firma alterada | 401 | 🤖 ⚔️ |
| SEG-05 | Token firmado con otra clave secreta | 401 | 🤖 |
| SEG-06 | Contraseñas en la base | Solo el hash; nunca en texto plano | 🤖 |
| SEG-07 | Dos hashes de la misma contraseña | Distintos entre sí (sal aleatoria) | 🤖 |
| SEG-08 | Respuesta de usuario | Nunca incluye `hashed_password` | 🤖 |
| SEG-09 | Contenido del token | Solo los datos declarados | 🤖 |
| SEG-10 | Errores internos | Mensaje genérico, sin traza ni detalle de la base | 🤖 |
| SEG-11 | Cinco altas simultáneas del mismo SKU | Se crea **una sola** | ⚔️ |

> **Sobre SEG-03.** La defensa contra XSS acá está en el frontend: React escapa el contenido
> al renderizarlo. Guardar el texto tal como se ingresó es correcto —un producto podría
> llamarse legítimamente `<3`—; lo que sería un defecto es **mostrarlo sin escapar**.
>
> **Sobre SEG-07.** Que dos hashes de la misma contraseña sean distintos parece un detalle,
> pero es lo que impide que quien acceda a la base descubra qué usuarios comparten
> contraseña, que es el primer paso de un ataque por diccionario.

> **Sobre SEG-03.** La defensa contra XSS acá está en el frontend: React escapa el contenido
> al renderizarlo. Guardar el texto tal como se ingresó es correcto —un producto podría
> llamarse legítimamente `<3`—; lo que sería un defecto es **mostrarlo sin escapar**.

---

## 10. Pruebas de interfaz y experiencia de uso

La interfaz se evalúa con las **10 heurísticas de usabilidad de Jakob Nielsen**, que dan un
criterio objetivo en lugar de una opinión. Cada heurística se convierte en casos concretos.

La columna **Estado** distingue lo que ya se verificó en esta ronda (✅) de lo que forma
parte del recorrido manual previo a cada entrega (✋).

| # | Heurística | Caso de prueba | Esperado | Estado |
|---|-----------|----------------|----------|:------:|
| H1 | **Visibilidad del estado del sistema** | Guardar un formulario | El botón cambia de texto y se deshabilita mientras guarda | ✅ |
| H1 | | Cargar un listado | Se ve un indicador de carga, no una pantalla en blanco | ✅ |
| H1 | | Procesar una factura con IA | Se avisa que puede demorar; no parece colgado | ✋ |
| H2 | **Correspondencia con el mundo real** | Estados de un pedido | «Pendiente», «En preparación», «Enviado», no `pending`/`shipped` | ✅ |
| H2 | | Mensajes de error | En español, sin códigos ni jerga técnica | ✅ |
| H3 | **Control y libertad del usuario** | Abrir un modal y arrepentirse | Se cierra con «Cancelar», con la X y con la tecla **Escape** | ✅ |
| H3 | | Clic al costado de un modal con datos cargados | **No** se cierra: perder el formulario por un clic al azar es peor | ✅ |
| H3 | | Confirmar una factura | Se pueden corregir descripción, cantidad y precio antes de confirmar | ✅ |
| H3 | | Salir de una factura a medias | Queda pendiente y se puede retomar después | ✅ |
| H4 | **Consistencia y estándares** | Botones de acción principal | Mismo color y posición en todas las pantallas | ✅ |
| H4 | | Tablas | Misma estructura y mismo orden de columnas de acción | ✋ |
| H5 | **Prevención de errores** | Borrar un producto con movimientos | El botón aparece deshabilitado **con el motivo**, no falla al pulsarlo | ✅ |
| H5 | | Único administrador | Las acciones que dejarían a la empresa sin administrador no se ofrecen | ✅ |
| H5 | | Campos con formato | Se avisa del formato inválido al salir del campo, antes de enviar | ✅ |
| H5 | | Doble envío de un formulario | El botón queda deshabilitado durante el guardado | ✅ |
| H6 | **Reconocer antes que recordar** | Elegir un producto en un pedido | Se ve el nombre y el SKU, no solo el identificador | ✅ |
| H6 | | SKU del proveedor | Se completa solo si ya se mapeó en una factura anterior | ✅ |
| H7 | **Flexibilidad y eficiencia** | Buscar en un listado largo | Hay filtro y búsqueda | ✋ |
| H7 | | Navegación con teclado | Todo el formulario se completa con Tab y Enter, con foco visible | ✅ |
| H8 | **Diseño estético y minimalista** | Pantallas principales | Sin información redundante compitiendo por atención | ✋ |
| H9 | **Ayudar a reconocer y recuperarse de errores** | Enviar un formulario inválido | El error aparece **junto al campo**, no solo arriba | ✅ |
| H9 | | Error del servidor | Mensaje en lenguaje llano y posibilidad de descartarlo | ✅ |
| H9 | | Error inesperado de la aplicación | Pantalla de recuperación, no una página en blanco | ✅ |
| H10 | **Ayuda y documentación** | Opción «Admite stock decimal» | Explica cuándo usarla (granel: kilos, litros, metros) | ✅ |
| H10 | | Campo «SKU del proveedor» | Explica para qué sirve en el propio campo | ✅ |

### 10.1 Estados de la interfaz

Un error frecuente es diseñar solo el estado «con datos». Cada listado se prueba en cuatro
estados:

| Estado | Caso | Esperado | Estado |
|--------|------|----------|:------:|
| Vacío | Organización recién creada, sin productos | Mensaje que explica qué es la pantalla e invita a crear el primero | ✅ |
| Cargando | Petición en curso | Indicador visible; no se puede enviar dos veces | ✅ |
| Con error | El backend no responde | Mensaje comprensible y posibilidad de reintentar | ✅ |
| Con datos | Uso normal | Listado correcto y ordenado | ✅ |

### 10.2 Adaptación a distintas pantallas

| Ancho | Dispositivo de referencia | Verificación | Estado |
|-------|--------------------------|--------------|:------:|
| 360 px | Teléfono | No hay desplazamiento horizontal; las tablas se pueden recorrer | ✋ |
| 768 px | Tableta | El menú lateral no tapa el contenido | ✋ |
| 1280 px | Notebook | Aprovecha el ancho sin líneas de texto excesivamente largas | ✋ |
| 1920 px | Monitor | El contenido no queda perdido en el centro | ✋ |

---

## 11. Accesibilidad (WCAG 2.1 nivel AA)

La accesibilidad se verifica con criterios medibles, no por impresión visual.

| ID | Criterio WCAG | Verificación | Umbral | Estado |
|----|---------------|--------------|--------|:------:|
| ACC-01 | 1.4.3 Contraste mínimo | Texto normal sobre su fondo | ≥ 4.5:1 | ✅ |
| ACC-02 | 1.4.11 Contraste de componentes | Bordes de campos e indicador de foco | ≥ 3:1 | ✅ |
| ACC-03 | 1.4.1 Uso del color | El color nunca es el único indicador | Todo estado lleva texto | ✅ |
| ACC-04 | 2.1.1 Teclado | Toda acción se alcanza con Tab; el modal se cierra con Escape | Sin trampas de foco | ✅ |
| ACC-05 | 2.4.7 Foco visible | Indicador de foco perceptible | Contorno de 2 px | ✅ |
| ACC-06 | 4.1.2 Nombre, función, valor | El diálogo se anuncia como tal y toma su título | `role="dialog"` con nombre | ✅ |
| ACC-07 | 1.1.1 Contenido no textual | Botones de solo icono con nombre accesible | Sin botones anónimos | ✅ |
| ACC-08 | 3.3.1 Identificación de errores | El error se identifica en texto y se anuncia | `role="alert"` junto al campo | ✅ |
| ACC-09 | 3.3.2 Etiquetas e instrucciones | Toda etiqueta está **asociada** a su campo | `htmlFor` / `id` en todos los campos | ✅ |
| ACC-10 | 2.4.3 Orden del foco | Al abrir un diálogo el foco entra; al cerrarlo vuelve | Sin saltos al inicio del documento | ✅ |
| ACC-11 | 1.4.10 Reajuste | Sin desplazamiento horizontal a 320 px | Contenido en una columna | ✋ |
| ACC-12 | 1.4.4 Cambio de tamaño del texto | Legible al 200 % de zoom | Sin texto cortado | ✋ |

> **ACC-09 no es un tecnicismo.** Una etiqueta que solo está *al lado* del campo se ve bien
> pero no está conectada con él: un lector de pantalla anuncia «campo de texto, en blanco» sin
> decir cuál, y hacer clic en el texto de la etiqueta no lleva el cursor al campo. Es la
> diferencia entre parecer accesible y serlo. Ver DEF-08.

### 11.1 Ratios de contraste verificados

Los valores del sistema de color están calculados y anotados en
[`frontend/src/index.css`](../../frontend/src/index.css) para que cualquier cambio futuro se
pueda contrastar contra el umbral:

| Elemento | Color | Sobre | Ratio | Umbral | Resultado |
|----------|-------|-------|------:|-------:|-----------|
| Texto principal | `#111827` | Blanco | 17.74:1 | 4.5:1 | ✅ |
| Texto secundario | `#3F6355` | Blanco | 6.72:1 | 4.5:1 | ✅ |
| Texto atenuado | `#547668` | Menta del menú | 4.78:1 | 4.5:1 | ✅ |
| Botón principal | Blanco | `#047857` | 5.48:1 | 4.5:1 | ✅ |
| Texto sobre menta | `#065F46` | `#D1FAE5` | 7.68:1 | 4.5:1 | ✅ |
| Éxito | `#15803D` | Blanco | 5.02:1 | 4.5:1 | ✅ |
| Advertencia | `#B45309` | Blanco | 5.02:1 | 4.5:1 | ✅ |
| Peligro | `#B91C1C` | Blanco | 6.47:1 | 4.5:1 | ✅ |
| Borde de campo | `#6F998A` | Blanco | 3.18:1 | 3:1 | ✅ |
| Anillo de foco | `#047857` | Blanco | 5.48:1 | 3:1 | ✅ |

---

## 12. Gestión de defectos

### 12.1 Clasificación por severidad

| Severidad | Definición | Plazo | Ejemplo real del proyecto |
|-----------|------------|-------|---------------------------|
| **Crítica** | Pérdida o filtración de datos, o el sistema no se puede usar | Antes de entregar, sin excepción | Registro público que permitía elegir rol de administrador |
| **Grave** | Una función central falla o una regla de negocio se puede violar | Antes de entregar | Cuentas duplicadas por diferencia de mayúsculas |
| **Media** | Molestia clara con alternativa disponible | Se corrige si hay margen | Contraste insuficiente en un botón |
| **Baja** | Detalle estético o de redacción | Se registra | Un texto de ayuda mejorable |

La severidad la fija el **impacto**, no la dificultad de arreglarlo. Un error de una línea
que expone datos de otro cliente es crítico aunque se corrija en un minuto.

### 12.2 Ciclo de vida de un defecto

```
Detectado → Reproducido → Clasificado → Corregido → Prueba de regresión → Cerrado
```

**El paso obligatorio es la prueba de regresión.** Todo defecto corregido suma una prueba
automatizada que falla con el código viejo y pasa con el nuevo. Sin eso, la corrección se
puede perder en cualquier cambio futuro y nadie se entera.

---

## 13. Ejecución: resultados y defectos encontrados

### 13.1 Batería adversarial

Se ejecutó un script propio contra el backend con la base real, con el único objetivo de
romperlo: inyección, contenido malicioso, valores extremos, normalización, aislamiento entre
organizaciones, escalada de privilegios, tokens falsificados y concurrencia.

**Resultado: 20 controles ejecutados, 18 correctos, 2 defectos encontrados.**

| Bloque | Controles | Resultado |
|--------|:---------:|-----------|
| Inyección y contenido malicioso | 4 | ✅ Todos correctos |
| Límites y valores extremos | 6 | ⚠️ 1 defecto |
| Normalización de datos | 1 | ⚠️ 1 defecto |
| Aislamiento entre organizaciones | 4 | ✅ Todos correctos |
| Autorización por rol | 2 | ✅ Todos correctos |
| Tokens y sesiones | 2 | ✅ Todos correctos |
| Concurrencia y doble envío | 1 | ✅ Correcto |

> **La prueba de concurrencia merece una mención.** Se lanzaron cinco altas simultáneas del
> mismo SKU desde cinco hilos. Se creó **una sola**; las otras cuatro fueron rechazadas. Esto
> confirma que la unicidad la garantiza una restricción en la base y no una consulta previa
> en el código, que es la implementación ingenua y la que falla justo cuando dos usuarios
> guardan a la vez.

### 13.2 Registro de defectos

| ID | Defecto | Severidad | Cómo se detectó | Estado |
|----|---------|-----------|-----------------|--------|
| DEF-01 | Al registrarse llegaban dos correos contradictorios: uno pedía verificar la casilla y el otro anunciaba que ya se podía iniciar sesión, cuando el acceso seguía bloqueado | Media | Uso real | ✅ Corregido — la bienvenida se envía al verificar |
| DEF-02 | El único administrador podía convertirse en operador y dejar a la organización sin nadie que pudiera administrarla | **Grave** | Uso real | ✅ Corregido — el backend lo rechaza y la interfaz ya no ofrece la acción |
| DEF-03 | El alta rápida de proveedor dentro de la pantalla de facturas aceptaba `mer` como correo y cualquier texto como teléfono | Media | Uso real | ✅ Corregido — valida correo, teléfono, nombre y SKU |
| DEF-04 | Un precio fuera del rango de la columna llegaba hasta PostgreSQL y volvía como **error 500** en lugar de un mensaje de validación | Media | Batería adversarial | ✅ Corregido — los límites del esquema replican los de la base |
| DEF-05 | `ana@test.com` y `ANA@TEST.COM` creaban **dos cuentas distintas**, y quien se registraba con mayúsculas no podía volver a entrar escribiéndolo en minúsculas | **Grave** | Batería adversarial | ✅ Corregido — el correo se normaliza a minúsculas |
| DEF-06 | Cuatro pares de color no alcanzaban el contraste mínimo; el peor era el botón «Desactivar», en 2.15:1 sobre un mínimo de 4.5:1 | Media | Auditoría de contraste | ✅ Corregido — paleta rediseñada y verificada |
| DEF-07 | No existía indicador de foco: navegando con Tab no se sabía qué control estaba seleccionado | Media | Auditoría de accesibilidad | ✅ Corregido — regla `:focus-visible` global |
| DEF-08 | En la pantalla de facturas, las etiquetas estaban solo **al lado** de los campos, sin asociarse a ellos: un lector de pantalla no podía nombrarlos y hacer clic en la etiqueta no llevaba el cursor al campo | Media | Auditoría de accesibilidad | ✅ Corregido — `htmlFor`/`id` en los 8 campos, más `aria-describedby` y `role="alert"` en los errores |
| DEF-09 | La ventana modal no se cerraba con Escape, no se anunciaba como diálogo y su botón de cerrar («×») no tenía nombre accesible; además el foco no entraba al abrirla ni volvía al cerrarla | Media | Auditoría de accesibilidad | ✅ Corregido — `role="dialog"`, `aria-modal`, título como nombre accesible, Escape y manejo del foco |

### 13.3 Pruebas de regresión agregadas

Cada defecto dejó su prueba:

| Defecto | Prueba de regresión |
|---------|--------------------|
| DEF-01 | `test_la_bienvenida_se_envia_al_verificar_y_no_al_registrarse` |
| DEF-02 | `test_no_se_puede_dejar_la_organizacion_sin_administradores` |
| DEF-04 | `test_precio_desmedido_da_422_y_no_error_de_servidor`, `test_stock_desmedido_da_422` |
| DEF-05 | `test_el_correo_no_distingue_mayusculas` |
| DEF-06 | Ratios anotados en el propio archivo de estilos (sección 11.1) |
| DEF-09 | `se_cierra_con_la_tecla_Escape`, `ignora_Escape_mientras_hay_una_operación_en_curso`, `se_anuncia_como_diálogo_y_toma_el_título_como_nombre_accesible`, `el_botón_de_cerrar_tiene_nombre_accesible`, `lleva_el_foco_adentro_de_la_ventana_al_abrirse` |

> **DEF-03, DEF-07 y DEF-08 no tienen prueba automatizada.** Son propiedades del marcado
> —que un campo tenga su etiqueta asociada, que exista una regla de foco— que se verifican
> mejor con una revisión del código o una herramienta de auditoría que con una aserción por
> campo. Anotarlo es preferible a inventar una prueba que no aporta.

### 13.4 Análisis de los defectos encontrados

Vale la pena mirar **de dónde salieron**, porque dice qué tipo de prueba conviene sostener:

- **Ninguno de los nueve apareció en las pruebas automatizadas existentes.** La suite estaba
  en verde con los nueve defectos presentes. Una suite verde prueba que no se rompió lo que
  ya se probaba; no prueba que el sistema esté bien.
- **Tres salieron del uso real** (DEF-01 a DEF-03). Son problemas de experiencia que ninguna
  aserción sobre un código HTTP puede detectar: el sistema respondía 200 y hacía exactamente
  lo programado; lo que estaba mal era lo programado.
- **Dos salieron de atacar el sistema a propósito** (DEF-04, DEF-05). Los dos son casos que
  a nadie se le ocurre escribir mientras programa la funcionalidad, porque quien la programa
  ya sabe cómo se usa «bien».
- **Cuatro salieron de medir en lugar de mirar** (DEF-06 a DEF-09). El contraste insuficiente
  no se percibe a simple vista: hay que calcularlo. Una etiqueta al lado de su campo *se ve*
  igual que una etiqueta asociada a su campo; la diferencia solo aparece si se revisa el
  marcado o se navega con un lector de pantalla.

| Origen | Defectos | Qué tipo de problema encuentra |
|--------|:--------:|-------------------------------|
| Uso real por otra persona | 3 | Lo que está mal aunque funcione |
| Pruebas adversariales | 2 | Lo que nadie pensó al programar |
| Auditoría medida (contraste, marcado) | 4 | Lo que no se ve mirando |
| Suite automatizada | 0 | Lo que ya se había roto antes |

Los cuatro orígenes encuentran cosas distintas y ninguno reemplaza a los otros. De ahí que
este plan tenga cuatro capas y no una. El renglón de la suite automatizada en cero no es un
reproche: su trabajo es que ninguno de estos nueve vuelva, y para eso sí es insustituible.

---

## 14. Riesgos y limitaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Las pruebas usan SQLite y producción usa PostgreSQL | Un comportamiento propio de PostgreSQL podría no detectarse | Los casos de límites numéricos replican los tipos de columna reales; las verificaciones adversariales corren contra PostgreSQL |
| Gemini y el correo están simulados en la suite | Un cambio en el contrato externo no se detecta automáticamente | Verificación manual sobre el entorno desplegado antes de cada entrega |
| La evaluación de usabilidad la hace quien desarrolló el sistema | Sesgo de familiaridad: se pasan por alto cosas obvias para quien ya sabe usarlo | Las heurísticas dan criterio externo; DEF-01 a DEF-03 salieron justamente de que otra persona lo usara |
| No hay integración continua configurada | Alguien podría entregar con la suite en rojo | Ejecución obligatoria antes de cada commit y antes de cada despliegue |
| Sin pruebas de carga | Un volumen alto podría degradar la respuesta | Declarado fuera de alcance; los listados ya usan carga anticipada de relaciones para evitar el problema N+1 |

---

## 15. Cómo ejecutar las pruebas

### Backend

```bash
cd backend
venv\Scripts\activate
pip install -r requirements-test.txt
pytest -q                 # suite completa
pytest tests/test_auth.py -v   # un módulo
pytest -k "aislamiento" -v     # solo las pruebas de aislamiento
```

### Frontend

```bash
cd frontend
npm install
npm test          # una pasada
npx vitest        # modo interactivo
```

### Criterio

Una entrega es válida solo si **ambas suites terminan sin fallos**. Una prueba omitida cuenta
como fallo: si no se puede ejecutar, no está probando nada.

---

## 16. Documentos relacionados

| Documento | Ubicación |
|-----------|-----------|
| Casos de prueba en planilla | [`docs/test-cases/`](../test-cases/) |
| Casos de uso | [`docs/use-cases/`](../use-cases/) |
| Diagramas de flujo | [`docs/flows/DIAGRAMAS_DE_FLUJO.md`](../flows/DIAGRAMAS_DE_FLUJO.md) |
| Modelo de datos | [`docs/der/DER.md`](../der/DER.md) |
| Guía de despliegue | [`docs/despliegue/DESPLIEGUE.md`](../despliegue/DESPLIEGUE.md) |
| Manual de usuario | [`docs/user-manual/`](../user-manual/) |
