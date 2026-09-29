"""Qué le pregunta el grabador a una cámara.

Incluye a propósito endpoints que muchos modelos NO tienen: un `403 notSupport` grabado es
evidencia tan válida como una respuesta correcta, y es lo que permitió demostrar que el domo
no expone analítica clásica.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Punto:
    nombre: str  # nombre del archivo de fixture
    ruta: str
    grupo: str
    json: bool = False  # pedirlo con ?format=json


def _smart(tipo: str, recurso: str, canal: int) -> list[Punto]:
    base = f"/ISAPI/Smart/{tipo}/{canal}"
    puntos = [
        Punto(f"smart{tipo}", base, "analítica clásica"),
        Punto(f"smart{tipo}Capabilities", f"{base}/capabilities", "analítica clásica"),
    ]
    # Solo el recurso individual dice la verdad (la lista devuelve coordenadas vacías).
    puntos += [
        Punto(f"smart{tipo}Item{i}", f"{base}/{recurso}/{i}", "analítica clásica")
        for i in range(1, 5)
    ]
    return puntos


def catalogo(canal: int = 1) -> list[Punto]:
    aiop = "/ISAPI/Intelligent/AIOpenPlatform"
    puntos: list[Punto] = [
        # --- identidad y sistema ---
        Punto("deviceInfo", "/ISAPI/System/deviceInfo", "sistema"),
        Punto("systemCapabilities", "/ISAPI/System/capabilities", "sistema"),
        Punto("systemStatus", "/ISAPI/System/status", "sistema"),
        Punto("systemTime", "/ISAPI/System/time", "sistema"),
        Punto("ntpServers", "/ISAPI/System/time/ntpServers", "sistema"),
        Punto("networkInterfaces", "/ISAPI/System/Network/interfaces", "sistema"),
        # --- video ---
        Punto("streamingChannels", "/ISAPI/Streaming/channels", "video"),
        Punto(
            "metadataCapabilities",
            f"/ISAPI/Streaming/channels/{canal}/metadata/capabilities",
            "video",
        ),
        Punto("overlays", f"/ISAPI/System/Video/inputs/channels/{canal}/overlays", "video"),
        Punto("imageColor", f"/ISAPI/Image/channels/{canal}/color", "video"),
        Punto(
            "vcaResource",
            f"/ISAPI/System/Video/inputs/channels/{canal}/VCAResource",
            "video",
        ),
        # --- eventos ---
        Punto("subscribeEventCap", "/ISAPI/Event/notification/subscribeEventCap", "eventos"),
        Punto("eventTriggersCap", "/ISAPI/Event/triggersCap", "eventos"),
        Punto("eventTriggers", "/ISAPI/Event/triggers", "eventos"),
        Punto("httpHosts", "/ISAPI/Event/notification/httpHosts", "eventos"),
        Punto(
            "motionDetection",
            f"/ISAPI/System/Video/inputs/channels/{canal}/motionDetection",
            "eventos",
        ),
        # --- AI Open Platform (domos DeepinView) ---
        Punto("aiopInfo", aiop, "IA", json=True),
        Punto("aiopCapabilities", f"{aiop}/capabilities", "IA", json=True),
        Punto("aiopVideoTask", f"{aiop}/videoTask", "IA", json=True),
        Punto("aiopVideoTaskCapabilities", f"{aiop}/videoTask/capabilities", "IA", json=True),
        Punto("aiopAlgorithmEngines", f"{aiop}/algorithmModel/engines", "IA", json=True),
        Punto("aiopAlgorithmModels", f"{aiop}/algorithmModel/management", "IA", json=True),
        Punto(
            "aiopRuleCapabilities",
            f"{aiop}/AIRuleConfig/channels/{canal}/capabilities",
            "IA",
            json=True,
        ),
        Punto(
            "appScheduleSwitch",
            "/ISAPI/Custom/OpenPlatform/App/appScheduleSwitch",
            "IA",
            json=True,
        ),
        # --- otras analíticas, para dejar registrado qué contesta cada modelo ---
        Punto("intelliTrace", f"/ISAPI/Smart/IntelliTrace/{canal}", "otras analíticas"),
        Punto(
            "peopleCounting",
            f"/ISAPI/System/Video/inputs/channels/{canal}/counting",
            "otras analíticas",
        ),
        Punto("heatMap", f"/ISAPI/Smart/HeatMap/{canal}", "otras analíticas"),
        Punto("faceCapture", f"/ISAPI/Smart/FaceCaptureStatistics/{canal}", "otras analíticas"),
        Punto("anpr", f"/ISAPI/ITC/instrument/{canal}/ANPR", "otras analíticas"),
        Punto("parking", f"/ISAPI/Smart/parking/{canal}", "otras analíticas"),
        Punto("loitering", f"/ISAPI/Smart/loitering/{canal}", "otras analíticas"),
        Punto("ptzStatus", f"/ISAPI/PTZCtrl/channels/{canal}/status", "PTZ"),
        Punto("ptzCapabilities", f"/ISAPI/PTZCtrl/channels/{canal}/capabilities", "PTZ"),
        Punto("ptzPresets", f"/ISAPI/PTZCtrl/channels/{canal}/presets", "PTZ"),
    ]
    for tipo, recurso in (
        ("LineDetection", "lineItem"),
        ("FieldDetection", "regions"),
        ("regionEntrance", "regions"),
        ("regionExiting", "regions"),
    ):
        puntos += _smart(tipo, recurso, canal)
    return puntos
