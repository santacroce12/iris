import { createBrowserRouter } from 'react-router'

import { Layout } from '@/app/Layout'
import { CameraDetailPage } from '@/features/cameras/CameraDetailPage'
import { CamerasPage } from '@/features/cameras/CamerasPage'
import { ComingSoon } from '@/app/ComingSoon'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <CamerasPage /> },
      { path: 'camaras/:cameraId', element: <CameraDetailPage /> },
      {
        path: 'eventos',
        element: (
          <ComingSoon title="Eventos en vivo" phase="Fase 3">
            Feed en tiempo real del alertStream de cada cámara, con la foto del evento, filtros y
            galería.
          </ComingSoon>
        ),
      },
      {
        path: 'matriz',
        element: (
          <ComingSoon title="Matriz de compatibilidad" phase="Fase 2">
            Cada función comparada por ISAPI, ONVIF y RTSP en todas las cámaras.
          </ComingSoon>
        ),
      },
    ],
  },
])
