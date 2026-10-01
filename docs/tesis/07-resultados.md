# 7. Resultados

> **Estado de este capítulo al 30/09/2026**: completo para ISAPI, ONVIF y RTSP en las **tres**
> cámaras Hikvision integradas (PTZ, domo y bullet de parking). El 29/09, el domo —que había
> cambiado de dirección IP tras un reinicio— empezó a responder también a la analítica clásica
> `/ISAPI/Smart/*`, que hasta entonces daba `403 notSupport`; el 30/09 se integró la bullet de
> parking, que expone una **tercera** familia de analítica y aporta la explicación estructural de
> por qué existen estas familias (§7.2.2). La cámara Scati sigue pendiente de acceso (§7.8).

## 7.1 Equipos utilizados

| Cámara | Modelo | Firmware | Rol en el trabajo |
|---|---|---|---|
| PTZ | DS-2DF8A836IX-AEL (Speed Dome 8MP, serie Ultra) | V5.6.0 | Caso fuerte de analítica clásica dibujable |
| Domo | iDS-2CD7146G2-IZS (DeepinView) | V5.9.24 | Caso de plataforma de IA abierta (AI Open Platform); desde el 29/09 responde también a la API clásica (§7.2.1) |
| Bullet | iDS-2CD7A46G0/P-IZHSY (DeepinView) | V5.8.61 | Tercera familia de analítica: reconocimiento de plazas de parking (§7.2.2) |
| Value | DS-2CD1023G2-I | V5.8.4 | Caso sin analítica, contraste |
| Scati | *(modelo a completar)* | — | Marca distinta a Hikvision; **pendiente de integración**, ver §7.7 |

## 7.2 Hallazgo central: tres APIs de analítica incompatibles dentro de la misma marca

Las tres cámaras Hikvision integradas en este trabajo hablan el mismo protocolo de transporte
(ISAPI) y, sin embargo, exponen su analítica por caminos que no tienen nada en común entre sí:

| | PTZ (DS-2DF8A836IX-AEL) | Domo (iDS-2CD7146G2-IZS) | Bullet (iDS-2CD7A46G0/P) |
|---|---|---|---|
| Recurso | `/ISAPI/Smart/<tipo>/<canal>` | `/ISAPI/Intelligent/AIOpenPlatform/AIRuleConfig/task/<tarea>/channels/<canal>` | `/ISAPI/Parking/channels/<canal>/packingSpaceRecognition` |
| Formato | XML | JSON | JSON, y `?format=json` es **obligatorio** |
| Coordenadas | enteros 0–1000 | decimales 0–1 | decimales 0–1 |
| Origen del eje vertical | abajo a la izquierda | arriba a la izquierda | arriba a la izquierda |
| Geometría | línea de 2 puntos o polígono | según el modelo de IA | polígono de **exactamente 4 puntos** |
| Qué detecta | cruce de línea, intrusión, entrada y salida de zona | lo que traiga el modelo de IA instalado | ocupación de plazas de estacionamiento |
| Activación | un interruptor por **tipo** de regla | un interruptor por **regla individual** | un interruptor **global** de la función |
| Documentación | en el manual ISAPI de la serie PTZ Ultra | **no figura en el manual DeepinView** | **tampoco figura**: el manual nombra la función pero no su API (ver abajo) |

En el domo, todos los indicadores de analítica clásica declaran `false` y cada endpoint de
`/ISAPI/Smart/*` responde explícitamente que no está soportado. Su analítica corre sobre AI Open
Platform, una plataforma de inferencia que aloja modelos cargables — el modelo presente durante
este trabajo reconoce persona, cuchillo, arma, hacha y manos en alto. En la bullet ocurre lo
simétrico: la analítica clásica responde `notSupport` y toda su funcionalidad vive en un tercer
árbol de endpoints, `/ISAPI/Parking/*`, que no comparte formato, convención de coordenadas ni
modelo de activación con ninguno de los otros dos.

Este hallazgo es más severo que la fragmentación *entre* marcas que motivó originalmente el
trabajo (§1.3): aparece **dentro del mismo fabricante y del mismo protocolo de transporte**. Tiene
una consecuencia directa sobre el diseño de cualquier capa de abstracción para este dominio: no es
válido asumir que "ser Hikvision" define un único comportamiento de API (desarrollado en detalle en
§6.7).

Un hallazgo secundario, relevante para evaluar el estado de la documentación pública disponible
para integradores: los endpoints de AI Open Platform no figuran en el manual oficial de la serie
DeepinView (974 páginas revisadas). Se recuperaron descargando y analizando los 561 archivos
JavaScript de la propia interfaz web de administración de la cámara y localizando las URLs que su
código arma dinámicamente — la funcionalidad de mayor valor del equipo no está documentada para
quien no tiene acceso al código fuente de su interfaz.

**El mismo patrón se repite, y se puede cuantificar, en la tercera familia.** El manual ISAPI de
la serie DeepinView —el que corresponde a la bullet de parking— se procesó completo a texto
(31.685 líneas). El resultado:

- `/ISAPI/Parking`: **cero apariciones**. El árbol de endpoints que configura la función central
  del modelo no está documentado en ninguna parte del manual de su propia serie.
- `packingSpaceRecognition` / `PackingSpaceRecognition`: **cuatro apariciones**, todas como
  *valor dentro de un enum* — en la lista de tipos de imagen buscables, en la de modos de análisis
  de video y en la de páginas que la interfaz web sabe mostrar. El manual reconoce que la función
  existe; no dice cómo se la configura.

La distinción importa para el argumento: no es que el fabricante oculte la función, es que
**documenta su nombre y no su interfaz**. Un integrador que lea el manual completo sabe que el
equipo hace reconocimiento de plazas y sigue sin poder programarlo. En este trabajo los endpoints
se recuperaron de un desarrollo propio anterior, validado contra este mismo modelo; sin esa
fuente, el camino habría sido el mismo que con AI Open Platform: leer el código de la interfaz web
del equipo.

Un detalle adicional del mismo manual refuerza §7.2.2: el enum de modos de análisis de video
documentado para la serie lista alrededor de ochenta valores posibles, mientras que la cámara
física declara solo cuatro (`roadDetection`, `smart`, `PackingSpaceRecognition`, `close`). Es
decir, **el manual describe el superconjunto de la familia y cada equipo expone su propio
subconjunto**, que solo se conoce preguntándole al equipo.

### 7.2.1 Actualización (29/09): el mismo domo empezó a responder también a la API clásica

Hasta el 24/09, todo endpoint de `/ISAPI/Smart/*` en el domo respondía explícitamente que la
función no estaba soportada (`403 notSupport`), lo que sostenía la lectura de la tabla anterior:
domo y PTZ como dos caminos mutuamente excluyentes. El 29/09, después de que el equipo cambiara de
dirección IP tras un reinicio (probablemente asociado a una actualización de firmware o de
configuración fuera del control de este trabajo), el mismo domo empezó a declarar y a aceptar
escrituras reales sobre `/ISAPI/Smart/LineDetection`, `FieldDetection`, `regionEntrance` y
`regionExiting` — la misma familia de endpoints que hasta ese momento solo respondía la PTZ.

Esto se verificó de dos maneras independientes, no solo por la respuesta HTTP:

1. **Por historial de control de versiones**: las fixtures grabadas contra el domo el 29/09
   contienen archivos que no existían en ningún commit anterior del repositorio (`git diff`/`git
   show` sobre el historial confirma que `smartLineDetection.xml` y equivalentes son nuevos, no un
   artefacto de sanitización), y `subscribeEventCap.xml` pasó a declarar diez tipos de evento
   nuevos que antes no figuraban.
2. **Por una prueba de escritura real**: se escribió una regla de línea con coordenadas de prueba,
   se releyó el recurso y la geometría devuelta coincidió con lo escrito — el mismo criterio de
   "escritura verificada, no solo código 200" que exige §7.3.1 para la PTZ. La regla se dejó
   deshabilitada a propósito, como evidencia sin generar alarmas.

Del lado de AI Open Platform, el domo no cambió: la tarea de análisis de video sigue vacía
(`{"Tasks": []}`, §7.7).

**Qué le hace esto al hallazgo de §7.2.** No lo invalida: en el momento en que se hizo la
integración inicial de ambas cámaras (fases 1 a 4 de este trabajo), la incompatibilidad entre PTZ
y domo era real, verificada y reproducible, y toda la analítica dibujable de este trabajo se
construyó contra esa realidad. Lo que corresponde es una lectura más precisa: **la fragmentación
de API dentro de una misma marca no es necesariamente una propiedad fija del modelo de cámara,
sino que puede depender del estado de firmware o configuración en un momento dado** — un dato que,
lejos de debilitar la motivación de este trabajo, la refuerza: si ni siquiera dos observaciones del
mismo equipo garantizan la misma superficie de API, una plataforma de integración no puede asumir
capacidades por modelo o por fabricante; tiene que seguir verificando contra el dispositivo real en
cada momento, que es exactamente el principio metodológico que sostiene este trabajo desde el
capítulo 5.

Queda como trabajo pendiente, no resuelto en esta versión: el motor de reglas de la plataforma hoy
elige una sola familia de analítica por cámara (prioriza AI Open Platform por ser más específica) y
no ofrece la familia clásica como alternativa cuando ambas responden en el mismo equipo.

### 7.2.2 Por qué existen estas familias: los modos de VCA son mutuamente excluyentes

La integración de la tercera cámara (30/09) aportó, además de una tercera familia de analítica, la
explicación estructural de todo el fenómeno descrito en §7.2 — que hasta ese momento este trabajo
solo podía constatar, no explicar.

Las cámaras declaran un **modo de recurso de análisis de video (VCA)**, y ese modo determina qué
familia de analítica responde:

```
GET /ISAPI/System/Video/inputs/channels/<canal>/VCAResource/capabilities
    → type opt="roadDetection,smart,PackingSpaceRecognition,close"
```

Los cuatro valores son **excluyentes entre sí**: la cámara puede ser una sola clase de cámara
analítica por vez. Contrastando el modo declarado por cada equipo con la familia que efectivamente
responde:

| Cámara | Modo de VCA | Familia que responde | Familia que rechaza |
|---|---|---|---|
| PTZ DS-2DF8A836IX-AEL | `smart` | `/ISAPI/Smart/*` | parking |
| Bullet iDS-2CD7A46G0/P | `PackingSpaceRecognition` | `/ISAPI/Parking/*` | `/ISAPI/Smart/*` → `notSupport` |

La correspondencia es exacta, y reencuadra el hallazgo central. Lo que en §7.2 se describió como
"modelos distintos con APIs distintas" es, en el nivel de abajo, algo más incómodo para cualquier
capa de abstracción: **un mismo equipo cambia su superficie de API completa según un parámetro de
configuración**. Un árbol de endpoints entero aparece mientras otro desaparece, sin que cambie el
modelo, el firmware ni el protocolo de transporte.

Esto tiene dos consecuencias para la tesis. La primera es metodológica: refuerza, con un mecanismo
concreto y verificable, por qué una matriz de compatibilidad no puede construirse a partir del
modelo del equipo. La segunda es que **ofrece una hipótesis fundada para el hallazgo de §7.2.1**:
si en el reinicio del 25/09 el domo cambió de modo de VCA, eso explicaría por qué
`/ISAPI/Smart/*` empezó a responder de un día para el otro en un equipo que antes lo rechazaba.
Esa hipótesis **queda sin confirmar** en esta versión del trabajo: requiere leer el `VCAResource`
del domo, lo que no fue posible en la sesión del 30/09 por una caída de la base de datos que
guarda sus credenciales. Es la primera verificación pendiente para la próxima sesión con hardware,
y se la señala explícitamente en vez de presentar la hipótesis como resultado.

## 7.3 Rarezas verificadas contra el hardware real

Los siguientes comportamientos se verificaron empíricamente, no figuran en ningún manual y
obligaron a modificar el diseño del sistema.

### 7.3.1 La cámara responde éxito y no aplica el cambio

Escribir la colección completa de reglas de una cámara (`PUT /ISAPI/Smart/LineDetection/1`)
devuelve HTTP 200 con `statusString = OK`, y al releer el recurso la geometría permanece sin
cambios. La escritura solo se aplica cuando se dirige al recurso individual de cada regla
(`…/lineItem/<id>`). **Sin una relectura y comparación posteriores, un sistema que confiara en el
código de respuesta reportaría esta función como soportada cuando en realidad ninguna escritura se
aplicó.**

### 7.3.2 Leer la colección devuelve datos falsos

`GET /ISAPI/Smart/LineDetection/1` reportó dos reglas existentes con coordenadas vacías
`(0,1000)-(0,1000)`:

| Regla | Reportado por la colección | Valor real (leído del recurso individual) |
|---|---|---|
| Línea 2 | `(0,1000)-(0,1000)` | `(349,560)-(619,560)` |
| Línea 3 | `(0,1000)-(0,1000)` | `(491,4)-(497,997)` |

Un editor que confiara en la respuesta de la colección mostraría reglas vacías y las sobrescribiría
al guardar, borrando configuración existente sin que el usuario lo advierta.

### 7.3.3 El interruptor de cada regla individual se ignora

El campo que activa o desactiva una regla individual (`<enabled>`) vuelve siempre a `false`, sin
importar qué valor se escriba. Lo que efectivamente activa la analítica es el `<enabled>` del
recurso global del tipo de regla. Esto se detectó comparando el estado completo de la cámara antes
y después de activar una regla a mano desde su interfaz web: el único campo que cambió entre ambas
capturas fue el `enabled` del recurso de tipo, no el de la regla individual.

### 7.3.4 Cada cámara mide el eje vertical al revés que la otra

Verificado midiendo directamente sobre capturas de la interfaz de cada cámara, no por
interpretación del manual: en la PTZ, una regla guardada con `y=560` se observa al 43,7 % de la
altura de la imagen desde arriba — el eje vertical de esa cámara cuenta desde abajo. En el domo,
una zona escrita con `y` entre 0,05 y 0,30 se observa efectivamente en la parte superior de la
imagen — ese eje cuenta desde arriba. La plataforma normaliza ambos casos a un sistema común
(0 a 1, origen arriba a la izquierda) y cada adaptador traduce en ambos sentidos.

### 7.3.5 La hora la define la cámara, y puede estar en otro huso

Las dos cámaras Hikvision reportaban la marca de tiempo de sus eventos en huso +08:00 (hora de
China), de fábrica, aun cuando su ubicación física es otra. La plataforma normaliza toda marca de
tiempo a UTC en el momento de persistirla, por lo que esto nunca afectó ningún resultado funcional
del trabajo — pero se corrigió igual en las dos cámaras el 29/09 (§7.3.6 explica por qué no fue
trivial).

### 7.3.6 El mismo campo de zona horaria necesita el signo opuesto en cada cámara

Al corregir la zona horaria de fábrica (§7.3.5), el mismo procedimiento documentado en el manual
ISAPI —`PUT /ISAPI/System/time` con un campo `timeZone` en formato `<nombre><signo><horas>:00:00`—
dio resultados opuestos en las dos cámaras. El manual explica que `CST-8:00:00` representa UTC+8
("-8:00:00 es la hora UTC local"), lo que implica la fórmula `UTC = hora_local + desplazamiento`.
Aplicando esa fórmula para Buenos Aires (UTC-3), el valor esperado era `GMT+3:00:00`.

Ese valor, escrito en la PTZ, dio el resultado correcto de inmediato: `localTime` pasó a mostrar el
offset `-03:00` verificado contra la hora real del sistema. El mismo valor exacto, escrito en el
domo, dio un resultado incorrecto: `localTime` quedó con offset `+03:00` — tres horas adelantado en
vez de atrasado. Fue necesario escribir el signo contrario, `GMT-3:00:00`, para que el domo llegara
al resultado correcto (que la propia cámara volvió a guardar internamente con un tercer signo
distinto, `CST+3:00:00`, sin que eso afectara el resultado real).

Es la misma familia de hallazgo que el eje vertical invertido de §7.3.4: un campo con el mismo
nombre, el mismo formato de cadena y la misma documentación oficial, implementado con una
convención de signo distinta entre dos cámaras del mismo fabricante. Refuerza la misma conclusión
metodológica: la cadena que devuelve la cámara no alcanza como prueba de que la configuración es
correcta; sólo la comparación contra un dato externo verificable —en este caso, la hora real del
sistema, en la línea de cruce el propio video de la cámara (§7.3.4)— permite confirmarlo.

### 7.3.7 Dos capacidades que se diferencian en cinco letras y significan cosas opuestas

La cámara de parking (§7.2.2) produjo el caso que mejor ilustra, sobre un solo equipo, el problema
que motiva el mecanismo de capacidades declaradas contra verificadas de este trabajo (§3.5).

Consultando qué declara el equipo sobre su propia capacidad de parking se obtiene:

| Documento | Campo | Valor |
|---|---|---|
| `/ISAPI/Smart/capabilities` | `isSupportParking` | **false** |
| `/ISAPI/System/capabilities` | `isSupportParking` | **false** |
| `/ISAPI/System/capabilities` | `isSupportParkingState` | **true** |

Corresponde ser preciso: **la cámara no miente**. Son dos funciones distintas que comparten una
palabra. `isSupportParking` se refiere a la regla clásica de estacionamiento indebido
(`/ISAPI/Smart/parking/*`), que este equipo efectivamente no soporta; el reconocimiento de plazas
—que es la función central del modelo, que estaba activa y que se verificó escribiendo y releyendo
geometría real— se declara en `isSupportParkingState`, en otro documento y apuntando a otro árbol
de endpoints.

El resultado práctico, sin embargo, es indistinguible de una declaración falsa: un integrador que
busque la palabra "parking" en el documento de capacidades que corresponde a la analítica encuentra
primero un `false`, y concluye lo contrario de lo que el equipo hace. **Los dos campos se
diferencian en cinco letras.** Este trabajo sostiene que el caso es más instructivo que una
declaración simplemente errónea: muestra que el problema de confiar en lo declarado no se resuelve
con fabricantes más honestos, porque acá no hay deshonestidad — hay un espacio de nombres
ambiguo, y ninguna cantidad de buena fe del fabricante protege a un integrador de leer el campo
correcto con el significado equivocado.

Tres detalles menores del mismo recurso refuerzan la conclusión, y se documentan porque cada uno
costó tiempo de integración real:

1. **La ruta distingue mayúsculas de minúsculas.** `packingSpaceRecognition` responde;
   `PackingSpaceRecognition` devuelve `403 invalidOperation`. La propia cámara usa las dos grafías
   **en el mismo documento de capacidades**, una al lado de la otra, dentro del enum
   `zoomFocusWebDisplay`.
2. **`?format=json` no es opcional.** Sin ese parámetro el recurso responde `403 invalidOperation`
   — un error que sugiere que la operación no corresponde, no que falte un parámetro. Un
   integrador razonable concluye que el endpoint no existe.
3. **Dos errores de tipeo congelados en la API pública**: la función se llama "**Packing**"
   (embalaje) en vez de "Parking" en la ruta, en el tipo de evento y en el modo de VCA; y dentro
   del payload, el identificador de cada plaza es `absoulteParkingNum` en vez de `absolute`.
   Ninguno se puede corregir del lado del cliente: hay que reproducirlos exactamente.

### 7.3.8 Tres luces verdes y el usuario no ve nada: el códec

La bullet de parking produjo el caso más claro de toda esta sección, porque el fallo ocurre
*después* de que todas las comprobaciones del sistema dieron bien.

Al abrir el video en vivo de esa cámara, el reproductor del navegador quedaba en negro. El estado
del sistema en ese momento era:

| Comprobación | Resultado |
|---|---|
| Prueba de conexión RTSP (`DESCRIBE`) de la plataforma | ✅ responde |
| Ruta publicada en el servidor de medios | ✅ creada |
| Estado de esa ruta (`ready`) | ✅ sí, recibiendo video |
| Pistas detectadas | **H265, G711** |
| Lo que ve el usuario | **nada** |

El motivo es la última fila: la cámara entrega **H.265 (HEVC)**, que los navegadores no
decodifican ni por WebRTC ni por HLS fuera de Safari. El video llegaba perfectamente hasta el
servidor de medios —de ahí el `ready`— y moría en el último salto.

Lo que vuelve al caso interesante para este trabajo es que **la cámara sí tenía streams
reproducibles**: de sus cinco perfiles, dos (el principal y el secundario) son H.265 y tres son
H.264. La plataforma no los ofrecía porque, como la mayoría de las herramientas del rubro, asumía
que un equipo tiene "principal" y "secundario" y que con eso alcanza. La información necesaria
para resolverlo ya estaba leída y guardada en la propia matriz de perfiles; simplemente no se la
estaba usando para decidir.

La corrección fue hacer que la plataforma elija el stream por códec y no por posición: si el
pedido no es reproducible, busca otro de la misma cámara que sí lo sea, y **dice por qué lo
cambió** en vez de dejar al usuario frente a un reproductor negro. Si ninguno sirve, lo informa y
sugiere un reproductor externo, porque el video existe aunque el navegador no pueda mostrarlo.

El valor metodológico del caso es que extiende la tesis central de este capítulo a una capa nueva.
Hasta acá, "declarado contra verificado" (§3.5) se aplicaba a si una función existe. Este caso
muestra que **una función puede estar verificada en todos los niveles que el sistema sabe medir y
seguir sin servir para nada en el nivel que le importa al usuario**: el protocolo responde, el
transporte funciona, el servidor recibe los datos, y el resultado sigue siendo una pantalla negra.
Una matriz de compatibilidad honesta tiene que poder distinguir "la cámara entrega video" de "el
usuario puede verlo", que no son la misma afirmación.

## 7.4 ONVIF: verificado contra hardware real

Hasta el 29/09/2026, ONVIF nunca había respondido nada distinto de un rechazo de conexión: el
protocolo de integración venía desactivado de fábrica en ambas cámaras Hikvision, y así lo
confirmó la propia cámara con un mensaje explícito al intentar acceder al servicio SOAP sin
haberlo activado: *"Request Refuse: ONVIF integrate function is disabled"*.

Se probó habilitarlo por API, sin intervención manual en la interfaz web, y funcionó al primer
intento:

```
GET /ISAPI/System/Network/Integrate       → confirma <ONVIF><enable>false</enable></ONVIF>
PUT /ISAPI/System/Network/Integrate       → se activa, preservando el resto del documento
                                             (CGI e ISAPI quedan como estaban)
GET /ISAPI/Security/ONVIF/users           → lista vacía: no existe un usuario ONVIF
POST /ISAPI/Security/ONVIF/users          → se crea un usuario dedicado, distinto del usuario
                                             web, con los límites que declaran las propias
                                             capacidades de la cámara (nombre 1–32 caracteres,
                                             contraseña 1–16)
```

Con el servicio activo y el usuario cargado, la prueba de conexión de la plataforma dio
**`status: online` por los tres protocolos a la vez** — la primera vez en todo el desarrollo de
este trabajo. La detección de capacidades completa dejó **8 de las 11 funciones del catálogo
comparadas entre ISAPI y ONVIF sobre la misma cámara**, con evidencia verificada (no solo
declarada) en ambos lados para 6 de ellas: información del dispositivo, perfiles de video, hora,
imagen, OSD y reglas de analítica (esta última solo declarada por ambos protocolos, ya que su
verificación pasa por el editor de reglas y no por las sondas del motor de capacidades).

**Un defecto propio, encontrado por el hardware real y no por los tests automatizados.** La
operación `GetOSDs` respondía sistemáticamente *"The requested configuration does not exist"*,
un error que en un primer momento podía confundirse con una limitación de la cámara. La causa
resultó ser un error de implementación: el código pasaba el token del *origen* de video
(`VideoSourceConfiguration.SourceToken`, correcto para `GetImagingSettings`) donde `GetOSDs`
espera el token de la *configuración* de ese origen (`VideoSourceConfiguration.token`) — dos
campos del mismo objeto ONVIF, con nombres parecidos y significados distintos. Se corrigió y se
reverificó contra la cámara real, quedando la función confirmada como soportada por los dos
protocolos. Este hallazgo es, en sí mismo, evidencia a favor del principio metodológico de este
trabajo (§5.1): sin la verificación contra hardware real, este error habría quedado invisible
para siempre detrás de un "no soportado" que en realidad era un error propio.

El mismo procedimiento se repitió, palabra por palabra, contra el domo DeepinView más tarde el
mismo día (29/09), en su nueva dirección tras el cambio de IP descrito en §7.2.1, y funcionó
igual al primer intento: `status: online` por los tres protocolos también en esa cámara. Con esto,
la verificación de ONVIF contra hardware real queda cerrada para las dos cámaras Hikvision del
trabajo — la única pendiente es la cámara Scati (§7.8).

## 7.5 Evidencia cuantitativa: tasa de éxito y latencias

Se ejecutó el corredor de experimentos (§6.8) con 30 repeticiones por función contra la PTZ real,
por los dos protocolos ya verificados (ISAPI y ONVIF). Es la primera corrida contra hardware real
de todo el trabajo; hasta este resultado, la evidencia cuantitativa solo existía contra el
simulador.

| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|
| Información del dispositivo | isapi | 30 | 30 | 100 % | 28,6 | 38,0 |
| Información del dispositivo | onvif | 30 | 30 | 100 % | 22,1 | 30,5 |
| Hora | isapi | 30 | 30 | 100 % | 50,3 | 61,9 |
| Hora | onvif | 30 | 30 | 100 % | 23,6 | 28,5 |
| Perfiles de video | isapi | 30 | 30 | 100 % | 41,6 | 55,6 |
| Perfiles de video | onvif | 30 | 30 | 100 % | 171,0 | 191,7 |
| Ajustes de imagen | isapi | 30 | 30 | 100 % | 31,5 | 38,0 |
| Ajustes de imagen | onvif | 30 | 30 | 100 % | 149,8 | 227,5 |
| OSD | isapi | 30 | 30 | 100 % | 34,1 | 46,4 |
| OSD | onvif | 30 | 30 | 100 % | 117,0 | 135,3 |
| Detección de movimiento | isapi | 30 | 30 | 100 % | 29,3 | 35,5 |
| Detección de movimiento | onvif | 30 | 0 | **0 %** | 29,9 | 38,4 |

*(Tabla completa, con estado y snapshot también medidos por ISAPI, en
`docs/evidencias/experimentos/2026-09-29T12-31-54+00-00/`.)*

Dos lecturas de esta tabla van más allá de confirmar que "ambos protocolos funcionan":

**No hay un ganador único en latencia.** Para información del dispositivo y hora, el pedido SOAP
de ONVIF resultó más liviano que el equivalente en ISAPI. Para todo lo que exige negociar antes un
perfil de video (imagen, OSD), el costo de las llamadas encadenadas que impone el modelo de ONVIF
—primero pedir los perfiles, después la operación específica— se traduce en una latencia de 3 a 5
veces mayor que ISAPI, medida y no estimada.

**La detección de movimiento por ONVIF falló las 30 veces, con el mismo motivo exacto las 30**:
*"La cámara no publica eventos de movimiento por ONVIF"*. No es un fallo intermitente ni un
problema de conectividad — es la confirmación empírica, y ya no solo teórica, de la asimetría
descrita en el marco teórico (§3.3): ONVIF no tiene esta función como una operación de
lectura/escritura, y lo único que se puede verificar es si la cámara *publica* el evento
correspondiente. Corresponde una aclaración metodológica: la tasa de éxito del 0 % en este caso no
representa una falla del mecanismo, sino la medición correcta y consistente de una ausencia real.

### 7.5.1 La misma corrida, contra el domo

El mismo corredor, con las mismas 30 repeticiones por función, se ejecutó también contra el domo
(29/09), una vez habilitado ONVIF (§7.4):

| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|
| Información del dispositivo | isapi | 30 | 30 | 100 % | 26,5 | 33,9 |
| Información del dispositivo | onvif | 30 | 30 | 100 % | 18,8 | 31,4 |
| Movimiento | isapi | 30 | 30 | 100 % | 25,9 | 30,6 |
| Movimiento | onvif | 30 | 0 | **0 %** | 47,7 | 56,4 |
| Perfiles de video | isapi | 30 | 30 | 100 % | 44,9 | 58,3 |
| Perfiles de video | onvif | 30 | 30 | 100 % | 120,9 | 365,8 |
| Snapshot | isapi | 30 | 30 | 100 % | 107,7 | 121,3 |
| Estado | isapi | 30 | 30 | 100 % | 131,1 | 157,4 |
| Hora | isapi | 30 | 30 | 100 % | 56,4 | 60,0 |
| Hora | onvif | 30 | 30 | 100 % | 21,1 | 30,9 |
| Ajustes de imagen | isapi | 30 | 30 | 100 % | 27,3 | 33,9 |
| Ajustes de imagen | onvif | 30 | 30 | 100 % | 109,1 | 140,1 |
| OSD | isapi | 30 | 30 | 100 % | 29,9 | 36,3 |
| OSD | onvif | 30 | 30 | 100 % | 87,6 | 106,2 |

*(Tabla completa en `docs/evidencias/experimentos/2026-09-29T13-30-29+00-00/informe.md`.)*

El patrón se repite de forma consistente con la PTZ: ONVIF gana en operaciones simples de una sola
llamada (información del dispositivo, hora) y pierde por un factor de 2 a 4 en todo lo que depende
de negociar antes un perfil de video, y la detección de movimiento vuelve a fallar el 100 % de las
veces por el mismo motivo exacto en las dos cámaras — evidencia de que la asimetría de §3.3 no es
una particularidad de un modelo de cámara, sino del propio protocolo ONVIF frente a este tipo de
evento.

## 7.6 Motor de eventos: de avisos a episodios

Las cámaras entregan eventos por una conexión HTTP de larga duración con un flujo *multipart* que
repite el mismo aviso mientras la condición persiste. Se observó, contra hardware real:

- Un aviso de mantenimiento (`videoloss / inactive`) cada aproximadamente 10 segundos, que no
  constituye un evento de negocio sino solo la confirmación de que la cámara sigue en línea.
- Repetición del mismo aviso una vez por segundo mientras dura una detección: en una prueba real se
  registraron 145 avisos de movimiento en dos minutos y medio.
- El aviso que cierra un evento de cruce de línea no incluye el identificador de la regla que lo
  originó, a diferencia del aviso que lo abre — tomados de forma literal, esto produce filas
  huérfanas en cualquier esquema de persistencia que agrupe por identificador de regla.

La plataforma agrupa estos avisos en episodios (criterio en §6.6). Medido contra las dos cámaras
Hikvision del laboratorio en una sesión de prueba: **311 avisos individuales se agruparon en 12
episodios**, una compresión de 25,9 veces respecto de persistir cada aviso por separado.

Un tipo de evento no documentado en la lista habitual de eventos de Hikvision apareció durante las
pruebas: el domo emite `soundclassificationdetection`, un evento de clasificación de sonido por
inteligencia artificial.

## 7.7 Analítica de inteligencia artificial del domo: un resultado negativo documentado

> Esta sección describe el estado de **AI Open Platform** específicamente, que a la fecha sigue sin
> emitir alarmas. No debe confundirse con el hallazgo de §7.2.1: desde el 29/09 el mismo domo
> soporta y aplica reglas por la vía **clásica** (`/ISAPI/Smart/*`), que es una API distinta y que
> sí quedó verificada funcionando. Ambos resultados conviven: AIOP sigue siendo un resultado
> negativo documentado; Smart es, desde el 29/09, una vía alternativa disponible en el mismo
> equipo.

Al 24/09/2026, la aplicación de IA del domo está instalada y el modelo cargado, pero no emite
alarmas. Se verificó:

| Verificación | Resultado |
|---|---|
| Plataforma de IA | Activa, versión `AI_V4.0.0`, cuatro motores disponibles |
| Modelo cargado | `deteccion_armas`: persona, cuchillo, arma, hacha, manos en alto |
| Tarea de análisis de video | **Inexistente** tras un reinicio de la cámara (`{"Tasks": []}`) |
| Disparador de la regla configurada | Vacío |
| Calendario de armado de la aplicación | Desactivado |

Se confirmó que la tarea de análisis existía y corría normalmente el día anterior a un reinicio de
la cámara, y que tras el reinicio la lista de tareas quedó vacía sin que el modelo se descargara del
motor. **No fue posible recrear la tarea únicamente por API**: se probaron seis variantes distintas
de la petición de creación, obteniendo en el mejor caso un error de "parámetros incorrectos" (que
indica que el formato del pedido fue entendido) y en el peor un error genérico del dispositivo (que
indica que la cámara falla al intentar crear la tarea por su cuenta). Se documenta este resultado
como un límite verificado de la API — la plataforma puede leer y modificar una tarea de análisis
existente, pero no puede levantar una tarea nueva cuando la cámara la perdió — y no como un defecto
de la implementación de este trabajo.

Un hallazgo metodológicamente relevante: los cuatro tipos de evento asociados a la analítica de IA
sí figuran entre los eventos suscribibles de la cámara, y la propia documentación de capacidades
declara que el método de notificación por defecto para esos eventos es el mismo canal (`center`)
que usa el resto de los eventos ya verificados. Esto permite afirmar, con razonable confianza, que
**si la tarea de análisis volviera a existir, los eventos de IA llegarían por el mismo mecanismo ya
verificado** — pero esa afirmación queda, correctamente, en el terreno de lo declarado y no de lo
verificado hasta que se observe un evento de IA real.

## 7.8 Cámara Scati: caso comparativo de otra marca

> 🔴 **Pendiente de integración al momento de escribir este capítulo.**

Se identificó el acceso a una cámara de la marca Scati, distinta de Hikvision, sin funciones de
analítica propietaria. Este caso corresponde directamente al escenario comparativo previsto en el
cronograma original del anteproyecto (validación de "Scati u otra marca disponible" como tercer
escenario de integración). Se espera, en línea con lo discutido en §2.5, que este caso ilustre el
extremo opuesto al del domo DeepinView: una cámara sin capacidades avanzadas propietarias que
exponer, cuyo aporte a la matriz de compatibilidad es demostrar que la interoperabilidad básica
(ONVIF, RTSP, información del dispositivo) es alcanzable incluso cuando no hay ninguna función
premium detrás — que es, en sí mismo, uno de los resultados esperados del trabajo (§4.4).

## 7.9 Síntesis de la matriz de compatibilidad

La matriz completa —11 funciones × 3 protocolos × todas las cámaras registradas, incluidas las
simuladas y la cámara VPN sin conexión al momento de generarla— se exportó directamente desde la
plataforma (botón "Exportar Markdown" de la pantalla Matriz, §6.7) y queda como evidencia completa
en `docs/evidencias/matriz/2026-09-29-matriz-compatibilidad.md`. Lo que sigue es esa misma matriz,
filtrada a las dos cámaras Hikvision reales, que es la comparación que importa para responder la
pregunta de investigación:

| Función | PTZ · ISAPI | PTZ · ONVIF | Domo · ISAPI | Domo · ONVIF |
|---|---|---|---|---|
| Información del dispositivo | ✓ v | ✓ v | ✓ v | ✓ v |
| Perfiles de video | ✓ v | ✓ v | ✓ v | ✓ v |
| Snapshot | ✓ v | ✓ d | ✓ v | ✓ d |
| Reglas de analítica | ✓ d | ✓ d | ✓ d | ✓ d |
| Estado y salud | ✓ v | ✓ d | ✓ v | ✓ d |
| Hora del dispositivo | ✓ v | ✓ v | ✓ v | ✓ v |
| Reinicio | · d | ✓ d | · d | ✓ d |
| OSD | ✓ v | ✓ v | ✓ v | ✓ v |
| Ajustes de imagen | ✓ v | ✓ v | ✓ v | ✓ v |
| Detección de movimiento | ✓ v | ✕ v | ✓ v | ✕ v |

*(`v` = verificado con una llamada real, `d` = solo declarado por la cámara. Video en vivo y RTSP
no figuran porque esa función no se resuelve por ISAPI ni por ONVIF en esta plataforma — se
resuelve exclusivamente por RTSP republicado en MediaMTX, ya cubierto en §6.3.)*

**Lo que muestra esta tabla, fila por fila, es la respuesta empírica a la pregunta central del
anteproyecto.** Las dos cámaras Hikvision dan exactamente el mismo patrón entre sí —lo cual es en
sí mismo un resultado, no una obviedad: confirma que la asimetría entre ISAPI y ONVIF documentada
en el marco teórico (§3.3) y verificada en §7.4 no es una particularidad de un modelo puntual, sino
del protocolo—: siete de diez funciones tienen paridad completa entre los dos protocolos (ambos
`✓`), una la resuelven de forma desigual en cuanto a evidencia disponible pero no en resultado
(reinicio: ISAPI no lo declara pero funciona igual por el otro protocolo, así que la fila queda
`unverified` de un lado por una limitación de la propia documentación del fabricante, no del
adaptador), y una sola función —detección de movimiento— tiene una respuesta binaria y opuesta:
ISAPI la soporta como operación de lectura/escritura, ONVIF solo permite confirmar que el evento
*no* se publica. Es la verificación empírica, ya no solo documental, de que "estándar" y
"propietario" no son sinónimos de "igual de completo": son dos superficies distintas del mismo
dispositivo, con una intersección amplia pero no total.

Queda pendiente agregar una columna más —la cámara Scati— cuando se resuelva el acceso descrito en
§7.8; el formato de la tabla no cambia, solo se agregan las columnas correspondientes.
