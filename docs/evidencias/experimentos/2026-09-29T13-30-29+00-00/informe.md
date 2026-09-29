# Experimento de evidencia — Fase 5

- **Corrido**: 2026-09-29T13:30:29+00:00
- **Repeticiones por función**: 30
- **Identificador**: `6b085204-d1ef-4002-b21e-83759bb26d11`

Cada número sale de repetir la misma llamada N veces contra la cámara real (o simulada) y medir. La tasa de éxito y la latencia son la evidencia que le falta a una demo para ser un resultado.

## DeepinView RLINK

- ISAPI: alcanzable
- ONVIF: alcanzable

| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) | media (ms) |
|---|---|---|---|---|---|---|---|
| device.info | isapi | 30 | 30 | 100% | 26.5 | 33.9 | 27.9 |
| device.info | onvif | 30 | 30 | 100% | 18.8 | 31.4 | 20.6 |
| events.motion | isapi | 30 | 30 | 100% | 25.9 | 30.6 | 25.3 |
| events.motion | onvif | 30 | 0 | 0% | 47.7 | 56.4 | 61.0 |
| media.profiles | isapi | 30 | 30 | 100% | 44.9 | 58.3 | 47.3 |
| media.profiles | onvif | 30 | 30 | 100% | 120.9 | 365.8 | 379.2 |
| media.snapshot | isapi | 30 | 30 | 100% | 107.7 | 121.3 | 106.8 |
| system.status | isapi | 30 | 30 | 100% | 131.1 | 157.4 | 136.0 |
| system.time | isapi | 30 | 30 | 100% | 56.4 | 60.0 | 56.1 |
| system.time | onvif | 30 | 30 | 100% | 21.1 | 30.9 | 21.8 |
| video.image | isapi | 30 | 30 | 100% | 27.3 | 33.9 | 27.8 |
| video.image | onvif | 30 | 30 | 100% | 109.1 | 140.1 | 123.3 |
| video.osd | isapi | 30 | 30 | 100% | 29.9 | 36.3 | 30.5 |
| video.osd | onvif | 30 | 30 | 100% | 87.6 | 106.2 | 93.3 |
