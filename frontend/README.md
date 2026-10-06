# CrimeGraph AI frontend

This React/Vite application is the investigator workspace for CrimeGraph AI. It calls the FastAPI backend through the Vite `/api` proxy and uses Cytoscape.js to render case entities and relationships.

From the repository root, start the backend first as described in [`../README.md`](../README.md), then run:

```powershell
cd frontend
npm install
npm run dev
```

The development server normally runs at `http://localhost:5173`. The API proxy expects FastAPI at `http://127.0.0.1:8000`.

Useful checks:

```powershell
npm run lint
npm run build
```
