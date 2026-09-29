# Experimento de evidencia — Fase 5

- **Corrido**: 2026-09-29T12:31:54+00:00
- **Repeticiones por función**: 30
- **Identificador**: `85d7e3ce-15f9-494a-afe1-ee059ae28e84`

Cada número sale de repetir la misma llamada N veces contra la cámara real (o simulada) y medir. La tasa de éxito y la latencia son la evidencia que le falta a una demo para ser un resultado.

## PTZ Oficina (Speed Dome 8MP)

- ISAPI: alcanzable
- ONVIF: alcanzable

| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) | media (ms) |
|---|---|---|---|---|---|---|---|
| device.info | isapi | 30 | 30 | 100% | 28.6 | 38.0 | 31.4 |
| device.info | onvif | 30 | 30 | 100% | 22.1 | 30.5 | 23.2 |
| events.motion | isapi | 30 | 30 | 100% | 29.3 | 35.5 | 29.8 |
| events.motion | onvif | 30 | 0 | 0% | 29.9 | 38.4 | 39.9 |
| media.profiles | isapi | 30 | 30 | 100% | 41.6 | 55.6 | 42.9 |
| media.profiles | onvif | 30 | 30 | 100% | 171.0 | 191.7 | 184.6 |
| media.snapshot | isapi | 30 | 30 | 100% | 227.0 | 243.8 | 227.7 |
| system.status | isapi | 30 | 30 | 100% | 148.4 | 170.1 | 151.7 |
| system.time | isapi | 30 | 30 | 100% | 50.3 | 61.9 | 48.1 |
| system.time | onvif | 30 | 30 | 100% | 23.6 | 28.5 | 24.3 |
| video.image | isapi | 30 | 30 | 100% | 31.5 | 38.0 | 31.5 |
| video.image | onvif | 30 | 30 | 100% | 149.8 | 227.5 | 163.0 |
| video.osd | isapi | 30 | 30 | 100% | 34.1 | 46.4 | 33.7 |
| video.osd | onvif | 30 | 30 | 100% | 117.0 | 135.3 | 120.0 |
