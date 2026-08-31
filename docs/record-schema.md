# Registro canónico

`schemas/record-v1.json` usa el vocabulario `inspector.schema/v1` y distingue `request`, `response` y `event` mediante `oneOf`.

## Cuerpo

Un cuerpo es exactamente uno de:

- `inline`: JSON/texto/base64 bajo 1 MiB.
- `blob`: path relativo bajo `blobs/` y hash SHA-256 del contenido sanitizado cuando supera el límite inline y no supera 8 MiB.
- `absent`: razón bounded cuando no fue observado.

La canonicalización JSON usa UTF-8, claves ordenadas, separadores compactos y `ensure_ascii=false`. El hash se calcula después de redacción.

## Sesión

`SessionWriter` escribe JSONL append-only y un manifest separado. `record_id` es único, `sequence` crece estrictamente, y una respuesta debe referenciar un `correlation_id` observado en una request salvo `orphaned=true`. Las sesiones incompletas se cierran con `complete=false`; nunca se reparan silenciosamente.

Los blobs se resuelven bajo el directorio de artefactos y se comprueba el contenido de un blob existente antes de reutilizarlo.
