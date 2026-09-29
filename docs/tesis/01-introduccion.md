# 1. Introducción

> [PORTADA — completar con los datos formales de la facultad: institución, carrera, cátedra,
> director/a, fecha. No están disponibles en el material fuente.]

> Los términos técnicos marcados como código (`así`) se explican en el
> [glosario](00-glosario.md), antes de este capítulo.

## 1.1 Presentación del problema

Los entornos de videovigilancia IP modernos combinan cámaras de distintos fabricantes, cada una
con su propio protocolo de configuración. Existen estándares orientados a resolver esta
fragmentación — en particular ONVIF, un perfil de interoperabilidad adoptado por la mayoría de los
fabricantes de cámaras de seguridad —, pero en la práctica la interoperabilidad estándar cubre
sobre todo las funciones básicas: obtener video, leer perfiles de streaming, consultar la
identidad del dispositivo. Las funciones de mayor valor agregado — analítica de video, reglas de
detección configurables, ajustes finos de imagen, módulos especializados — suelen exponerse
únicamente a través de APIs propietarias, documentadas de forma parcial o directamente no
documentadas para integradores externos.

Esta fragmentación tiene un costo concreto: un integrador que administra cámaras de varias marcas
—o incluso varios modelos de una misma marca— no puede asumir que una función que funciona en un
equipo funcione igual, o exista siquiera, en otro. El presente trabajo parte de esa observación
para plantear una pregunta más específica y más verificable de lo que suele plantearse en la
literatura comercial de "plataformas unificadas": **no si es posible mostrar video de varias
cámaras en una sola pantalla — eso ya lo resuelven los VMS comerciales —, sino hasta dónde es
posible unificar el acceso a las funciones avanzadas, y qué mecanismo permite saber, con evidencia
y no por confianza en la documentación del fabricante, qué función está realmente disponible en
cada equipo.**

## 1.2 Antecedentes

La construcción de esta plataforma tuvo dos intentos previos, ninguno de los cuales llegó a una
versión sostenible:

Un primer prototipo (mayo–julio de 2026) se validó contra una cámara Hikvision real por VPN y
desarrolló, entre otras cosas, un módulo de estacionamiento (*parking*) sobre la API propietaria de
esa cámara. No llegó a incorporar un motor de capacidades central: cada función avanzada se
resolvía por fuera de una arquitectura común, lo que dificultaba extender el sistema a funciones o
cámaras nuevas.

Un segundo intento (agosto de 2026) definió patrones de diseño más sólidos — un contrato de
adaptador explícito, cifrado de credenciales, un mecanismo de respaldo antes de cada escritura en
la cámara — pero nunca se probó contra hardware real, por lo que ninguno de esos patrones estaba
validado frente al comportamiento efectivo de una cámara IP.

La versión descrita en este trabajo retoma los patrones de diseño validados en ambos intentos y
descarta lo que no se sostuvo: adaptadores monolíticos de más de mil líneas, lógica de analítica
resuelta por fuera del motor central, y un cliente de eventos que dejaba de escuchar tras la
primera desconexión.

## 1.3 Planteamiento del problema

La gestión de cámaras IP multimarca presenta, en la práctica, los siguientes problemas:

1. Cada fabricante implementa su propia API, con su propia estructura de autenticación y sus
   propios mecanismos de configuración.
2. ONVIF no garantiza acceso uniforme a las funciones avanzadas: cubre, en el mejor de los casos,
   un subconjunto interoperable de funciones básicas.
3. El acceso a capacidades premium — analítica, parking, reconocimiento de patentes, overlays
   avanzados — suele quedar restringido al software propio del fabricante, y con frecuencia a
   documentación que no está pensada para integradores externos.
4. En instalaciones reales, esta fragmentación aumenta el tiempo de integración, complica el
   mantenimiento y reduce la posibilidad de operar equipos de distintas marcas desde una interfaz
   común.

Un quinto problema, encontrado durante el desarrollo de este trabajo y no anticipado en el
planteamiento original, resultó ser el más relevante de los cinco: **la fragmentación no se da
solo entre marcas, sino también dentro de una misma marca.** Las dos cámaras Hikvision principales
usadas en este trabajo hablan el mismo protocolo (ISAPI) y, sin embargo, exponen su analítica por
dos caminos completamente incompatibles entre sí — uno en XML con coordenadas enteras, el otro en
JSON con coordenadas decimales, cada uno con su propio modelo de reglas y de activación. Este
hallazgo se desarrolla en detalle en el capítulo de resultados (§7.2) y tiene una consecuencia
directa sobre el diseño de la solución: **una capa de abstracción no puede asumir que "ser de la
marca X" implica "hablar la API de la marca X de una sola manera".**

## 1.4 Justificación

La relevancia de este trabajo se apoya en tres ejes.

**Desde lo técnico**, aborda un problema real y documentado de interoperabilidad en sistemas de
videovigilancia, donde la existencia de un protocolo estándar (ONVIF) no elimina la dependencia de
mecanismos propietarios para acceder a las funciones de mayor valor.

**Desde lo práctico**, una plataforma de este tipo reduce el tiempo de integración, de pruebas y
de mantenimiento en instalaciones con infraestructura heterogénea — que es, en la práctica, la
norma y no la excepción en instalaciones de más de un par de años de antigüedad.

**Desde lo académico**, el trabajo permite analizar de forma concreta los límites de la
abstracción de dispositivos IoT/edge en un escenario real: no en el sentido de si es posible
escribir una capa de software encima de dos protocolos, sino de si esa capa puede sostener
afirmaciones verificables sobre lo que cada dispositivo soporta, en lugar de heredar las
afirmaciones — a veces incompletas, a veces optimistas — de la documentación del fabricante.

## 1.5 Estructura del documento

El capítulo 2 presenta los objetivos y el alcance del trabajo. El capítulo 3 desarrolla el marco
teórico: los tres protocolos involucrados (ISAPI, ONVIF, RTSP) y los conceptos de motor de
capacidades y matriz de compatibilidad. El capítulo 4 sitúa el trabajo frente a las alternativas
existentes — software VMS comercial y las propias limitaciones documentadas de ONVIF. El capítulo
5 describe la metodología aplicada, de carácter experimental. El capítulo 6 documenta la
arquitectura y las decisiones de implementación. El capítulo 7 presenta los resultados: qué se
verificó, con qué evidencia, y qué quedó sin verificar y por qué. El capítulo 8 reúne las
conclusiones y el trabajo futuro.
