# Diagramas de Flujo — StockFlow CRM

Documento de procesos del sistema. Describe la **lógica de cada proceso**: los
pasos, las decisiones, las validaciones y los caminos alternativos.

> 📌 Los diagramas están en formato **Mermaid**: GitHub los renderiza
> automáticamente y se pueden exportar a PNG/SVG pegándolos en
> [mermaid.live](https://mermaid.live).

## Índice

1. [Autenticación y acceso](#1-autenticación-y-acceso)
   - 1.1 [Registro de una organización](#11-registro-de-una-organización)
   - 1.2 [Verificación del correo electrónico](#12-verificación-del-correo-electrónico)
   - 1.3 [Inicio de sesión](#13-inicio-de-sesión)
2. [Procesamiento de facturas con IA](#2-procesamiento-de-facturas-con-ia)
3. [ABM de Proveedores](#3-abm-de-proveedores)
4. [ABM de Clientes](#4-abm-de-clientes)
5. [ABM de Productos](#5-abm-de-productos)
6. [Gestión de pedidos](#6-gestión-de-pedidos)
7. [Gestión de usuarios del equipo](#7-gestión-de-usuarios-del-equipo)
8. [Flujos de trabajo integrales](#8-flujos-de-trabajo-integrales)

### Convenciones

| Símbolo | Significado |
|---|---|
| Óvalo | Inicio o fin del proceso |
| Rectángulo | Acción o proceso |
| Rombo | Decisión / validación |
| Cilindro | Persistencia en la base de datos |

---

## 1. Autenticación y acceso

### 1.1 Registro de una organización

Alta pública del sistema. Cada registro crea una organización independiente y
deja a su autor como administrador.

```mermaid
flowchart TD
    A([El visitante entra a la pantalla de registro]) --> B[Completa nombre de la organizacion, <br/>nombre y apellido, correo, telefono y contrasena]
    B --> C{Los datos son validos?}
    C -->|No| D[El sistema senala el campo <br/>y explica que corregir]
    D --> B
    C -->|Si| E{El correo ya esta registrado?}
    E -->|Si| F[El sistema informa que ya existe una cuenta <br/>y sugiere iniciar sesion]
    F --> B
    E -->|No| G[Se crea la organizacion]
    G --> H[Se crea el primer usuario <br/>con rol de administrador]
    H --> I[Se genera un enlace de confirmacion <br/>con vigencia de 24 horas]
    I --> J[(Se guarda la organizacion, <br/>el usuario y el enlace)]
    J --> K{El servicio de correo <br/>esta disponible?}
    K -->|Si| L[Se envia el correo de confirmacion]
    K -->|No| M[El enlace queda registrado <br/>en el servidor para su recuperacion]
    L --> N([Se informa al usuario <br/>que revise su casilla])
    M --> N
```

### 1.2 Verificación del correo electrónico

Paso obligatorio: hasta completarlo, la cuenta no puede operar.

```mermaid
flowchart TD
    A([El usuario abre el enlace <br/>recibido por correo]) --> B{El enlace existe?}
    B -->|No| C[Se informa que el enlace no es valido]
    C --> D[Se ofrece solicitar uno nuevo]
    D --> E([Fin])
    B -->|Si| F{Esta dentro <br/>de las 24 horas?}
    F -->|No| G[Se informa que el enlace vencio]
    G --> D
    F -->|Si| H{Ya fue utilizado?}
    H -->|Si| G
    H -->|No| I[Se marca la cuenta como confirmada]
    I --> J[Se invalida el enlace <br/>para que no pueda reutilizarse]
    J --> K[(Se actualiza el usuario)]
    K --> L([La cuenta queda habilitada <br/>para iniciar sesion])
```

### 1.3 Inicio de sesión

```mermaid
flowchart TD
    A([El usuario ingresa <br/>correo y contrasena]) --> B{Existe una cuenta <br/>con ese correo?}
    B -->|No| C[Se informa que el correo <br/>o la contrasena son incorrectos]
    C --> A
    B -->|Si| D{La contrasena coincide?}
    D -->|No| C
    D -->|Si| E{El correo <br/>fue confirmado?}
    E -->|No| F[Se informa que debe confirmar su correo <br/>y se ofrece reenviar el enlace]
    F --> A
    E -->|Si| G{La cuenta <br/>esta habilitada?}
    G -->|No| H[Se informa que la cuenta fue desactivada <br/>y que contacte al administrador]
    H --> A
    G -->|Si| I[Se genera la credencial de sesion]
    I --> J[Se resuelve la organizacion del usuario]
    J --> K([Acceso al panel principal <br/>con los datos de su organizacion])
```

---

## 2. Procesamiento de facturas con IA

Proceso central del sistema. La inteligencia artificial **asiste** la carga, pero
la revisión humana es obligatoria: nada modifica el inventario sin confirmación
explícita del usuario.

```mermaid
flowchart TD
    A([El usuario selecciona el archivo <br/>de la factura]) --> B{El contenido real es <br/>una imagen o un PDF?}
    B -->|No| C[Se rechaza el archivo: <br/>la extension no coincide con el contenido]
    C --> Z([Fin: no se guarda nada])
    B -->|Si| D{Supera el tamano <br/>maximo admitido?}
    D -->|Si| E[Se informa que el archivo es demasiado grande]
    E --> Z
    D -->|No| F[El asistente de IA analiza el documento]
    F --> G{Es una factura <br/>o un remito?}
    G -->|No| H[Se rechaza el documento <br/>y se explica el motivo]
    H --> Z
    G -->|Si| I[La IA extrae proveedor, fecha <br/>y lineas con cantidades y precios]
    I --> J{Se detecto <br/>alguna linea?}
    J -->|No| K[Se informa que no se encontraron <br/>articulos para cargar]
    K --> Z
    J -->|Si| L[Se asigna a cada linea <br/>un nivel de confianza]
    L --> M[Se propone el proveedor que coincide <br/>y los productos del catalogo]
    M --> N[(Se guarda la factura <br/>en estado pendiente)]
    N --> O[/El usuario revisa las lineas, <br/>resaltadas segun su confianza/]
    O --> P[Corrige descripcion, cantidad y precio <br/>si hace falta]
    P --> Q{Para cada linea: <br/>que hacer?}
    Q -->|Asociar| R[Se vincula a un producto del catalogo]
    Q -->|Crear| S[Se da de alta un producto nuevo]
    Q -->|Omitir| T[La linea no afectara el inventario]
    R --> U{Quedan lineas <br/>sin resolver?}
    S --> U
    T --> U
    U -->|Si| O
    U -->|No| V{El usuario confirma <br/>la factura?}
    V -->|Rechaza| W[La factura queda rechazada <br/>sin tocar el inventario]
    W --> Z2([Fin])
    V -->|Confirma| X{Todas las cantidades respetan <br/>la unidad de medida?}
    X -->|No| Y[Se informa el error y la factura <br/>sigue pendiente: no se aplica nada]
    Y --> O
    X -->|Si| AA[Se incrementa el stock <br/>de cada producto confirmado]
    AA --> AB[Se registra un ingreso en el historial <br/>por cada articulo]
    AB --> AC[Se memoriza la equivalencia entre el codigo <br/>del proveedor y el producto propio]
    AC --> AD[(Se marca la factura <br/>como confirmada)]
    AD --> AE{Algun producto quedo <br/>bajo su stock minimo?}
    AE -->|Si| AF[Se emite el aviso de stock bajo]
    AE -->|No| AG([Fin: inventario actualizado])
    AF --> AG
```

> **Nota sobre la atomicidad.** La confirmación es *todo o nada*: si falla
> cualquier línea, no se aplica ningún cambio y la factura permanece pendiente.
> Así se evita que el inventario quede a medio actualizar.

---

## 3. ABM de Proveedores

```mermaid
flowchart TD
    A([El usuario entra al modulo <br/>de proveedores]) --> B{Que operacion <br/>desea realizar?}

    B -->|Alta| C[Completa razon social, persona de contacto, <br/>correo y telefono]
    C --> D{Los datos <br/>son validos?}
    D -->|No| E[Se senala el campo a corregir]
    E --> C
    D -->|Si| F[(Se registra el proveedor <br/>en la organizacion)]
    F --> M([El listado queda actualizado])

    B -->|Modificacion| G[Selecciona el proveedor del listado]
    G --> H{Pertenece a <br/>su organizacion?}
    H -->|No| I[El sistema responde <br/>como si no existiera]
    I --> M
    H -->|Si| J[Edita los datos necesarios]
    J --> D

    B -->|Baja| K[Selecciona el proveedor <br/>y confirma la eliminacion]
    K --> H2{Pertenece a <br/>su organizacion?}
    H2 -->|No| I
    H2 -->|Si| L[(Se elimina el proveedor. <br/>Las facturas historicas se conservan <br/>sin la referencia)]
    L --> M

    B -->|Consulta| N[Se muestra el listado <br/>ordenado por nombre]
    N --> M
```

> **Nota.** Al eliminar un proveedor, las facturas que lo referenciaban se
> conservan pero pierden la referencia. Se prioriza no perder el historial de
> compras.

---

## 4. ABM de Clientes

```mermaid
flowchart TD
    A([El usuario entra al modulo <br/>de clientes]) --> B{Que operacion <br/>desea realizar?}

    B -->|Alta| C[Completa nombre, correo, <br/>telefono y domicilio]
    C --> D{El correo tiene <br/>formato valido?}
    D -->|No| E[Se senala el campo a corregir]
    E --> C
    D -->|Si| F{Ya existe un cliente con ese <br/>correo en la organizacion?}
    F -->|Si| G[Se informa que el correo <br/>ya esta en uso]
    G --> C
    F -->|No| H[(Se registra el cliente)]
    H --> R([El listado queda actualizado])

    B -->|Modificacion| I[Selecciona el cliente y edita sus datos]
    I --> J{Pertenece a <br/>su organizacion?}
    J -->|No| K[El sistema responde <br/>como si no existiera]
    K --> R
    J -->|Si| D

    B -->|Baja| L[Selecciona el cliente <br/>y confirma la eliminacion]
    L --> J2{Pertenece a <br/>su organizacion?}
    J2 -->|No| K
    J2 -->|Si| M{Tiene pedidos <br/>registrados?}
    M -->|Si| N[Se impide la baja <br/>para preservar el historial comercial]
    N --> R
    M -->|No| O[(Se elimina el cliente)]
    O --> R

    B -->|Historial| P[Selecciona el cliente <br/>y solicita su historial]
    P --> Q[Se muestran sus pedidos <br/>con estado e importe total]
    Q --> R
```

> **Nota.** El correo del cliente es único **dentro de cada organización**: dos
> empresas distintas pueden tener registrado al mismo cliente.

---

## 5. ABM de Productos

```mermaid
flowchart TD
    A([El usuario entra al modulo <br/>de inventario]) --> B{Que operacion <br/>desea realizar?}

    B -->|Alta| C[Completa codigo, nombre, descripcion, <br/>precio, stock inicial y stock minimo]
    C --> C2[Indica si el articulo es por unidad <br/>o a granel]
    C2 --> D{Los datos <br/>son validos?}
    D -->|No| E[Se senala el campo a corregir]
    E --> C
    D -->|Si| F{El codigo ya existe <br/>en la organizacion?}
    F -->|Si| G[Se informa que el codigo <br/>ya esta en uso]
    G --> C
    F -->|No| H[(Se registra el producto)]
    H --> I{Se cargo <br/>con stock inicial?}
    I -->|Si| J[Se registra el ingreso <br/>en el historial]
    I -->|No| W([El catalogo queda actualizado])
    J --> W

    B -->|Modificacion| K[Selecciona el producto <br/>y edita sus datos]
    K --> L{La cantidad respeta <br/>la unidad de medida?}
    L -->|No| M[Se rechaza: el articulo por unidad <br/>no admite decimales]
    M --> K
    L -->|Si| N[(Se actualiza el producto)]
    N --> O{Cambio el stock?}
    O -->|Si| P[Se registra un ajuste en el historial <br/>con la diferencia]
    O -->|No| W
    P --> W

    B -->|Baja| Q[Selecciona el producto]
    Q --> R{Tiene stock <br/>pendiente?}
    R -->|Si| S[Se impide la baja: primero <br/>debe ajustarse el stock a cero]
    S --> W
    R -->|No| T{Tiene historial comercial <br/>en pedidos o facturas?}
    T -->|Si| U[Se impide la baja <br/>para preservar la trazabilidad]
    U --> W
    T -->|No| V[(Se elimina el producto y <br/>sus ajustes internos)]
    V --> W
```

---

## 6. Gestión de pedidos

El stock se descuenta **al comenzar la preparación**, no al crear el pedido.

```mermaid
flowchart TD
    A([Se crea un pedido <br/>para un cliente]) --> B[Estado: Pendiente]
    B --> C[Se agregan articulos <br/>indicando cantidad y precio]
    C --> D{Hay stock <br/>suficiente?}
    D -->|No| E[Se informa la disponibilidad real]
    E --> C
    D -->|Si| F{El producto <br/>esta activo?}
    F -->|No| G[No se permite incorporarlo]
    G --> C
    F -->|Si| H[Se incorpora el articulo <br/>y se recalcula el total]
    H --> I{Se agregan <br/>mas articulos?}
    I -->|Si| C
    I -->|No| J{Que sucede <br/>con el pedido?}

    J -->|Se anula| K{Sigue en <br/>estado Pendiente?}
    K -->|No| L[No puede anularse: <br/>el stock ya fue descontado]
    L --> J
    K -->|Si| M[(Se elimina el pedido <br/>sin afectar el inventario)]
    M --> Z([Fin])

    J -->|Se avanza| N{Tiene articulos?}
    N -->|No| O[No puede prepararse <br/>un pedido vacio]
    O --> C
    N -->|Si| P[Estado: Procesando]
    P --> Q[Se descuenta el stock de cada articulo]
    Q --> R[Se registran las salidas en el historial]
    R --> S[Se notifica al cliente por correo <br/>con el detalle adjunto]
    S --> T[Estado: Enviado]
    T --> U[Se notifica al cliente]
    U --> V[Estado: Entregado]
    V --> W[Se notifica al cliente]
    W --> Z
```

---

## 7. Gestión de usuarios del equipo

Proceso exclusivo del administrador.

```mermaid
flowchart TD
    A([El administrador entra <br/>al modulo de usuarios]) --> B{Tiene rol de <br/>administrador?}
    B -->|No| C[El modulo no esta disponible <br/>y la operacion se rechaza]
    C --> Z([Fin])
    B -->|Si| D[Se muestran unicamente los usuarios <br/>de su organizacion]
    D --> E{Que operacion <br/>desea realizar?}

    E -->|Alta| F[Completa correo, nombre, telefono, <br/>contrasena inicial y rol]
    F --> G{El correo <br/>ya esta en uso?}
    G -->|Si| H[Se informa que ya existe una cuenta]
    H --> F
    G -->|No| I[(Se crea el usuario dentro <br/>de la organizacion)]
    I --> Y([El equipo queda actualizado])

    E -->|Cambiar rol| J[Selecciona el integrante <br/>y el nuevo rol]
    J --> K{La organizacion quedaria sin <br/>ningun administrador habilitado?}
    K -->|Si| L[Se rechaza la operacion <br/>y se explica el motivo]
    L --> Y
    K -->|No| M[(Se actualiza el rol)]
    M --> Y

    E -->|Habilitar o deshabilitar| N[Selecciona el integrante]
    N --> K

    E -->|Baja| O{Es su propia cuenta?}
    O -->|Si| P[No se permite eliminar <br/>la propia cuenta]
    P --> Y
    O -->|No| K2{La organizacion quedaria sin <br/>ningun administrador habilitado?}
    K2 -->|Si| L
    K2 -->|No| Q[(Se elimina el usuario)]
    Q --> Y
```

---

## 8. Flujos de trabajo integrales

Procesos operativos completos que atraviesan varios módulos del sistema.

### 8.1 Recepción de mercadería con factura

```mermaid
flowchart LR
    A([Llega mercaderia <br/>con su factura]) --> B[Se procesa la factura <br/>con asistencia de IA]
    B --> C[Se revisan y corrigen <br/>las lineas extraidas]
    C --> D[Se confirma la factura]
    D --> E[El stock se incrementa <br/>automaticamente]
    E --> F[Se generan los ingresos <br/>en el historial]
    F --> G{Algun producto quedo <br/>bajo el minimo?}
    G -->|Si| H[Se emite el aviso <br/>de stock bajo]
    G -->|No| I([Mercaderia incorporada <br/>al inventario])
    H --> I
```

### 8.2 Atención de un pedido de cliente

```mermaid
flowchart LR
    A([El cliente realiza <br/>un pedido]) --> B[Se registra el pedido <br/>y se agregan los articulos]
    B --> C[Se avanza a Procesando: <br/>el stock se descuenta]
    C --> D[Se avanza a Enviado <br/>al despachar]
    D --> E[Se avanza a Entregado <br/>al confirmar la recepcion]
    E --> F([Pedido completado])
    C -.-> N[El cliente recibe <br/>un correo en cada etapa]
    D -.-> N
    E -.-> N
```

### 8.3 Alta de un producto nuevo desde una factura

Cuando la IA detecta un artículo que todavía no existe en el catálogo.

```mermaid
flowchart LR
    A([La IA detecta un articulo <br/>que no esta en el catalogo]) --> B[El usuario elige <br/>crear un producto nuevo]
    B --> C[Completa codigo, nombre, <br/>precio y stock minimo]
    C --> D[Se confirma la factura]
    D --> E[El producto se da de alta <br/>en el catalogo]
    E --> F[Su stock se inicializa con la cantidad <br/>recibida en la factura]
    F --> G([Producto incorporado <br/>y stock actualizado])
```

---

## Trazabilidad con los casos de uso

| Proceso | Casos de uso relacionados |
|---|---|
| 1.1 Registro de una organización | UC-20 |
| 1.2 Verificación del correo | UC-21, UC-22 |
| 1.3 Inicio de sesión | UC-01, UC-02, UC-03 |
| 2. Facturas con IA | UC-09, UC-25, UC-26, UC-10, UC-11 |
| 3. ABM de Proveedores | UC-07, UC-08 |
| 4. ABM de Clientes | UC-12, UC-13 |
| 5. ABM de Productos | UC-04, UC-05, UC-06, UC-24 |
| 6. Gestión de pedidos | UC-14, UC-15, UC-16, UC-17 |
| 7. Gestión de usuarios | UC-23 |
| Transversal a todos | UC-28 (aislamiento entre organizaciones) |
