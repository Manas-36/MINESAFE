# MineSafe Control (frontend)

Source of the 3D control-room app served by `hub/admin_hub.py` at `/control/`. Full guide: [../docs/control_app.md](../docs/control_app.md).

```
npm install
npm run dev     # http://localhost:5173/control/  (proxies /api to the hub on :5000, or HUB_URL)
npm run build   # → ../hub/control (commit it; the hub serves it, no Node needed on the laptop)
```

| Folder | |
|---|---|
| `src/api.ts` | types for the hub's `/api/state`, polling, every action (alert, evacuate, danger zone, entry approve) |
| `src/store.tsx` | live state (polled every second), connection health, page + selection |
| `src/scene/` | the 3D mine: tunnels from the map, repeaters + LED exit signs, workers, danger zones, routes |
| `src/pages/`, `src/panels/` | Mine, Workers, Gas & air, Network, Entry, Log; worker / repeater detail panels |
| `src/components/` | top bar, alert + evacuation dialogs, banners, navigation, charts |
