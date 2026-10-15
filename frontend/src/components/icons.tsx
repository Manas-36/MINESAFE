const s = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

export const IMine = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M3 20h18" /><path d="M5 20V11a7 7 0 0 1 14 0v9" /><path d="M9 20v-5h6v5" /></svg>
);
export const IWorkers = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M5 10a7 7 0 0 1 14 0" /><path d="M4 10h16" /><path d="M8 10v1a4 4 0 0 0 8 0v-1" /><path d="M5 21a7 5 0 0 1 14 0" /></svg>
);
export const IGas = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M4 12c3-4 5 4 8 0s5 4 8 0" /><path d="M4 7c3-4 5 4 8 0s5 4 8 0" /><path d="M4 17c3-4 5 4 8 0s5 4 8 0" /></svg>
);
export const INetwork = () => (
  <svg viewBox="0 0 24 24" {...s}><circle cx="5" cy="12" r="2.2" /><circle cx="12" cy="6" r="2.2" /><circle cx="19" cy="12" r="2.2" /><circle cx="12" cy="18" r="2.2" /><path d="M7 11l3-3.5M14 7.5l3 3.5M17 13l-3 3.5M10 16.5 7 13" /></svg>
);
export const IEntry = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z" /><path d="m8.5 12 2.5 2.5 4.5-5" /></svg>
);
export const ILog = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M7 4h10a2 2 0 0 1 2 2v14l-3-2-3 2-3-2-3 2V6a2 2 0 0 1 2-2" transform="translate(-2 0)" /><path d="M8 9h6M8 13h6" /></svg>
);
export const ISetup = () => (
  <svg viewBox="0 0 24 24" {...s}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></svg>
);
export const IBell = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0" /></svg>
);
export const IExit = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M14 4h5v16h-5" /><path d="M10 8l-4 4 4 4" /><path d="M6 12h10" /></svg>
);
export const IClose = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M6 6l12 12M18 6 6 18" /></svg>
);
export const IAlertTri = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></svg>
);
export const ICheck = () => (
  <svg viewBox="0 0 24 24" {...s}><path d="m5 12 5 5 9-10" /></svg>
);
export const IFocus = () => (
  <svg viewBox="0 0 24 24" {...s}><circle cx="12" cy="12" r="3" /><path d="M3 9V5a2 2 0 0 1 2-2h4M15 3h4a2 2 0 0 1 2 2v4M21 15v4a2 2 0 0 1-2 2h-4M9 21H5a2 2 0 0 1-2-2v-4" /></svg>
);
