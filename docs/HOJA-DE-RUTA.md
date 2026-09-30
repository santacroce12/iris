# Hoja de ruta para terminar la tesis

Última actualización: 29/09/2026 (ONVIF verificado en las dos Hikvision + el domo ahora habla Smart)

Este documento es el plan de trabajo. Está dividido en dos columnas:

- **Sin cámaras**: lo puedo hacer solo, en cualquier momento, contra el simulador.
- **Con cámaras**: sesiones cortas y guionadas, para cuando estés en la oficina o con la VPN.

La regla es simple: **el acceso al hardware es el recurso escaso**. Todo lo que se pueda hacer sin
cámaras se hace sin cámaras, y el tiempo con cámaras se gasta solo en lo que no se puede hacer de
otra manera.

---

## Cómo trabajamos

Cuando tengas acceso, me decís **"estoy en la red"** y yo hago el resto. No necesitás quedarte
mirando: cada sesión está guionada acá abajo, con los comandos exactos y con qué significa que
salió bien.

**Lo único que necesito de vos** es que la máquina llegue a `192.168.239.x`, por LAN o por VPN. Se
verifica en 10 segundos:

```bash
ping -n 2 192.168.239.189
```

Si responde, arranco.

**Cómo toco las cámaras** (esto no cambia): respaldo antes de escribir, releo después para
verificar, y al final del documento queda anotado qué quedó cambiado en cada equipo.

---

## Estado al 29/09/2026

| Fase del anteproyecto | Estado | Qué falta |
|---|---|---|
| 0 — Esqueleto | ✅ Completa | — |
| 1 — Las 3 APIs conectadas | ✅ ~98 % | Repetirlo en la Scati, si se consigue acceso |
| 2 — Capacidades y matriz | ✅ ~95 % | Pantalla de funciones comunes (la API y los datos ya están) |
| 3 — Eventos en vivo | ✅ ~95 % | Verificar las fotos contra una cámara real (implementado, sin probar en vivo) |
| 4 — Reglas sobre la imagen | ✅ ~95 % | Que el motor pueda ofrecer Smart *y* AIOP en el domo (hoy elige una sola) |
| 5 — Evidencia para la tesis | ✅ ~90 % | Repetir la corrida real en la Scati si hay acceso |

**29/09 — ONVIF verificado contra hardware real en la PTZ *y en el domo***, al primer intento por
API en las dos, con el mismo procedimiento: `status: online` por los tres protocolos a la vez,
matriz con 8 de 11 funciones comparadas ISAPI-vs-ONVIF, y una corrida real de 30 repeticiones por
función con latencias medidas (no del simulador) contra el domo. Detalle completo en
`bitacora-apis.md` §6.5. Esto era el bloqueo más importante del proyecto y ya no lo es, en ninguna
de las dos cámaras.

**29/09 — Hallazgo grande: el domo cambió de IP (a `.174`) y, tras un reinicio, empezó a responder
también a la analítica clásica** (`/ISAPI/Smart/*`), que antes daba `403 notSupport` y que se creía
exclusiva de la PTZ. Confirmado escribiendo una regla real y verificando que se aplica (no un
`200` vacío). El domo hoy responde **las dos familias de analítica** (AI Open Platform y Smart) a
la vez — un hallazgo que nuancea el "hallazgo central" de la tesis (dos productos de la misma marca
con analíticas incompatibles): ahora es más preciso decir que la incompatibilidad se dio en un
momento dado, y que el mismo equipo puede exponer ambas caras según firmware/config. Detalle en
`bitacora-apis.md` §6.7 y pendiente en `PENDIENTES.md`.

112 tests en verde. El motor de eventos y el editor de reglas están verificados contra las dos
cámaras reales (PTZ y domo).

**Novedad (27/09):** hay una **cámara Scati** disponible además de las dos Hikvision — es
literalmente la marca que el cronograma del anteproyecto pedía para el caso comparativo de
"otra marca" (Fase 3: *"validación de Scati u otra marca disponible"*). No tiene analítica, y
eso está bien: el propio anteproyecto dice que una marca sin API avanzada es un caso
comparativo válido, no algo que invalide la tesis. Además puede ser el atajo para verificar
ONVIF: si trae ONVIF activado de fábrica (a diferencia de Hikvision, que hay que habilitarlo a
mano), conseguimos ahí la verificación real que falta.

---

## Parte A — Protocolo de los primeros 10 minutos

**Esto se hace SIEMPRE que haya acceso, antes que cualquier otra cosa.** Si la red se corta a los
quince minutos, que por lo menos nos hayamos llevado esto.

### A.1 — Grabar las respuestas de las dos cámaras (~3 min)

```bash
cd backend
uv run python -m tools.recorder --host 192.168.239.189 --clave <clave_ptz> --eventos 30
uv run python -m tools.recorder --host 192.168.239.101 --clave <clave_domo> --eventos 30
```

Barre ~60 endpoints por cámara, guarda cada respuesta como fixture, saca un snapshot y escucha 30
segundos de eventos. Deja un `indice.json` con latencias y subStatusCode.

**Listo cuando**: hay carpeta nueva o actualizada en `backend/tests/fixtures/hikvision/<modelo>/`
y el índice dice cuántos endpoints respondieron.

### A.2 — Encender la grabación de video (~1 min)

Pestaña **Vivo** de cada cámara → botón **Grabar**. Queda grabando en
`backend/media/grabaciones/` en segmentos de 10 minutos.

**Listo cuando**: aparece el cartel rojo "grabando". *Pendiente de verificar con hardware real:
que el archivo aparezca en disco.*

### A.3 — Detección de capacidades (~2 min)

Página **Matriz** → "Detectar en ..." para cada cámara. Deja la matriz al día con las latencias
reales de ese momento.

---

## Parte B — Sesiones con cámara

Ordenadas por valor para la tesis. La 1 es la que más importa.

---

### Sesión 0 — Alta de la Scati · ~15 min

**Se hace antes que la Sesión 1**, porque puede resolverla gratis. Necesito de vos: IP/host,
usuario, contraseña, y si está en la misma red que las Hikvision o hay que llegarle distinto.

**Paso 1.** La doy de alta en la plataforma y corro la prueba de conexión por los 3 protocolos.
ISAPI va a fallar limpio (no es Hikvision, no tiene ese API) — es exactamente lo esperado, no
un error a resolver. Lo que importa es ONVIF y RTSP.

**Paso 2.** Si ONVIF responde de fábrica (probable en una marca chica/regional), corro la
detección de capacidades. Ahí sale la verificación real que la Sesión 1 venía necesitando,
sin depender de los endpoints no confirmados de Hikvision.

**Paso 3.** Documento en la bitácora: es el caso comparativo "otra marca" que pedía el
cronograma del anteproyecto (Fase 3), y el hallazgo esperado es justamente que **no tiene**
capacidades premium — eso es un resultado, no una falla.

**Listo cuando**: la Scati está registrada, con ISAPI en "no soportada" (esperado) y ONVIF/RTSP
con el resultado real, sea cual sea.

---

### Sesión 1 — ONVIF en las Hikvision — ✅ Hecha en la PTZ y en el domo el 29/09

**Funcionó al primer intento, por API, sin necesitar hacerlo a mano en la interfaz. Se repitió
palabra por palabra en el domo (con nueva IP, `.174`) más tarde el mismo día y funcionó igual.**

```
GET  /ISAPI/System/Network/Integrate           → confirmó ONVIF apagado
PUT  /ISAPI/System/Network/Integrate           → <ONVIF><enable>true</enable></ONVIF>
GET  /ISAPI/Security/ONVIF/users               → lista vacía (había que crear uno)
POST /ISAPI/Security/ONVIF/users               → usuario "tesisonvif" creado
```

Resultado: `status: online` por ISAPI + ONVIF + RTSP a la vez, en las dos cámaras reales del
proyecto. Detalle completo, con las latencias medidas y un bug de código que el propio hardware
destapó (`GetOSDs` recibía el token equivocado), en `bitacora-apis.md` §6.5. El experimento de
la Fase 5 (30 repeticiones por función) ya corrió contra el domo con ONVIF encendido — resultados
en `docs/evidencias/experimentos/2026-09-29T13-30-29+00-00/informe.md`.

**Esta sesión ya está completa para las dos Hikvision.** Queda solo para la Scati, si se consigue
acceso (ver Sesión 0 más abajo).

---

### Sesión 2 — Fotos en los eventos — ✅ Implementada el 29/09 (falta probarla contra cámara real)

**Revisado en la interfaz de la PTZ**: este modelo no tiene una opción para adjuntar la foto al
canal que ya escuchamos ("Notificar al software remoto"). Solo ofrece "Cargar en
FTP/tarjeta de memoria/NAS", un mecanismo de entrega distinto. Detalle en `bitacora-apis.md` §6.6.

**Se implementó sin necesitar cámara**: cuando el motor abre un episodio nuevo sin foto adjunta,
pide él mismo un snapshot (`GET /ISAPI/Streaming/channels/<canal>01/picture`) antes de guardarlo.
Si la cámara ya mandó una foto, no pide nada de más; si el snapshot falla, el episodio se guarda
igual sin foto. Probado con 5 tests contra un servidor simulado (`respx`), incluida una prueba de
punta a punta que confirma el archivo escrito en disco.

**Lo que sigue pendiente con cámara**: verlo funcionar en vivo contra la PTZ o el domo reales (la
próxima vez que haya red), y repetir la revisión de "Método enlace" en el domo por si su modelo sí
ofrece adjuntar la imagen (es otra familia de firmware, puede ser distinto — si la tiene, se puede
evaluar si vale la pena sumarla como fuente adicional más adelante).

---

### Sesión 3 — La analítica de IA del domo · ~45 min

Es la parte más incierta y la que más material dio para la bitácora. Objetivo: **que dispare al
menos una vez**, o cerrar el tema con una conclusión documentada.

**Novedad (29/09), importante para esta sesión**: el domo (ahora en `192.168.239.174`) empezó a
responder también a la analítica **clásica** `/ISAPI/Smart/*` (antes daba `403 notSupport`), y esa
sí se pudo configurar y verificar por API sin depender de la interfaz web (ver Sesión 1 y
`bitacora-apis.md` §6.7). Si esta sesión de AIOP sigue sin poder recrear la tarea, **el camino
Smart es la alternativa real** para tener analítica de IA disparando en el domo: ya hay una regla
de línea escrita (desactivada) como prueba. Evaluar si conviene cerrar el capítulo AIOP como
"limitación documentada" y avanzar con Smart en su lugar.

**Paso 1.** Reviso si la tarea de análisis de AIOP volvió:

```
GET /ISAPI/Intelligent/AIOpenPlatform/videoTask?format=json
```

**Paso 2, si sigue vacía.** Hay que recrearla desde la interfaz de la cámara, y ahí necesito que
me ayudes con el navegador (yo no puedo poner tu clave en un formulario de login):

1. Entrás a `http://192.168.239.174` y llegás hasta la pantalla de AI Open Platform.
2. Me avisás y yo capturo el estado por API.
3. Creás la tarea de análisis de video con el modelo `deteccion_armas`.
4. Comparo antes y después: así sale la estructura del pedido que la API rechazaba con
   `deviceError` en las seis variantes que probé.

**Paso 3, la prueba decisiva.** Con la tarea corriendo, cambio el objetivo de la regla de "manos
en alto" a **persona** por unos minutos:

- Si dispara: la cadena entera funciona y el problema era la exigencia del objetivo.
- Si no dispara con una persona caminando delante: el motor no está analizando, y el problema es
  de la app o de su licencia.

**Aviso**: mientras esté en "persona" va a mandar una alarma por minuto a HikCentral. Lo hago por
5 o 10 minutos y lo dejo como estaba.

**Paso 4.** Si llega algún evento de IA, guardo el payload crudo como fixture y verifico que el
mapeo a `ai_rule` sea correcto. Hoy ese mapeo está escrito pero **nunca se vio llegar uno**.

**Listo cuando**: hay un evento de IA capturado, o una conclusión escrita de por qué no dispara.

---

### Sesión 4 — Grabar la demo de la defensa · ~30 min

Con el hardware disponible, grabar el video que vas a poder mostrar aunque el día de la defensa no
haya cámaras ni red.

**Guión a grabar** (con la grabación de video encendida):

1. Alta de la cámara y prueba de conexión por los tres protocolos.
2. Detección de capacidades y la matriz llenándose.
3. Dibujar una línea sobre la imagen y guardarla.
4. Cruzarla físicamente.
5. El evento apareciendo en vivo en la pantalla, con foto si la sesión 2 salió bien.
6. Mostrar la agrupación en episodios (el contador de avisos).

**Listo cuando**: el video está en `backend/media/grabaciones/` y las capturas en
`docs/evidencias/`.

---

### Sesión 5 — Experimentos de la Fase 5 · ~15 min, desatendida — ✅ Hecha en la PTZ y en el domo el 29/09

**El corredor ya está construido y probado** (27/09, contra el simulador), y ya se corrió contra
las dos cámaras reales el 29/09 con ONVIF activado: 14 filas de resultados (éxito y p50/p95 por
función y protocolo) en cada corrida —
`docs/evidencias/experimentos/2026-09-29T12-31-54+00-00/` (PTZ, citada en `tesis/07-resultados.md`
§7.5) y `docs/evidencias/experimentos/2026-09-29T13-30-29+00-00/informe.md` (domo, todavía no
volcada a la tesis). Falta solo repetirla contra la Scati si hay acceso.

```bash
cd backend && uv run python -m tools.experiments --repeticiones 30
```

Sin `--camera-id` corre contra todas las cámaras registradas. Antes de las N repeticiones hace
un solo pedido de reconocimiento por cámara y protocolo: si no responde, lo anota y sigue sin
esperar N timeouts. Ya se probó así contra las 3 cámaras reales (inalcanzables desde esta red):
tardó segundos, no minutos, y quedó todo documentado como "no alcanzable".

**Listo cuando**: el CSV y el informe en `docs/evidencias/experimentos/<fecha>/` tienen filas con
`isapi` para las dos cámaras reales, no solo para las simuladas.

---

### Sesión 6 — Limpieza y restauración · ~15 min

Al final de todo, dejar las cámaras como estaban y anotarlo:

- Borrar la línea 2 de la PTZ (quedó dibujada a mano en una prueba).
- Corregir la zona horaria de la PTZ, que está en +08:00.
- Revisar si la detección de movimiento del domo tiene que quedar encendida o no.
- Restaurar el umbral de confianza de la regla de IA (quedó en 600, era 800).
- Actualizar la sección "Estado que dejamos modificado en las cámaras" de `PENDIENTES.md`.

---

## Parte C — Trabajo sin cámaras (voy avanzando yo)

En orden de valor para la tesis:

### C.1 — Corredor de experimentos (Fase 5) — ✅ Hecho el 27/09

N repeticiones de cada función por protocolo y cámara, tasa de éxito, latencias p50/p95,
exportación a CSV y Markdown, con reconocimiento previo para no colgarse con una cámara
inalcanzable. Corrido contra el simulador y las cámaras reales (que en ese momento no
respondían desde esta red, y el corredor lo manejó bien: las detectó como "no alcanzable" en
segundos, no en minutos). **Falta correrlo contra hardware real** para tener los números que
van a la tesis — es la Sesión 5 de la Parte B.

```bash
cd backend && uv run python -m tools.experiments --repeticiones 30
```

### C.2 — Exportar la matriz a Markdown — ✅ Hecha el 29/09

Botón "Exportar Markdown" al lado de "Exportar CSV" en la pantalla Matriz. Usado para llenar
`docs/tesis/07-resultados.md` §7.9.

### C.3 — Pantalla de funciones comunes — ✅ Hecha el 29/09

Pestaña "Funciones" en el detalle de cámara: ISAPI y ONVIF lado a lado (hora con sincronización,
OSD/imagen/movimiento editables por ISAPI, reinicio por cualquiera de los dos), probada de punta a
punta contra el simulador. **Es la pantalla que mejor muestra la comparación** en una defensa.

### C.4 — Vincular grabaciones con eventos

Que al abrir un episodio se pueda ver el video de ese momento. Los dos datos ya existen (los
segmentos tienen hora, los episodios también); falta cruzarlos.

### C.5 — Deudas chicas

- `GET /api/events/{id}` (hoy el detalle se arma con el listado).
- Endpoint de estadísticas agregadas (hoy se calculan en el navegador sobre 300 episodios).
- Botón "Probar" en el editor de reglas.
- 4 advertencias de lint en la pantalla de eventos.

### C.6 — El documento de la tesis — 🟡 Arrancado el 28/09

Está en `docs/tesis/`, capítulo por capítulo. **6 de 9 capítulos con borrador completo** sin
depender de las cámaras (introducción, objetivos, marco teórico, estado del arte, metodología,
arquitectura), reusando el relevamiento y la bitácora como fuente. El de resultados está escrito
hasta donde da la evidencia actual, con las secciones de ONVIF y Scati marcadas como pendientes. El
de conclusiones es un esqueleto de preguntas guía: no se puede cerrar en serio hasta que el de
resultados lo esté. Ver `docs/tesis/README.md` para el estado exacto de cada uno.

---

## Parte D — Entregables académicos

Lo que hay que tener el día de la defensa:

1. **Matriz de compatibilidad exportada** (CSV y Markdown), con la columna "cómo se supo".
2. **Mediciones**: tasa de éxito y latencias por función y protocolo.
3. **La bitácora de hallazgos**: las rarezas verificadas, las dos APIs incompatibles dentro de la
   misma marca, y cómo se recuperaron los endpoints no documentados del domo.
4. **Video de la demo**, por si falla la red.
5. **Fixtures y tests**: la prueba de que todo lo afirmado se puede volver a correr.
6. **Guión de la defensa**, de 20 a 30 minutos.

---

## Riesgos y decisiones abiertas

| Riesgo | Qué hacemos |
|---|---|
| Se pierde el acceso al hardware | Ya está mitigado: simulador + fixtures + video. Lo validado queda validado. |
| ONVIF no se puede habilitar | Se documenta como resultado y la comparación se hace con lo que ONVIF **declara** contra lo que ISAPI **verifica**. Es un resultado más pobre pero honesto. |
| La analítica del domo nunca dispara | Ya es un hallazgo documentado. No bloquea la tesis. |
| La red de la oficina cambia | El protocolo de los primeros 10 minutos existe justamente por esto. |

---

## Bitácora de sesiones

Se completa al final de cada sesión con cámaras.

| Fecha | Sesión | Qué se hizo | Qué quedó cambiado en las cámaras |
|---|---|---|---|
| 18/09 | Reglas | Línea 1 de la PTZ escrita por API y cruzada físicamente | Línea 1 activa (150,500)→(850,500) |
| 23/09 | Analítica domo | Umbral bajado 800→600, calendario no se pudo activar | Umbral en 600 |
| 24/09 | Editor de reglas | Arrastre y guardado verificados; línea restaurada | Sin cambios netos |
| | | | |
