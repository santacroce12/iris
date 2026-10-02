"""Comprobaciones de integración sin exponer credenciales de cámara."""

import asyncio
import json
import re
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent


async def main():
    ids = json.loads((OUT / "qa_ids.json").read_text())
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        api = "http://localhost:8000"
        cid = ids["real"]
        logs = (await client.get(f"{api}/api/cameras/{cid}/operations?limit=500")).json()
        results["operaciones_camara_real"] = logs
        camera = (await client.get(f"{api}/api/cameras/{cid}")).json()
        results["identidad_camara_real"] = {k: camera[k] for k in ("vendor", "model", "firmware", "http_port", "onvif_port", "rtsp_port", "status")}
        urls = (await client.post(f"{api}/api/cameras/{cid}/live")).json()
        path = urls["path"]
        response = await client.get(f"http://localhost:9997/v3/config/paths/get/{path}")
        source = response.json().get("source", "")
        results["api_mediamtx_sin_auth"] = {"status": response.status_code, "credenciales_rtsp_en_respuesta": bool(re.search(r"rtsp://[^/@]+:[^/@]+@", source)), "cors": response.headers.get("access-control-allow-origin")}
        cid = ids["ptz"]
        root = f"{api}/api/cameras/{cid}"
        await client.post(root + "/recording?enabled=true")
        results["grabacion_antes_de_vivo"] = (await client.get(root + "/recording")).json()["recording"]
        await client.post(root + "/live")
        results["grabacion_despues_de_vivo"] = (await client.get(root + "/recording")).json()["recording"]
        await client.post(root + "/recording?enabled=false")
        # Carga de lecturas de plataforma: no manda ráfagas al hardware.
        async def read(i):
            response = await client.get(api + ["/api/health", "/api/cameras", "/api/matrix", "/api/events?limit=20"][i % 4])
            return response.status_code
        statuses = await asyncio.gather(*(read(i) for i in range(40)))
        results["40_lecturas_concurrentes"] = {str(status): statuses.count(status) for status in set(statuses)}
        results["health"] = (await client.get(api + "/api/health")).json()
    (OUT / "complementarias.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if k != "operaciones_camara_real"}, ensure_ascii=False, indent=2))


asyncio.run(main())
