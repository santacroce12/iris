# Vigía — Plataforma unificada de cámaras IP

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
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
```

```bash
cd frontend && pnpm install && pnpm dev
```

Abrir http://localhost:5173. La API documentada queda en http://localhost:8000/docs.

| Servicio | Puerto |
|---|---|
| Frontend (Vite) | 5173 |
| Backend (FastAPI) | 8000 |
| PostgreSQL | 5434 |
| MediaMTX WebRTC / HLS / API | 8889 / 8888 / 9997 |

## Tests

```bash
cd backend && uv run pytest
```

Los tests de integración usan la base `camaras_test` del mismo contenedor de Postgres. Los unitarios
usan respuestas **reales** de cámaras Hikvision guardadas en `backend/tests/fixtures/`.

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

- [docs/PLAN.md](docs/PLAN.md): plan aprobado, fases y backlog de analíticas.
- [docs/relevamiento-camaras.md](docs/relevamiento-camaras.md): qué API de analítica expone cada cámara real.
- [docs/PENDIENTES.md](docs/PENDIENTES.md): lo que quedó para después.
