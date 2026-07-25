import './App.css'
import { Dashboard } from './Dashboard'

import { Toaster } from 'sonner'

function App() {
  return (
    <>
      <Dashboard />
      <Toaster position="top-right" richColors />
    </>
  )
}

export default App
