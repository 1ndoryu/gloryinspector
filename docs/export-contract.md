# Contrato de exportación

## Envelope

`schemas/export-v1.json` define `inspector.export/v1`. El envelope contiene únicamente estado, clasificación, findings, aserciones, hashes y provenance bounded. No contiene cuerpos, prompts, respuestas, URLs upstream, referencias de credenciales ni rutas privadas.

Campos de provenance:

- `fixture_id`: identificador estable del fixture sanitizado.
- `profile_id`: identificador del perfil, nunca el valor de una credencial.
- `source`: `mock`, `import`, `loopback` o `authorized`.
- `tool_version`: versión del inspector.

La compatibilidad se negocia por `export_version` y `supported_versions`; un consumidor debe rechazar versiones no soportadas y validar el schema antes de leer findings.

## Consumo en GloryAPI

GloryAPI puede convertir el envelope en un evento de su `CompatibilityAdapter` mediante un adaptador propio que consuma JSON validado. No debe importar módulos de `gloryInspector`, leer archivos internos, resolver credenciales ni asumir que un `PASS` mock prueba comportamiento live.

La integración física en GloryAPI queda fuera de este repositorio y requiere una tarea separada en ese proyecto.

## Validación

```text
python -m inspector export --result fixtures/... --output artifacts/export.json --fixture-id foreign-toolset-v1 --profile-id historical-case
```

El exportador no sobrescribe salidas existentes sin `--force`.
