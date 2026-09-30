"""El bug de `--reload` colgado (PENDIENTES.md, "Código"), diagnosticado y resuelto.

Causa confirmada leyendo el propio código de uvicorn (`Server.shutdown`): espera a que todas las
conexiones HTTP terminen *antes* de mandarle el shutdown al `lifespan` de la app, sin timeout por
defecto. Un SSE que solo se corta escuchando ese shutdown (`bus.cerrando`) nunca lo ve — candado
circular. La solución instala nuestro propio manejador de SIGINT/SIGTERM que libera el bus de
inmediato y después llama al manejador que uvicorn ya había instalado, sin reemplazarlo.

Se prueba la lógica de encadenamiento en sí, no la entrega real de la señal por el sistema
operativo (eso ya lo prueba `uvicorn` mismo, y simularlo de punta a punta sería frágil en CI).
"""

import signal

import pytest

from app.engine.event_bus import EventBus
from app.main import _instalar_cierre_temprano_del_bus


@pytest.fixture
def bus_de_prueba(monkeypatch):
    """Un bus nuevo por test: el real es un singleton compartido con el resto de la app."""
    nuevo = EventBus()
    monkeypatch.setattr("app.main.bus", nuevo)
    return nuevo


@pytest.fixture(autouse=True)
def restaurar_manejadores_de_señal():
    """La función bajo prueba llama a `signal.signal`, que es un efecto global del proceso.
    Se restaura lo que había antes de cada test para no dejar manejadores de prueba instalados
    y afectar al resto de la suite (o a pytest mismo)."""
    previos = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    yield
    for sig, manejador in previos.items():
        signal.signal(sig, manejador)


def test_libera_el_bus_apenas_llega_la_señal(bus_de_prueba):
    _instalar_cierre_temprano_del_bus()
    assert not bus_de_prueba.cerrando.is_set()

    manejador_instalado = signal.getsignal(signal.SIGTERM)
    manejador_instalado(signal.SIGTERM, None)

    assert bus_de_prueba.cerrando.is_set()


def test_encadena_con_el_manejador_que_ya_estaba_instalado(bus_de_prueba):
    """Simula lo que hace uvicorn: instala su propio manejador antes que nosotros. El nuestro
    tiene que llamarlo, no reemplazarlo silenciosamente — si no, uvicorn nunca se entera de la
    señal y no arranca su propia secuencia de apagado."""
    llamadas: list[int] = []

    def manejador_de_uvicorn(signum: int, frame: object) -> None:
        llamadas.append(signum)

    signal.signal(signal.SIGINT, manejador_de_uvicorn)
    _instalar_cierre_temprano_del_bus()

    manejador_instalado = signal.getsignal(signal.SIGINT)
    assert manejador_instalado is not manejador_de_uvicorn  # el nuestro lo envolvió

    manejador_instalado(signal.SIGINT, None)

    assert bus_de_prueba.cerrando.is_set()
    assert llamadas == [signal.SIGINT]  # y el de uvicorn se terminó llamando igual


def test_las_dos_señales_manejadas_quedan_encadenadas(bus_de_prueba):
    # Simula el escenario real: uvicorn ya instaló un manejador propio para las dos señales
    # (`Server.capture_signals`) antes de que la app arranque. El de Python por defecto para
    # SIGINT *levanta* `KeyboardInterrupt`, así que sin este paso el test terminaría probando
    # ese caso particular en vez del encadenamiento en sí.
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda signum, frame: None)

    _instalar_cierre_temprano_del_bus()
    for sig in (signal.SIGINT, signal.SIGTERM):
        bus_de_prueba.cerrando = type(bus_de_prueba.cerrando)()  # reset entre señales
        signal.getsignal(sig)(sig, None)
        assert bus_de_prueba.cerrando.is_set()
