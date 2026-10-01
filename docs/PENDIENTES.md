# Pendientes

Lista larga de cosas sueltas. **Para el plan de trabajo ordenado, ver
[HOJA-DE-RUTA.md](HOJA-DE-RUTA.md)**: ahí está qué se hace con cámaras, qué sin cámaras, y en
qué orden. **El documento de tesis en sí está en [docs/tesis/](tesis/README.md)**.

## Eventos

- [x] **Fotos en los eventos — implementado (29/09).** Se revisó en la interfaz de la PTZ: **este
      modelo no tiene una opción para adjuntar la foto al canal que ya escuchamos** ("Notificar al
      software remoto"). Lo único que ofrece es "Cargar en FTP/tarjeta de memoria/NAS", un mecanismo
      distinto. Ver `bitacora-apis.md` §6.6 para el detalle. Se optó por la alternativa más simple
      (sin infraestructura extra): **si el aviso que abre un episodio no trae ninguna foto, la
      plataforma pide ella misma un snapshot** (`GET .../picture`) antes de guardarlo — no es el
      fotograma exacto del instante, pero es real y no depende de una función que al menos la PTZ
      no tiene. Implementado en `CameraListener._snapshot_on_open`
      (`backend/app/engine/event_hub.py`), 5 tests nuevos contra un servidor ISAPI simulado con
      `respx` (`backend/tests/integration/test_event_hub_snapshot.py`), incluida una prueba de
      punta a punta que verifica el archivo escrito en disco, no solo el registro en la base.
      **Confirmado contra la PTZ real el mismo 29/09**, apenas volvió la conectividad: desde el
      reinicio del backend con este código, todos los eventos de cruce de línea de la PTZ
      quedaron con 1 foto real adjunta (antes, 0), con el archivo `.jpg` verificado en disco y a
      simple vista (una foto real de la oficina, con el overlay de fecha/hora de la propia
      cámara).
- [ ] **Recrear la tarea de análisis del domo desde su interfaz web** y capturar el pedido que
      manda el navegador. Después de un reinicio la tarea desapareció y no se pudo recrear por
      API (6 variantes, ver `bitacora-apis.md` §5.1). Sin tarea no hay analítica de IA.
- [x] Los eventos de `sound_classification` del domo: ver qué sonido clasificó (está en el
      payload). **27 de 27 eventos capturados desde el 18/09 clasificaron `"gunfire"`** — casi
      seguro un falso positivo recurrente sobre ruido ambiente, no algo real. Ver
      `bitacora-apis.md` §6.8.

## Reglas

- [x] Orientación vertical verificada en las dos cámaras: la PTZ cuenta desde abajo y el domo
      desde arriba (ver `bitacora-apis.md`).
- [x] Zona de la Regla1 del domo restaurada a pantalla completa.
- [x] Editor de reglas sobre la imagen: probado contra la PTZ real (se arrastró un punto en el
      navegador, se guardó, la cámara lo aplicó y se restauró la línea de la demo).
- [ ] La línea 2 de la PTZ quedó con una línea dibujada a mano durante la prueba; borrarla si
      molesta (la línea 1 es la de la demo).
- [ ] Si se cambia el montaje de la PTZ o se activa la rotación de imagen, repetir la verificación
      de orientación.

## Analítica del domo que no dispara

- [ ] El disparador de la Regla1 está vacío (`…/AIRuleConfig/task/<tarea>/channels/1/trigger` →
      `{}`) y el calendario de armado de la app está en `enabled: false`. Falta confirmar si
      HikCentral recibe igual las alarmas por su canal propio.
- [ ] Revisar del lado de HikCentral si llegan eventos de esa cámara y con qué nombre.
- [ ] El parser ya mapea los cuatro tipos de IA (`AIOpenPlatform`, `AIOP_Video`,
      `AIOP_Polling_Snap`, `HEOPCustomEvent`) y la cámara los declara suscribibles, pero todavía
      **no se vio llegar ninguno de estos cuatro** (la tarea de video sigue vacía, §"Analítica del
      domo que no dispara"). Aclaración (29/09): esto no significa que el domo no mande *ningún*
      evento de IA — `sound_classification`, que es un tipo de evento distinto y no depende de la
      tarea de AIOP, sí llegó (27 veces, ver arriba). Queda sin verificar solo lo que depende de
      esa tarea puntual.

## Cámaras y red

- [x] **Tercera cámara real integrada: la bullet de parking** (30/09), iDS-2CD7A46G0/P-IZHSY,
      firmware V5.8.61, en `192.168.1.11`. Aporta una **tercera familia de analítica**
      (`/ISAPI/Parking/channels/1/packingSpaceRecognition?format=json`) y, con ella, la
      explicación estructural de por qué existen las familias: **los modos de VCA son mutuamente
      excluyentes** (`roadDetection|smart|PackingSpaceRecognition|close`). Escritura de geometría
      verificada con respaldo, relectura, comparación y restauración. ONVIF ya venía activado, a
      diferencia de las otras dos. Ver `bitacora-apis.md` §6.9 y `07-resultados.md` §7.2.2/§7.3.7.
- [ ] **Confirmar el `VCAResource` del domo** — es la verificación más importante que quedó
      pendiente. Si el domo cambió de modo de VCA en el reinicio del 25/09, eso explicaría el
      hallazgo de §7.2.1 (que de golpe empezara a responder la analítica clásica). No se pudo
      hacer el 30/09 porque su contraseña vive cifrada en la base y Postgres estaba caído. Es un
      solo `GET /ISAPI/System/Video/inputs/channels/1/VCAResource`.
- [x] **Bullet de parking dada de alta en la plataforma** (30/09): `status: degraded` — ISAPI y
      RTSP en verde, ONVIF falla (ver abajo).
- [x] **Familia de parking soportada en el motor de reglas** (30/09): driver nuevo
      (`app/drivers/isapi/rules/parking.py`), detección automática de la familia, lectura con
      ocupación en vivo y escritura con respaldo/relectura/verificación. **Las plazas se dibujan y
      se arrastran desde la pantalla de Reglas** igual que las líneas y zonas de las otras dos
      cámaras. 9 tests unitarios con la respuesta real del equipo; round-trip verificado contra
      hardware (mover la plaza 001, la cámara la aplicó, restaurada).
- [ ] **ONVIF de la bullet de parking falla** con `Fault('Unknown fault occured')`, aunque el
      equipo lo trae activado (`Integrate.ONVIF.enable = true`, `certificateType: digest`) y
      tiene un usuario ONVIF `admin` de tipo administrador. Es el único de los tres protocolos en
      rojo en esta cámara, y el tercer comportamiento distinto de ONVIF entre las tres Hikvision:
      dos venían apagadas de fábrica y se habilitaron bien, esta viene encendida y falla. Vale la
      pena entenderlo: puede ser que el usuario ONVIF necesite recrearse, o una diferencia de
      autenticación (digest contra WS-UsernameToken).
- [ ] **Dar de alta la cámara Scati** (27/09: confirmado que hay acceso). Es el caso "otra marca"
      que pedía el cronograma del anteproyecto (Fase 3: "validación de Scati u otra marca
      disponible"). No tiene analítica — es el resultado esperado, no un problema: el propio
      anteproyecto dice que una marca sin API avanzada es un caso comparativo válido. Puede
      resolver ONVIF gratis si lo trae activado de fábrica. Ver Sesión 0 de `HOJA-DE-RUTA.md`.
- [x] **ONVIF habilitado y verificado en la PTZ y en el domo** (29/09), por API en el primer
      intento en las dos: `PUT /ISAPI/System/Network/Integrate` + usuario ONVIF creado.
      `status: online` por los tres protocolos en ambas cámaras. Ver `bitacora-apis.md` §6.5.
      Falta repetirlo en la Scati si se consigue acceso.
- [x] **El domo cambió de IP** (192.168.239.101 → .174, mismo equipo y firmware, reiniciado el
      25/09). Actualizado en la plataforma.
- [ ] **Hallazgo grande (29/09): el domo ahora responde a la analítica clásica** (`/ISAPI/Smart/*`),
      que antes daba `403 notSupport` — confirmado escribiendo una regla real y viendo que se
      aplica. Ver `bitacora-apis.md` §6.7. La plataforma hoy elige una sola familia de reglas por
      cámara (AI Open Platform, por ser más específica) y no ofrece la clásica aunque responda.
      Falta que el motor de reglas pueda mostrar las dos cuando las dos funcionen.
- [ ] Video del domo en el navegador del usuario: del lado del servidor funciona (MediaMTX lo lee,
      WebRTC y HLS responden). Falta saber qué ve exactamente el usuario para cerrar el tema.
- [x] **El video en vivo de la bullet de parking no se veía: entrega H.265** (01/10), que el
      navegador no reproduce ni por WebRTC ni por HLS. Todo lo demás daba bien —RTSP en verde,
      ruta publicada, MediaMTX en `ready` recibiendo video— y el usuario igual veía negro. De sus
      5 perfiles, main y sub son H.265 y tres son H.264; la plataforma solo ofrecía main/sub.
      **Arreglado**: ahora elige el stream por códec (`app/domain/video.py`), y si tiene que
      cambiarlo lo explica en pantalla en vez de dejar un reproductor negro. 16 tests nuevos.
      Verificado a nivel API (elige el canal 104, H.264) pero **falta verlo reproducir en el
      navegador**: la cámara se apagó antes de poder confirmarlo. Ver `07-resultados.md` §7.3.8.
- [x] El usuario `stmcam` del domo es rechazado por RTSP (401): revisar si existe o sus permisos.
      **Confirmado por API (29/09): existe, es Operator, y tiene `preview: true` en el canal de
      video — los permisos están bien.** El 401 es una contraseña incorrecta o desconocida, no un
      problema de permisos. Falta la contraseña real para seguir; no se intentó adivinarla.
- [x] **Las dos cámaras tenían la zona horaria en +08:00 (China) y se corrigieron (29/09)**, con
      respaldo y relectura. La plataforma ya normalizaba a UTC así que no afectaba nada
      funcionalmente, pero es una rareza más: el mismo campo `timeZone` necesitó el signo opuesto
      en cada cámara para dar el mismo resultado real (`GMT+3:00:00` en la PTZ,
      `GMT-3:00:00` en el domo). Ver `bitacora-apis.md` §6.8.
- [ ] Credenciales de la cámara 192.168.239.151 (responde ISAPI pero con otras credenciales).

## Estado que dejamos modificado en las cámaras

- PTZ (192.168.239.189): regla de cruce de línea 1 activa, línea horizontal (150,500)→(850,500),
  filtro persona + vehículo. Respaldo de la configuración original en el scratchpad de la sesión
  del 18/09.
- PTZ (192.168.239.189): **ONVIF activado** (estaba apagado) y usuario ONVIF `tesisonvif`
  creado (29/09). Respaldo del `Integrate` original en el scratchpad de esa sesión. Esto queda
  así a propósito, no hay que restaurarlo: es la comparación que necesita la tesis.
- Domo (ahora 192.168.239.174): detección de movimiento encendida (estaba apagada), sensibilidad 80.
- Domo (192.168.239.174): **ONVIF activado** y usuario `tesisonvif` creado (29/09), igual que
  en la PTZ. No hay que restaurarlo.
- Domo (192.168.239.174): **la línea 1 de `/ISAPI/Smart/LineDetection` quedó con coordenadas de
  prueba** (0,2/0,8)–(0,8/0,2), sensibilidad 70, **desactivada** (`enabled: false`, no genera
  alarmas). Se dejó a propósito como evidencia de que la escritura se aplica de verdad; no hace
  falta limpiarla antes de la demo porque está apagada.
- PTZ (192.168.239.189) y Domo (192.168.239.174): **zona horaria corregida de China (UTC+8) a
  Argentina (UTC-3)** (29/09). Respaldo del `/ISAPI/System/time` original de cada una en el
  scratchpad de esa sesión. Cambio intencional y permanente, no hay que restaurarlo.

## Reglas: lo que falta del editor


- [ ] Botón "Probar": después de guardar, marcar en el feed el próximo evento de esa regla.
- [ ] Horario de armado de la regla (`/ISAPI/Event/schedules/...`), hoy queda como esté en la cámara.
- [ ] Vinculación del evento (`/ISAPI/Event/triggers/<evento>-<canal>`): sin notificación "center"
      la regla existe pero no avisa. Hoy se asume que ya está configurada.

## Fase 2 (anteproyecto): capacidades y matriz

- [x] Catálogo de 11 funciones, motor de detección (declarada vs verificada) y página de matriz
      con exportación a CSV.
- [x] Seis funciones comunes por ISAPI: estado, hora, OSD, imagen, movimiento y reinicio.
- [x] Las mismas por ONVIF, escritas y sin verificar (falta habilitar ONVIF en las cámaras).
- [x] **Verificar la columna ONVIF contra hardware.** Cerrado el 29/09 en las dos cámaras
      Hikvision reales — es la comparación central del anteproyecto. Ver `07-resultados.md` §7.4
      y §7.9 (matriz filtrada a las dos cámaras reales).
- [x] **Pantalla de funciones comunes en el detalle de cámara** (29/09): pestaña nueva
      "Funciones" (`frontend/src/features/cameras/FunctionsTab.tsx`), ISAPI y ONVIF lado a lado
      —estado, hora con sincronización, OSD, imagen y movimiento editables por ISAPI (ONVIF en
      solo lectura, porque el driver ONVIF de este trabajo no implementa esos `Set*` — ver
      `07-resultados.md` §7.4) y reinicio por cualquiera de los dos protocolos. Probada de punta a
      punta contra el simulador: guardado de OSD verificado con una relectura real por API, y el
      panel ONVIF muestra el error de conexión sin romper la pantalla cuando ese protocolo no
      responde (el caso real de un simulador que no habla ONVIF).
- [x] **Exportar la matriz también a Markdown** (29/09): botón nuevo al lado de "Exportar CSV" en
      la pantalla Matriz (`frontend/src/features/matrix/MatrixPage.tsx`). Usado para llenar
      `docs/tesis/07-resultados.md` §7.9 y guardar la evidencia completa en
      `docs/evidencias/matriz/`.

## Fase 5 (anteproyecto): evidencia

- [x] **Corredor de experimentos** (`backend/tools/experiments`): N repeticiones de cada función
      por protocolo y cámara, con reconocimiento previo para no colgarse con cámaras
      inalcanzables. Exporta CSV y Markdown a `docs/evidencias/experimentos/<fecha>/`.
      `uv run python -m tools.experiments --repeticiones 30`. 15 tests nuevos (6 unitarios de
      percentiles/export, 9 de integración contra el simulador... en realidad son 3 de
      integración + 6 unitarios, revisar conteo exacto en el commit).
- [x] Primera corrida real hecha (30/09, con el simulador y las 3 cámaras reales inalcanzables
      desde esta red): confirma que el mecanismo de "no alcanzable" no cuelga con cámaras que no
      responden, y que la VPN duplica el timeout como corresponde (8s LAN, 16s la de Sarmiento).
- [ ] Cuando haya cámaras reales, correr de nuevo para tener las latencias de verdad (las de
      ahora son solo del simulador, útiles para probar el mecanismo, no para citar en la tesis).

## Simulador

- [x] Cámara simulada con los tres perfiles (`backend/tools/simulator`), con las rarezas del
      hardware reproducidas y 10 tests.
- [ ] El simulador no habla ONVIF ni RTSP: la prueba de conexión marca esas dos en rojo. Si hace
      falta demostrar el vivo sin cámaras, se puede publicar un archivo de video en MediaMTX.
- [x] Grabador de fixtures (`tools/recorder`): barre ~60 endpoints, sanitiza y deja índice.

## Evidencia para cuando haya acceso al hardware

- [x] Grabador de respuestas: `uv run python -m tools.recorder --host <ip> --clave <clave>`.
- [x] Grabación de video continua por cámara (botón en la pestaña "Vivo"), en segmentos de 10 min.
- [x] **Grabación de video probada de punta a punta contra la PTZ real (29/09).** Se descargó
      ffmpeg (build de gyan.dev, en el scratchpad de la sesión — no resultó ni siquiera necesario
      para esta prueba: MediaMTX graba directo de la cámara, sin ffmpeg de por medio; sirve para
      inspeccionar los archivos con `ffprobe`/`ffmpeg`, como se hizo acá). Se encendió la
      grabación por API (`POST .../recording?enabled=true`), apareció un `.mp4` real en
      `backend/media/grabaciones/` a los pocos segundos, `ffprobe` confirmó video H.264 real
      (4096×2160, el streaming principal de la PTZ) creciendo mientras grababa, y un frame
      extraído mostró la escena real de la oficina con el timestamp de la propia cámara. Apagada
      la grabación después de confirmar (quedó un archivo de ~93 MB de prueba, no versionado —
      `backend/media/` está en `.gitignore`).
- [ ] Vincular las grabaciones con los episodios de eventos por rango de tiempo, para poder abrir
      el video del momento exacto de un evento.
- [ ] Cuando vuelvas a tener las cámaras, en este orden: correr el grabador en las dos, encender
      la grabación de video, y recién entonces hacer las pruebas (cruzar la línea, etc.).

## Código

- [x] **El backend se cuelga al recargar (`--reload`) — causa encontrada, no se arregla desde
      acá.** Se creía resuelto (el feed SSE
      escucha `bus.cerrando`), pero se reprodujo de nuevo y esta vez se leyó el propio código
      fuente de uvicorn instalado (`uvicorn.server.Server.shutdown`) en vez de suponer: confirma
      que uvicorn espera a que **todas** las conexiones HTTP terminen (`_wait_tasks_to_complete`,
      **sin timeout por defecto**) *antes* de mandarle el shutdown al `lifespan` de la app. Un SSE
      que solo se corta escuchando ese mismo shutdown nunca lo ve — el candado circular que ya se
      sospechaba, confirmado línea por línea.

      **Arreglo**: `app/main.py` ahora instala sus propios manejadores de SIGINT/SIGTERM que
      cortan el bus (`bus.close()`) apenas llega la señal del sistema operativo, **antes** de que
      uvicorn arranque su espera, y después encadenan con el manejador que uvicorn ya había
      instalado (para no pisarle su propio apagado). 3 tests nuevos que prueban el encadenamiento
      en sí (`backend/tests/unit/test_shutdown_signals.py`); 120/120 tests en verde.

      **Corrección (01/10): el arreglo de las señales NO alcanzaba, y la confirmación del 30/09
      estaba mal hecha.** Las tres recargas limpias que se tomaron como prueba no tenían ninguna
      conexión SSE abierta (el `curl` de prueba ya había expirado), así que no probaban nada: una
      recarga sin conexiones abiertas funciona igual con o sin el arreglo. Con el navegador
      abierto en la aplicación —que mantiene el feed de eventos conectado— el cuelgue se reprodujo
      igual el 01/10.

      **Causa real, encontrada el 01/10 — y las dos explicaciones anteriores estaban equivocadas.**
      Se probó con el feed abierto y `--timeout-graceful-shutdown 3` puesto, y se colgó igual. La
      pista decisiva: **"Shutting down" no aparece nunca en el log**. Si ese mensaje no sale,
      `Server.shutdown()` jamás se llamó, así que el problema no está en cómo uvicorn apaga la app
      — está antes, en que **el worker nunca se entera de que tiene que apagarse**.

      Leyendo `uvicorn/supervisors/basereload.py`, el recargador en Windows hace:

      ```python
      os.kill(self.process.pid, signal.CTRL_C_EVENT)
      ```

      `CTRL_C_EVENT` en Windows no se entrega a un PID: se entrega al **grupo de procesos de una
      consola**. Cuando el servidor se lanza sin consola adjunta —como lo lanza el entorno de
      desarrollo de este proyecto— ese evento no llega a ningún lado. El propio uvicorn tiene un
      parche al lado (`sys.stdout.write(" ")` "para asegurar que el evento se procese") que delata
      lo frágil que es el mecanismo.

      Conclusión: **no hay ninguna señal que atrapar**, así que ni los manejadores de
      SIGINT/SIGTERM de `app/main.py` ni `--timeout-graceful-shutdown` pueden resolverlo — los dos
      actúan después de un disparador que nunca ocurre. Se dejan igual porque no molestan y sí
      ayudan cuando el apagado viene por una vía que sí entrega señal (Ctrl+C en una terminal de
      verdad, o `preview_stop`).

      **No se va a seguir persiguiendo**: es una limitación del recargador de uvicorn en Windows
      sin consola, no un defecto de esta plataforma, y no afecta ni los resultados ni la demo. La
      salida práctica es reiniciar el proceso en vez de confiar en `--reload` cuando la aplicación
      está abierta en el navegador.
- [ ] 4 advertencias de lint en `frontend/src/features/events/` (estilo de React, no rompen nada).
- [ ] `GET /api/events/{id}` no existe: hoy el detalle se arma con el listado.
- [ ] Endpoint de estadísticas agregadas (hoy los contadores se calculan en el navegador sobre los
      últimos 300 episodios).
