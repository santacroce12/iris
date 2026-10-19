# Iris — Plataforma unificada de cámaras IP

Tesis de Luca Santacroce: *Diseño e implementación de una plataforma unificada para el acceso a
funciones avanzadas en cámaras IP multimarca*.

La plataforma integra cámaras combinando tres APIs y compara qué se logra con cada una:

| API | Rol | Implementación |
|---|---|---|
| **ISAPI** | Propietaria Hikvision: la analítica rica | `backend/app/drivers/isapi/` |
| **ONVIF** | Estándar de interoperabilidad | `backend/app/drivers/onvif/` |
| **RTSP** | Transporte de video → MediaMTX → WebRTC/HLS | `backend/app/drivers/rtsp/` |

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 solo para este proyecto)
- Node 22 + pnpm
- Docker Desktop

## Levantar en desarrollo

```bash
docker compose -f infra/docker-compose.yml up -d
```

```bash
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --timeout-graceful-shutdown 3
```

```bash
cd frontend && pnpm install && pnpm dev
```

Abrir http://localhost:15173. La API documentada queda en http://localhost:8000/docs.

| Servicio | Puerto |
|---|---|
| Frontend (Vite) | 15173 |
| Backend (FastAPI) | 8000 |
| PostgreSQL | 15432 |
| MediaMTX WebRTC / HLS / API | 8889 / 8888 / 9997 |

## Tests

```bash
cd backend && uv run pytest
```

Los tests de integración usan la base `camaras_test` del mismo contenedor de Postgres. Los unitarios
usan respuestas **reales** de cámaras Hikvision guardadas en `backend/tests/fixtures/`.

## Cuando tengas las cámaras: llevate todo

El acceso al hardware es el recurso escaso del trabajo. Con esto, una sesión de cinco minutos
frente a una cámara deja material para meses:

```bash
cd backend && uv run python -m tools.recorder --host 192.168.239.189 --clave TU_CLAVE
```

Barre unos 60 endpoints —incluidos los que ese modelo **no** tiene, porque un `403 notSupport`
grabado también es evidencia—, guarda cada respuesta como fixture bajo
`tests/fixtures/hikvision/<modelo>/<firmware>/`, saca un snapshot y escucha 30 segundos de
eventos. Deja un `indice.json` con qué contestó cada endpoint, con cuánta latencia y con qué
subStatusCode.

Antes de guardar borra número de serie, MAC, direcciones IP y credenciales: las fixtures se
versionan en el repositorio.

Con `--eventos 60` escucha más tiempo; con `--eventos 0` no escucha.

## Grabar video de las pruebas

En la pestaña "Vivo" de cada cámara hay un botón **Grabar**. Mientras está encendido, MediaMTX
mantiene abierta la conexión con la cámara aunque nadie esté mirando y guarda en
`backend/media/grabaciones/<ruta>/` en segmentos de 10 minutos.

Sirve para tener documentación en video de cada prueba: cruzar una línea, disparar una regla,
mostrar que un evento llegó. Si en algún momento se pierde el acceso al hardware, esas
grabaciones quedan como evidencia de lo que se hizo.

## La matriz de compatibilidad

`Matriz` compara cada función por ISAPI, ONVIF y RTSP en todas las cámaras. Distingue lo que la
cámara **declara** de lo que se **verificó** llamándola, y se exporta a CSV. El botón "Detectar"
recorre el catálogo entero y deja la evidencia de cada llamada (latencia incluida) en la base.

## Evidencia medible (Fase 5): tasa de éxito y latencias

```bash
cd backend && uv run python -m tools.experiments --repeticiones 30
```

Repite cada función del catálogo N veces por protocolo y por cámara —reales o simuladas, todas
las que estén registradas, o solo las que pases con `--camera-id`— y calcula tasa de éxito y
latencias p50/p95. Es la misma infraestructura de la matriz (`operation_logs`), solo que
repetida y agregada: una demo muestra que algo funcionó una vez, esto mide qué tan bien funciona
siempre.

Antes de las N repeticiones hace **una sola** llamada de reconocimiento por cámara y protocolo:
si no responde, lo anota como "no alcanzable" y sigue, en vez de esperar N timeouts de 8
segundos cada uno.

Deja un CSV y un informe en Markdown en `docs/evidencias/experimentos/<fecha>/`.

## Trabajar sin las cámaras

Hay una **cámara Hikvision simulada** para desarrollar, probar y hacer la demo sin depender de la
red de las cámaras:

```bash
cd backend && uv run python -m tools.simulator --modelo ptz --puerto 8101
```

Modelos: `ptz` (analítica clásica `/ISAPI/Smart/*`), `domo` (AI Open Platform) y `basica` (sin
analítica). Se da de alta como cualquier cámara: host `127.0.0.1`, puerto `8101`, usuario `admin`,
clave `simulada`.

No es una cámara "ideal": responde con las **grabaciones reales** de las cámaras de la oficina y
**reproduce sus rarezas** (la lista de reglas devuelve coordenadas vacías, escribir la colección
responde OK sin aplicar, el interruptor de cada regla se ignora). Si la plataforma funciona contra
el simulador, es porque se defiende de lo que hace el hardware de verdad.

Para disparar un evento a mano:

```bash
curl -X POST "http://127.0.0.1:8101/_sim/disparar?tipo=linedetection&segundos=6&regla=1"
```

Manda una ráfaga de un aviso por segundo y la cierra, igual que la cámara real. `GET /_sim` muestra
el estado. El snapshot es un patrón con la rejilla de coordenadas, así se ve de inmediato si una
regla quedó espejada.

## Preparar una cámara Hikvision

1. **ISAPI**: viene habilitado. Usar un usuario con permisos de configuración.
2. **ONVIF**: *Configuración → Red → Configuración avanzada → Protocolo de integración*.
   Habilitar "Open Network Video Interface" y **crear un usuario ONVIF** (es distinto al de la web).
   Cargarlo en "Usuario ONVIF" al agregar la cámara.
3. **RTSP**: puerto 554 abierto. Autenticación Digest (la plataforma la soporta).
4. **Hora**: sincronizar con NTP. ONVIF firma los pedidos con la hora y falla si hay mucha diferencia.
5. **Por VPN**: elegir "VPN" al agregar la cámara (timeouts más largos). El descubrimiento automático
   (WS-Discovery) solo funciona en la red local.

## Si todo anda lento

La carpeta se llama `OneDrive` pero OneDrive no está instalado: no es la causa. Lo que sí pesa:

- **Windows Defender** revisa cada archivo de `node_modules` y `.venv`. Conviene excluir la carpeta
  del proyecto, `%LOCALAPPDATA%\pnpm` y `%LOCALAPPDATA%\uv`.
- **Internet lento** (2–3 Mbit/s medidos): la primera instalación de dependencias tarda minutos;
  las siguientes salen de la caché.
- **Procesos colgados de otras herramientas** (servidores MCP de Codex) pueden agotar la memoria.

## Documentación

- **[docs/HOJA-DE-RUTA.md](docs/HOJA-DE-RUTA.md)** — el plan para terminar: qué falta, qué se hace
  con cámaras y qué sin ellas.
- **[docs/tesis/](docs/tesis/README.md)** — el documento de tesis en sí, capítulo por capítulo.
- [docs/PLAN.md](docs/PLAN.md): plan aprobado, fases y backlog de analíticas.
- [docs/bitacora-apis.md](docs/bitacora-apis.md): **bitácora para la tesis**: qué se encontró al integrar cada API real.
- [docs/relevamiento-camaras.md](docs/relevamiento-camaras.md): qué API de analítica expone cada cámara real.
- [docs/PENDIENTES.md](docs/PENDIENTES.md): lo que quedó para después.
