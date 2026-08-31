# gloryInspector

Toolkit local, portable y agnóstico de proveedor para capturar evidencia autorizada, reproducir regresiones y detectar deriva.

## Estado

El MVP offline de F0–F9 está implementado. Funciona sin red ni credenciales mediante fixtures sintéticos, mock determinista, importación local y loopback `127.0.0.1`. Los tracks CDP, MITM y live ampliado permanecen pendientes explícitos porque requieren un entorno autorizado y evidencia manual que no forma parte del gate determinista.

## Requisitos

- Python 3.11 o posterior.
- Sin dependencias externas obligatorias.
- El gate no abre red externa ni resuelve credenciales.

## Gate reproducible

Desde esta carpeta, en un Python normal:

```text
python -m unittest discover -s tests -v
python -m compileall -q inspector scripts
python -m inspector --help
python scripts/check_no_secrets.py
python scripts/check_core_provider_neutral.py
```

El entorno de desarrollo aislado puede quitar el directorio actual de `sys.path`; la evidencia local equivalente usa:

```text
python -I -c "import sys; sys.path.insert(0, '.'); from inspector.cli import main; raise SystemExit(main(['--help']))"
```

## Circuito offline

```text
redact → replay mock → classify/assert → diff → capture import/loopback
       → bundle offline → probe mock → track → export
```

Ejemplos:

```text
python -m inspector redact --input fixtures/valid-request.json --check
python -m inspector replay --input fixtures/valid-request.json --target mock://historical-auto
python -m inspector diff --input fixtures/historical-case.json
python -m inspector bundle --input path/to/local-bundle.js --pack packs/bundle.json
python -m inspector probe --state rate_limited
python -m inspector track --input fixtures/valid-request.json --golden fixtures/golden/protocol-regression-v1.json
python -m inspector export --result fixtures/export/foreign-toolset-v1.json --output artifacts/export.json --fixture-id foreign-toolset-v1 --profile-id historical-case
```

Todas las entradas y salidas son explícitas. No se sobrescribe una salida sin `--force`. `replay` acepta `mock://...` o `http://127.0.0.1/...`; cualquier otro host queda bloqueado.

## Contratos

- Registro y sesión: [`docs/record-schema.md`](docs/record-schema.md).
- Política de autorización y datos: [`docs/operating-policy.md`](docs/operating-policy.md).
- Probe y límites live: [`docs/live-runbook.md`](docs/live-runbook.md).
- Exportación a consumidores: [`docs/export-contract.md`](docs/export-contract.md).
- Dirección y Definition of Done: [`PLAN-GLORYINSPECTOR.md`](PLAN-GLORYINSPECTOR.md).

## Seguridad

La redacción ocurre antes de persistir evidencia; desconocidos, blobs crudos, tamaños fuera de límite y rutas inseguras bloquean la operación. El scanner busca secretos sintéticos y el core no contiene nombres de proveedores. Los bundles se tratan como bytes no confiables: nunca se importan, evalúan ni ejecutan.

No se intercepta tráfico de terceros, no se evaden controles, no se crean cuentas, no se rotan credenciales y no se escriben APIs o bases de datos externas. La integración física con GloryAPI requiere una tarea separada en ese repositorio.
