import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* 2. Wrap App with HelmetProvider */}
    <HelmetProvider>
      <App />
    </HelmetProvider>
  </StrictMode>,
)
