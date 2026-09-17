# Plan — Plataforma unificada de cámaras IP (Tesis Luca Santacroce)

## Contexto
El anteproyecto está aprobado. El objetivo es una plataforma web local que unifica el acceso a cámaras IP combinando **3 APIs: ISAPI (Hikvision, propietaria) + ONVIF (estándar) + RTSP (video)**. El foco es la **analítica rica**, no solo el video, y el resultado académico es una matriz que compara lo que se logra por cada protocolo.

**Punto de partida:** proyecto nuevo en `C:\Users\lucas\OneDrive\Escritorio\TESIS CLAUDE` (decisión del usuario). Hay dos intentos previos que no se continúan, pero se rescatan cosas concretas:
- `Escritorio\Cámaras` (may–jul 2026). **Se validó contra una iDS-2CD7A46G0 real por VPN.**
  - Qué rescatar: la lógica de parking (`backend\app\adapters\hikvision\parking.py`), el editor de plazas (`frontend\src\components\ParkingPanel.tsx`), las respuestas reales de la cámara en `tmp\hikvision-value-*` y el documento `docs\VALIDACION_HIKVISION_VPN_2026-06-28.md`.
  - Qué no repetir: adaptadores de más de 1000 líneas, analíticas por fuera del motor de capacidades, un alertStream que no queda escuchando.
- `Escritorio\Tesis\plataforma-camaras-tesis` (ago 2026). **Nunca se probó con hardware.**
  - Qué rescatar: los patrones de diseño. Adaptador con contrato, XML con defusedxml, contraseñas cifradas con Fernet, guardar un respaldo antes de cada escritura y poder restaurarlo, listener de eventos → SSE, y que el PTZ siempre mande la orden de parada.

**Hardware:**
- iDS-2CD7A46G0-IZHS(Y) (DeepinView)
- iDS-2CD7147G2-IZHSY (DeepinView)
- PTZ Speed Dome 8MP Ultra
- Hikvision Value/ColorVu (sirve como caso "básico" para comparar)

**Acceso a las cámaras:** a veces en LAN y a veces por VPN. Hoy hay una sola cámara accesible por VPN.

**Demo principal:** (1) eventos en vivo con foto, (2) dibujar reglas de analítica sobre la imagen. El resto de las analíticas queda anotado en el backlog.

**Sin login** (herramienta local; el anteproyecto excluye la gestión de usuarios).

---

## Stack (se mantiene el del anteproyecto, con ajustes)
| Capa | Elección | Ajuste respecto del anteproyecto / motivo |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, **uv** | uv para tener dependencias reproducibles en Windows |
| HTTP ISAPI | httpx async + `DigestAuth`, defusedxml | TLS configurable por cámara (con HTTPS de certificado autofirmado) |
| ONVIF | `onvif-zeep-async` | Device, Media, **Events (PullPoint)**, **Analytics (GetRules)** y PTZ: comparación real contra ISAPI |
| DB | **PostgreSQL 16** + SQLAlchemy 2 async (asyncpg) + Alembic | **Solo Postgres, también en los tests** (sin SQLite: evita diferencias de comportamiento). JSONB para payloads heterogéneos. TimescaleDB no hace falta a esta escala |
| Video | MediaMTX: **WebRTC (WHEP)** para vivo con baja latencia, HLS de respaldo | Las rutas se crean por la API de MediaMTX; el navegador nunca ve credenciales |
| Tiempo real | **SSE** backend → frontend | Alcanza porque el flujo es unidireccional; más simple que WebSocket |
| Frontend | React 19 + TS + Vite, **TanStack Query**, React Router, **Tailwind + shadcn/ui** (tema oscuro tipo consola de monitoreo), **SVG** para dibujar reglas | Estética de VMS profesional ("lindo") |
| Infra | Docker Compose (postgres, mediamtx y, para la demo, backend + frontend) | En desarrollo, backend y frontend corren locales con hot reload |
| Calidad | pytest + respx (respuestas grabadas), ruff, Playwright smoke, git desde el día 1 | — |

**Nota OneDrive:** la carpeta está sincronizada. Hay que excluir `node_modules`, `.venv` y `media/` de la sincronización, o moverlas. Se documenta en el README.

---

## Arquitectura
```
TESIS CLAUDE/
  backend/app/
    api/            routers: cameras, capabilities, live, events (SSE), rules, reports
    core/           config, db, seguridad (Fernet), logging
    domain/         enums + modelos normalizados (Capability, NormalizedEvent, RuleGeometry)
    drivers/        un paquete por API, archivos chicos por función
      isapi/        client, xml, capabilities, media, events (parser multipart alertStream), rules/{line,field,region}
      onvif/        device, media, events (PullPoint), analytics (rules), ptz
      rtsp/         mediamtx, probe (RTSP DESCRIBE real, no solo puerto abierto)
    engine/         capability_engine (detectar → resolver proveedor → ejecutar + log)
                    event_hub (una tarea asyncio por cámara, reconexión con backoff, persistencia + fan-out SSE)
    services/       orquestación de casos de uso
  backend/migrations/
  backend/tests/    unit + fixtures/<modelo>/<firmware>/*.xml|json
  tools/recorder/   graba respuestas reales (sanitizadas) de una cámara → fixtures
  tools/simulator/  "cámara Hikvision falsa" que reproduce fixtures y emite alertStream sintético
  frontend/src/     pages, features/{cameras,live,events,rules,matrix}, components/ui
  infra/            docker-compose.yml, mediamtx.yml
  docs/             matriz, evidencias, decisiones (ADR cortos)
```

**Decisiones clave:**
1. **La capacidad se registra por protocolo.** Cada función (p. ej. `events.line_crossing`) tiene una fila por ISAPI, otra por ONVIF y otra por RTSP. Así la matriz muestra lado a lado qué da cada API: esa es la pregunta de investigación.
2. **Detección automática.** Nada de elegir la familia a mano. Se usa:
   - `GET /ISAPI/System/capabilities` (bloque `SmartCap`)
   - `/ISAPI/Event/triggersCap` y `/ISAPI/Event/notification/subscribeEventCap`
   - ONVIF `GetServices` / `GetEventProperties`

   Cada capacidad queda como **declarada** (la cámara dice soportarla) o **verificada** (se llamó y respondió), con la evidencia guardada.
3. **Escrituras seguras.** Siempre se lee y se guarda un respaldo, después se escribe con PUT, se relee para verificar y hay restauración con un clic.
4. **Offline-first.** El grabador de fixtures y el simulador permiten desarrollar sin VPN y hacer una demo de respaldo si la red falla en la defensa.
5. **VPN.** El alta es manual (host/puerto/https) y los timeouts son tolerantes. WS-Discovery solo funciona en LAN y la UI lo aclara.

---

## Modelo de datos (PostgreSQL)
- `cameras`: id uuid, name, host, http_port, use_https, verify_tls, rtsp_port, onvif_port, username, secret_enc, onvif_username/secret_enc (Hikvision usa un usuario ONVIF aparte), vendor, model, serial, firmware, mac, status, last_seen_at, network_mode (lan/vpn), vca_mode.
- `capability_checks`: camera_id, capability_code, protocol (isapi|onvif|rtsp), level (supported|partial|unsupported|unverified|error), source (declared|verified), evidence jsonb, latency_ms, checked_at. UNIQUE(camera, code, protocol).
- `video_profiles`: camera_id, protocol, token, stream_type, codec, width, height, fps, bitrate, rtsp_path, mediamtx_path.
- `events`: id, camera_id, protocol, raw_type, type (normalizado), state, channel, occurred_at, received_at, rule_ref, target_type (human/vehicle/…), bbox jsonb, payload jsonb (sanitizado). Índices en (camera_id, occurred_at desc) y (type, occurred_at).
- `event_media`: event_id, kind (full/target/plate), path (en disco, `media/`), mime, bytes, width, height.
- `analytic_rules`: camera_id, protocol, rule_type (line|field|entrance|exiting), external_id, channel, enabled, geometry jsonb (normalizada 0–1), params jsonb (dirección, sensibilidad, duración, filtro de objetivo), linkage jsonb, synced_at, raw jsonb.
- `config_backups`: camera_id, resource (URL), content, created_at, restored_at.
- `operation_logs`: camera_id, capability_code, protocol, operation, http_status, success, latency_ms, error_code, detail jsonb, experiment_id (nullable, para las corridas de comparación), created_at.

---

## Fases de implementación

### Fase 0 — Esqueleto
- Crear el monorepo, `git init`, uv, pnpm, docker compose (postgres + mediamtx), ruff/pytest/Playwright y un README con los pasos para levantar todo.
- Layout del frontend con shadcn: sidebar Cámaras / Eventos / Matriz, tema oscuro.

### Fase 1 — Las 3 APIs conectadas (el mínimo que pide el profesor)
- Alta de cámara con prueba de conexión separada por **ISAPI** (deviceInfo), **ONVIF** (GetDeviceInformation) y **RTSP** (DESCRIBE).
- Perfiles de video (ISAPI `/Streaming/channels` y ONVIF `GetProfiles`), snapshot (`/ISAPI/Streaming/channels/101/picture`) y video en vivo por MediaMTX con WebRTC.
- Grabador de fixtures, ejecutado contra la cámara de la VPN, y simulador.
- **UI:** listado de cámaras con estado por protocolo (3 luces) y detalle con pestaña "Vivo".

### Fase 2 — Motor de capacidades + funciones comunes (alcance del anteproyecto)
- Detección automática y matriz por protocolo.
- Funciones comunes, cada una intentada por ISAPI y por ONVIF cuando exista (es la comparación estándar vs propietario):
  - estado/salud
  - sincronización horaria
  - reinicio (con confirmación)
  - OSD
  - ajustes de imagen
  - detección de movimiento
- **UI:** pestaña "Capacidades", página "Matriz" y log de operaciones.

### Fase 3 — DEMO 1: eventos en vivo con fotos
- `event_hub`: por cada cámara mantiene abierto `GET /ISAPI/Event/notification/alertStream`.
  - Parser multipart robusto: XML y JSON, adjuntos JPEG, heartbeat `videoloss`, reconexión con backoff.
  - En paralelo, ONVIF PullPoint para comparar cobertura y latencia.
- Normalización de tipos de evento: `linedetection`, `fielddetection`, `regionEntrance`/`regionExiting`, `VMD`, `tamper`, etc. → `type`.
- Persistencia en `events` + `event_media`, y fan-out por SSE.
- **UI:**
  - Feed en vivo con tarjetas: foto, tipo, cámara, hora y recuadro del objetivo dibujado encima.
  - Aviso emergente en cualquier página.
  - Galería con filtros (cámara, tipo, rango de fechas, humano/vehículo) y línea de tiempo.
  - Contador por tipo.

### Fase 4 — DEMO 2: dibujar reglas sobre la imagen
- Drivers ISAPI de reglas (`GET/PUT` + `/capabilities`):

  | Regla | Endpoint |
  |---|---|
  | Cruce de línea | `/ISAPI/Smart/LineDetection/<ch>` (lineItem) |
  | Intrusión | `/ISAPI/Smart/FieldDetection/<ch>` (regions) |
  | Entrada a región | `/ISAPI/Smart/regionEntrance/<ch>` |
  | Salida de región | `/ISAPI/Smart/regionExiting/<ch>` |

- Vinculación de la regla, para que el evento llegue al alertStream: `/ISAPI/Event/triggers/<event>-<ch>` con notificación "center". **Es un detalle crítico: sin esto la regla existe pero no emite eventos.**
- Horario: `/ISAPI/Event/schedules/...`, con "siempre activo" por defecto.
- Conversión de coordenadas: canvas (0–1) ↔ ISAPI (escala 0–1000; el origen del eje Y se confirma con un fixture real).
- **Modo VCA:** leer `/ISAPI/System/Video/inputs/channels/<ch>/VCAResource`. Si la cámara está en un modo incompatible (p. ej. parking), la UI lo avisa. **No se cambia automáticamente**, porque reinicia la cámara.
- ONVIF Analytics `GetRules` (solo lectura) como contraste en la matriz.
- **UI:** editor sobre el snapshot con herramientas línea / polígono, dirección A→B / B→A / ambas, sensibilidad, filtro humano/vehículo (si AcuSense lo soporta), activar/desactivar y un botón "Probar": el feed marca el próximo evento de esa regla. Incluye respaldo y restauración.

### Fase 5 — Evidencia para la tesis
- Experimento repetible por cámara (con `experiment_id`): N ejecuciones por función y protocolo → tasa de éxito, latencia p50/p95, cobertura de eventos ISAPI vs ONVIF.
- Exportar la matriz y los resultados a CSV y Markdown, más capturas para los anexos.

### Backlog anotado (después de la demo)
- ANPR (`/ISAPI/ITC/*`, `/ISAPI/Traffic/ANPR/*`, eventos ANPR con foto de patente) y listas blancas/negras
- Parking en la 7A46G0 (portar la lógica y el editor del proyecto `Cámaras`)
- PTZ: joystick, presets, patrullas, `position3D` (clic para centrar), auto-tracking si `isSupportIntelliTrace`
- Captura facial (`faceRule`), detección mixta humano/vehículo (`mixedTargetDetection?format=json`)
- Conteo de personas, heatmap, colas (dependen de `VCAResource`), merodeo y aglomeración (`/ISAPI/Smart/loitering`, `/group`)
- Búsqueda en la memoria de la cámara (`/ISAPI/ContentMgmt/search`)
- Recuadros en vivo sobre el video usando metadata (`/ISAPI/Streaming/channels/<ch>/metadata`)
- Otras marcas vía ONVIF para ampliar la comparación

---

## Riesgos y cómo se mitigan
- **Protocolos deshabilitados en la cámara:** hay que activar ONVIF y crear un usuario ONVIF aparte en la integración de protocolos. Se agrega un checklist de preparación en el README y un mensaje claro en la prueba de conexión.
- **Diferencias de firmware entre modelos:** todo se decide por `capabilities` y nada queda hardcodeado por modelo. Fixtures por modelo y firmware.
- **alertStream con límite de conexiones o corte por VPN:** una sola conexión por cámara compartida por el hub, reconexión con backoff y estado visible en la UI.
- **La documentación DeepinView no se revisó en detalle** (solo la de PTZ Ultra). Antes de la Fase 4 se contrastan los endpoints de reglas con el PDF DeepinView y con la cámara real.

## Verificación
- **Unit:** parsers XML/JSON y multipart, normalización de eventos, conversión de coordenadas, resolución del motor, todo con fixtures reales vía respx.
- **Integración:** pytest contra Postgres en docker y el simulador (alta → detección → evento sintético → SSE).
- **E2E:** Playwright smoke (alta de cámara simulada, feed recibe evento, dibujar línea y guardar).
- **Hardware, por cámara:**
  1. registrar
  2. detectar (matriz con 3 protocolos)
  3. video en vivo WebRTC
  4. snapshot
  5. dibujar una línea y guardar
  6. cruzarla físicamente
  7. el evento con foto aparece en el feed en menos de ~2 s
  8. restaurar la configuración

  El resultado se registra en `docs/evidencias/`.
