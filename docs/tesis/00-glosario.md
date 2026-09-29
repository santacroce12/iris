# Glosario de términos técnicos

Los términos que aparecen en el documento entre comillas simples de código (así: `Analytics`)
suelen ser nombres exactos de un protocolo — un servicio, un método o un campo — y no una palabra
común. Este glosario los explica en lenguaje llano, en orden alfabético. Cada entrada dice también
en qué capítulo se usa, por si hace falta ver el contexto completo.

---

**Adaptador (patrón *adapter*)** — Una pieza de software que traduce entre dos formas de hablar
distintas. En este trabajo, cada protocolo (ISAPI, ONVIF, RTSP) tiene su propio adaptador: el resto
del sistema le pide "dame la hora de la cámara" sin saber si eso, por dentro, significa mandar un
XML o llamar un método SOAP. *Capítulos 3, 6.*

**AI Open Platform** — El nombre que Hikvision le puso a la plataforma de inteligencia artificial
que traen algunas de sus cámaras (las de la serie DeepinView). No es un estándar de la industria:
es una función propia de esa cámara, con su propia forma de configurar reglas de detección,
totalmente distinta de la analítica "clásica" que traen otras cámaras Hikvision. *Capítulos 6, 7.*

**Analytics (servicio ONVIF)** — Uno de los módulos opcionales que un fabricante puede implementar
dentro de ONVIF, pensado para configurar reglas de analítica (líneas de cruce, zonas) de forma
estandarizada. Muy pocos fabricantes lo implementan a fondo; muchos lo dejan sin usar. *Capítulo 3.*

**Anti-corruption layer (capa anticorrupción)** — Un concepto de diseño de software: una capa que
se pone deliberadamente entre "el mundo de afuera" (en este caso, cada cámara con su protocolo
particular) y "el mundo de adentro" (el modelo de datos propio del sistema), para que lo raro o
inconsistente de afuera no se filtre para adentro. Es una forma más elaborada del patrón adaptador.
*Capítulo 3.*

**Autenticación Digest / Basic** — Dos formas estándar de mandar usuario y contraseña por HTTP.
Basic los manda casi en texto plano (solo codificados, no cifrados); Digest hace un cálculo
matemático (un *hash*) para no mandar la contraseña real por la red. La mayoría de las cámaras de
este trabajo exigen Digest. *Capítulos 3, 6.*

**DESCRIBE** — Uno de los comandos del protocolo RTSP. Es el que se usa para preguntarle a la
cámara "¿qué video tenés para ofrecer?" — la cámara responde con una descripción técnica (ver
**SDP**) de sus pistas de audio y video. Sirve como la forma real de confirmar que una cámara habla
RTSP, en lugar de solo ver si el puerto está abierto. *Capítulo 3.*

**Device, Media, Media2, Events, Imaging, PTZ (servicios ONVIF)** — ONVIF no es una sola cosa: es
un conjunto de módulos independientes, y cada cámara puede implementar unos sí y otros no.
`Device` da la identidad del equipo (marca, modelo, serie). `Media`/`Media2` da los perfiles de
video disponibles. `Events` permite suscribirse a avisos de la cámara. `Imaging` ajusta brillo,
contraste, etc. `PTZ` mueve una cámara motorizada. Que una cámara "hable ONVIF" no dice nada sobre
cuáles de estos módulos tiene realmente activos — hay que probarlos uno por uno. *Capítulo 3, 7.*

**Edge / dispositivo de borde** — Un equipo que procesa datos donde se generan (en este caso, en la
propia cámara) en lugar de mandar todo a un servidor central. Una cámara con analítica de IA hace
inferencia "en el borde": decide si hay una persona sin mandar el video a ningún lado.
*Capítulo 3.*

**experiment_id** — Un identificador que se le pone a un grupo de pruebas para poder buscarlas
juntas después, sin mezclarlas con el resto de lo que la plataforma hace en el día a día. Cuando se
corre el corredor de experimentos (capítulo 6, §6.8), todas las llamadas de esa corrida comparten
el mismo `experiment_id`. *Capítulo 6, 7.*

**GetDeviceInformation, GetProfiles, GetSystemDateAndTime, GetOSDs, GetImagingSettings,
GetEventProperties, GetServices** — Nombres exactos de operaciones concretas dentro de los
servicios ONVIF de arriba. Por ejemplo, `GetServices` es la operación que devuelve la lista
completa de qué módulos tiene activos una cámara — es la que permite saber con certeza si un
servicio *no* existe (a diferencia de otros casos donde "no se pudo probar" no es lo mismo que "no
existe", ver capítulo 3 §3.5). *Capítulos 3, 6, 7.*

**HLS (HTTP Live Streaming)** — Una forma de mandar video por internet cortándolo en archivos
chiquitos que el navegador va pidiendo uno detrás del otro. Es más lenta que WebRTC (unos segundos
de demora) pero funciona en cualquier navegador sin configuración especial. En este trabajo es el
respaldo si WebRTC falla. *Capítulos 3, 6.*

**HTTP 200 / 401 / 403 / 404** — Los códigos con los que un servidor web responde a un pedido. 200
es "todo bien"; 401 y 403 son variantes de "no tenés permiso"; 404 es "eso no existe". Un hallazgo
central de este trabajo (capítulo 6, §6.4) es que Hikvision usa el mismo código (403) tanto para
"no tenés permiso" como para "esta función no existe en este modelo", y hay que mirar el cuerpo de
la respuesta para saber cuál de las dos es. *Capítulos 6, 7.*

**ISAPI** — La API propia de Hikvision (no es un estándar de la industria). El nombre viene de
*Intelligent Security API*. Es la forma en que este trabajo habla con las cámaras Hikvision para
todo lo que ONVIF no cubre. *Capítulo 3.*

**JSONB** — Un tipo de columna de la base de datos PostgreSQL que guarda un documento JSON
completo (no una tabla con columnas fijas). Se usa para guardar la respuesta cruda de cada cámara
tal cual llegó, porque esa respuesta es la evidencia y no conviene "aplanarla" perdiendo
información. *Capítulo 6.*

**Long-polling / multipart** — Una forma de mandar datos por HTTP donde la conexión se queda
abierta mucho tiempo (en vez de responder una sola vez y cerrarse) y el servidor va mandando
"partes" nuevas a medida que hay novedades. Es como funciona el flujo de eventos de las cámaras:
la conexión queda abierta escuchando, y cada vez que pasa algo llega una parte nueva sin cerrar la
conexión. *Capítulos 3, 6.*

**Percentil 50 / percentil 95 (p50 / p95)** — Una forma de resumir muchas mediciones de tiempo sin
que un caso raro (una sola vez que tardó mucho) arruine el promedio. El p50 es "la mitad de las
veces tardó menos que esto" (es la mediana). El p95 es "el 95 % de las veces tardó menos que esto"
— muestra el peor caso típico, sin contar el 5 % más raro. *Capítulos 6, 7.*

**PullPoint** — El mecanismo que usa ONVIF para avisar eventos. A diferencia de ISAPI (que mantiene
una conexión abierta y empuja los avisos apenas pasan), en ONVIF el cliente tiene que ir
preguntando cada tanto "¿pasó algo nuevo?" — es un modelo de *pedir*, no de *recibir*. *Capítulo 3.*

**SDP (Session Description Protocol)** — El formato en el que una cámara describe, en respuesta a
un `DESCRIBE`, qué video y audio tiene para ofrecer: códec, resolución, etc. No transporta el video
en sí, solo lo describe. *Capítulo 3.*

**SOAP / WS-*** — Una forma de armar pedidos entre programas usando XML con una estructura muy
formal (a diferencia de las APIs modernas, que suelen usar JSON simple). ONVIF está construido
sobre SOAP; ISAPI, en cambio, permite XML simple o JSON directo. *Capítulo 3.*

**subStatusCode** — Un campo dentro de la respuesta de error de una cámara Hikvision que aclara
*por qué* falló, más allá del código HTTP general. El valor `notSupport`, por ejemplo, dice "esta
cámara no tiene esta función", distinto de un error de permisos. *Capítulos 3, 6, 7.*

**VMS (Video Management Software)** — El tipo de software comercial que junta el video de varias
cámaras en una sola pantalla (HikCentral, Milestone, Genetec, etc.). Se menciona en el capítulo 4
para explicar en qué se parece y en qué no se parece este trabajo a ese tipo de producto.
*Capítulo 4.*

**WebRTC / WHEP** — Una tecnología pensada para video en tiempo real con muy poca demora (la que
usan las videollamadas). WHEP es la forma estándar de "pedir" un video por WebRTC a un servidor. Es
la opción preferida en este trabajo para mostrar el video en vivo en el navegador. *Capítulos 3, 6.*
