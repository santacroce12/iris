import { createBrowserRouter } from 'react-router'

import { Layout } from '@/app/Layout'
import { CameraDetailPage } from '@/features/cameras/CameraDetailPage'
import { CamerasPage } from '@/features/cameras/CamerasPage'
import { ComingSoon } from '@/app/ComingSoon'
import { EventsPage } from '@/features/events/EventsPage'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <CamerasPage /> },
      { path: 'camaras/:cameraId', element: <CameraDetailPage /> },
      { path: 'eventos', element: <EventsPage /> },
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
