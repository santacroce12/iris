# Experimento de evidencia — Fase 5

- **Corrido**: 2026-09-27T13:47:11+00:00
- **Repeticiones por función**: 30
- **Identificador**: `14c66e77-ca7e-4cef-810a-725af87f390d`

Cada número sale de repetir la misma llamada N veces contra la cámara real (o simulada) y medir. La tasa de éxito y la latencia son la evidencia que le falta a una demo para ser un resultado.

## DeepinView RLINK

- ISAPI: no alcanzable (unreachable: Timeout en GET /ISAPI/System/deviceInfo)
- ONVIF: no alcanzable (unreachable: ONVIF timeout: sin respuesta en 8s)

_Sin mediciones: ningún protocolo respondió._

## PTZ Oficina (Speed Dome 8MP)

- ISAPI: no alcanzable (unreachable: Timeout en GET /ISAPI/System/deviceInfo)
- ONVIF: no alcanzable (unreachable: ONVIF timeout: sin respuesta en 8s)

_Sin mediciones: ningún protocolo respondió._

## Sarmiento

- ISAPI: no alcanzable (unreachable: Timeout en GET /ISAPI/System/deviceInfo)
- ONVIF: no alcanzable (unreachable: ONVIF timeout: sin respuesta en 16s)

_Sin mediciones: ningún protocolo respondió._

## Simulada PTZ (sin hardware)

- ISAPI: alcanzable
- ONVIF: no alcanzable (unreachable: ONVIF sin conexión: Cannot connect to host 127.0.0.1:80 ssl:default [El equipo remoto rechazó la conexión de red])

| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) | media (ms) |
|---|---|---|---|---|---|---|---|
| device.info | isapi | 30 | 30 | 100% | 17.0 | 26.9 | 18.8 |
| events.motion | isapi | 30 | 30 | 100% | 16.1 | 34.3 | 18.2 |
| media.profiles | isapi | 30 | 30 | 100% | 14.3 | 24.4 | 15.9 |
| media.snapshot | isapi | 30 | 30 | 100% | 15.8 | 37.6 | 18.4 |
| system.status | isapi | 30 | 30 | 100% | 15.9 | 26.6 | 17.4 |
| system.time | isapi | 30 | 30 | 100% | 28.5 | 65.0 | 34.3 |
| video.image | isapi | 30 | 30 | 100% | 12.3 | 25.5 | 14.6 |
| video.osd | isapi | 30 | 30 | 100% | 14.6 | 35.6 | 17.7 |

## Simulada Value (sin analitica)

- ISAPI: alcanzable
- ONVIF: no alcanzable (unreachable: ONVIF sin conexión: Cannot connect to host 127.0.0.1:9 ssl:default [El equipo remoto rechazó la conexión de red])

| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) | media (ms) |
|---|---|---|---|---|---|---|---|
| device.info | isapi | 30 | 30 | 100% | 15.1 | 38.6 | 18.8 |
| events.motion | isapi | 30 | 30 | 100% | 15.4 | 23.6 | 16.7 |
| media.profiles | isapi | 30 | 30 | 100% | 17.8 | 33.6 | 20.6 |
| media.snapshot | isapi | 30 | 30 | 100% | 16.4 | 38.0 | 22.1 |
| system.status | isapi | 30 | 30 | 100% | 15.3 | 26.9 | 17.0 |
| system.time | isapi | 30 | 30 | 100% | 27.8 | 45.0 | 30.2 |
| video.image | isapi | 30 | 0 | 0% | 13.6 | 21.8 | 14.7 |
| video.osd | isapi | 30 | 0 | 0% | 14.3 | 35.6 | 17.3 |
