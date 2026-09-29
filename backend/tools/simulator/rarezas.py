"""El estado de las reglas de la cámara simulada, con las rarezas verificadas en la real.

Esto es lo que hace útil al simulador: si solo respondiera "bien", no serviría para probar que
la plataforma se defiende. Cada rareza está documentada en docs/bitacora-apis.md §3.
"""

import re

VACIO = ("0", "1000")  # lo que la PTZ devuelve en la lista para reglas que sí existen


class EstadoSmart:
    """Reglas de /ISAPI/Smart/*, con el comportamiento real de la PTZ."""

    def __init__(self, items: dict[str, str], lista: str) -> None:
        self.items = dict(items)  # id -> XML del recurso individual
        self.lista = lista  # XML de la colección
        self.habilitado = self._leer_enabled_global(lista)
        self.escrituras_a_la_lista = 0

    @staticmethod
    def _leer_enabled_global(xml: str) -> bool:
        m = re.search(r"<enabled>(\w+)</enabled>", xml)
        return bool(m and m.group(1) == "true")

    def leer_lista(self) -> str:
        """RAREZA 1: la colección devuelve coordenadas vacías para reglas que sí existen.

        Solo el recurso individual dice la verdad (verificado en las líneas 2 y 3 de la PTZ).
        """
        cuerpo = re.sub(
            r"<enabled>\w+</enabled>",
            f"<enabled>{'true' if self.habilitado else 'false'}</enabled>",
            self.lista,
            count=1,
        )
        return re.sub(
            r"<positionX>\d+</positionX>\s*<positionY>\d+</positionY>",
            f"<positionX>{VACIO[0]}</positionX><positionY>{VACIO[1]}</positionY>",
            cuerpo,
        )

    def leer_item(self, rule_id: str) -> str | None:
        xml = self.items.get(rule_id)
        if xml is None:
            return None
        # RAREZA 3: el <enabled> de cada regla siempre vuelve en false, pase lo que pase.
        return re.sub(r"<enabled>\w+</enabled>", "<enabled>false</enabled>", xml, count=1)

    def escribir_lista(self, contenido: str) -> None:
        """RAREZA 2: escribir la colección responde 200 OK y NO cambia la geometría.

        Lo único que se aplica es el <enabled> global.
        """
        self.escrituras_a_la_lista += 1
        self.habilitado = self._leer_enabled_global(contenido)

    def escribir_item(self, rule_id: str, contenido: str) -> bool:
        if rule_id not in self.items:
            return False
        self.items[rule_id] = contenido
        return True
