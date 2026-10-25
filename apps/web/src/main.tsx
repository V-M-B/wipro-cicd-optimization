import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ApiProvider } from './api/ApiProvider';
import { App } from './App';
import { ApiClient } from './lib/api';
import './styles.css';

const api = new ApiClient({ baseUrl: import.meta.env.VITE_API_BASE_URL ?? '' });

const root = document.getElementById('root');
if (!root) throw new Error('Missing #root element');

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <ApiProvider api={api}>
        <App />
      </ApiProvider>
    </BrowserRouter>
  </StrictMode>,
);
