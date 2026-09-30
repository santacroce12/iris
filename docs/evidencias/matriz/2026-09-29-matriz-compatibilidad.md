# Matriz de compatibilidad

Generada el 2026-09-29 desde `GET /api/matrix` (exportación "Exportar Markdown" de la pantalla
Matriz). Incluye las dos cámaras Hikvision reales, la cámara VPN "Sarmiento" (offline al momento
de generar esto) y las dos cámaras simuladas, tal como las devuelve la plataforma sin filtrar —
la versión filtrada a solo las cámaras reales está en `docs/tesis/07-resultados.md` §7.9.

| Función | DeepinView RLINK (isapi) | DeepinView RLINK (onvif) | DeepinView RLINK (rtsp) | PTZ Oficina (Speed Dome 8MP) (isapi) | PTZ Oficina (Speed Dome 8MP) (onvif) | PTZ Oficina (Speed Dome 8MP) (rtsp) | Sarmiento (isapi) | Sarmiento (onvif) | Sarmiento (rtsp) | Simulada PTZ (sin hardware) (isapi) | Simulada PTZ (sin hardware) (onvif) | Simulada PTZ (sin hardware) (rtsp) | Simulada Value (sin analitica) (isapi) | Simulada Value (sin analitica) (onvif) | Simulada Value (sin analitica) (rtsp) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Dispositivo** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Información del dispositivo | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| **Video** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Perfiles de video | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| Video en vivo | — | — | ✓`v` | — | — | ✓`v` | — | — | !`v` | — | — | !`v` | — | — | · |
| Snapshot | ✓`v` | ✓`d` | — | ✓`v` | ✓`d` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| **Analítica** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Reglas de analítica | ✓`d` | ✓`d` | — | ✓`d` | ✓`d` | — | · | ·`v` | — | ✓`d` | ·`v` | — | · | ·`v` | — |
| **Sistema** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Estado y salud | ✓`v` | ✓`d` | — | ✓`v` | ✓`d` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| Hora del dispositivo | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| Reinicio | ·`d` | ✓`d` | — | ·`d` | ✓`d` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — |
| **Imagen** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Texto sobre la imagen (OSD) | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✕`v` | ·`v` | — |
| Ajustes de imagen | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✕`v` | ·`v` | — |
| **Eventos** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Detección de movimiento | ✓`v` | ✕`v` | — | ✓`v` | ✕`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
