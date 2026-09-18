# Relevamiento de cámaras y APIs (2026-09-18)

Sondeo real sobre el hardware disponible, contrastado con la documentación ISAPI oficial
(DeepinView Series, 974 págs., y PTZ Ultra Series, 896 págs.).
Las respuestas crudas quedaron como fixtures en `backend/tests/fixtures/hikvision/<modelo>/<firmware>/`.

## Cámaras encontradas en la red

| Modelo | IP | Firmware | Rol para la tesis |
|---|---|---|---|
| **DS-2DF8A836IX-AEL** (PTZ Speed Dome 8MP, Ultra) | 192.168.239.189 | V5.6.0 | **Caso fuerte de reglas dibujables** |
| **iDS-2CD7146G2-IZS** (DeepinView) | 192.168.239.101 | V5.9.24 | **Caso de plataforma abierta (AIOP)** |
| iDS-2CD7A46G0/P-IZHSY (DeepinView) | — (validada antes por VPN) | V5.8.61 | Parking / ANPR, según manual |
| DS-2CD1023G2-I (Value) | — | V5.8.4 | Caso "sin analítica" para contraste |

En la LAN hay ~30 equipos más con puerto 80 o 554 abiertos que no son ISAPI, y uno en
192.168.239.151 que responde ISAPI pero con otras credenciales.

## Qué encontró el sondeo

### DS-2DF8A836IX-AEL — analítica clásica, y responde
Es la mejor candidata para la demo de **dibujar reglas sobre la imagen**:

| Función | Endpoint | Estado |
|---|---|---|
| Cruce de línea | `/ISAPI/Smart/LineDetection/1` | **OK** |
| Intrusión | `/ISAPI/Smart/FieldDetection/1` | **OK** |
| Entrada / salida de región | `/ISAPI/Smart/regionEntrance|regionExiting/1` | **OK** |
| Objeto abandonado / retirado | `/ISAPI/Smart/unattendedBaggage|attendedBaggage/1` | **OK** |
| Metadata (recuadros sobre el video) | `/ISAPI/Streaming/channels/101/metadata` | **OK** |
| Eventos en vivo | `/ISAPI/Event/notification/alertStream` | **OK** (latido cada ~10 s) |
| Conteo de personas, mapa de calor, colas, ANPR, rostros | — | No soportado |

Forma real de la regla de línea (confirmada contra la cámara):
coordenadas normalizadas **1000×1000**, hasta **4 líneas**, `sensitivityLevel` 1–100,
`directionSensitivity` = `any | left-right | right-left`, `detectionTarget` = `human | vehicle | others`.

**Modo de analítica activo:** `GET /ISAPI/System/Video/inputs/channels/1/VCAResource` → `smart`,
y solo admite `smart` o `facesnap`. Es decir: **o perímetro, o captura facial; nunca las dos**.

### iDS-2CD7146G2-IZS — la analítica va por AI Open Platform
Todos los flags clásicos vienen en `false` (`/ISAPI/Smart/capabilities`,
`/ISAPI/Intelligent/channels/1/capabilities`) y cada `/ISAPI/Smart/*` responde **403 notSupport**.
`VCAResource` tampoco existe en este modelo. La analítica se entrega por una API distinta:

| Recurso | Endpoint | Formato |
|---|---|---|
| Info de la plataforma | `GET /ISAPI/Intelligent/AIOpenPlatform?format=json` | JSON |
| Capacidades | `GET /ISAPI/Intelligent/AIOpenPlatform/capabilities?format=json` | JSON |
| Tareas de análisis de video | `GET /ISAPI/Intelligent/AIOpenPlatform/videoTask?format=json` | JSON |
| Capacidades de tarea | `GET .../videoTask/capabilities?format=json` | JSON |
| Análisis por muestreo de imágenes | `GET .../picturePollingAnalysisTask?format=json` | JSON |
| Reglas de la tarea | `.../videoTask/<taskID>/AIRule`, `.../AIRuleConfig/<taskID>` | **pendiente** |

La cámara ya tiene **una tarea corriendo** (`taskID 545933c16c6bfe2g`, motor 1001, 24×7,
notificación a "center" y FTP), con `algorithmVersion AI_V4.0.0` y 4 motores disponibles.
Sus capacidades declaran configuración de reglas, conteo por regla con reset manual, OSD,
umbral de confianza y disparo de eventos.

Eventos que puede emitir: `AIOpenPlatform`, `AIOP_Video`, `AIOP_Polling_Snap`, `HEOPCustomEvent`,
además de VMD, sabotaje, desenfoque, audio y cambio de escena.

**Pendiente:** leer las reglas de la tarea. `AIRule` y `AIRuleConfig/<taskID>` existen pero rechazan
GET (`methodNotAllowed` / `badParameters`): faltan los parámetros exactos, que no están en el manual
DeepinView. Se resuelve mirando qué pide la propia interfaz web de la cámara.

## Lo que dicen los manuales (y no está en estas dos cámaras)

- **Conteo de personas**: la serie DeepinView sí tiene API completa —36 endpoints bajo
  `/ISAPI/System/Video/inputs/channels/<ch>/counting*`, con configuración, reset, superposición en
  pantalla y **búsqueda histórica** (`POST .../counting/search`). La serie PTZ **no tiene ninguno**.
- **ANPR**: DeepinView tiene `/ISAPI/Traffic/channels/<ch>/vehicleDetect*` más listas de patentes y
  búsqueda (`searchLPListAudit`). La PTZ solo tiene incidentes de tránsito, sin lectura de patentes.
- **Mapa de calor y gestión de colas**: **no tienen API en ninguno de los dos manuales.** Aparecen
  solo como banderas de capacidad y como modos de `VCAResource`. Es un límite real y documentable.
- **Exclusión mutua**: `VCAResource` define un único modo activo por canal, y `mutexFunction`
  (`/ISAPI/System/mutexFunction`) permite consultar qué funciones chocan entre sí. Ninguna de las dos
  cámaras expone `mutexFunction`, pero la PTZ sí expone `VCAResource`.

## Qué significa para la tesis

1. **La demo de dibujar reglas va sobre la PTZ (192.168.239.189)**, que responde los cuatro tipos de
   regla de perímetro. La iDS-2CD7A46G0 debería sumar parking y ANPR según el manual.
2. **El caso "AIOP" es un hallazgo fuerte**: dos cámaras del mismo fabricante, ambas con ISAPI, exponen
   la analítica por APIs completamente distintas (`/ISAPI/Smart/*` en XML contra
   `/ISAPI/Intelligent/AIOpenPlatform/*` en JSON). Es exactamente la fragmentación que plantea la tesis,
   ahora **dentro de una misma marca**.
3. **La matriz necesita una columna de modo activo.** Una función puede estar soportada por el hardware
   y aun así responder "no soportada" porque el canal está en otro modo de `VCAResource`. Sin eso, la
   matriz miente.
4. **Límites documentados**: mapa de calor y colas no tienen API en ninguna serie; la PTZ no hace
   conteo ni ANPR. Sirve como resultado negativo, con evidencia.

## Próximos pasos

- Descubrir los parámetros de `AIRuleConfig` en la iDS-2CD7146G2 (mirando su interfaz web).
- Agregar al motor de capacidades la lectura del modo `VCAResource` y el driver de AIOP.
- Cargar las dos cámaras en la plataforma y correr la detección para generar la primera matriz real.
