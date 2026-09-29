# 6. Arquitectura e implementación

## 6.1 Vista general

La plataforma sigue una arquitectura de tres capas con un componente central que le da nombre al
enfoque de este trabajo: el motor de capacidades.

```
Frontend (React + TypeScript)
        |
Backend (FastAPI, Python 3.12)
        |
Motor de capacidades
    |-- Adaptador ISAPI (Hikvision)
    |     |-- Analítica clásica (/ISAPI/Smart/*, XML)
    |     `-- AI Open Platform (/ISAPI/Intelligent/AIOpenPlatform/*, JSON)
    |-- Adaptador ONVIF (estándar)
    `-- Adaptador RTSP / MediaMTX (video)
        |
PostgreSQL (persistencia)      MediaMTX (republicación de video)
```

Cada adaptador implementa las operaciones normalizadas que el motor de capacidades necesita
(identidad del dispositivo, perfiles de video, snapshot, estado, hora, OSD, imagen, movimiento,
reglas de analítica) traduciendo desde y hacia el modelo de datos común. El motor nunca conoce el
detalle de un protocolo particular; solo conoce la interfaz común y el resultado normalizado.

## 6.2 Justificación de las decisiones de stack

| Capa | Elección | Justificación |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 | Tipado explícito de extremo a extremo; ecosistema maduro para HTTP asíncrono, condición necesaria para mantener conexiones de eventos de larga duración sin bloquear el resto del servidor |
| Cliente HTTP hacia ISAPI | `httpx` asíncrono + autenticación Digest propia | Control fino sobre el manejo de errores, necesario porque los códigos de error de ISAPI no siempre son concluyentes por sí solos (§6.4) |
| Cliente ONVIF | `onvif-zeep-async` | Implementación SOAP/WS-* madura sobre asyncio |
| Persistencia | PostgreSQL 16 + SQLAlchemy 2 (async) + Alembic | Tipo `JSONB` para conservar la respuesta cruda de cada llamada, que es evidencia y no puede normalizarse sin pérdida de información; **se usa la misma base también en las pruebas automatizadas**, para no introducir diferencias de comportamiento entre SQLite y Postgres que enmascararan defectos reales |
| Video | MediaMTX (WebRTC/WHEP con respaldo HLS) | Las credenciales de la cámara nunca llegan al navegador: el backend es el único que las conoce y republica el flujo autenticado hacia un origen que el cliente consume sin autenticación |
| Tiempo real (eventos) | *Server-Sent Events* | El flujo de eventos hacia el navegador es unidireccional; SSE resuelve el caso sin la complejidad adicional de WebSocket |
| Frontend | React 19 + TypeScript + Vite, TanStack Query | — |
| Credenciales | Cifradas con Fernet (clave simétrica derivada de un secreto de configuración) | Las cámaras se registran con usuario y contraseña; ninguna credencial se almacena en texto plano |

## 6.3 El modelo de datos

Las tablas centrales del sistema son:

- **`cameras`**: identidad y credenciales (cifradas) de cada cámara, con soporte para un usuario
  ONVIF distinto del usuario web —una particularidad verificada en el hardware Hikvision, donde
  ambos usuarios no son necesariamente el mismo—.
- **`capability_checks`**: una fila por cámara, función y protocolo, con el nivel de soporte
  (soportada / parcial / no soportada / sin verificar / error), la fuente (declarada / verificada),
  la evidencia cruda y la latencia. Es la tabla que materializa la matriz de compatibilidad.
- **`operation_logs`**: un registro de **cada llamada realizada** a cualquier cámara durante toda
  la vida del sistema, con protocolo, operación, resultado, latencia y un `experiment_id` opcional
  que permite agrupar las llamadas de una corrida experimental (capítulo 7, §7.5) sin mezclarlas
  con el resto del tráfico de la plataforma.
- **`events`** y **`event_media`**: episodios de eventos (no avisos individuales, ver §6.6) con sus
  imágenes asociadas.
- **`analytic_rules`** y **`config_backups`**: el estado normalizado de las reglas de analítica de
  cada cámara y el respaldo de cada configuración antes de sobrescribirla, necesario para el
  principio de escritura segura descrito en §6.4.

## 6.4 Disambiguación de errores en ISAPI: un caso de diseño forzado por el hardware

Un ejemplo concreto de cómo el comportamiento real del hardware forzó una decisión de diseño no
prevista inicialmente: Hikvision responde con el mismo código HTTP (403) tanto cuando las
credenciales no tienen permiso para una operación como cuando la operación **no existe** en ese
modelo de cámara. La única forma de distinguir ambos casos es inspeccionar el cuerpo de la
respuesta, que en el segundo caso incluye un campo `subStatusCode` con el valor `notSupport`. El
cliente HTTP desarrollado en este trabajo intercepta la respuesta antes de decidir qué tipo de error
propagar:

```python
if status in (404, 405, 501) or detail.lower() in ("notsupport", "invalid operation"):
    raise NotSupported(message, http_status=status)
if status in (401, 403):
    raise AuthenticationFailed(message, http_status=status)
```

Esta distinción no es cosmética: si el sistema tratara ambos casos como el mismo tipo de error, la
matriz de compatibilidad no podría distinguir "esta cámara no tiene esta función" de "las
credenciales configuradas no alcanzan", que son hallazgos con implicancias completamente distintas
para quien lea la matriz.

## 6.5 Escritura segura: respaldo, escritura, relectura, comparación

Se verificó empíricamente (capítulo 7) que una cámara puede responder con éxito (HTTP 200) a una
operación de escritura sin aplicar el cambio solicitado. En consecuencia, ninguna escritura del
sistema se da por válida a partir del código de respuesta únicamente. El flujo aplicado es:

1. **Leer y respaldar** el estado actual del recurso antes de modificarlo (tabla `config_backups`).
2. **Escribir** solo los campos solicitados, preservando el resto del documento devuelto por la
   cámara — evitando así que una escritura parcial pise datos que no se pretendía modificar.
3. **Releer** el recurso después de escribir.
4. **Comparar** lo releído contra lo solicitado, con una tolerancia numérica que absorbe el
   redondeo introducido por la propia cámara (por ejemplo, al convertir coordenadas normalizadas a
   enteros de una escala 0–1000) sin enmascarar una escritura genuinamente ignorada.

Si la comparación falla, el sistema no reporta éxito: reporta explícitamente que la cámara aceptó
el pedido pero no lo aplicó, con el detalle de qué campo quedó sin cambiar.

## 6.6 Motor de eventos: de avisos a episodios

Los eventos de una cámara llegan por una conexión HTTP de larga duración que entrega un flujo
*multipart*. El sistema mantiene una tarea asíncrona por cámara que lee ese flujo, reconecta con
espera creciente ante cortes (entre 2 y 60 segundos) y agrupa los avisos en **episodios** — un
episodio es un intervalo con inicio, fin y una cuenta de avisos, delimitado por: misma cámara, mismo
tipo de evento, mismo canal, misma regla; cerrado por un aviso explícito de fin, por 20 segundos de
inactividad o, como tope duro, a los 10 minutos.

Una particularidad del hardware que condicionó este diseño: el aviso que **cierra** un evento de
cruce de línea no incluye el identificador de la regla que lo originó (a diferencia del aviso que lo
abre, que sí lo incluye). Un agrupador que exigiera coincidencia exacta de regla para cerrar un
episodio dejaría episodios abiertos indefinidamente. El agrupador desarrollado en este trabajo
cierra por coincidencia de tipo y canal cuando el aviso de cierre no trae identificador de regla,
reproduciendo el comportamiento real observado en el hardware.

## 6.7 Dos adaptadores para una misma marca

La decisión de arquitectura más directamente derivada de un hallazgo empírico (desarrollado con
evidencia en el capítulo 7) es que **Hikvision no es un adaptador, son dos**: la analítica clásica
(líneas de cruce, intrusión) se resuelve contra `/ISAPI/Smart/*` en XML con coordenadas enteras de
escala 0–1000; la analítica de las cámaras de la serie DeepinView con IA se resuelve contra
`/ISAPI/Intelligent/AIOpenPlatform/*`, una API completamente distinta, en JSON, con coordenadas
decimales de 0 a 1, un modelo de reglas distinto y una activación por regla individual en lugar de
por tipo. El sistema detecta cuál de las dos familias responde una cámara dada e instancia el
adaptador correspondiente; **ninguna decisión de la plataforma asume que "ser Hikvision" implica un
único comportamiento**.

## 6.8 Herramientas construidas como parte del trabajo

Más allá del sistema en sí, se construyeron tres herramientas auxiliares que forman parte del
aporte metodológico de este trabajo:

- **Grabador de respuestas** (`tools/recorder`): sondea sistemáticamente una cámara real, sanitiza
  la respuesta (elimina identificadores del equipo y credenciales) y la conserva como fixture,
  produciendo además un índice con la latencia y el resultado de cada endpoint sondeado.
- **Simulador de cámara** (`tools/simulator`): reproduce, a partir de esas fixtures, el
  comportamiento verificado del hardware real —incluidas sus particularidades adversas—, con
  autenticación Digest real y tres perfiles distintos (PTZ, domo DeepinView, cámara básica sin
  analítica).
- **Corredor de experimentos** (`tools/experiments`): repite cada función del catálogo N veces por
  protocolo y cámara, con un reconocimiento previo de una sola llamada para no esperar N tiempos de
  espera agotados si la cámara está fuera de línea, y produce tasa de éxito y latencias en los
  percentiles 50 y 95, exportadas a CSV y a un informe en Markdown.
