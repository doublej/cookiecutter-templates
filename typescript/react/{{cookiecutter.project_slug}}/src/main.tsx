import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { getLocale } from './paraglide/runtime'

document.documentElement.lang = getLocale()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
