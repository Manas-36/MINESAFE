import { Banners, Rail, TopBar } from './components/chrome';
import { Toasts } from './components/common';
import MinePage from './pages/MinePage';
import { EntryPage, GasPage, LogPage, NetworkPage, WorkersPage } from './pages/Pages';
import { StoreProvider, useStore } from './store';
import { HUB } from './api';

function Boot() {
  const { error } = useStore();
  return (
    <div className="boot">
      <div>
        <span className="badge"><img src={`${import.meta.env.BASE_URL}logo_icon.png`} alt="MineSafe logo" /></span>
        <h1>Mine<span style={{ color: 'var(--amber)' }}>Safe</span> control room</h1>
        {error ? (
          <>
            <p>Can't reach the hub{HUB ? ` at ${HUB}` : ''}: {error}.</p>
            <p>Start it on the control-room laptop with <span className="mono">start_admin.bat</span> (or <span className="mono">python admin_hub.py</span>), and make sure this device is on the same Wi-Fi. This page keeps trying every second.</p>
          </>
        ) : <p>Connecting to the hub…</p>}
      </div>
    </div>
  );
}

function Shell() {
  const { s, page } = useStore();
  if (!s) return <Boot />;
  return (
    <div className="app">
      <TopBar />
      <Banners />
      <Rail />
      <main>
        <div style={{ display: page === 'mine' ? 'contents' : 'none' }}><MinePage /></div>
        {page === 'workers' && <WorkersPage />}
        {page === 'gas' && <GasPage />}
        {page === 'network' && <NetworkPage />}
        {page === 'entry' && <EntryPage />}
        {page === 'log' && <LogPage />}
      </main>
      <Toasts />
    </div>
  );
}

export default function App() {
  return <StoreProvider><Shell /></StoreProvider>;
}
