# Bitácora de integración con las APIs de las cámaras

Registro de lo que se fue encontrando al integrar cámaras Hikvision reales con la plataforma.
Todo lo que está acá se verificó contra el hardware; cuando algo viene solo del manual, se aclara.

Equipos usados:

| Cámara | Modelo | Firmware | Rol |
|---|---|---|---|
| PTZ | DS-2DF8A836IX-AEL (Speed Dome 8MP, serie Ultra) | V5.6.0 | Analítica clásica |
| Domo | iDS-2CD7146G2-IZS (DeepinView) | V5.9.24 | Analítica por app de IA |
| Bullet | iDS-2CD7A46G0/P-IZHSY (DeepinView) | V5.8.61 | Validada antes, por VPN |
| Value | DS-2CD1023G2-I | V5.8.4 | Caso sin analítica |

---

## 1. Método

La plataforma no confía en lo que declara el fabricante. Para cada función distingue entre:

- **Declarada**: la cámara dice soportarla en su respuesta de capacidades.
- **Verificada**: se llamó a la función y respondió como corresponde.

Cada operación queda registrada con protocolo, resultado, latencia y la respuesta cruda, y toda
escritura hace **respaldo → escritura → relectura → comparación**. Los apartados que siguen
explican por qué esa verificación no es una formalidad.

---

## 2. Hallazgo central: dos APIs incompatibles dentro de la misma marca

Las dos cámaras son Hikvision, las dos hablan ISAPI, y sin embargo exponen su analítica por
caminos que no tienen nada que ver entre sí.

| | PTZ (DS-2DF8A836IX-AEL) | Domo (iDS-2CD7146G2-IZS) |
|---|---|---|
| Recurso | `/ISAPI/Smart/<tipo>/<canal>` | `/ISAPI/Intelligent/AIOpenPlatform/AIRuleConfig/task/<tarea>/channels/<canal>` |
| Formato | XML | JSON |
| Coordenadas | enteros 0–1000 | decimales 0–1 |
| Origen del eje vertical | **abajo** a la izquierda | **arriba** a la izquierda |
| Qué detecta | cruce de línea, intrusión, entrada y salida de zona | lo que traiga el modelo instalado |
| Activación | un interruptor por **tipo** de regla | un interruptor por **regla** |
| Documentación | manual ISAPI PTZ Ultra | **no está en el manual DeepinView** |

En el domo, todos los indicadores de analítica clásica vienen en `false` y cada `/ISAPI/Smart/*`
responde "no soportado". Su analítica corre sobre **AI Open Platform**: una aplicación que se
instala en la cámara y define qué objetos detecta. El modelo cargado hoy se llama
`deteccion_armas` y reconoce: persona, cuchillo, arma, hacha y manos en alto.

Esto es más fuerte que la fragmentación entre marcas que planteaba el anteproyecto: aparece
**dentro del mismo fabricante y del mismo protocolo**. Una capa de abstracción no puede asumir
que "Hikvision" sea un solo adaptador.

### Cómo se obtuvieron las URLs del domo

Los endpoints de AI Open Platform **no figuran en el manual ISAPI de la serie DeepinView** (974
páginas, revisadas). Se obtuvieron descargando los 561 archivos JavaScript de la propia interfaz
web de la cámara y buscando las URLs que arma su código. Es un resultado en sí mismo: la
funcionalidad más valiosa del equipo no está documentada para integradores.

---

## 3. Rarezas verificadas contra el hardware

Cada una de estas obligó a cambiar el código, y ninguna está en el manual.

### 3.1 La cámara responde "200 OK" y no aplica nada

Escribir la lista completa de reglas (`PUT /ISAPI/Smart/LineDetection/1`) devuelve `200 OK` con
`statusString = OK`, y al releer, la geometría sigue igual. La escritura solo se aplica sobre el
recurso individual de cada regla (`…/lineItem/<id>`).

**Consecuencia**: sin relectura y comparación, la matriz de compatibilidad diría "soportada"
cuando en realidad no pasó nada.

### 3.2 Leer la colección devuelve datos falsos

`GET /ISAPI/Smart/LineDetection/1` informó las líneas 2 y 3 con coordenadas vacías
`(0,1000)-(0,1000)`, cuando en realidad existían:

| Regla | En la lista | En su recurso individual |
|---|---|---|
| Línea 2 | `(0,1000)-(0,1000)` | `(349,560)-(619,560)` |
| Línea 3 | `(0,1000)-(0,1000)` | `(491,4)-(497,997)` |

**Consecuencia**: hay que leer regla por regla. Un editor que confiara en la lista mostraría
reglas vacías y las pisaría al guardar.

### 3.3 El interruptor de cada regla se ignora

El campo `<enabled>` de cada línea vuelve siempre a `false`, aunque se escriba en `true`. Lo que
activa la analítica es el `<enabled>` del recurso global del tipo. Se detectó comparando el estado
completo de la cámara antes y después de activar la regla a mano desde su interfaz web: **el único
campo que cambió fue el `enabled` global**.

### 3.4 Cada cámara mide el eje vertical al revés que la otra

Verificado midiendo sobre capturas de la interfaz de cada cámara, no por interpretación del manual:

- **PTZ**: una regla guardada en `y=560` se ve al **43,7 %** desde arriba de la imagen → el eje
  vertical está invertido (la cámara cuenta desde abajo).
- **Domo**: una zona escrita en `y = 0,05–0,30` se ve **arriba** → cuenta desde arriba.

**Consecuencia**: la plataforma normaliza todo a 0–1 con origen arriba a la izquierda, y cada
driver traduce. Sin esta verificación, las reglas de una de las dos cámaras habrían quedado
espejadas verticalmente.

### 3.5 La hora la pone la cámara, y puede estar en otro huso

La PTZ reporta sus eventos en `+08:00` (huso de China). La plataforma normaliza a UTC al guardar.

---

## 4. Eventos

Las dos cámaras entregan eventos por `GET /ISAPI/Event/notification/alertStream`, un flujo
multipart que se mantiene abierto. Observaciones de las pruebas:

- **Latido**: cada ~10 s llega un `videoloss / inactive` aunque no pase nada. No es un evento: solo
  confirma que la cámara sigue viva.
- **Inundación**: mientras dura una detección, la cámara repite el aviso **una vez por segundo**.
  En una prueba real llegaron **145 avisos de movimiento en 2 minutos y medio**.
- **El cierre no trae el número de regla**: el aviso `active` del cruce de línea incluye el
  `regionID`, y el `inactive` que lo cierra no. Tomados literalmente, quedan 72 filas huérfanas.

Por eso la plataforma no guarda mensajes sino **episodios**: agrupa por cámara, tipo, canal y
regla, y cierra el episodio con el `inactive`, con 20 segundos de silencio o a los 10 minutos.
Medido contra las dos cámaras: **311 avisos quedaron en 12 episodios** (compresión de 25,9×).

También apareció un tipo de evento no documentado en la lista habitual: el domo emite
`soundclassificationdetection`, clasificación de sonido por IA.

---

## 5. Estado de la analítica del domo (24/09/2026)

La app de IA está instalada y el modelo cargado, pero **no emite alarmas**. Lo observado:

| Qué se revisó | Estado |
|---|---|
| Plataforma de IA | `AI_V4.0.0`, motores 1001–1004, canal 1 |
| Modelo cargado | `deteccion_armas`: persona, cuchillo, arma, hacha, manos en alto |
| Tarea de análisis de video | **No existe** (`{"Tasks": []}`, el máximo es 1) |
| Regla "Regla1" | Inaccesible: su recurso depende del id de la tarea |
| Disparador de la regla (`…/trigger`) | **Vacío** (`{}`) |
| Calendario de armado de la app | **Desactivado** (`enabled: false`), sin apps asignadas |
| Servidores HTTP de eventos | Sin configurar (`0.0.0.0`) |

### 5.1 La analítica no sobrevive a un reinicio

El 23/09 la tarea existía y corría (`status: 1`, motor 1001, 24×7). El 24/09, con
`deviceUpTime` de 69 minutos —es decir, después de un reinicio—, la lista de tareas quedó
**vacía**. El modelo sigue cargado en el motor, pero sin tarea no hay análisis.

**No se pudo recrear la tarea por API.** Se probaron seis formas del pedido a partir del
respaldo del día anterior:

| Pedido | Respuesta |
|---|---|
| `PUT /videoTask` con la lista completa | 404 `RequestUrlNotFound` |
| `POST /videoTask` con la lista completa | 404 `RequestUrlNotFound` |
| `PUT /videoTask/<taskID>` | 403 `notSupport` |
| `POST /videoTask` con la tarea suelta | 500 `deviceError` |
| `POST /videoTask` con lo mínimo | 500 `deviceError` |
| `POST /videoTask` sin `taskID` | 400 `badParameters` |

La diferencia entre `badParameters` y `deviceError` indica que la forma del pedido es
correcta —la cámara la entiende— y que falla al crear la tarea por su cuenta. Es un límite de
la API: **la plataforma puede leer y modificar la analítica, pero no levantarla.**

### 5.2 Los eventos de IA sí se pueden suscribir

`GET /ISAPI/Event/notification/subscribeEventCap` del domo lista cuatro tipos de IA:
`AIOpenPlatform`, `AIOP_Video`, `AIOP_Polling_Snap` y `HEOPCustomEvent`. Ninguno aparece en
`/ISAPI/Event/triggers`, que es donde se configuran los enlaces de la analítica clásica: el
enlace de estas reglas vive en su propio recurso `…/AIRuleConfig/task/<tarea>/channels/<ch>/trigger`.

Además, `videoTask/capabilities` declara `EventTrigger.notificationMethod` con
`"@def": "center"`, y "center" es el alertStream. O sea que, con la tarea corriendo, los
eventos de IA tienen que llegar por el mismo canal que el resto.

En una escucha de 100 s con gente en escena, el domo entregó movimiento (`VMD`, objetivo
`human`) y ningún evento de IA, como corresponde a no tener tarea.

## 6. La matriz: qué se puede afirmar y con qué prueba

El anteproyecto pide comparar qué da cada protocolo. Al construir la matriz apareció una
decisión de método que vale la pena dejar escrita, porque cambia lo que el trabajo puede
afirmar.

### 6.1 Tres estados, no dos

| Estado | Qué significa | De dónde sale |
|---|---|---|
| **Soportada** | Se llamó a la función y respondió | Una llamada real |
| **No soportada** | Se llamó y la cámara contestó que no la tiene | Un `403 notSupport` |
| **Sin verificar** | No se pudo comprobar | No se llamó, o falló por red o credenciales |

La tentación es tratar "sin verificar" como "no soportada". Sería un error: perder la red no
dice nada sobre la cámara.

### 6.2 Que no esté declarada no prueba que no exista

El documento `/ISAPI/System/capabilities` no es exhaustivo: hay funciones que responden
perfectamente sin estar anunciadas ahí. Por eso, cuando una marca no aparece, la matriz
anota **sin verificar**, no "no soportada". Solo una llamada que devuelva `notSupport`
prueba la ausencia.

Con ONVIF es distinto: `GetServices` sí es la lista completa de servicios, así que si la
cámara no publica el servicio *imaging*, por ONVIF no hay manera de ajustar la imagen. Ahí
la ausencia sí concluye.

### 6.3 Lo que no se prueba se dice

El reinicio no se llama automáticamente: corta el video varios minutos. Queda marcado como
**sin verificar**, con el motivo escrito en la evidencia. Declararlo "soportado" sin haberlo
llamado sería exactamente lo que este trabajo critica del material de los fabricantes.

### 6.4 Diferencias reales entre los dos protocolos

Al implementar las mismas seis funciones por ISAPI y por ONVIF aparecieron asimetrías que no
son de implementación sino de diseño de cada protocolo:

| Función | ISAPI | ONVIF |
|---|---|---|
| Hora | texto con el huso de la cámara | siempre UTC, desarmada en campos |
| Imagen | enteros 0–100 | rango propio por cámara, declarado en `GetOptions` |
| OSD | recurso `overlays` completo | opcional en Media2; muchas cámaras no lo exponen |
| Movimiento | recurso propio con sensibilidad | **no existe como función**: solo se ve como evento |
| Estado/salud | `/ISAPI/System/status` con CPU y memoria | no tiene equivalente |

La detección de movimiento es el caso más claro: por ISAPI se lee y se cambia; por ONVIF lo
único que se puede saber es si la cámara *publica* ese evento. Comparar esas dos cosas como
si fueran la misma función sería falsear el resultado, así que la matriz las distingue.

### 6.5 ONVIF verificado contra hardware real (29/09/2026)

Hasta esta fecha, ONVIF nunca había respondido nada distinto de "conexión rechazada": el
protocolo de integración venía desactivado de fábrica en las dos cámaras Hikvision. El 29/09 se
recuperó el acceso a la red y se probó habilitarlo por API, sin tocar la interfaz web:

```
GET /ISAPI/System/Network/Integrate
→ <ONVIF><enable>false</enable></ONVIF>
PUT /ISAPI/System/Network/Integrate  (con <enable>true</enable> dentro de <ONVIF>, sin tocar
    el resto del documento)
→ 200 OK, releído y confirmado: <ONVIF><enable>true</enable></ONVIF>
```

Funcionó al primer intento, sin necesidad de las nueve variantes que hicieron falta para otros
endpoints de este mismo fabricante. `GET /ISAPI/Security/ONVIF/users` devolvió una lista vacía,
confirmando que el usuario ONVIF es distinto del usuario web y hay que crearlo aparte
(`POST /ISAPI/Security/ONVIF/users`, con `userNameLen` 1–32 y `passwordLen` 1–16 según sus
propias capacidades). Con eso, la prueba de conexión de la plataforma dio **`status: online`
por los tres protocolos a la vez** — la primera vez en todo el proyecto.

**Un bug propio, encontrado por el hardware real y no por los tests.** `GetOSDs` de ONVIF
respondía `The requested configuration does not exist`, no un error de credenciales. La causa:
el driver le pasaba el token del *origen* de video (`VideoSourceConfiguration.SourceToken`,
correcto para `Imaging.GetImagingSettings`) donde `Media.GetOSDs` espera el token de la
*configuración* (`VideoSourceConfiguration.token`) — dos campos del mismo objeto, con nombres
parecidos y significados distintos. Corregido y reverificado contra la cámara real.

**Latencias medidas, no estimadas** (30 repeticiones por función, corredor de experimentos):

| Función | ISAPI p50 | ONVIF p50 | Quién gana |
|---|---|---|---|
| Información del dispositivo | 28,6 ms | 22,1 ms | ONVIF |
| Hora | 50,3 ms | 23,6 ms | ONVIF |
| Perfiles de video | 41,6 ms | 171,0 ms | ISAPI, por 4× |
| Ajustes de imagen | 31,5 ms | 149,8 ms | ISAPI, por 5× |
| OSD | 34,1 ms | 117,0 ms | ISAPI, por 3× |

No hay un ganador único: para identidad y hora, el pedido SOAP de ONVIF resultó más liviano que
el XML de ISAPI; para todo lo que exige negociar un perfil de video primero (imagen, OSD), el
costo de las llamadas encadenadas de ONVIF se nota en la latencia real, no solo en la teoría.

**Detección de movimiento por ONVIF: 0 % de éxito, 30 de 30 veces, con el mismo motivo exacto
las 30**: *"La cámara no publica eventos de movimiento por ONVIF"*. No es un fallo intermitente:
es la confirmación empírica, y no ya solo teórica, de que ONVIF no tiene esta función como
operación de lectura/escritura (§3.3 del marco teórico).

Queda pendiente: repetir esto mismo en el domo DeepinView, hoy inalcanzable desde la red (el
puerto 80 no responde ni siquiera a nivel TCP, aunque el equipo contesta ping intermitentemente).

### 6.6 Por qué nunca llegó una foto adjunta al evento (29/09/2026)

Se revisó directamente en la interfaz web de la PTZ, en *Evento → Evento inteligente →
Detección de traspaso de línea → Método enlace*, qué opciones de enlace existen para un evento
de cruce de línea:

| Opción | Qué hace | Estado en esta cámara |
|---|---|---|
| Enviar email | manda un correo | apagado |
| Notificar al software remoto | dispara el `alertStream` (esto es "center") | **activo** |
| Cargar en FTP/tarjeta de memoria/NAS | guarda una foto en un destino aparte | apagado |
| Seguimiento inteligente | mueve la PTZ hacia el objetivo | activo |

**No existe una opción para adjuntar la foto al mismo canal que ya escuchamos.** La única vía
de imagen que ofrece este modelo es "Cargar en FTP/tarjeta de memoria/NAS", un mecanismo de
entrega completamente distinto: la cámara sube el archivo a un servidor FTP (o lo guarda en su
tarjeta SD), no lo adjunta al aviso HTTP de "Notificar al software remoto".

Esto cambia el enfoque para lograr fotos en los eventos. No es, como se pensaba, activar un
casillero que faltaba prender: es que **esta cámara no puede adjuntar la imagen por el canal
que la plataforma usa**. El camino que sí es viable con lo que el equipo ofrece:

1. Levantar un servidor FTP simple dentro de la plataforma (o usar uno embebido), activar
   "Cargar en FTP" apuntando ahí, y correlacionar los archivos que lleguen con el episodio
   abierto por hora — más trabajo, y depende de un servicio nuevo.
2. **Alternativa más simple**: cuando el motor de eventos abre un episodio, la plataforma pide
   ella misma un snapshot (`GET /ISAPI/Streaming/channels/<canal>01/picture`, ya implementado y
   probado) en el momento. No es "la foto exacta del instante detectado por la cámara", pero es
   una foto real de la escena tomada en el momento del evento, sin depender de que el modelo
   soporte adjuntarla — y no exige levantar ningún servicio nuevo.

Queda pendiente repetir la revisión en el domo por si su modelo sí tiene la opción que a la PTZ le
falta.

**Decisión e implementación (29/09/2026): se eligió la alternativa 2.** Montar un servidor FTP
propio agrega una pieza de infraestructura nueva solo para resolver un caso de contorno; pedir un
snapshot propio reutiliza un endpoint que la plataforma ya tenía implementado y probado, y no
depende de que el modelo de cámara ofrezca una opción de enlace que al menos esta PTZ no tiene.

La regla quedó así: cuando `CameraListener` abre un episodio nuevo, si el aviso que lo abrió no
trajo ninguna foto en el propio `alertStream` (`episodio.pictures` vacío), la plataforma pide un
`GET /ISAPI/Streaming/channels/<canal>01/picture` antes de guardarlo (`_snapshot_on_open` en
`app/engine/event_hub.py`). Si la cámara ya mandó una foto adjunta —el diseño no asume que
*ninguna* cámara lo soporte, solo que al menos una no— no se pide nada de más. Si el snapshot
falla (cámara ocupada, sin respuesta), se registra el error y el episodio se guarda igual sin
foto: una foto que no se pudo tomar no puede tirar abajo el guardado del evento en sí.

Probado con 5 tests contra un servidor ISAPI simulado con `respx`
(`backend/tests/integration/test_event_hub_snapshot.py`), incluida una prueba de punta a punta que
verifica el archivo `.jpg` escrito en disco, no solo la fila en la base. Todavía no se probó
contra una cámara real (PTZ o domo) — es lo primero para confirmar la próxima vez que haya acceso
a la red.

### 6.7 El domo cambió de IP y de comportamiento (29/09/2026)

El domo volvió a estar accesible con una IP nueva (192.168.239.174, antes .101; mismo modelo,
mismo firmware `V5.9.24 build 260702`, encendido el 25/09 según su `bootTime`). Se repitió el
protocolo completo — grabado de respuestas, habilitación de ONVIF, corredor de experimentos — y
salió todo bien: **`status: online` por los tres protocolos**, igual que en la PTZ, con el mismo
patrón de latencias (ONVIF más rápido en identidad y hora, 2 a 4 veces más lento en perfiles e
imagen, 0 % de éxito en movimiento) confirmado ahora en **dos familias de cámara distintas**, no
solo en una.

**Un hallazgo que matiza el hallazgo central de este trabajo (§2).** Al grabar las respuestas de
este domo se encontró que **`/ISAPI/Smart/LineDetection/1` y el resto de la analítica clásica ya
no responden `403 notSupport`: responden `200 OK`**, con cuatro reglas reales (vacías, sin
configurar, pero genuinas — no un error). La comparación contra el historial de git de las
fixtures lo confirma sin ambigüedad: son archivos que **no existían antes** en el repositorio
para esta cámara, y `subscribeEventCap` ahora declara diez tipos de evento de analítica clásica
(`linedetection`, `fielddetection`, `parking`, `loitering`, etc.) que antes no aparecían.

No se quedó en la declaración: se probó escribir una regla de verdad
(`PUT …/LineDetection/1/lineItem/1` con coordenadas y sensibilidad nuevas) y, al releer,
**la geometría había cambiado de verdad** — no es un endpoint decorativo que responde 200 sin
aplicar nada, como sí ocurre en la PTZ (§3.1). El endpoint de AI Open Platform sigue intacto y sin
tarea de análisis (`{"Tasks": []}`, igual que el 24/09): no es que una API haya reemplazado a la
otra, es que **ahora responden las dos a la vez**.

La causa más probable es una actualización de firmware o un cambio de licencia/modo de VCA
aplicado en el reinicio del 25/09 — no se puede confirmar sin acceso al historial de
mantenimiento del equipo. Lo que sí se puede afirmar con evidencia es el resultado: **la
compatibilidad de una cámara no es una propiedad fija que se mide una vez**; el mismo equipo, sin
cambiar de firmware documentado ni de modelo, pasó de exponer una sola familia de analítica a
exponer dos. Es el argumento más fuerte a favor de que la plataforma verifique en vivo en lugar
de memorizar un resultado — el propio método de este trabajo, confirmado por su objeto de
estudio cambiando debajo de él mientras se lo medía.

**Consecuencia para el diseño de la plataforma**: el motor de reglas (`detect_backend`, capítulo
6 §6.7) hoy elige una sola familia por cámara y se queda con la primera que responde (AI Open
Platform, por ser más específica). Con este domo, eso significa que la interfaz de reglas sigue
mostrando "sin tarea de IA" y nunca ofrece la analítica clásica que ahora sí funciona. Queda
pendiente: que el motor pueda ofrecer ambas familias cuando las dos respondan, en vez de
comprometerse con la primera.

---

### 6.8 Tres verificaciones sueltas con las cámaras activas (29/09/2026)

Con las dos cámaras Hikvision alcanzables, se resolvieron tres pendientes menores que estaban
anotados en `PENDIENTES.md` desde hacía semanas.

**Qué clasificó el detector de sonido del domo.** El evento `soundclassificationdetection` (§4)
venía llegando desde el 18/09 sin que se revisara el payload. Se consultó la base: **27 eventos
capturados entre el 18/09 y hoy, y los 27 clasificados como `"gunfire"`** (disparo de arma de
fuego), en sesiones separadas y con intervalos irregulares (1 a 6 minutos entre uno y otro, no un
patrón de reloj fijo). No hay ningún indicio de disparos reales en la oficina donde está instalada
la cámara: es casi con certeza un falso positivo recurrente del modelo de audio sobre algún ruido
ambiente (compresor, puerta, tráfico). Queda documentado como límite conocido de esa función —
sirve como evidencia de que el canal de eventos de IA del domo sí entrega datos reales (algo que
§5 no había podido confirmar todavía para ningún tipo de evento de IA), aunque sea con una tasa de
falsos positivos alta para este detector en particular.

**El usuario `stmcam` del domo, aclarado.** Se sospechaba que el rechazo 401 por RTSP podía deberse
a un problema de permisos. Se confirmó por API (`GET /ISAPI/Security/users` y
`/ISAPI/Security/UserPermission`) que `stmcam` es un usuario real de nivel *Operator* (id 2, no un
usuario "solo RTSP" aparte) con `preview: true` tanto a nivel general como en el canal de video —
permisos suficientes para RTSP. El 401 es, entonces, casi con certeza una contraseña incorrecta o
desconocida, no una restricción de permisos. Sin la contraseña no se puede seguir sin involucrar al
usuario.

**Las dos cámaras tenían la hora en huso de China, y se corrigió — con una sorpresa.** Tanto la PTZ
como el domo traían `timeZone: CST-8:00:00` (documentado en el manual ISAPI como "UTC+8"), de
fábrica, sin relación con su ubicación real. Se corrigió en las dos, con el respaldo y relectura de
siempre:

- **PTZ** (modo `manual`): `PUT /ISAPI/System/time` con `timeZone: GMT+3:00:00` y la hora local
  actual → quedó en `2026-09-29T11:12:13-03:00`, correcto.
- **Domo** (modo `NTP`, sin tocar la hora en sí): el mismo valor `GMT+3:00:00` que funcionó en la
  PTZ dio, en el domo, `localTime` con offset `+03:00` — **al revés**, tres horas adelantado en vez
  de atrasado. Se probó el signo contrario, `GMT-3:00:00`, y ahí sí quedó correcto:
  `2026-09-29T11:12:11-03:00` (la cámara volvió a guardarlo internamente como `CST+3:00:00`, con
  otro signo todavía, pero el resultado final — lo único que importa — es el correcto).

**Es una rareza más para el catálogo del capítulo 7 (§7.3.4 ya documenta el eje Y invertido entre
las dos cámaras; esta es la misma familia de problema en otro campo)**: el mismo recurso ISAPI, con
el mismo nombre de campo y el mismo formato de cadena, documentado de la misma manera en el mismo
manual, requiere el signo *opuesto* en la PTZ (V5.6.0) y en el domo (V5.9.24) para llegar al mismo
resultado real. Ninguna interpretación literal de la cadena devuelta por la propia cámara alcanza
para saber si el resultado es correcto: la única prueba verificable es comparar el `localTime` que
devuelve contra la hora real, exactamente el mismo principio metodológico que sostiene el resto de
este capítulo.

---

### 6.9 Una tercera familia de analítica: el parking de la bullet (30/09/2026)

Apareció una tercera cámara real, la **iDS-2CD7A46G0/P-IZHSY** (firmware `V5.8.61 build 250901`,
en `192.168.1.11`). Es el modelo de parking que figuraba en la tabla de equipos como "validada por
VPN en un proyecto anterior" pero que nunca se había integrado acá. Trae **una familia de analítica
distinta de las dos ya documentadas**, y con ella la explicación estructural de por qué existen
esas familias.

**El recurso, y cómo se encuentra.** La geometría de las plazas vive en:

```
GET/PUT /ISAPI/Parking/channels/1/packingSpaceRecognition?format=json
```

Tres detalles que hacen que no se encuentre adivinando:

1. **`?format=json` es obligatorio.** Sin el parámetro, el mismo recurso responde
   `403 invalidOperation` — no "falta un parámetro", no "usá json": un error que sugiere que la
   operación no corresponde.
2. **La ruta distingue mayúsculas.** `packingSpaceRecognition` (p minúscula) funciona;
   `PackingSpaceRecognition` (P mayúscula) da `403 invalidOperation`. La propia cámara usa **las
   dos grafías en el mismo documento de capacidades**: en `/ISAPI/System/capabilities`, el enum
   `zoomFocusWebDisplay` lista `...,PackingSpaceRecognition,packingSpaceRecognition`, una al lado
   de la otra.
3. **El nombre tiene un error de tipeo del fabricante**: es "**Packing**" (embalaje), no "Parking",
   y está congelado en la superficie pública de la API — en la ruta, en el tipo de evento
   suscribible y en el modo de VCA. Dentro del payload hay un segundo error del mismo tipo:
   `absoulteParkingNum` en vez de `absolute`.

**Qué declara la cámara sobre sí misma.** Acá está el detalle fino, y conviene no exagerarlo:

| Dónde | Campo | Valor |
|---|---|---|
| `/ISAPI/Smart/capabilities` | `isSupportParking` | **false** |
| `/ISAPI/System/capabilities` | `isSupportParking` | **false** |
| `/ISAPI/System/capabilities` | `isSupportParkingState` | **true** |

No es que la cámara mienta: son **dos funciones distintas que comparten la palabra "parking"**.
`isSupportParking` se refiere a la regla clásica de estacionamiento indebido
(`/ISAPI/Smart/parking/*`), que este equipo efectivamente no soporta. El reconocimiento de plazas
se declara en otro campo, `isSupportParkingState`, en otro documento, y apunta a otro árbol de
endpoints. **El resultado práctico es el mismo que si mintiera**: un integrador que busque
"parking" en el documento de capacidades que corresponde a la analítica encuentra primero el
`false`, y concluye lo contrario de lo que el equipo hace. Los dos campos se diferencian en cinco
letras.

**La explicación estructural: los modos de VCA son excluyentes.** Esto es lo más importante de la
sesión. La cámara declara:

```
GET /ISAPI/System/Video/inputs/channels/1/VCAResource/capabilities
    → type opt="roadDetection,smart,PackingSpaceRecognition,close"
GET /ISAPI/System/Video/inputs/channels/1/VCAResource
    → type = PackingSpaceRecognition
```

Es decir: **el equipo puede ser una sola clase de cámara analítica por vez**. Cruzado con las
fixtures grabadas de la PTZ (`vcaResource.xml` → `type = smart`), el patrón cierra:

| Cámara | Modo de VCA | Analítica que responde | La que no |
|---|---|---|---|
| PTZ DS-2DF8A836IX-AEL | `smart` | `/ISAPI/Smart/*` (clásica) | parking |
| Bullet iDS-2CD7A46G0/P | `PackingSpaceRecognition` | `/ISAPI/Parking/*` | `/ISAPI/Smart/*` → `notSupport` |

Esto reencuadra todo lo que veníamos llamando "fragmentación entre modelos". No son solo APIs
distintas por producto: **un mismo equipo cambia su superficie de API completa según un modo de
configuración**. Un árbol de endpoints aparece y otro desaparece. Y da una hipótesis mucho mejor
fundada para el hallazgo del domo (§6.7, §7.2.1): si en el reinicio del 25/09 cambió su modo de
VCA, eso explicaría por qué `/ISAPI/Smart/*` empezó a responder de un día para el otro. **Queda
por confirmar leyendo el `VCAResource` del domo** la próxima vez que esté accesible — no se pudo
hacer en esta sesión porque su contraseña vive cifrada en la base y Postgres estaba caído.

**Escritura verificada.** Se aplicó la disciplina de siempre sobre la plaza 001: respaldo del
payload completo, mover un punto (`positionX 0.311 → 0.331`), releer, comparar, restaurar,
verificar. La cámara **aplicó el cambio de verdad** y quedó restaurada exactamente como estaba.
No es un endpoint decorativo de los que responden 200 sin hacer nada, como sí hace la PTZ con la
colección de reglas (§3.1).

**El resto de lo que se verificó**, sin tocar nada:

- 14 plazas configuradas, máximo 40 (`/ISAPI/Parking/channels/1/parkingStatus/capabilities`).
- Estado en vivo por plaza en `/ISAPI/Parking/channels/1/parkingStatus`: ocupada o libre, número
  de vehículo y tiempo estacionado. Curiosidad: el elemento raíz se llama `ParkingStatusCap` aunque
  devuelva estado en vivo, no capacidades.
- Geometría: polígonos de **exactamente 4 puntos** (`Region.maxSize: 4`), coordenadas decimales
  0–1 — la misma convención que AI Open Platform, no la de la analítica clásica (enteros 0–1000).
- El OSD de la cámara quema los contadores en el video: `totalNumber: 14`,
  `availableNumber: 14`, `occupiedNumber: 0`. La analítica está corriendo de verdad (la cámara
  está apuntando a una pared de oficina, así que no hay autos que contar).
- `subscribeEventCap` declara el evento `PackingSpaceRecognition`, así que el estado de las plazas
  debería poder llegar por el `alertStream` que la plataforma ya sabe escuchar.
- **ONVIF ya venía activado**, con usuario `admin` de tipo administrador — a diferencia de la PTZ
  y el domo, que lo traían apagado de fábrica y hubo que habilitarlo (§6.5). Puede ser de fábrica
  o haber quedado así de la validación por VPN del proyecto anterior: no se puede distinguir, y
  conviene decirlo así en vez de afirmar cuál de las dos. **Pero no funciona**: la prueba de
  conexión da `Fault('Unknown fault occured')`, así que este equipo queda `degraded` (ISAPI y RTSP
  en verde, ONVIF en rojo). Es el tercer comportamiento distinto de ONVIF en tres cámaras de la
  misma marca: dos apagadas de fábrica que se habilitaron sin problema, y una encendida que falla.
  Queda pendiente entender si es el usuario ONVIF o una diferencia de autenticación (la cámara
  declara `certificateType: digest`).

**Integrado en la plataforma el mismo día.** Se sumó un driver de la familia
(`app/drivers/isapi/rules/parking.py`) y la detección automática la reconoce sin configuración: al
abrir la pestaña de Reglas de esta cámara aparece "ISAPI Parking", las 14 plazas con su ocupación
en vivo, y **cada plaza se puede arrastrar sobre el snapshot** igual que las líneas de la PTZ. La
escritura pasa por el mismo camino de respaldo → escribir → releer → verificar que el resto.

**Una validación del equipo que conviene conocer**: al mover una plaza encima de otra, la cámara
rechaza la escritura con `403` y `subStatusCode: parkingAreaOverlap`. Eso destapó un error propio
de la plataforma: todo `403` se estaba traduciendo a "fallo de autenticación", lo que mandaba a
revisar la contraseña cuando el problema era el contenido del pedido. Ahora un `403` con
`subStatusCode` propio se reporta como rechazo del equipo (`RejectedByCamera`), y solo un `401`
—o un `403` sin ningún detalle— se toma como problema de credenciales.

---

## 7. Qué implica para la plataforma

1. **Un adaptador por familia, no por marca.** La misma marca necesitó dos traductores distintos.
2. **Toda escritura se verifica releyendo**, porque la cámara puede responder "OK" sin aplicar.
3. **Las lecturas de colecciones no son confiables**: hay que ir al recurso individual.
4. **La matriz necesita una columna de "cómo se supo"**: declarado por la cámara o verificado con
   una llamada real.
5. **Los eventos se agrupan en episodios** antes de guardarlos.
6. **Todo se normaliza**: coordenadas a 0–1 con origen arriba a la izquierda, horas a UTC y tipos
   de evento a un vocabulario común.

---

## 8. Anexo: endpoints usados

### Comunes
- `GET /ISAPI/System/deviceInfo` — identidad del equipo
- `GET /ISAPI/System/capabilities` — capacidades declaradas
- `GET /ISAPI/Streaming/channels` — perfiles de video
- `GET /ISAPI/Streaming/channels/<canal>01/picture` — snapshot
- `GET /ISAPI/Event/notification/alertStream` — flujo de eventos
- `GET /ISAPI/Event/notification/subscribeEventCap` — qué eventos se pueden suscribir

### Analítica clásica (PTZ)
- `GET/PUT /ISAPI/Smart/{LineDetection,FieldDetection,regionEntrance,regionExiting}/<canal>`
- `GET/PUT …/<canal>/lineItem/<id>` y `…/<canal>/regions/<id>` — **la escritura va acá**
- `GET …/<canal>/capabilities` — máximos, objetivos y direcciones permitidas
- `GET/PUT /ISAPI/Event/triggers/<evento>-<canal>` — a dónde se avisa
- `GET/PUT /ISAPI/System/Video/inputs/channels/<canal>/VCAResource` — modo de analítica activo
- `GET /ISAPI/Smart/IntelliTrace/<canal>` — seguimiento automático

### AI Open Platform (domo)
- `GET /ISAPI/Intelligent/AIOpenPlatform?format=json` — plataforma, versión y motores
- `GET …/capabilities?format=json` — qué permite la plataforma
- `GET …/videoTask?format=json` — tareas de análisis en curso
- `GET/PUT …/AIRuleConfig/task/<tarea>/channels/<canal>?format=json` — **las reglas**
- `GET …/AIRuleConfig/channels/<canal>/capabilities?format=json` — límites y nombres de reglas
- `GET/PUT …/AIRuleConfig/task/<tarea>/channels/<canal>/trigger?format=json` — método de enlace
- `GET …/algorithmModel/engines?format=json` — modelo cargado y sus etiquetas
- `GET …/algorithmModel/management?format=json` — modelos instalados
- `GET/PUT /ISAPI/Custom/OpenPlatform/App/appScheduleSwitch?format=json` — calendario de armado

Las respuestas crudas de todos estos endpoints están guardadas como archivos de prueba en
`backend/tests/fixtures/hikvision/<modelo>/<firmware>/`, y se usan en los tests automáticos.
