# Runbook de probe

## Gate offline

La matriz de estados se ejecuta sin red:

```text
ok, banned, rate_limited, token_invalid, country_blocked,
model_locked, ip_capped, timeout, unknown
```

Cada estado devuelve clasificación, estado (`PASS`, `FAIL` o `TOOL_ERROR`), exit code y un TTL de cache. La cache solo guarda estado y fingerprint de cuenta; nunca guarda bodies, headers o credenciales.

## Live

El transporte live permanece deliberadamente bloqueado en el MVP offline. Una futura implementación solo podrá continuar después de:

1. perfil cargado y validado con host allowlist explícita;
2. `--live --confirm-live --no-retry` presentes en la misma invocación;
3. timeout y presupuesto declarados;
4. endpoint de costo cero confirmado y autorización del propietario;
5. manifest sin valores de credenciales y cleanup documentado.

No se ejecutan llamadas live desde el gate local. Un intento sin confirmación produce un error de política, no un `PASS` ni un retry silencioso.
