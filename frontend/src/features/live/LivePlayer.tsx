import Hls from 'hls.js'
import { Loader2, RefreshCw, VideoOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import type { LiveUrls } from '@/api/types'
import { Badge, Button } from '@/components/ui'

type Transport = 'webrtc' | 'hls'
type State = 'connecting' | 'playing' | 'failed'

/** WHEP: el navegador manda una oferta SDP y MediaMTX contesta; latencia típica < 500 ms. */
async function playWebrtc(video: HTMLVideoElement, whepUrl: string): Promise<RTCPeerConnection> {
  const pc = new RTCPeerConnection()
  pc.addTransceiver('video', { direction: 'recvonly' })
  pc.addTransceiver('audio', { direction: 'recvonly' })
  pc.ontrack = (event) => {
    if (video.srcObject !== event.streams[0]) video.srcObject = event.streams[0]
  }
  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)
  const response = await fetch(whepUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/sdp' },
    body: offer.sdp,
  })
  if (!response.ok) {
    pc.close()
    throw new Error(`WHEP ${response.status}`)
  }
  await pc.setRemoteDescription({ type: 'answer', sdp: await response.text() })
  return pc
}

export function LivePlayer({ urls, onRetry }: { urls: LiveUrls; onRetry: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [transport, setTransport] = useState<Transport>('webrtc')
  const [state, setState] = useState<State>('connecting')

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    let pc: RTCPeerConnection | undefined
    let hls: Hls | undefined
    let cancelled = false
    setState('connecting')

    const onPlaying = () => setState('playing')
    video.addEventListener('playing', onPlaying)

    const fail = () => {
      if (cancelled) return
      // WebRTC puede fallar por ICE (Docker/VPN): HLS tiene más latencia pero pasa por HTTP.
      if (transport === 'webrtc') setTransport('hls')
      else setState('failed')
    }

    if (transport === 'webrtc') {
      playWebrtc(video, urls.whep)
        .then((conn) => {
          if (cancelled) return conn.close()
          pc = conn
          conn.onconnectionstatechange = () => {
            if (conn.connectionState === 'failed') fail()
          }
        })
        .catch(fail)
      // Si en 12 s no arrancó (p. ej. la cámara tarda en entregar el primer keyframe), pasa a HLS.
      const timer = setTimeout(() => video.readyState < 2 && fail(), 12000)
      return () => {
        cancelled = true
        clearTimeout(timer)
        video.removeEventListener('playing', onPlaying)
        pc?.close()
        video.srcObject = null
      }
    }

    if (Hls.isSupported()) {
      hls = new Hls({ liveSyncDurationCount: 2 })
      hls.loadSource(urls.hls)
      hls.attachMedia(video)
      hls.on(Hls.Events.ERROR, (_, data) => data.fatal && fail())
    } else {
      video.src = urls.hls
    }
    // hls.js reintenta el manifiesto un buen rato: se corta antes para mostrar el error.
    const timer = setTimeout(() => video.readyState < 2 && fail(), 20000)
    return () => {
      cancelled = true
      clearTimeout(timer)
      video.removeEventListener('playing', onPlaying)
      hls?.destroy()
    }
  }, [transport, urls])

  return (
    <div className="relative aspect-video overflow-hidden rounded-xl border border-line bg-black">
      <video ref={videoRef} autoPlay muted playsInline className="size-full object-contain" />
      <div className="absolute top-3 left-3 flex gap-2">
        {state === 'playing' && (
          <Badge tone="bad" className="bg-black/60">
            <span className="size-1.5 animate-pulse rounded-full bg-bad" /> EN VIVO
          </Badge>
        )}
        <Badge className="bg-black/60 font-mono uppercase">{transport}</Badge>
      </div>
      {state !== 'playing' && (
        <div className="absolute inset-0 grid place-items-center bg-black/60">
          {state === 'connecting' ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 className="size-4 animate-spin" />
              Conectando por {transport === 'webrtc' ? 'WebRTC' : 'HLS'}…
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 text-sm text-muted">
              <VideoOff className="size-7" />
              No se pudo reproducir el video.
              <Button
                icon={<RefreshCw className="size-4" />}
                onClick={() => {
                  setTransport('webrtc')
                  onRetry()
                }}
              >
                Reintentar
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
