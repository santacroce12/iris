# Evidencia: analítica de parking (iDS-2CD7A46G0/P-IZHSY)

`2026-09-30-parking-14-plazas.json` es la configuración real de plazas leída de la cámara el
30/09/2026 con:

```
GET /ISAPI/Parking/channels/1/packingSpaceRecognition?format=json
```

Son las **14 plazas** configuradas en el equipo (máximo 40 según sus capacidades), cada una como
un polígono de exactamente 4 puntos en coordenadas decimales 0–1. Sirve como respaldo del estado
original —la prueba de escritura de ese día lo restauró exactamente— y como muestra del formato
de la tercera familia de analítica documentada en `bitacora-apis.md` §6.9 y
`tesis/07-resultados.md` §7.2.2.

Dos particularidades del formato que se ven en el archivo y que están explicadas en §7.3.7:

- El identificador de cada plaza es `absoulteParkingNum` — error de tipeo del fabricante, hay que
  reproducirlo tal cual.
- La función se llama "Packing" (embalaje), no "Parking", en toda la superficie de la API.

No contiene credenciales ni datos personales: es geometría de plazas.
