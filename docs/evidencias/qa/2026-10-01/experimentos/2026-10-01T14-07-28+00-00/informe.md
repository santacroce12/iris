# Experimento de evidencia — Fase 5

- **Corrido**: 2026-10-01T14:07:28+00:00
- **Repeticiones por función**: 30
- **Identificador**: `efece0e2-0a89-4abc-8d7b-50ed49580689`

Cada número sale de repetir la misma llamada N veces contra la cámara real (o simulada) y medir. La tasa de éxito y la latencia son la evidencia que le falta a una demo para ser un resultado.

## QA Sarmiento 18080

- ISAPI: no alcanzable (unreachable: No se pudo conectar: All connection attempts failed)
- ONVIF: no alcanzable (unreachable: ONVIF sin conexión: Cannot connect to host 190.15.193.250:18080 ssl:default [No es posible el acceso a la ubicación de red. Para obtener información para solucionar problemas de red, vea la Ayuda de Windows])

_Sin mediciones: ningún protocolo respondió._

## QA ptz

- ISAPI: alcanzable
- ONVIF: no alcanzable (unreachable: ONVIF sin conexión: Cannot connect to host 127.0.0.1:9 ssl:default [El equipo remoto rechazó la conexión de red])

| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) | media (ms) |
|---|---|---|---|---|---|---|---|
| device.info | isapi | 30 | 30 | 100% | 47.4 | 81.4 | 51.6 |
| events.motion | isapi | 30 | 30 | 100% | 46.4 | 94.0 | 53.2 |
| media.profiles | isapi | 30 | 30 | 100% | 51.7 | 70.2 | 52.3 |
| media.snapshot | isapi | 30 | 30 | 100% | 47.9 | 90.6 | 52.5 |
| system.status | isapi | 30 | 30 | 100% | 37.6 | 68.3 | 40.4 |
| system.time | isapi | 30 | 30 | 100% | 67.0 | 106.5 | 72.6 |
| video.image | isapi | 30 | 30 | 100% | 34.2 | 45.8 | 35.5 |
| video.osd | isapi | 30 | 30 | 100% | 35.1 | 44.0 | 35.9 |
