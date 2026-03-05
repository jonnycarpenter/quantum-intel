import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PinnedItemsProvider } from './context/PinnedItemsContext'
import './index.css'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,    // 2 min
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <PinnedItemsProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </PinnedItemsProvider>
    </QueryClientProvider>
  </StrictMode>,
)
