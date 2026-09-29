# 4. Estado del arte

## 4.1 Software VMS comercial

El mercado ofrece numerosos sistemas de gestión de video (*Video Management Software*, VMS) que
integran cámaras multimarca — HikCentral del propio Hikvision, Milestone XProtect, Genetec
Security Center, entre otros. Estos productos resuelven de forma madura el problema de
**visualización** unificada: agregan flujos RTSP u ONVIF de múltiples fabricantes en una sola
consola. Sin embargo, su enfoque respecto de las funciones avanzadas es, en general, uno de dos:

- Limitarse a las funciones que el perfil ONVIF cubre razonablemente bien (streaming, PTZ básico,
  algunos eventos), dejando fuera la analítica propietaria.
- Ofrecer integración profunda solo con la marca propia del fabricante del VMS (es el caso de
  HikCentral con Hikvision), reproduciendo el mismo problema de dependencia de marca que este
  trabajo busca evitar, solo que centralizado en un software distinto en lugar de en cada cámara.

Ninguno de estos productos publica, como parte de su interfaz de usuario, una matriz explícita de
qué función está *verificada* contra qué protocolo y con qué evidencia — la información de
compatibilidad, cuando existe, suele estar en documentación de ventas, no en una herramienta que el
integrador pueda ejecutar contra su propio hardware. Esa carencia es, precisamente, el aporte
diferencial que este trabajo propone: no una consola de video más completa, sino un instrumento de
medición de compatibilidad.

## 4.2 Limitaciones documentadas de ONVIF

El propio consorcio ONVIF reconoce, en la estructura de sus especificaciones, que la conformidad
se certifica por perfil (S, T, G, A, M, entre otros) y no de forma monolítica, lo cual admite
implícitamente que dos dispositivos "compatibles con ONVIF" pueden diferir sustancialmente en qué
servicios exponen. La literatura técnica y los foros de integración de videovigilancia documentan
de forma recurrente y informal —sin llegar a constituir un cuerpo académico consolidado— casos de
cámaras que declaran un perfil sin implementar todos sus servicios opcionales con la misma
profundidad, o que exponen el servicio `Analytics` de forma nominal sin permitir la creación de
reglas por esa vía.

Este trabajo no se apoya en esas observaciones de forma anecdótica: las **verifica empíricamente**
contra el hardware disponible (capítulo 7), lo cual constituye una diferencia metodológica
relevante respecto de la discusión habitual sobre las limitaciones de ONVIF, que suele quedar en el
plano de la experiencia de integración reportada informalmente y no en el de la medición
sistemática con evidencia registrada.

## 4.3 Patrones de arquitectura para integración de dispositivos heterogéneos

El patrón de diseño *adapter*, y su variante a nivel de sistema conocida como *anti-corruption
layer* en el vocabulario del diseño guiado por dominio, es la base conceptual del motor de
capacidades de este trabajo: cada protocolo (ISAPI, ONVIF, RTSP) se encapsula detrás de una interfaz
común que expone operaciones normalizadas, y el resto del sistema nunca interactúa directamente con
los detalles de cada protocolo. Este patrón es de uso extendido en integración de sistemas
empresariales y en el desarrollo de *gateways* IoT, pero su aplicación específica a videovigilancia
IP, con la particularidad de que la heterogeneidad aparece **dentro de un mismo fabricante** y no
solo entre fabricantes, no está documentada de forma explícita en la literatura revisada para este
trabajo.

## 4.4 Posicionamiento de este trabajo

Frente a lo anterior, este trabajo se posiciona en un punto intermedio poco cubierto: no es un VMS
comercial (no compite en cobertura de marcas ni en funciones de grabación y gestión de usuarios), ni
es una discusión puramente teórica sobre los límites de ONVIF. Es una implementación acotada,
verificada contra hardware real, que instrumenta la pregunta "¿qué se puede afirmar con evidencia
sobre la compatibilidad de una cámara IP?" con un mecanismo concreto —el motor de capacidades y la
matriz de compatibilidad— y que documenta, con casos reales, tanto los éxitos de la unificación
(las funciones que sí se lograron ejecutar de forma equivalente por dos protocolos) como sus
límites estructurales (las funciones que no tienen equivalente posible, o que la propia cámara deja
de sostener tras un evento como un reinicio).

> [Nota para la revisión: esta sección se beneficiaría de dos o tres citas académicas formales
> sobre integración IoT/edge y sobre el patrón anti-corruption layer, si la cátedra las exige. El
> borrador actual prioriza la caracterización correcta del estado del arte disponible sobre el
> mercado y el estándar por sobre la cita formal, que puede completarse en la revisión de
> bibliografía (capítulo 9) sin reescribir el argumento.]
