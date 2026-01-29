// import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

console.log("Main.tsx executing...");

const root = document.getElementById('root');
if (!root) console.error("Root not found!");
else {
  console.log("Root found, attempting mount...");
  createRoot(root).render(
    // <StrictMode>
    <App />
    // </StrictMode>,
  )
}
