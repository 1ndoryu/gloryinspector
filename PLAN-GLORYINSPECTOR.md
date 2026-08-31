# PLAN-GLORYINSPECTOR

> Plan de producto y ejecución para `gloryInspector`: un toolkit local, portable y
> agnóstico de proveedor para capturar evidencia autorizada, caracterizar
> protocolos, reproducir regresiones y detectar deriva.
>
> **Estado:** MVP OFFLINE F0–F9 IMPLEMENTADO — TRACKS LIVE OPCIONALES PENDIENTES  
> **Versión del plan:** 3  
> **Fecha de revisión:** 2026-08-10  
> **Revisado por:** supervisor_thinker — VEREDICTO VIABLE CON RESERVAS  
> **Ediciones aplicadas:** exit code para `NOT_RUN`, test de blob 1–8 MiB en F2,
> límite de regex también en `core/schema.py`, loopback acotado a 127.0.0.1 en F5
> y documentación mínima en F0.
> **Repositorio actual:** repositorio Git local inicializado, sin remoto; el checkout contiene la implementación offline y sus fixtures.  
> **Gate actual:** no declarado; no se debe inventar Sentinel ni un `package.json`
> para este proyecto.

## 1. Veredicto y dirección

**VEREDICTO: VIABLE CON RESERVAS.**

La idea es viable si se ejecuta como un producto de evidencia local y no como un
proxy universal ni como un servicio de probing. El riesgo principal del plan
anterior era intentar entregar a la vez un núcleo de registros, un MITM TLS, un
cliente CDP, un analizador de bundles, probes live y una integración con GloryAPI.
Eso hace que la primera fase sea demasiado grande y que los errores de seguridad o
contrato aparezcan tarde.

La dirección aprobada para ejecutar es:

1. fijar primero el contrato de datos, los exit codes, la política de secretos y
   un mock completamente determinista;
2. construir `redact`, `replay`, `classify` y `diff` sobre ese contrato;
3. añadir captura como adaptadores separados: importación/loopback primero, CDP y
   MITM después y sin bloquear el núcleo;
4. validar cada perfil contra mock antes de permitir `--live`;
5. exportar evidencia compatible con GloryAPI sin acoplar los dos repositorios;
6. tratar las llamadas reales como una operación explícita, limitada, auditable y
   nunca como parte del gate local por defecto.

El plan queda **AUTORIZADO PARA EJECUTAR** en todo su ciclo local: crear archivos,
crear el repositorio Git local, probar, ejecutar el gate, documentar y commitear.
No autoriza deploy, push, SSH ni escrituras en APIs/BD externas. Cualquier
`--live` que pueda consumir cuota, cambiar estado o afectar una cuenta requiere
autorización puntual y debe ejecutarse fuera del gate determinista.

## 2. Problema, resultado y no objetivos

### 2.1 Problema real

Los incidentes de compatibilidad se están diagnosticando comparando a mano
requests, bundles, respuestas y versiones de repositorios ajenos. Eso produce
observaciones difíciles de repetir y no permite distinguir rápidamente entre:

- cuota real y downgrade silencioso;
- fallo de autenticación y bloqueo de cuenta;
- cambio de schema y cambio de detección anti-cliente;
- regresión del worker local y deriva del upstream;
- error del proveedor y error del adaptador.

El caso de 2026-08-10 es el primer caso de aceptación: un request con tools sin la
firma esperada fue clasificado como `foreign_toolset`, respondió con un modelo
degradado y terminó pareciendo un 429 de cuota. La evidencia relacionada está en
`../gloryapi/PLAN-GLORYAPI.md` y en su `roadmap.md`; no se copian secretos ni
payloads crudos de ese repositorio.

### 2.2 Resultado deseado

Un repositorio local que permita ejecutar este circuito con evidencia sanitizada:

```text
fuente autorizada → registro canónico → redact → classify/diff
                  → fixture versionado → replay contra mock
                  → track de deriva → export opcional al consumidor
```

El resultado debe ser útil aunque nunca se active MITM ni se haga una llamada
real. Los adaptadores live aumentan la capacidad, pero no definen la salud del
núcleo.

### 2.3 No objetivos

- No reimplementar ningún servicio de proveedor, web, worker ni API upstream.
- No evadir pagos, límites, anti-bot, controles de acceso ni términos de uso.
- No interceptar tráfico de terceros ni tráfico sin autorización del propietario.
- No redistribuir bundles, sesiones ni contenido capturado de proveedores.
- No construir un framework general de pruebas ni un daemon de monitorización.
- No enviar automáticamente requests live, crear cuentas, rotar credenciales ni
  modificar configuración externa.
- No introducir Node, Rust, una base de datos o un servicio remoto en el núcleo.
- No integrar código de `gloryInspector` dentro de GloryAPI en esta tarea. La
  integración se limita a un contrato de exportación y a una tarea consumidora
  posterior si hace falta.
- No prometer que una respuesta 200 implica que el modelo solicitado fue usado.

## 3. Hechos confirmados, supuestos y decisiones bloqueantes

### 3.1 Hechos confirmados

- `gloryInspector` no tiene todavía código, manifest, README, tests ni Git.
- El workspace usa Python 3.11+ como runtime disponible para este proyecto.
- GloryAPI ya tiene una taxonomía sanitizada que incluye `foreign_toolset` y
  `model_downgrade`, y su Fase 9 local está cerrada en el plan maestro.
- El caso histórico requiere comparar `model_requested` con
  `model_effective`; mirar solo HTTP 200/429 no basta.
- Las operaciones live pueden consumir cuota o generar efectos secundarios aunque
  el endpoint se describa como una sonda de salud.

### 3.2 Supuestos operativos

- La primera versión puede funcionar sin red y sin credenciales.
- Los fixtures se crean a partir de datos propios, autorizados o sintéticos.
- El mock puede expresar responses, errores, downgrades, streams truncados y
  cambios de contrato sin depender de un proveedor.
- El consumidor inicial de exportación es GloryAPI, pero el formato de exportación
  no debe contener rutas, secretos ni detalles internos del inspector.

### 3.3 Decisiones que quedan fijadas

| Decisión | Elección | Motivo |
| --- | --- | --- |
| Formato de perfil | JSON canónico con schema versionado | Python stdlib no incluye parser YAML; no se introduce una dependencia obligatoria por conveniencia documental. |
| Formato de sesión | JSONL append-only + manifest JSON | Permite streaming, diff por línea, recuperación parcial y hashes reproducibles. |
| Cuerpo grande | Inline solo bajo límite; si excede, referencia a blob local con SHA-256 | Evita fixtures gigantes y hace verificable que el cuerpo no cambió. |
| Redacción | Fail-closed antes de persistir | Si un cuerpo o header no puede clasificarse, no se escribe como evidencia dorada. |
| Transporte MVP | Mock loopback e importación de registros | La captura real no bloquea la validación del modelo de datos. |
| Captura oficial | Adaptadores independientes: CDP primero; MITM experimental después | CDP reduce la superficie de certificados; MITM tiene fricción por CA, TLS y ToS. |
| Live | Opt-in explícito, rate limitado, sin retries por defecto | Un probe no debe convertirse en una tormenta ni en una escritura accidental. |
| Integración | Export contract-first; sin dependencia física entre repos | Evita que el inspector herede el ciclo de releases de GloryAPI. |
| Escala | Herramienta single-user, concurrencia 1 por defecto | No hay evidencia para diseñar un servicio multiusuario. |

Si en el futuro se necesita YAML para edición humana, se podrá añadir un
convertidor opcional fuera del núcleo. No se cambia el formato canónico por eso.

## 4. Contrato funcional del producto

### 4.1 Comandos del MVP y extensión

| Comando | MVP | Entrada | Salida | Side effect por defecto |
| --- | --- | --- | --- | --- |
| `inspector redact` | Sí | archivos, JSONL, texto | fixture saneado + informe | ninguno; escribe solo en ruta explícita |
| `inspector replay` | Sí | fixture + target mock | resultado, aserciones, trace | solo mock/local |
| `inspector classify` | Sí | respuesta/trace + perfil | clasificación tipada | ninguno |
| `inspector diff` | Sí | caso base + mutation spec + mock | matriz variable→resultado | solo mock/local |
| `inspector bundle` | Sí, offline | bundle local + pack | candidatos con offsets/hashes | ninguno |
| `inspector capture` | Importación/loopback | HAR/JSONL o target local | sesión canónica | local |
| `inspector probe` | Mock primero; live posterior | perfil + referencias de credencial | estados y exit code | live solo con opt-in |
| `inspector track` | Sí sobre mock | fixture + profile + target | alerta de deriva | local; sin scheduler |

`capture cdp` y `capture mitm` son plugins/adaptadores del comando `capture`,
no dos núcleos alternativos. Un fallo de un adaptador no puede romper `redact`,
`replay`, `classify`, `diff` o `track`.

### 4.2 Flags y política de ejecución

Flags globales mínimos:

```text
--profile PATH       perfil JSON validado
--input PATH         entrada explícita; nunca se adivina un archivo sensible
--output PATH        salida explícita; no se sobrescribe sin --force
--format json|md     salida de máquina o informe humano
--timeout MS         límite acotado; cada subcomando define máximo
--live               habilita transporte externo, nunca implícito
--confirm-live       confirmación adicional requerida por operaciones live
--no-retry           fuerza cero reintentos; valor por defecto en live
--dry-run            muestra el plan sin ejecutar el transporte
```

No se aceptan URLs, headers, credenciales o shell commands concatenados desde
plantillas sin validación. El perfil solo puede referenciar una credencial por
identificador; el valor se resuelve desde una fuente local protegida y nunca se
serializa en una salida.

Exit codes estables:

```text
0  éxito y aserciones satisfechas
1  aserción de protocolo fallida o deriva detectada
2  entrada, perfil o fixture inválido
3  política de seguridad/redacción bloqueó la operación
4  transporte inaccesible, timeout o error de herramienta
5  operación live no autorizada o flags incompatibles
```

`NOT_RUN` (cobertura no ejecutada) y `TOOL_ERROR` nunca devuelven 0: un resultado
con esas marcas usa el exit code 4 o el código documentado para la fase
correspondiente, de modo que una suite incompleta nunca se confunde con un PASS.

El código de salida no sustituye a la clasificación: cada resultado incluye
`status`, `findings[]`, `classification`, `assertions[]`, `trace_id` y
`tool_version`.

## 5. Arquitectura propuesta

### 5.1 Capas y responsabilidades

```text
CLI / output
    ↓
casos de uso: capture, redact, replay, classify, diff, bundle, probe, track
    ↓
core: records, redaction, profiles, transport, mutations, assertions, reports
    ↓
adapters: mock, import, cdp, mitm, live HTTP
    ↓
artefactos: manifest, JSONL sanitizado, blobs hashados, reportes JSON/MD
```

- `core.records`: schema, validación, correlación request/response/event y
  serialización determinista.
- `core.redaction`: pipeline ordenado de headers, query, JSON, texto, blobs y
  nombres; resultado `clean`, `changed` o `blocked`.
- `core.profiles`: carga JSON, validación estructural, límites y referencias a
  packs; no resuelve secretos.
- `core.transport`: timeout, tamaño máximo, cancelación, backpressure y política
  de retry. `retry` queda desactivado en live salvo que el perfil declare que una
  operación es idempotente.
- `core.spec`: mutaciones allowlisted, una variable por corrida, generación de
  casos y aserciones de modelo/stream/error.
- `core.output`: salida determinista, ordenada y sin cuerpo sensible en mensajes.
- `adapters/*`: conocimiento de transporte, no reglas de clasificación.

### 5.2 Registro canónico versionado

El registro no debe tratar cada línea como una sesión completa. Cada línea es un
`record` correlacionado y el manifest describe la sesión:

```json
{
  "schema": "inspector.record/v1",
  "record_id": "r-000001",
  "session_id": "s-20260810-0001",
  "correlation_id": "c-0001",
  "sequence": 1,
  "ts": "2026-08-10T00:00:00Z",
  "kind": "request|response|event",
  "direction": "outbound|inbound|internal",
  "url": "https://example.invalid/v1/chat/completions",
  "method": "POST",
  "headers": {"content-type": "application/json"},
  "query": {},
  "body": {"mode": "inline", "encoding": "json", "value": {"model": "{{model}}"}},
  "body_sha256": "sha256:...",
  "meta": {
    "client_id": "{{client}}",
    "capture_adapter": "mock|import|cdp|mitm|replay",
    "model_requested": "{{model_requested}}",
    "model_effective": "{{model_effective}}",
    "classification": null,
    "redaction": {"status": "clean", "rules": []},
    "notes": []
  }
}
```

Reglas del contrato:

- `schemas/record-v1.json` es normativo y usa una discriminación `oneOf` por
  `kind`: `request` exige método y dirección outbound, `response` exige status y
  dirección inbound, y `event` exige `event_type` y no puede fingir un status HTTP.
  El schema también fija los campos requeridos, tipos, enums, longitudes y
  propiedades adicionales permitidas; el bloque anterior es solo un ejemplo.
- `body` es exactamente uno de `mode=inline` con `value`, `mode=blob` con path
  relativo/hash, o `mode=absent` con razón bounded. `inline` y blob no pueden
  coexistir. Un campo omitido significa “no aplica al tipo de record”; `null`
  significa “aplica, pero no fue observado o no pudo capturarse”. Los campos
  required nunca aceptan `null`.
- La canonicalización para hashes es UTF-8 sin BOM; los cuerpos JSON se
  serializan con claves ordenadas, separadores compactos y `ensure_ascii=false`.
  El hash se calcula sobre esos bytes ya redactados, no sobre la representación
  de Python ni sobre el cuerpo original.
- `sequence` es estrictamente creciente dentro de una sesión; un response debe
  referenciar un `correlation_id` de request observado o declarar
  `orphaned=true`; un evento puede ser independiente, pero nunca reutiliza
  `record_id`.
- Los archivos de `schemas/` usan el vocabulario acotado
  `inspector.schema/v1`, no pretenden ser JSON Schema completo. F0 implementa
  `core/schema.py` con stdlib y soporta exactamente `type`, `required`,
  `properties`, `additionalProperties`, `items`, `enum`, `const`, `oneOf`,
  `minLength`, `maxLength`, `minimum`, `maximum` y `pattern` bounded. Ninguna
  fase puede usar una keyword no soportada sin cambiar primero este contrato;
  así se conserva el núcleo sin dependencias obligatorias y se evita fingir
  compatibilidad con un validador JSON Schema que no está instalado.
- `Authorization`, cookies, API keys, tokens, emails, UUIDs identificables y
  valores de alta entropía se reemplazan por placeholders o se bloquean.
- `body_sha256` se calcula sobre el cuerpo ya sanitizado; nunca sobre el secreto
  original.
- `content_encoding`, `truncated`, `status`, `headers` de respuesta y errores
  de transporte son campos explícitos; no se deducen de texto libre.
- `model_requested` y `model_effective` son opcionales individualmente, pero una
  aserción de downgrade falla si el perfil exige ambos y solo aparece uno.
- El manifest registra perfil, versión de schema, versión de herramienta, hashes,
  reloj usado y origen declarado. No registra credenciales ni rutas privadas.
- JSONL es el formato de intercambio; el informe puede ser JSON o Markdown.

### 5.3 Perfil JSON de proveedor

Ejemplo reducido de `profiles/_template.json`:

```json
{
  "schema": "inspector.profile/v1",
  "id": "template",
  "display_name": "Template",
  "targets": {
    "chat": {
      "method": "POST",
      "url_template": "https://example.invalid/v1/chat/completions",
      "auth": {"mode": "header", "name": "Authorization", "credential_ref": "chat-key"}
    },
    "health": {"method": "GET", "url_template": "https://example.invalid/health"}
  },
  "limits": {"timeout_ms": 10000, "max_body_bytes": 1048576, "concurrency": 1},
  "capture": {"host_allowlist": ["example.invalid"]},
  "redaction": {
    "pack": "secrets/v1",
    "unknown_policy": "block",
    "max_matches": 1000
  },
  "mutations": [],
  "classification": {"taxonomy": "inspector.error/v1", "rules": []},
  "assertions": {"downgrade_is_failure": true}
}
```

`schemas/profile-v1.json` es normativo. Son obligatorios `schema`, `id`,
`targets`, `limits`, `capture`, `redaction`, `classification`, `mutations` y
`assertions`; no existen defaults silenciosos para seguridad, allowlists o
clasificación. El perfil es inválido si falta cualquiera de ellos, si
`unknown_policy` no es `block` o si contiene credenciales inline. No puede
contener una URL arbitraria generada por entrada del usuario. El perfil
específico del caso histórico vive fuera de `inspector/core/`.

### 5.4 Packs de reglas

`packs/secrets.json` y `packs/bundle.json` también son JSON versionado. Cada regla
declara `id`, `kind`, patrón, prioridad, reemplazo y si el desconocimiento bloquea
la persistencia. Los patrones deben tener tests positivos y negativos; no se
aceptan regex de backtracking sin límite en entradas grandes.

## 6. Estructura objetivo del repositorio

```text
gloryInspector/
  PLAN-GLORYINSPECTOR.md
  AGENTS.md                         # reglas locales si se requieren
  README.md
  roadmap.md                        # cola compacta de ejecución
  pyproject.toml                    # metadata/lint/test, sin dependencias obligatorias
  inspector/
    __main__.py
    cli.py
    capture.py
    redact.py
    replay.py
    classify.py
    diff.py
    bundle.py
    probe.py
    track.py
    core/
      schema.py
      records.py
      redaction.py
      profiles.py
      transport.py
      mutations.py
      assertions.py
      output.py
      errors.py
    adapters/
      mock.py
      import_jsonl.py
      cdp.py                       # posterior al MVP
      mitm.py                      # experimental; posterior al MVP
  schemas/
    record-v1.json
    profile-v1.json
    result-v1.json
  profiles/
    _template.json
    historical-case.json
  packs/
    secrets.json
    bundle.json
  fixtures/
    mock/
    golden/
  tests/
    unit/
    integration/
    fixtures/
  scripts/
    check_no_secrets.py
    check_core_provider_neutral.py
    bootstrap-ca.ps1
    bootstrap-ca.sh
  docs/
    operating-policy.md
    record-schema.md
    live-runbook.md
    export-contract.md
```

`cdp.py` y `mitm.py` pueden no existir durante el MVP. No se crean archivos
vacíos para aparentar capacidad.

## 7. Fases ejecutables y gates de salida

Cada fase tiene una salida verificable. No se inicia la siguiente por el mero hecho
de que el código compile; debe quedar un artefacto y un test que demuestre el
contrato. La estimación se expresa en bloques, no en horas, porque todavía no hay
historial del repositorio.

### F0 — Bootstrap, contrato y política

**Dependencias:** ninguna.  
**Objetivo:** convertir la carpeta en un proyecto ejecutable y fijar las reglas
que evitan rehacer el núcleo.

Trabajo:

- Inicializar Git local sin remoto; comprobar rama y `HEAD` válido.
- Crear `README.md`, `roadmap.md`, `pyproject.toml` y estructura mínima; en F0
  solo se redactan los documentos con evidencia inmediata (operating-policy y
  record-schema si procede); `live-runbook.md` (F7) y `export-contract.md` (F9)
  se crean en sus fases, no como documentos vacíos al arrancar.
- Documentar Python 3.11+, comandos, licencia, uso responsable, datos autorizados
  y límites de live.
- Crear los schemas normativos `record-v1.json`, `profile-v1.json` y
  `result-v1.json`, con fixtures válidos e inválidos para `request`, `response`
  y `event`; fijar también exit codes y estados de aserción.
- Implementar el validador acotado `core/schema.py` en stdlib, con una prueba por
  cada keyword soportada y una prueba que rechace una keyword no declarada;
  `pattern` aplica el mismo límite de regex bounded que los packs para evitar
  backtracking sin límite en entradas grandes.
- Crear el mock de contrato como diseño, aunque todavía no ejecute red.
- Crear `scripts/check_no_secrets.py` y `scripts/check_core_provider_neutral.py`
  como checks ejecutables desde F0; F1 ampliará el pack y sus fixtures, pero el
  gate no dependerá de archivos inexistentes.
- Decidir explícitamente qué se considera secreto, identificador personal,
  contenido sensible y artefacto permitido.

**DoD F0:** un clon local sin dependencias externas puede mostrar `--help`,
validar los tres schemas, rechazar un perfil sin `redaction` o
`classification`, ejecutar los dos checks del gate y demostrar la diferencia
entre un record `request`, `response` y `event`; el validador solo acepta el
vocabulario `inspector.schema/v1` declarado.

**Evidencia:** commit local, `python --version`, `python -m inspector --help`,
schema de ejemplo y decisión de política.

### F1 — Redacción y almacenamiento seguro

**Dependencias:** F0.  
**Objetivo:** que ningún capturador pueda persistir material crudo por accidente.

Trabajo:

- Implementar redacción por contexto: headers, query, JSON, texto, nombres y
  blobs; aplicar reglas antes de escribir JSONL o informes.
- Implementar placeholders estables por sesión, sin revelar el valor original.
- Añadir límites de tamaño, profundidad JSON, longitud de string y cantidad de
  matches.
- Registrar una línea base informativa de tiempo y memoria con entradas de 1 MiB
  y 8 MiB; una regresión de 2x se reporta antes de ampliar los límites.
- Definir estados `clean`, `changed`, `blocked` y `unknown`; `unknown`
  bloquea fixture dorado.
- Implementar `inspector redact --check` y `--write` sin sobrescritura implícita.
- Añadir `check_no_secrets.py` sobre el árbol versionado y fixtures.

**DoD F1:** tokens, cookies, emails, UUIDs y valores de alta entropía de los casos
de prueba no aparecen en la salida; entradas ambiguas se bloquean; el escaneo
detecta un secreto sintético inyectado.

**Evidencia:** tests positivos/negativos, fixture antes/después fuera del árbol
versionado, salida JSON del scanner y ausencia de secretos en el fixture final.

### F2 — Registros, manifest y mock determinista

**Dependencias:** F1.  
**Objetivo:** tener una fuente de verdad reproducible para todas las herramientas.

Trabajo:

- Implementar `records.py` y validación estricta contra los schemas normativos;
  usar `oneOf` por `kind`, exclusividad inline/blob/absent y las reglas de
  canonicalización, `null`, correlación y secuencia descritas arriba.
- Implementar manifest de sesión, correlación, secuencia y hashes.
- Definir blobs locales con path relativo acotado al directorio de artefactos.
- Añadir un test explícito de cuerpo entre 1 MiB y 8 MiB que demuestre la
  transición inline → blob con SHA-256 (o `blocked` si no puede redactarse),
  cerrando la asimetría entre el límite inline y el máximo leído.
- Crear mock configurable para 200, 429, 401, timeout, stream truncado, schema
  inválido, modelo efectivo diferente y error estructurado.
- Hacer que el mock pueda cambiar una regla mediante un fixture de versión para
  probar deriva sin red.

**DoD F2:** el mismo input produce los mismos JSONL, hashes y resultados; una
sesión incompleta se marca como incompleta en lugar de repararse silenciosamente;
el mock no abre red externa.

**Evidencia:** fixtures válidos e inválidos por `kind`, tests de round-trip,
test de determinismo dos veces consecutivas, matriz de respuestas del mock y
validación de tamaños/límites.

### F3 — Replay, aserciones y clasificación

**Dependencias:** F2.  
**Objetivo:** poder demostrar una regresión completa contra el mock.

Trabajo:

- Implementar `core.transport` con timeout, cancelación, límite de bytes y
  backpressure; sin retry por defecto.
- Implementar `replay` con targets `mock://...` y
  `http://127.0.0.1/...` solamente.
- Implementar aserciones de status, schema, headers relevantes, stream completo,
  tool calls y `model_requested`/`model_effective`.
- Implementar `classify` con taxonomía versionada: `auth`, `rate_limit`,
  `foreign_toolset`, `model_downgrade`, `schema`, `timeout`,
  `stream_truncated`, `model_not_found`, `provider_error`, `unknown`.
- Separar clasificación de política: clasificar no decide retry, cooldown ni
  fallback.

**DoD F3:** un 200 con modelo degradado falla la aserción; un 429 con evidencia de
`foreign_toolset` no se confunde con cuota en el informe; un stream truncado queda
tipado y no pasa como éxito.

**Evidencia:** fixture `golden/protocol-regression-v1`, trace sanitizada, matriz de
clasificación y tests de errores parciales.

### F4 — Diferenciador experimental

**Dependencias:** F3.  
**Objetivo:** medir el efecto de una sola mutación por corrida.

Trabajo:

- Definir `mutation_spec` allowlisted: ruta JSON, valor base, variantes y nombre
  de variable; rechazar comodines ambiguos y mutaciones múltiples.
- Ejecutar concurrencia 1, orden estable y presupuesto global de requests/tiempo.
- Generar una matriz con input hash, variable, resultado, clasificación, modelo
  efectivo, latency bucket y trace id.
- Implementar comparación por campos estructurales, no por texto completo cuando
  haya timestamps o ids dinámicos.
- Añadir el caso histórico como **fixture sintético/mocked**; reservar toda
  comprobación live para una operación aparte y autorizada.

**DoD F4:** el mock reproduce las tres ramas esperadas del caso histórico y el
reporte prueba que solo cambió la variable declarada; una spec con dos variables
es rechazada.

**Evidencia:** `golden/foreign-toolset-v1.jsonl`, reporte JSON/MD y test de orden,
rate limit, cancelación y no-retry.

### F5 — Captura por adaptadores

**Dependencias:** F1–F3.  
**Objetivo:** ingresar evidencia real/autorizada sin contaminar el núcleo.

Orden de implementación:

1. `capture import`: convertir un formato local autorizado a registro canónico.
2. `capture loopback`: capturar únicamente tráfico generado contra el mock local.
   El listener escucha solo en `127.0.0.1`, con timeout global y sin exponer
   puertos a otras interfaces.
3. `capture cdp`: conectar a una sesión CDP explícitamente seleccionada, con
   allowlist de hosts y redacción antes de persistir.
4. `capture mitm`: experimento separado con CA generada localmente, límites,
   limpieza de certificados y documentación por SO.

El adaptador debe declarar si soporta requests, responses, eventos, streaming,
websockets y cuerpos truncados. Si no puede sanitizar una parte, la sesión queda
`blocked`; no se rellena con datos inventados.

**DoD F5-MVP:** importación y loopback producen exactamente el mismo registro que
el mock.  
**DoD F5-CDP/MITM:** solo se cierra cada adaptador con una prueba manual/autorizada,
un runbook de cleanup y evidencia de cero secretos en disco. Si no hay entorno
autorizado, el adaptador queda documentado como pendiente, no simulado.

**Evidencia:** fixtures por adaptador, matriz de capacidades y prueba de fallo
seguro ante host fuera de allowlist.

### F6 — Bundle offline

**Dependencias:** F1–F2.  
**Objetivo:** extraer candidatos de un bundle local sin ejecutar JavaScript.

Trabajo:

- Implementar `bundle` sobre archivos locales, con hash, tamaño, offsets y
  contexto acotado.
- Extraer URLs, nombres de headers, nombres de tools, UUIDs y constantes mediante
  packs JSON configurables.
- No usar `eval`, importar el bundle ni ejecutar código del proveedor.
- Añadir deduplicación, puntuación explicable y salida que distinga candidato de
  afirmación confirmada.
- Medir tiempo y memoria con bundles sintéticos de 1 MiB y 8 MiB; el resultado es
  evidencia operativa, no una promesa de throughput.
- Separar `bundle fetch` como operación posterior y live; no incluir descargas
  remotas en el gate.

**DoD F6:** un bundle sintético contiene los candidatos esperados, los offsets son
reproducibles y el informe no presenta un regex match como contrato confirmado.

**Evidencia:** bundle sintético hashado, golden de candidatos y tests de strings
minificadas/escapadas.

### F7 — Probe y perfiles operativos

**Dependencias:** F3–F4; F5-MVP no es suficiente para live.  
**Objetivo:** clasificar salud sin convertir la herramienta en un generador de
tráfico agresivo.

Trabajo:

- Implementar primero todos los estados contra mock:
  `ok`, `banned`, `rate_limited`, `token_invalid`, `country_blocked`,
  `model_locked`, `ip_capped`, `timeout`, `unknown`.
- Definir contrato de probe de costo cero: endpoint, método, body vacío o
  explícitamente permitido, máximo de una llamada por target y cooldown local.
- Implementar cache bounded con TTL declarado en el resultado, nunca cachear
  secretos ni respuestas completas sensibles.
- Soportar referencias de múltiples cuentas sin mostrar valores; cada cuenta se
  identifica por alias/fingerprint.
- Habilitar live solo con `--live --confirm-live`, host allowlist, timeout,
  `--no-retry` y presupuesto máximo. Registrar la autorización en el manifest sin
  identificar a la persona.

**DoD F7:** la matriz mock de estados produce clasificación y exit codes estables;
el probe rechaza un target sin contrato de costo cero; el modo live no puede
activarse por configuración persistida ni por una plantilla sin flag.

**Evidencia:** matriz de 9 estados, tests de cooldown/cache, prueba de límites y
runbook para una ejecución live autorizada si existe un entorno disponible.

### F8 — Rastreador de deriva

**Dependencias:** F3–F5-MVP. F5-CDP y F5-MITM son tracks opcionales y no bloquean
esta fase ni el MVP.  
**Objetivo:** comparar un contrato esperado con una ejecución nueva y explicar la
deriva.

Trabajo:

- Definir manifest de golden: perfil, versión de schema, fixture base, reglas de
  comparación, tolerancias y severidad.
- Implementar `track` como ejecución única; el scheduler queda fuera del alcance.
- Comparar schema, status, clasificación, modelo efectivo, tools, terminación de
  stream, latencia por bucket y límites observados.
- Producir `PASS`, `WARN`, `FAIL`, `TOOL_ERROR` y `NOT_RUN` sin mezclar
  cobertura no ejecutada con éxito.
- Añadir un mock que cambie una regla y genere un diff mínimo, accionable y
  reproducible.

**DoD F8:** el cambio simulado se detecta con el campo afectado, severidad,
fixture/trace de origen y siguiente acción; una ejecución sin red se distingue de
un PASS live.

**Evidencia:** reporte de deriva JSON/MD, golden baseline y test de cada estado de
resultado.

### F9 — Exportación y adopción controlada

**Dependencias:** F3, F4, F5-MVP y F8. F5-CDP y F5-MITM siguen siendo opcionales.
  
**Objetivo:** hacer consumible la evidencia por otro repositorio sin acoplar los
ciclos de desarrollo.

Trabajo:

- Definir `docs/export-contract.md`: envelope, schema, clasificación, aserciones,
  hashes y compatibilidad.
- Implementar exportación de fixture sanitizado y trace bounded; excluir prompt,
  response sensible, URL upstream, credential refs y paths privados.
- Crear un fixture de exportación del caso `foreign_toolset`/`model_downgrade`
  basado en mock o evidencia autorizada, con versión y provenance.
- Documentar cómo GloryAPI puede consumir el envelope en su
  `CompatibilityAdapter` sin importar módulos de `gloryInspector`.
- Si se requiere código en GloryAPI, abrir una tarea separada en ese repositorio;
  no mezclar commits ni afirmar que la integración está hecha por publicar el
  exportador.

**DoD F9:** un consumidor puede validar el export con el schema, reconstruir la
clasificación y rechazar un fixture que contenga secretos o una versión no
soportada.

**Evidencia:** export fixture, schema, validador externo mínimo y documentación de
handoff.

## 8. Pruebas, gate y evidencia

### 8.1 Gate mínimo del proyecto

Hasta que el proyecto declare otro gate, el comando canónico será:

```text
python -m unittest discover -s tests -v
python -m compileall -q inspector scripts
python -m inspector --help
python scripts/check_no_secrets.py
python scripts/check_core_provider_neutral.py
```

El gate debe ejecutarse sin red, sin credenciales y sin depender de un proveedor.
Un error de herramienta se reporta como tal; no se convierte en `FAIL` de
protocolo ni se oculta como warning.

### 8.2 Matriz de pruebas

| Área | Casos mínimos |
| --- | --- |
| Records | schema válido/inválido, orden, correlación, truncado, hash y round-trip |
| Redacción | headers, query, JSON anidado, texto, alta entropía, desconocido, límites |
| Profiles | campos obligatorios, host allowlist, target inválido, credencial inline rechazada |
| Transport | timeout, cancelación, max bytes, no retry, error parcial |
| Replay | 200, 429, 401, downgrade, tool call, stream completo/truncado |
| Classify | precedencia de reglas, `foreign_toolset`, `model_downgrade`, unknown |
| Diff | una mutación, orden, presupuesto, aserción, dos mutaciones rechazadas |
| Bundle | match con contexto, deduplicación, offsets, no ejecución de JS |
| Probe | nueve estados mock, cooldown, cache, live sin flags bloqueado |
| Track | PASS/WARN/FAIL/TOOL_ERROR/NOT_RUN y diff mínimo |
| Seguridad | secreto sintético, path traversal, overwrite, URL fuera de allowlist |

### 8.3 Criterio de evidencia

Cada fase cerrada debe dejar:

- commit local trazable;
- tests reproducibles y comando exacto;
- fixture o schema que pruebe el contrato;
- reporte JSON con tool version, profile, hashes y cobertura;
- actualización de `roadmap.md` y de este plan solo en lo que tenga evidencia;
- un pendiente separado si el bloqueo pertenece a live, legal, UI o integración.

No se considera evidencia válida una captura manual sin fixture sanitizado, un
200 sin modelo efectivo, un log que contenga secretos o una suite que no indique
que omitió red/live.

## 9. Seguridad, operación y modelo de fallo

### 9.1 Amenazas y controles

| Amenaza | Control preventivo | Respuesta |
| --- | --- | --- |
| Secreto en fixture | redacción antes de persistir, scanner y hook | bloquear el artefacto, rotar solo si hubo exposición real y registrar incidencia sin valor |
| Host externo no previsto | allowlist del perfil y loopback por defecto | abortar con exit 3/5, sin retry |
| Probing agresivo | concurrency 1, presupuesto, cooldown y no-retry | detener la corrida y conservar trace bounded |
| Downgrade silencioso | comparar modelo pedido/efectivo en cada response/chunk | `FAIL` tipado, nunca éxito silencioso |
| Bundle malicioso | análisis textual offline, sin `eval` ni importación | tratarlo como bytes no confiables y limitar tamaño |
| Path traversal | resolver y comprobar rutas bajo workspace de artefactos | rechazar antes de abrir/escribir |
| Fixture alterado | hashes y manifest versionado | marcar deriva o corrupción; no regenerar automáticamente |
| Falla parcial | estados explícitos y cleanup de temporales | conservar `NOT_RUN`/`TOOL_ERROR` con siguiente acción |
| MITM inseguro | CA local, instrucciones de instalación/limpieza y scope por host | abortar, retirar CA temporal y no guardar tráfico sin redacción |

### 9.2 Recursos acotados

Valores iniciales del MVP, configurables solo dentro de máximos:

- timeout por request: 10 s; máximo 60 s;
- body por record: 1 MiB inline; máximo 8 MiB leído;
- sesión: 10 MiB de JSONL antes de rotar o bloquear;
- profundidad JSON: 32;
- strings: 64 KiB;
- diff: 1 request por variante en mock; live requiere presupuesto declarado;
- concurrencia: 1;
- retries: 0 por defecto; solo idempotencia declarada y fuera del MVP.

Estos números son límites iniciales, no una afirmación de rendimiento. Cualquier
subida requiere medición y actualización del plan. F1 debe registrar una línea
base de tiempo/memoria para redacción de 1 MiB y 8 MiB con el pack vigente; F6
debe hacer lo mismo para bundles de 1 MiB y 8 MiB. Los umbrales iniciales son
informativos, pero la tendencia y cualquier regresión de 2x deben quedar en el
reporte antes de elevar cotas.

### 9.3 SOLID y límite de abstracción

- **SRP:** clasificación, transporte, redacción, replay y routing de casos viven
  en módulos distintos; `classify` no hace HTTP.
- **OCP:** nuevos perfiles y adaptadores se agregan por schema/adapter; el núcleo
  no añade `if provider == ...`.
- **LSP:** todos los adaptadores declaran capacidades y producen el mismo record;
  uno que no soporta streaming debe devolver `NOT_SUPPORTED`, no fingir eventos.
- **ISP:** interfaces pequeñas (`RecordSource`, `Target`, `Redactor`,
  `Reporter`) evitan que un mock implemente CDP o MITM.
- **DIP:** casos de uso dependen de interfaces locales y reciben el transporte;
  no importan sockets, CDP o subprocess directamente.
- **Núcleo compartido:** no abstraer a GloryAPI ni a un paquete externo todavía.
  La lógica es genérica, pero solo existe un consumidor real; primero se valida el
  contrato con dos adaptadores locales. La exportación es la frontera estable.

### 9.4 Eficiencia y escala

El objetivo es una herramienta single-user para sesiones pequeñas/medianas:

- parseo JSONL: O(n) en registros;
- redacción: O(bytes + matches), con límites de entrada;
- diff: O(variantes × coste de target), serial por defecto;
- track: O(registros + reglas), sin almacenar todas las respuestas en memoria;
- bundle: O(bytes del bundle × número de packs), con contexto acotado.

No se diseña para múltiples usuarios, alta concurrencia, almacenamiento remoto ni
sesiones ilimitadas. Si aparece esa necesidad, primero se medirán volumen,
concurrencia, latencia P95, memoria y tasa de fixtures; después se abrirá un plan
de servicio separado.

## 10. Documentación y ciclo de trabajo

Durante la implementación se deben mantener estas fuentes, sin duplicar decisiones:

- `PLAN-GLORYINSPECTOR.md`: dirección, fases, contratos y DoD.
- `roadmap.md`: solo cola abierta, siguiente bloque y bloqueos reales.
- `README.md`: instalación, uso local y ejemplo reproducible.
- `docs/record-schema.md`: schema y compatibilidad (crear en F2, con el contrato
  implementado y fixtures; no como documento de entrada).
- `docs/operating-policy.md`: autorización, redacción, live y datos permitidos
  (crear en F0, porque fija la política antes del código).
- `docs/live-runbook.md`: preflight, ejecución autorizada, cleanup y evidencia
  (crear en F7, con la matriz de probe y el contrato live).
- `docs/export-contract.md`: frontera con consumidores como GloryAPI (crear en
  F9, con el exportador y el validador externo).
- `Agente/completados/` y `Agente/planes/` solo si el proyecto adopta esa
  estructura local durante F0; no crear carpetas históricas vacías por anticipado.

Antes de cerrar cada bloque: revisar diff, separar cambios ajenos, ejecutar el
gate, actualizar documentación con evidencia y commitear explícitamente por
archivos. No añadir remoto ni hacer push.

## 11. Riesgos abiertos y mitigaciones

| Riesgo abierto | Señal de activación | Mitigación / decisión |
| --- | --- | --- |
| No existe aún un entorno autorizado para captura oficial | F5 no puede probar CDP/MITM | cerrar F5-MVP y dejar el adaptador live como pendiente explícito |
| El proveedor cambia el contrato mientras se construye el perfil | fixture live no reproduce | versionar por build, conservar evidencia y no modificar golden sin diff/revisión |
| La redacción tiene falsos negativos | scanner pasa un secreto sintético | ampliar pack, bloquear desconocidos y añadir caso de regresión antes de seguir |
| El formato exportado no cubre GloryAPI | validador consumidor rechaza envelope | revisar contrato en F9; no compartir módulos internos |
| MITM exige dependencias/privilegios no portables | bootstrap falla en un SO | mantener CDP/import como capacidad principal; MITM no bloquea releases |
| El mock oculta un comportamiento real | live contradice el golden | registrar el caso como nueva evidencia; separar cambio de perfil de cambio de core |
| Se intenta convertir el toolkit en servicio | aparecen usuarios, scheduler o API remota | congelar alcance y abrir un plan de producto distinto |

## 12. Criterios de aceptación globales

El proyecto puede declararse **MVP completo** cuando se cumpla todo lo siguiente:

- `redact`, `replay`, `classify`, `diff`, `bundle` offline y `track` funcionan
  sin red ni credenciales contra fixtures/mock;
- el registro, perfil, manifest y export tienen schema versionado y validación
  fail-closed;
- el caso histórico `foreign_toolset`/`model_downgrade` se reproduce en mock y el
  downgrade no pasa como éxito;
- capture import/loopback genera el mismo contrato que el mock;
- la matriz de probe existe completa en mock, con exit codes y estados explícitos;
- el scanner de secretos y el chequeo de neutralidad del núcleo pasan;
- el gate local produce evidencia de cobertura y distingue `NOT_RUN` de `PASS`;
- README y runbooks permiten a otra persona reproducir el circuito sin acceso a
  credenciales;
- no hay remoto, push, deploy, SSH ni escritura externa automática.

La capacidad **live ampliada** solo puede declararse completa si, además, existe
un entorno autorizado, una prueba observada, cleanup documentado, fixture
sanitizado y evidencia de límites. Si no existe, el MVP sigue siendo válido.

## 13. Orden obligatorio y siguiente acción

```text
F0 bootstrap/contratos/política
→ F1 redacción/seguridad
→ F2 records/manifest/mock
→ F3 replay/assertions/classify
→ F4 diff
→ F5 capture import/loopback [→ CDP → MITM opcionales]
→ F6 bundle offline
→ F7 probe mock [→ live autorizado]
→ F8 track
→ F9 exportación/adopción
```

No se puede saltar F1 para capturar tráfico real ni saltar F3 para interpretar
errores live. F6 puede avanzar en paralelo con F3 después de F2, pero su gate no
habilita live.

**CIERRE OFFLINE:** F0–F9 están implementadas y verificadas contra mock, importación y loopback local. Los únicos pendientes reales son CDP, MITM y live ampliado, que requieren un entorno autorizado y pruebas manuales; no se simulan en el gate local.
