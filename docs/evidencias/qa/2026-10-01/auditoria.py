"""Pruebas manuales repetibles. No modifica la configuración de la cámara real.

Ejecutar desde backend: uv run python ../docs/evidencias/qa/2026-10-01/auditoria.py prepare|real|sim|cleanup
Los simuladores deben escuchar en 18101, 18102 y 18103. Las cámaras QA se eliminan con cleanup.
"""

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parents[3] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.security import decrypt  # noqa: E402
from app.db.models import Camera  # noqa: E402


async def main(mode):
    results = []
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=150) as api:
        async def request(label, method, path, **kwargs):
            start = time.perf_counter()
            try:
                r = await api.request(method, path, **kwargs)
                data = r.json() if r.content and "json" in r.headers.get("content-type", "") else {"bytes": len(r.content), "mime": r.headers.get("content-type")}
                # Identidad y configuración no se copian completas a evidencia versionable.
                if isinstance(data, dict):
                    data = {k: v for k, v in data.items() if k not in {"serial", "mac", "username", "onvif_username"}}
                results.append({"test": label, "status": r.status_code, "ms": round((time.perf_counter() - start) * 1000), "result": data})
                print(f"{label}: HTTP {r.status_code} ({results[-1]['ms']} ms)", flush=True)
                return r
            except httpx.HTTPError as exc:
                results.append({"test": label, "error": type(exc).__name__})
                print(f"{label}: {type(exc).__name__}", flush=True)
                return None

        if mode == "prepare":
            cams = (await api.get("/api/cameras")).json()
            ids = {}
            async with SessionLocal() as session:
                source = await session.scalar(select(Camera).where(Camera.host == "190.15.193.250"))
                if source is not None:
                    payload = {"name": "QA Sarmiento 18080", "host": source.host, "http_port": 18080, "onvif_port": 18080, "rtsp_port": source.rtsp_port, "username": source.username, "password": decrypt(source.secret_enc), "network_mode": "vpn"}
                    if source.onvif_username and source.onvif_secret_enc:
                        payload.update(onvif_username=source.onvif_username, onvif_password=decrypt(source.onvif_secret_enc))
                    old = next((c for c in cams if c["name"] == payload["name"]), None)
                    r = await api.post("/api/cameras", json=payload) if old is None else None
                    ids["real"] = old["id"] if old else r.json()["id"]
                for model, port in (("ptz", 18101), ("domo", 18102), ("basica", 18103)):
                    name = f"QA {model}"
                    old = next((c for c in cams if c["name"] == name), None)
                    r = await api.post("/api/cameras", json={"name": name, "host": "127.0.0.1", "http_port": port, "onvif_port": 9, "rtsp_port": 9, "username": "admin", "password": "simulada"}) if old is None else None
                    ids[model] = old["id"] if old else r.json()["id"]
            (OUT / "qa_ids.json").write_text(json.dumps(ids, indent=2))
            print(json.dumps(ids), flush=True)
        elif mode == "real":
            cid = json.loads((OUT / "qa_ids.json").read_text())["real"]
            root = f"/api/cameras/{cid}"
            await request("conexión real", "POST", root + "/connection-test")
            await request("perfiles real", "POST", root + "/profiles/refresh")
            await request("snapshot real", "GET", root + "/snapshot")
            await request("funciones ISAPI real", "GET", root + "/functions?protocol=isapi")
            await request("funciones ONVIF real", "GET", root + "/functions?protocol=onvif")
            await request("reglas real", "GET", root + "/rules")
            await request("detectar real", "POST", root + "/capabilities/detect")
            await request("capacidades real", "GET", root + "/capabilities")
            await request("inicio listener real", "POST", root + "/listener")
            await asyncio.sleep(35)
            r = await request("estado listeners real", "GET", "/api/listeners")
            if r is not None:
                results[-1]["result"] = [v for v in r.json() if v["camera_id"] == cid]
            await request("eventos real", "GET", f"/api/events?camera_id={cid}&limit=20")
            await request("parar listener real", "DELETE", root + "/listener")
            await request("publicar video real", "POST", root + "/live")
        elif mode == "sim":
            ids = json.loads((OUT / "qa_ids.json").read_text())
            for model in ("ptz", "domo", "basica"):
                cid = ids[model]
                root = f"/api/cameras/{cid}"
                await request(f"{model} conexión", "POST", root + "/connection-test")
                await request(f"{model} perfiles", "POST", root + "/profiles/refresh")
                await request(f"{model} snapshot", "GET", root + "/snapshot")
                await request(f"{model} funciones", "GET", root + "/functions")
                await request(f"{model} reglas", "GET", root + "/rules")
                await request(f"{model} detección", "POST", root + "/capabilities/detect")
            cid = ids["ptz"]
            root = f"/api/cameras/{cid}"
            await request("cambiar OSD", "PATCH", root + "/functions/osd", json={"name": "QA PRUEBA", "show_name": True})
            await request("cambiar imagen", "PATCH", root + "/functions/image", json={"brightness": 37, "contrast": 65})
            await request("cambiar movimiento", "PATCH", root + "/functions/motion", json={"enabled": True, "sensitivity": 73})
            await request("sincronizar hora", "POST", root + "/functions/time/sync")
            await request("reinicio sin confirmación", "POST", root + "/functions/reboot")
            await request("reinicio simulador confirmado", "POST", root + "/functions/reboot?confirm=true")
            rules = (await api.get(root + "/rules")).json()
            line = next(r for r in rules["rules"] if r["kind"] == "line")
            await request("editar línea", "PATCH", root + f"/rules/line/{line['external_id']}", json={"points": [[0.2, 0.3], [0.8, 0.7]]})
            backups = (await api.get(root + "/backups")).json()
            if backups:
                await request("restaurar línea", "POST", root + f"/backups/{backups[0]['id']}/restore")
                await request("línea restaurada", "GET", root + "/rules")
            await request("iniciar listener simulador", "POST", root + "/listener")
            await asyncio.sleep(2)
            sse = []

            async def listen():
                async with api.stream("GET", "/api/events/stream") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            if data.get("camera_id") == cid:
                                sse.append(data)

            task = asyncio.create_task(listen())
            await asyncio.sleep(1)
            await api.post("http://127.0.0.1:18101/_sim/disparar?tipo=linedetection&segundos=4&regla=1")
            await asyncio.sleep(8)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            results.append({"test": "SSE simulador", "messages": sse})
            r = await request("episodios y foto simulador", "GET", f"/api/events?camera_id={cid}")
            if r is not None and r.json():
                event = r.json()[0]
                if event["media"]:
                    await request("servir foto del episodio", "GET", f"/api/events/{event['id']}/media/{event['media'][0]['id']}")
            await request("parar listener simulador", "DELETE", root + "/listener")
            await request("logs escrituras simulador", "GET", root + "/operations?limit=100")
            await request("matriz completa", "GET", "/api/matrix")
            for bad in ("limit=-1", "limit=501", "since=invalida"):
                await request(f"validación eventos {bad}", "GET", f"/api/events?{bad}")
            await request("cámara inexistente", "GET", f"/api/cameras/{uuid.uuid4()}")
        elif mode == "cleanup":
            ids = json.loads((OUT / "qa_ids.json").read_text())
            for cid in ids.values():
                await api.delete(f"/api/cameras/{cid}/listener")
                await request("eliminar cámara QA", "DELETE", f"/api/cameras/{cid}")
        if results:
            (OUT / f"{mode}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
