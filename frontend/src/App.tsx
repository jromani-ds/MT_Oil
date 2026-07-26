import { ErrorBoundary } from './components/ErrorBoundary';
import './App.css'
import { Dashboard } from './Dashboard'

import { Toaster } from 'sonner'

function App() {
  return (
    <ErrorBoundary>
      <Dashboard />
      <Toaster position="top-right" richColors />
    </ErrorBoundary>
  )
}

export default App
