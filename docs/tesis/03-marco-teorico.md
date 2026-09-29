# 3. Marco teórico

## 3.1 El problema de la interoperabilidad en dispositivos IoT/edge

Una cámara IP es, en términos de arquitectura de software, un dispositivo de borde (*edge*) que
combina tres funciones que rara vez se estudian juntas: es un servidor de video (expone uno o más
flujos comprimidos), es un servidor de configuración (expone y modifica su propio estado a través
de una API HTTP) y es, cuando incorpora analítica, un sistema de inferencia embebido que produce
eventos derivados del contenido del video. La interoperabilidad entre dispositivos de borde de
distintos fabricantes es un problema general del ecosistema IoT, y la industria lo ha resuelto de
manera parcial mediante estándares de transporte (RTSP para el video) y perfiles de
interoperabilidad de más alto nivel (ONVIF para la configuración), dejando fuera del estándar,
casi por definición, todo lo que constituye la ventaja competitiva de cada fabricante: sus
funciones de analítica propias.

Este trabajo no propone una solución nueva a ese problema general: construir una capa de
abstracción sobre protocolos heterogéneos es un patrón de arquitectura de software bien conocido
(el patrón *adaptador*, o más ampliamente, una *capa anticorrupción* en el vocabulario del diseño
guiado por dominio — ver glosario). Lo que este trabajo aporta es la aplicación concreta de ese
patrón a un caso real de hardware de videovigilancia, verificada empíricamente, y una discusión
honesta de sus límites.

Dos preguntas concretas guían esa discusión. Primero, **hasta dónde llega la abstracción**: qué
tan lejos se puede unificar el acceso a distintas cámaras antes de que las diferencias reales entre
ellas queden ocultas en lugar de resueltas. Segundo, y es el eje central de todo el trabajo:
**qué mecanismo permite distinguir, con evidencia, una función que la cámara efectivamente soporta
de una función que el fabricante *dice* soportar pero que, al probarla contra el equipo real, no
se confirma.**

## 3.2 RTSP: transporte de video

*Real Time Streaming Protocol* (RTSP, RFC 2326) es un protocolo de control, no de transporte de
medios en sí mismo: negocia una sesión (mediante los métodos `DESCRIBE`, `SETUP`, `PLAY`,
`TEARDOWN`) cuyo contenido real viaja habitualmente por RTP sobre UDP o, cuando la red no lo
permite, encapsulado sobre la misma conexión TCP (*RTSP interleaved*). El método `DESCRIBE`
devuelve una descripción de sesión en formato SDP (*Session Description Protocol*) que enumera las
pistas de audio y video disponibles, sus códecs y sus parámetros.

Para los fines de este trabajo, RTSP tiene tres particularidades relevantes:

- **La autenticación es HTTP Digest o Basic**, embebida en la URL o negociada en el primer
  intercambio, y varía de implementación en implementación — algunas cámaras solo aceptan Digest,
  otras aceptan ambas.
- **Verificar que el puerto 554 esté abierto no equivale a verificar que la cámara hable RTSP.**
  Una verificación real requiere completar al menos el intercambio `DESCRIBE` y confirmar que la
  respuesta contiene un SDP válido con al menos una pista de video — una distinción que resultó
  relevante durante el desarrollo, descrita en el capítulo 6.
- Las credenciales de la cámara no deben llegar nunca al navegador. Por eso el video no se sirve
  RTSP directo al cliente web (que de todos modos no lo soporta de forma nativa), sino que se
  republica a través de un servidor intermedio (MediaMTX) que expone el mismo contenido por
  WebRTC o HLS, protocolos que sí soporta un navegador moderno.

## 3.3 ONVIF: el perfil de interoperabilidad estándar

ONVIF (*Open Network Video Interface Forum*) es un conjunto de especificaciones basadas en SOAP y
WS-* que define servicios estandarizados para dispositivos de video en red: `Device` (identidad y
capacidades del dispositivo), `Media`/`Media2` (perfiles de streaming), `Events` (suscripción a
eventos mediante un mecanismo de *pull* llamado PullPoint), `Imaging` (ajustes de imagen),
`PTZ` (control de movimiento) y, más recientemente, `Analytics` (reglas de analítica, con soporte
muy desigual entre fabricantes).

La observación central de la literatura y de la documentación del propio consorcio ONVIF, que
este trabajo se propuso verificar empíricamente y no dar por sentada, es que **la conformidad con
un perfil ONVIF no implica que todos los servicios del perfil estén implementados con la misma
profundidad**. Un fabricante puede declarar conformidad con el perfil S (streaming) sin exponer
`Analytics`, o exponer `Imaging` con un subconjunto mínimo de los parámetros que el estándar
permite. Esto tiene una consecuencia metodológica directa para este trabajo: **no alcanza con
verificar que una cámara "habla ONVIF"**; hay que verificar, servicio por servicio y operación por
operación, cuáles responde realmente.

Un caso particular, relevante para la comparación de funciones de este trabajo, es que ONVIF **no
tiene un servicio equivalente a "detección de movimiento configurable"** como función de primera
clase: lo más cercano es suscribirse a los eventos que la cámara publica y verificar si existe un
tópico relacionado con movimiento, lo cual permite *saber que la función existe* pero no *leer ni
modificar su sensibilidad* del mismo modo en que lo permite una API propietaria como ISAPI. Este
tipo de asimetría —dos protocolos que a primera vista parecen cubrir "la misma función" pero que en
realidad ofrecen una interacción cualitativamente distinta— es señalado por el estándar mismo y
confirmado en este trabajo; se desarrolla con evidencia concreta en el capítulo 7 (§7.4).

## 3.4 ISAPI: el caso de la API propietaria (Hikvision)

ISAPI (*Intelligent Security API*) es la API HTTP propietaria de Hikvision. A diferencia de ONVIF,
no está gobernada por un consorcio externo: la documenta y la versiona el propio fabricante, y su
completitud y consistencia dependen de la política de documentación de cada línea de producto. Para
los fines de este trabajo, ISAPI expone dos características que resultaron centrales:

- **Puede exponer XML o JSON** según el recurso (agregando `?format=json` a la mayoría de los
  endpoints), y la profundidad de la documentación pública varía enormemente entre familias de
  producto — una observación que se verificó empíricamente y se documenta en el capítulo 7.
- **La autenticación es HTTP Digest**, y los códigos de error no siempre distinguen con precisión
  entre "no tenés permiso" y "esta función no existe en este modelo": un mismo código HTTP (403)
  puede significar ambas cosas, y solo el cuerpo de la respuesta (un campo `subStatusCode`) permite
  diferenciarlas. Este comportamiento, no documentado de forma explícita, tuvo que inferirse
  empíricamente y tiene una consecuencia directa en el diseño del cliente HTTP del sistema
  (capítulo 6).

## 3.5 El motor de capacidades y la matriz de compatibilidad

El concepto central que este trabajo aporta sobre la bibliografía de interoperabilidad de
dispositivos es la distinción entre **capacidad declarada** y **capacidad verificada**:

- Una capacidad está **declarada** cuando el propio dispositivo, o su documentación, afirma
  soportarla — por ejemplo, un campo `isSupportOSD` en `true` dentro del documento de capacidades
  de ISAPI, o la presencia del servicio `imaging` en la respuesta `GetServices` de ONVIF.
- Una capacidad está **verificada** cuando se ejecutó una llamada real contra esa función y la
  cámara respondió de forma consistente con lo esperado.

Esta distinción no es una formalidad metodológica: se sostiene, con evidencia concreta descrita en
el capítulo 7, que **una cámara puede responder con éxito aparente (código HTTP 200) a una
operación de escritura sin aplicar el cambio**, lo cual significa que un sistema que registrara
como "soportada" cualquier función que no devuelva un error explícito produciría una matriz de
compatibilidad falsa. Por esa razón, el motor de capacidades desarrollado en este trabajo aplica
un principio de verificación estricta: **toda escritura se relee y se compara** antes de darse por
aplicada, y toda función que no fue efectivamente probada —ya sea porque el protocolo no respondió
o porque se trata de una operación destructiva que no conviene automatizar (como un reinicio) —
queda registrada como *sin verificar*, un tercer estado explícitamente distinto de *soportada* y de
*no soportada*.

La matriz de compatibilidad es la representación tabular de este motor: una fila por función, una
columna por cámara y protocolo, con el estado (soportada / no soportada / sin verificar), la fuente
de esa afirmación (declarada / verificada) y la evidencia que la respalda (latencia de la llamada,
código de respuesta, fragmento de la respuesta cruda). Es, en sí misma, el instrumento con el que
este trabajo responde a su pregunta de investigación: no con una afirmación general sobre "qué tan
unificable es la videovigilancia IP", sino con una tabla verificable, función por función y cámara
por cámara.

## 3.6 Normalización de datos heterogéneos

Un problema técnico recurrente al construir el motor de capacidades es que **dos protocolos que
resuelven la misma función lo hacen con representaciones de datos incompatibles entre sí**, y esa
incompatibilidad no siempre es evidente hasta que se mide contra hardware real. Dos ejemplos que
aparecen en los resultados de este trabajo (capítulo 7) ilustran por qué la normalización no es un
detalle de implementación sino una decisión de diseño con consecuencias verificables:

- **Coordenadas de reglas de analítica**: una familia de cámaras las expresa en enteros de 0 a
  1000 con el origen en la esquina inferior izquierda; otra familia, en decimales de 0 a 1 con el
  origen en la esquina superior izquierda. Una plataforma que no normalice explícitamente este
  sistema de coordenadas produciría reglas invertidas verticalmente en una de las dos familias, sin
  que ningún error lo señale — el sistema aceptaría la escritura y la aplicaría, solo que en el
  lugar equivocado de la imagen.
- **Zona horaria de los eventos**: una cámara puede reportar la marca de tiempo de sus eventos en
  el huso horario con el que fue configurada de fábrica, no necesariamente el del lugar de
  instalación. Sin una normalización explícita a UTC, los eventos de distintas cámaras no serían
  temporalmente comparables entre sí.

## 3.7 Agrupación de eventos en tiempo real

Los eventos de una cámara IP no llegan como notificaciones discretas de "ocurrió algo": llegan como
un flujo HTTP de larga duración (*long-polling* multipart) que repite el mismo aviso mientras la
condición que lo originó persiste, además de enviar avisos periódicos de mantenimiento ("sigo
viva") que no constituyen eventos en el sentido de negocio. Guardar cada aviso tal como llega
produce una base de datos dominada por ruido redundante. Este trabajo adopta el concepto de
**episodio**: un evento de negocio no es un aviso individual, sino un intervalo de tiempo — con
inicio, fin y una cuenta de cuántos avisos lo compusieron — delimitado por reglas de agrupación
(misma cámara, mismo tipo de evento, mismo canal y misma regla; cierre explícito o por inactividad).
La efectividad de este mecanismo se mide en el capítulo 7 con una métrica concreta de compresión.
