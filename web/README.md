# Guardia AI Web Dashboard

Next.js-based operator dashboard for real-time security monitoring and event management.

## Features

- **Authentication**: JWT-based login with role-based access control
- **Live Dashboard**: Real-time event timeline with WebSocket updates
- **Camera Views**: Live camera preview grid
- **Event Management**: Acknowledge, filter, and search security events
- **Analytics**: Visual charts for events by severity, class, and camera
- **Responsive Design**: TailwindCSS + Radix UI for modern, accessible UI
- **Dark Mode**: System-aware dark mode support

---

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **Components**: Radix UI primitives
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Charts**: Recharts
- **API Client**: Axios

---

## Getting Started

### Install Dependencies

```bash
npm install
```

### Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8007
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
npm start
```

---

## Authentication

Default credentials (change in production):
- **Username**: `admin`
- **Password**: `guardia_admin`

---

## Project Structure

```
web/
├── src/
│   ├── app/                    # Next.js app router pages
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home (redirect)
│   │   ├── login/              # Login page
│   │   └── dashboard/          # Dashboard page
│   ├── components/
│   │   ├── ui/                 # Radix UI components
│   │   ├── layout/             # Layout components
│   │   └── dashboard/          # Dashboard-specific components
│   ├── lib/
│   │   ├── api.ts              # API client & types
│   │   ├── store.ts            # Zustand stores (auth, WebSocket)
│   │   └── utils.ts            # Utility functions
│   └── styles/
│       └── globals.css         # Global styles
├── public/                     # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

---

## Key Components

### Dashboard Layout
- Header with user info, logout button
- Responsive navigation

### Event Timeline
- Real-time event updates via WebSocket
- Filter by severity (critical, high, medium, low)
- Acknowledge events inline
- View video clips

### Live Cameras
- Grid view of all cameras
- Status indicators (online/offline)
- Placeholder for live MJPEG/WebRTC streams

### Analytics
- Pie chart: Events by severity
- Bar chart: Events by class
- Date range filtering (future enhancement)

---

## API Integration

The dashboard communicates with the FastAPI backend:

### Auth Endpoints
- `POST /auth/login` - Login and get JWT
- `GET /auth/me` - Get current user

### Events Endpoints
- `GET /events` - List events with filtering
- `PATCH /events/{id}/acknowledge` - Acknowledge event

### Analytics Endpoints
- `POST /analytics` - Get aggregated statistics

### WebSocket
- `ws://localhost:8007/ws/alerts` - Real-time event stream

---

## Customization

### Theme Colors

Edit `tailwind.config.js` and `src/styles/globals.css` to customize colors.

### Adding Features

1. **Video Player**: Integrate video.js or react-player for clip playback
2. **WebRTC Streams**: Use simple-peer or LiveKit for real-time camera feeds
3. **Search**: Add full-text search with fuzzy matching
4. **Export**: CSV/PDF export for reports
5. **Notifications**: Browser push notifications for critical events

---

## Docker Deployment

```bash
# Build image
docker build -t guardia-web .

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://api:8000 \
  -e NEXT_PUBLIC_WS_URL=ws://alerts:8007 \
  guardia-web
```

---

## Performance

- **Code Splitting**: Automatic per-route
- **Image Optimization**: Next.js Image component
- **Lazy Loading**: React.lazy for heavy components
- **Caching**: React Query with stale-while-revalidate

---

## Accessibility

- ARIA labels on interactive elements
- Keyboard navigation support
- Screen reader friendly
- Focus management

---

## Security

- JWT tokens stored in localStorage (consider httpOnly cookies for production)
- CORS configured in API
- Input validation on forms
- XSS protection via React's escaping

---

## Future Enhancements

- [ ] Multi-language support (i18n)
- [ ] Advanced filtering (date range, multi-camera)
- [ ] User management page (admin only)
- [ ] Model registry viewer
- [ ] System health monitoring
- [ ] Audit log viewer
- [ ] Mobile responsive improvements
- [ ] PWA support for offline mode

---

**Guardia AI Web** - Modern operator interface for proactive security intelligence.
