import { createBrowserRouter } from 'react-router'

import { Layout } from '@/app/Layout'
import { CameraDetailPage } from '@/features/cameras/CameraDetailPage'
import { CamerasPage } from '@/features/cameras/CamerasPage'
import { EventsPage } from '@/features/events/EventsPage'
import { MatrixPage } from '@/features/matrix/MatrixPage'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <CamerasPage /> },
      { path: 'camaras/:cameraId', element: <CameraDetailPage /> },
      { path: 'eventos', element: <EventsPage /> },
      { path: 'matriz', element: <MatrixPage /> },
    ],
  },
])
