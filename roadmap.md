# Roadmap — gloryInspector

## Contexto

- Fuente canónica: [`PLAN-GLORYINSPECTOR.md`](PLAN-GLORYINSPECTOR.md).
- Gate local: unittest, compileall, ayuda CLI y checks de seguridad/neutralidad.
- Git local inicializado, sin remoto y sin commit creado por el agente.

## Estado

**MVP offline F0–F9 completado localmente.** El circuito determinista funciona sin credenciales ni red externa: redacción fail-closed, records/manifests/blobs, mock, replay, clasificación, diff, importación/loopback, bundle offline, probe mock, track y exportación.

## Evidencia de cierre

- Python 3.12.10; `pyproject.toml` válido para Python `>=3.11`.
- 52 tests unitarios: OK.
- `python -m compileall -q inspector scripts`: OK.
- `python scripts/check_no_secrets.py`: `NO_SECRET_SHAPED_VALUES`.
- `python scripts/check_core_provider_neutral.py`: `CORE_PROVIDER_NEUTRAL`.
- Schemas y fixtures request/response/event/profile/result/export: válidos.
- Baseline offline 1 MiB/8 MiB ejecutado para redacción y bundle; ambos estados `clean`/sin candidatos inseguros.
- CLI smoke de validate, replay, diff, bundle, probe, track, export y capture loopback: OK.

## Pendientes reales

- CDP, MITM y live ampliado: tracks opcionales que requieren un entorno autorizado, prueba manual, cleanup y evidencia de cero secretos. No se simulan ni bloquean el MVP offline.
- GloryAPI consume el envelope por contrato; cualquier código consumidor requiere una tarea separada en ese repositorio.

## Decisiones y límites

- No se instala Sentinel/VarSense porque el plan declara que este proyecto no tiene gate coordinado.
- No hay deploy, push, SSH, credenciales ni escrituras externas.
- No se creó commit porque el usuario no solicitó una operación Git de commit.
