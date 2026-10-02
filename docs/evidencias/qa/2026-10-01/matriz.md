# Matriz de compatibilidad

Generada el 2026-10-01. Cada celda muestra el nivel de soporte (`✓` soportado, `~` parcial, `✕` no soportado, `·` no verificado, `!` error) y, entre backticks, si se verificó llamando a la función (`v`) o solo se tomó de lo que la cámara declara (`d`). `—` significa que ese protocolo no aplica a esa función.

| Función | Bullet Parking (DeepinView) (isapi) | Bullet Parking (DeepinView) (onvif) | Bullet Parking (DeepinView) (rtsp) | DeepinView RLINK (isapi) | DeepinView RLINK (onvif) | DeepinView RLINK (rtsp) | PTZ Oficina (Speed Dome 8MP) (isapi) | PTZ Oficina (Speed Dome 8MP) (onvif) | PTZ Oficina (Speed Dome 8MP) (rtsp) | QA Sarmiento 18080 (isapi) | QA Sarmiento 18080 (onvif) | QA Sarmiento 18080 (rtsp) | QA basica (isapi) | QA basica (onvif) | QA basica (rtsp) | QA domo (isapi) | QA domo (onvif) | QA domo (rtsp) | QA ptz (isapi) | QA ptz (onvif) | QA ptz (rtsp) | Sarmiento (isapi) | Sarmiento (onvif) | Sarmiento (rtsp) | Simulada PTZ (sin hardware) (isapi) | Simulada PTZ (sin hardware) (onvif) | Simulada PTZ (sin hardware) (rtsp) | Simulada Value (sin analitica) (isapi) | Simulada Value (sin analitica) (onvif) | Simulada Value (sin analitica) (rtsp) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Dispositivo** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Información del dispositivo | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| **Video** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Perfiles de video | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| Video en vivo | — | — | ✓`v` | — | — | ✓`v` | — | — | ✓`v` | — | — | !`v` | — | — | !`v` | — | — | !`v` | — | — | !`v` | — | — | !`v` | — | — | !`v` | — | — | · |
| Snapshot | ✓`v` | ✓`d` | — | !`v` | ✓`d` | — | !`v` | ✓`d` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | !`v` | ·`v` | — | !`v` | ·`v` | — |
| **Analítica** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Reglas de analítica | ✓`d` | ✓`d` | — | ✓`d` | ✓`d` | — | ✓`d` | ✓`d` | — | ·`d` | ·`v` | — | · | ·`v` | — | ✓`d` | ·`v` | — | ✓`d` | ·`v` | — | · | ·`v` | — | ✓`d` | ·`v` | — | · | ·`v` | — |
| **Sistema** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Estado y salud | ✓`v` | ✓`d` | — | ✓`v` | ✓`d` | — | ✓`v` | ✓`d` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| Hora del dispositivo | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |
| Reinicio | ·`d` | ✓`d` | — | ·`d` | ✓`d` | — | ·`d` | ✓`d` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — | ·`d` | ·`v` | — |
| **Imagen** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Texto sobre la imagen (OSD) | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✕`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✕`v` | ·`v` | — |
| Ajustes de imagen | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | ✓`v` | ✓`v` | — | !`v` | ·`v` | — | ✕`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✕`v` | ·`v` | — |
| **Eventos** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Detección de movimiento | ✕`v` | ✕`v` | — | ✓`v` | ✕`v` | — | ✓`v` | ✕`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — | !`v` | ·`v` | — | ✓`v` | ·`v` | — | ✓`v` | ·`v` | — |