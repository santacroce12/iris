# El documento de tesis

Esto es el documento en sí — no notas de trabajo como la bitácora o el relevamiento, sino los
capítulos que se entregan y se defienden. Está en Markdown, capítulo por capítulo, para poder
editarlo con el resto del proyecto y llevar el historial en git. Cuando esté estable se pasa a
Word con el formato que pida la facultad.

**Principio de redacción**: todo lo que dice "verificado" o da un número concreto sale de la
bitácora, del relevamiento o de una corrida real de la plataforma — nunca se inventa un dato para
rellenar un capítulo. Donde falta evidencia, el capítulo lo dice explícitamente en vez de
disimularlo.

## Estado de cada capítulo

| # | Capítulo | Estado | Depende de |
|---|---|---|---|
| — | [Glosario de términos técnicos](00-glosario.md) | 🟡 Borrador completo | — |
| 1 | [Introducción](01-introduccion.md) | 🟡 Borrador completo | — |
| 2 | [Objetivos y alcance](02-objetivos-alcance.md) | 🟡 Borrador completo | — |
| 3 | [Marco teórico](03-marco-teorico.md) | 🟡 Borrador completo | — |
| 4 | [Estado del arte](04-estado-del-arte.md) | 🟡 Borrador completo | — |
| 5 | [Metodología](05-metodologia.md) | 🟡 Borrador completo | — |
| 6 | [Arquitectura e implementación](06-arquitectura-implementacion.md) | 🟡 Borrador completo | — |
| 7 | [Resultados](07-resultados.md) | 🟠 Parcial: falta ONVIF y Scati | Hardware real |
| 8 | [Conclusiones](08-conclusiones.md) | 🔴 Esqueleto con preguntas guía | Resultados cerrados |
| 9 | [Bibliografía](09-bibliografia.md) | 🟡 Borrador, crece con las citas que se agreguen | — |

🟡 = escrito, listo para que Luca lo lea y corrija estilo/énfasis. 🟠 = escrito hasta donde da la
evidencia actual, con huecos marcados. 🔴 = todavía no se puede escribir en serio.

## Cómo se completa lo que falta

Los capítulos 🟠 y 🔴 dependen de las sesiones con cámara de `../HOJA-DE-RUTA.md`, en particular:

- **Sesión 0** (Scati) y **Sesión 1** (ONVIF en las Hikvision) → llenan la sección de ONVIF del
  capítulo 7 y con eso se puede escribir la comparación ONVIF vs. propietaria del capítulo 8.
- **Sesión 5** (experimentos contra hardware real) → reemplaza los números del simulador en el
  capítulo 7 por los definitivos.
- **Sesión 3** (analítica del domo) → cierra si el hallazgo queda en "no dispara, documentado" o
  si se consigue un evento real.

Cuando cualquiera de esas sesiones cierre, el capítulo 7 se actualiza con los datos reales y el 8
se termina de escribir. No hace falta rehacer nada de lo ya escrito: los capítulos 1 a 6 no
dependen de las cámaras y no deberían cambiar salvo detalle de redacción.

## Qué le falta a este documento y no es responsabilidad mía completar

- **Portada con los datos formales** (institución, carrera, cátedra, director, fecha de defensa):
  no los tengo. Dejé un marcador en el propio documento.
- **Formato exacto que pida la facultad** (interlineado, citas APA/IEEE/Vancouver, numeración):
  ningún archivo que encontré en tu máquina lo especifica. Si tenés una guía de la facultad,
  pasámela y ajusto todo de una.
- **Revisión de estilo en primera persona vs. impersonal**: escribí en impersonal
  ("se desarrolló", "se verificó"), que es lo más común en tesis de ingeniería en español, pero
  cambialo si tu facultad pide otra cosa.
