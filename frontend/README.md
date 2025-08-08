# Case Management Suite - React Frontend

A modern React frontend for the Case Management Suite, built with Vite, Tailwind CSS, and integrated with the FastAPI backend.

## 🚀 Features

- **Modern React 18** with hooks and functional components
- **Vite** for fast development and building
- **Tailwind CSS** for styling with custom design system
- **React Router** for client-side routing
- **React Query** for data fetching and caching
- **Lucide React** for beautiful icons
- **React Hook Form** for form management
- **React Hot Toast** for notifications
- **Framer Motion** for animations

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Header.jsx      # Main navigation header
│   ├── Sidebar.jsx     # Sidebar navigation
│   └── StatsCard.jsx   # Statistics card component
├── pages/              # Page components
│   ├── CaseManagement.jsx
│   ├── HousingSearch.jsx
│   ├── AIChat.jsx
│   ├── SmartDaily.jsx
│   ├── Benefits.jsx
│   ├── Legal.jsx
│   ├── Resume.jsx
│   └── Services.jsx
├── App.jsx             # Main app component with routing
├── main.jsx           # React entry point
└── index.css          # Global styles and Tailwind
```

## 🛠️ Development

### Prerequisites

- Node.js 16+ 
- npm or yarn

### Installation

```bash
npm install
```

### Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## 🔗 API Integration

The frontend is configured to proxy API requests to the FastAPI backend running on `http://localhost:8000`. Key integrations include:

- **Enhanced AI Module**: `/api/ai-enhanced/chat` for AI chat functionality
- **Enhanced Reminders**: `/api/reminders-enhanced/` for task management
- **Search System**: `/api/search/` for unified search functionality
- **Case Management**: `/api/clients` for client data

## 🎨 Design System

The frontend uses a custom design system with:

- **Color Palette**: Primary gradients and semantic colors
- **Typography**: Inter font family
- **Spacing**: Consistent spacing scale
- **Components**: Reusable card, button, and form components
- **Animations**: Smooth transitions and micro-interactions

## 📱 Responsive Design

The interface is fully responsive and works on:
- Desktop (1200px+)
- Tablet (768px - 1199px)
- Mobile (320px - 767px)

## 🔧 Configuration

### Vite Configuration
- React plugin for JSX support
- Proxy configuration for API calls
- Build optimization

### Tailwind Configuration
- Custom color palette
- Custom animations
- Responsive breakpoints
- Component utilities

## 🚀 Deployment

The frontend can be deployed to any static hosting service:

1. Build the project: `npm run build`
2. Deploy the `dist/` folder to your hosting service
3. Configure the API endpoint for production

## 🔄 State Management

- **Local State**: React hooks for component state
- **Server State**: React Query for API data
- **Form State**: React Hook Form for form management
- **Global State**: Context API for app-wide state (if needed)

## 📊 Performance

- **Code Splitting**: Automatic route-based code splitting
- **Lazy Loading**: Components loaded on demand
- **Optimized Builds**: Vite's fast build system
- **Caching**: React Query for intelligent caching

## 🧪 Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm test -- --watch
```

## 📝 Contributing

1. Follow the existing code style
2. Use TypeScript for new components (optional)
3. Add tests for new features
4. Update documentation as needed

## 🔗 Backend Integration

This frontend is designed to work with the Case Management Suite FastAPI backend. Make sure the backend is running on `http://localhost:8000` for full functionality. 