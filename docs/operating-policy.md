# Política operativa

## Datos permitidos

Solo se aceptan datos sintéticos, propios o capturados con autorización verificable del propietario. Los fixtures versionados deben estar sanitizados y no pueden contener prompts, respuestas, sesiones, rutas privadas, cookies, tokens, claves, identificadores personales ni referencias de credenciales reales.

## Redacción y persistencia

La redacción debe ocurrir antes de persistir JSONL, blobs o informes. Si el sistema no puede clasificar un valor o no puede demostrar que un artefacto es seguro, la operación se bloquea; no se sustituye el dato por una suposición silenciosa. Los hashes se calculan sobre el contenido ya sanitizado.

## Red y operaciones live

F0 no abre sockets ni hace llamadas externas. Las fases posteriores deberán mantener el modo offline como predeterminado. Una operación live necesitará `--live --confirm-live`, allowlist de host, timeout acotado, presupuesto explícito y cero reintentos por defecto. No se crearán cuentas, no se rotarán credenciales y no se modificarán APIs o bases de datos externas automáticamente.

## Errores y evidencia

`NOT_RUN` y `TOOL_ERROR` no son éxito. Los informes deben distinguir fallo de protocolo, error de herramienta, warning y cobertura no ejecutada. Las salidas no deben incluir secretos ni valores originales usados por las pruebas.

## Limpieza y límites

Los procesos y archivos temporales deben tener límites de tiempo, tamaño y ruta. Las rutas de artefactos deben quedar bajo el workspace designado. No se ejecuta JavaScript de bundles, no se usa `eval` y no se intercepta tráfico de terceros.

## Responsabilidad

La herramienta caracteriza evidencia; no prueba por sí sola que un proveedor haya usado el modelo solicitado. Cualquier evidencia real debe conservar provenance sanitizada y una autorización separada del gate local.
