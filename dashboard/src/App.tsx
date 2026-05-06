import { useState, useCallback, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import type { ChartOptions, ChartDataset } from 'chart.js';
import { useApi } from './useApi';
import type { SimConfig, SupervisorVerdict, LLMActionPayload } from './types';

// -- Constants ---------------------------------------------------------------
const WINDOW_OPTIONS = [60, 120, 300, 600] as const;
const SPEED_OPTIONS  = [0.25, 0.5, 1, 2, 5, 10] as const;

const SP = {
  temp: { lo: 18,  hi: 22,   set: 20  },
  co2:  { lo: 600, hi: 1000, set: 800 },
  rh:   { lo: 40,  hi: 85,   set: 85  },
} as const;

const STORAGE_KEY = 'gh_ctrl_settings';

type Tab = 'thermals' | 'actuators' | 'weather' | 'ood';

// -- Chart helpers -----------------------------------------------------------
const BASE_OPTS: ChartOptions<'line'> = {
  animation: false,
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index' as const, intersect: false },
  plugins: {
    legend: {
      position: 'top' as const,
      labels: {
        boxWidth: 12, color: '#8b949e', font: { size: 11 },
        filter: (item) => !item.text.startsWith('__'),
      },
    },
    tooltip: {
      backgroundColor: '#1c2128', borderColor: '#30363d', borderWidth: 1,
      titleColor: '#e6edf3', bodyColor: '#8b949e',
    },
  },
  scales: {
    x: {
      ticks: { maxTicksLimit: 8, color: '#8b949e', font: { size: 10 } },
      grid:  { color: '#21262d' },
    },
    y: {
      ticks: { color: '#8b949e', font: { size: 10 } },
      grid:  { color: '#21262d' },
    },
  },
};

function chartOpts(yLabel: string, yMin?: number, yMax?: number): ChartOptions<'line'> {
  return {
    ...BASE_OPTS,
    scales: {
      x: BASE_OPTS.scales!.x,
      y: {
        ...BASE_OPTS.scales!.y,
        ...(yMin !== undefined ? { min: yMin } : {}),
        ...(yMax !== undefined ? { max: yMax } : {}),
        title: { display: true, text: yLabel, color: '#8b949e', font: { size: 11 } },
      },
    },
  };
}

function lds(label: string, data: number[], color: string, fill = false): ChartDataset<'line'> {
  return {
    label, data, borderColor: color,
    backgroundColor: fill ? `${color}28` : 'transparent',
    borderWidth: 2, pointRadius: 0, tension: 0.3, fill,
  } as ChartDataset<'line'>;
}

/** Two datasets that render a filled band between lo and hi. Upper dataset is hidden from legend. */
function bandLds(
  label: string, n: number, lo: number, hi: number, color: string,
): [ChartDataset<'line'>, ChartDataset<'line'>] {
  const flat = (v: number) => Array(n).fill(v) as number[];
  const base = { pointRadius: 0, borderWidth: 0, tension: 0, borderColor: 'transparent' as const };
  return [
    { ...base, label: '__band_hi', data: flat(hi), backgroundColor: 'transparent', fill: false } as unknown as ChartDataset<'line'>,
    { ...base, label, data: flat(lo), backgroundColor: `${color}28`, fill: '-1' } as unknown as ChartDataset<'line'>,
  ];
}

function flatLds(label: string, n: number, value: number, color: string): ChartDataset<'line'> {
  return {
    label, data: Array(n).fill(value) as number[],
    borderColor: color, backgroundColor: 'transparent',
    borderWidth: 1, borderDash: [5, 5], pointRadius: 0, fill: false, tension: 0,
  } as unknown as ChartDataset<'line'>;
}

// -- Sub-components ----------------------------------------------------------
function StatusDot({ on }: { on: boolean }) {
  return (
    <span style={{
      display: 'inline-block', width: 10, height: 10,
      borderRadius: '50%', flexShrink: 0,
      background: on ? 'var(--green)' : 'var(--red)',
      transition: 'background .3s',
    }} />
  );
}

function MetricCard({ label, value, unit, lo, hi }: {
  label: string; value: number | null; unit: string; lo?: number; hi?: number;
}) {
  const display = value != null ? value.toFixed(1) : '\u2014';
  let inRange: boolean | null = null;
  if (value != null && lo !== undefined && hi !== undefined) {
    inRange = value >= lo && value <= hi;
  }
  const color = inRange === null ? 'var(--text)' : inRange ? 'var(--green)' : 'var(--red)';
  return (
    <div className="metric-card">
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value" style={{ color }}>
        {display} <span className="metric-card__unit">{unit}</span>
      </div>
      {lo !== undefined && hi !== undefined && (
        <div className="metric-card__delta">target {lo}&ndash;{hi}</div>
      )}
    </div>
  );
}

function LogEntry({ entry }: { entry: SupervisorVerdict }) {
  return (
    <div className="log-entry">
      <div className="log-header">
        <span className="log-step">Step {entry.step}</span>
        <span className={`badge badge--${entry.decision}`}>{entry.decision}</span>
        <span className="log-conf">{((entry.confidence ?? 0) * 100).toFixed(0)}%</span>
      </div>
      {entry.reason && <div className="log-reason">{entry.reason}</div>}
    </div>
  );
}

function LLMLogEntry({ entry }: { entry: LLMActionPayload }) {
  return (
    <div className="log-entry">
      <div className="log-header">
        <span className="log-step">Step {entry.step}</span>
        <span className="badge badge--APPROVE">LLM</span>
      </div>
      {entry.reasoning && <div className="log-reason">{entry.reasoning}</div>}
    </div>
  );
}

function ChartCard({ title, height, children }: {
  title: string; height: number; children: React.ReactNode;
}) {
  return (
    <div className="chart-wrap">
      <div className="chart-label">{title}</div>
      <div style={{ height }}>{children}</div>
    </div>
  );
}

// -- Config panel ------------------------------------------------------------
function ConfigPanel({
  config, onSave,
}: {
  config: SimConfig | null;
  onSave: (c: SimConfig) => void;
}) {
  const [local, setLocal] = useState<SimConfig | null>(config);

  useEffect(() => { if (config && !local) setLocal(config); }, [config]);

  if (!local) return <div style={{ color: 'var(--muted)', fontSize: 12 }}>Loading config...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div className="cfg-row">
        <label>Start date</label>
        <input className="cfg-input" value={local.start_date}
          onChange={e => setLocal({ ...local, start_date: e.target.value })} />
      </div>
      <div className="cfg-row">
        <label>Season length (days)</label>
        <input className="cfg-input" type="number" min={1} max={365}
          value={local.n_days}
          onChange={e => setLocal({ ...local, n_days: parseInt(e.target.value, 10) || 60 })} />
      </div>
      <div className="cfg-row">
        <label>MPC horizon (steps)</label>
        <input className="cfg-input" type="number" min={5} max={96}
          value={local.mpc_horizon}
          onChange={e => setLocal({ ...local, mpc_horizon: parseInt(e.target.value, 10) || 20 })} />
      </div>
      <div className="cfg-row">
        <label>LLM call interval</label>
        <input className="cfg-input" type="number" min={1} max={96}
          value={local.llm_call_interval}
          onChange={e => setLocal({ ...local, llm_call_interval: parseInt(e.target.value, 10) || 1 })} />
      </div>
      <div className="cfg-row">
        <label>LLM history window</label>
        <input className="cfg-input" type="number" min={1} max={96}
          value={local.llm_history_window}
          onChange={e => setLocal({ ...local, llm_history_window: parseInt(e.target.value, 10) || 1 })} />
      </div>
      <button className="btn btn--primary" style={{ marginTop: 4 }}
        onClick={() => onSave(local)}>
        Save & Apply
      </button>
    </div>
  );
}

// -- Main App ----------------------------------------------------------------
export default function App() {
  const {
    state, startSim, stopSim, resetSim,
    setControl, setController, setAgent, updateConfig, fetchConfig,
  } = useApi();

  const [windowSize, setWindowSize]   = useState<number>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved).windowSize ?? 120 : 120;
  });
  const [activeTab, setActiveTab]     = useState<Tab>('thermals');
  const [speed, setSpeed]             = useState<number>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved).speed ?? 1 : 1;
  });
  const [showConfig, setShowConfig]   = useState(false);
  const [serverConfig, setServerConfig] = useState<SimConfig | null>(null);

  // Persist UI settings
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ windowSize, speed }));
  }, [windowSize, speed]);

  // Load server config once connected
  useEffect(() => {
    if (state.serverConnected && !serverConfig) {
      fetchConfig().then(cfg => { if (cfg) setServerConfig(cfg); });
    }
  }, [state.serverConnected, serverConfig, fetchConfig]);

  const handleSpeed = useCallback((s: number) => {
    setSpeed(s);
    setControl(false, s);
  }, [setControl]);

  const handlePause = useCallback(() => {
    setControl(!state.simPaused, speed);
  }, [state.simPaused, speed, setControl]);

  const handleControllerSwitch = useCallback((mode: 'mpc' | 'llm') => {
    setController(mode);
  }, [setController]);

  const handleAgentToggle = useCallback(() => {
    setAgent(!state.agentEnabled);
  }, [state.agentEnabled, setAgent]);

  const handleReset = useCallback(() => { resetSim(); }, [resetSim]);

  const handleSaveConfig = useCallback((cfg: SimConfig) => {
    setServerConfig(cfg);
    updateConfig(cfg);
  }, [updateConfig]);

  const n      = windowSize;
  const labels = state.timestamps.slice(-n);
  const tel    = state.latestTelemetry;
  const ood    = state.latestOOD;

  return (
    <div className="layout">

      <header className="header">
        <StatusDot on={state.serverConnected} />
        <h1 className="header__title">Greenhouse Control</h1>
        <span className="header__subtitle">
          {state.serverConnected
            ? (state.simRunning ? 'Running' : 'Stopped')
            : 'Offline'}
        </span>
        <span className="header__step">Step: <b>{state.simStep > 0 ? state.simStep : '\u2014'}</b></span>
      </header>

      <div className="metrics-bar">
        <MetricCard label="Indoor Temp"  value={tel?.t_in  ?? null} unit="°C"   lo={SP.temp.lo} hi={SP.temp.hi} />
        <MetricCard label="CO₂"          value={tel?.co2   ?? null} unit="ppm"  lo={SP.co2.lo}  hi={SP.co2.hi} />
        <MetricCard label="Humidity"     value={tel?.rh    ?? null} unit="%"    lo={SP.rh.lo}   hi={SP.rh.hi} />
        <MetricCard label="Outdoor Temp" value={tel?.T_out ?? null} unit="°C" />
        <MetricCard label="Solar Rad"    value={tel?.rad   ?? null} unit="W/m²" />
        <div className="window-select">
          <span>Window:</span>
          {WINDOW_OPTIONS.map(w => (
            <button key={w} className={`btn${windowSize === w ? ' btn--active' : ''}`}
              onClick={() => setWindowSize(w)}>{w}</button>
          ))}
        </div>
      </div>

      <div className="main-grid">

        <div className="charts-col">
          <div className="card">
            <div className="tabs">
              {(['thermals', 'actuators', 'weather', 'ood'] as Tab[]).map(tab => (
                <button key={tab}
                  className={`tab-btn${activeTab === tab ? ' tab-btn--active' : ''}`}
                  onClick={() => setActiveTab(tab)}>
                  {tab === 'thermals' ? 'Thermals'
                    : tab === 'actuators' ? 'Actuators'
                    : tab === 'weather' ? 'Weather'
                    : 'OOD'}
                </button>
              ))}
            </div>

            {activeTab === 'thermals' && (
              <div className="chart-col">
                <ChartCard title="Temperature (°C)" height={160}>
                  <Line data={{ labels, datasets: [
                    ...bandLds('Comfort zone (18–22°C)', labels.length, 18, 22, '#58a6ff'),
                    lds('Indoor', state.t_in.slice(-n), '#58a6ff', true),
                    lds('Outdoor', state.T_out.slice(-n), '#8b949e'),
                    flatLds('Setpoint 20°C', labels.length, 20, '#3fb950'),
                  ]}} options={chartOpts('°C')} />
                </ChartCard>
                <ChartCard title="CO₂ (ppm)" height={140}>
                  <Line data={{ labels, datasets: [
                    ...bandLds('Optimal range (600–1000 ppm)', labels.length, 600, 1000, '#d2a8ff'),
                    lds('CO₂', state.co2.slice(-n), '#d2a8ff', true),
                    flatLds('Setpoint 800 ppm', labels.length, 800, '#3fb950'),
                  ]}} options={chartOpts('ppm', 300, 1200)} />
                </ChartCard>
                <ChartCard title="Relative Humidity (%)" height={140}>
                  <Line data={{ labels, datasets: [
                    ...bandLds('Safe zone (40–85%)', labels.length, 40, 85, '#79c0ff'),
                    lds('RH', state.rh.slice(-n), '#79c0ff', true),
                    flatLds('Max 85%', labels.length, 85, '#f85149'),
                  ]}} options={chartOpts('%', 0, 100)} />
                </ChartCard>
              </div>
            )}

            {activeTab === 'actuators' && (
              <div className="chart-col">
                {(['uBoil','uCO2','uThScr','uVent','uLamp','uBlScr'] as const).map((key, i) => {
                  const labels2 = ['Boiler','CO₂ Inject','Thermal Screen','Ventilation','Lamps','Blackout Screen'];
                  const colors  = ['#ff7b72','#79c0ff','#d2a8ff','#56d364','#ffa657','#8b949e'];
                  return (
                    <ChartCard key={key} title={labels2[i]} height={120}>
                      <Line data={{ labels, datasets: [lds(labels2[i], state[key].slice(-n), colors[i], true)] }}
                        options={chartOpts('', 0, 1)} />
                    </ChartCard>
                  );
                })}
              </div>
            )}

            {activeTab === 'weather' && (
              <div className="chart-col">
                <ChartCard title="Solar Radiation (W/m²)" height={180}>
                  <Line data={{ labels, datasets: [lds('Radiation', state.rad.slice(-n), '#ffa657', true)] }}
                    options={chartOpts('W/m²', 0)} />
                </ChartCard>
                <ChartCard title="Outdoor Temperature (°C)" height={180}>
                  <Line data={{ labels, datasets: [lds('T_out', state.T_out.slice(-n), '#8b949e', true)] }}
                    options={chartOpts('°C')} />
                </ChartCard>
              </div>
            )}

            {activeTab === 'ood' && (
              <div className="chart-col">
                <ChartCard title="Mahalanobis Distance (OOD)" height={220}>
                  <Line data={{ labels, datasets: [
                    lds('Mahal. dist', state.mahal.slice(-n), '#ff7b72', true),
                    flatLds(`Threshold ${state.oodThreshold.toFixed(1)}`, labels.length, state.oodThreshold, '#f85149'),
                  ]}} options={chartOpts('distance', 0)} />
                </ChartCard>
              </div>
            )}
          </div>
        </div>

        <div className="controls-col">

          {/* Simulation start/stop */}
          <div className="card">
            <div className="card__title">Simulation</div>
            <div className="pause-row" style={{ gap: 8, flexWrap: 'wrap' }}>
              {!state.simRunning ? (
                <button className="btn btn--primary" style={{ flex: 1 }}
                  onClick={startSim} disabled={!state.serverConnected}>
                  &#9654; Start
                </button>
              ) : (
                <>
                  <button className="btn btn--warning" style={{ flex: 1 }}
                    onClick={handlePause}>
                    {state.simPaused ? '\u25BA Resume' : '\u23F8 Pause'}
                  </button>
                  <button className="btn" style={{ flex: 1 }}
                    onClick={stopSim}>
                    &#9632; Stop
                  </button>
                </>
              )}
              <button className="btn" style={{ flex: 1 }}
                onClick={handleReset} disabled={!state.serverConnected}
                title="Reset simulation episode">
                &#x21BA; Reset
              </button>
            </div>
            {state.simRunning && (
              <>
                <div className="speed-section-label" style={{ marginTop: 10 }}>Speed:</div>
                <div className="speed-btns">
                  {SPEED_OPTIONS.map(s => (
                    <button key={s}
                      className={`btn${speed === s && !state.simPaused ? ' btn--active' : ''}`}
                      disabled={state.simPaused}
                      onClick={() => handleSpeed(s)}>
                      {s}&times;
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Simulation config */}
          <div className="card">
            <div className="card__title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Config</span>
              <button className="btn" style={{ padding: '2px 8px', fontSize: 11 }}
                onClick={() => setShowConfig(v => !v)}>
                {showConfig ? 'Hide' : 'Edit'}
              </button>
            </div>
            {showConfig && (
              <ConfigPanel config={serverConfig} onSave={handleSaveConfig} />
            )}
            {!showConfig && serverConfig && (
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                {serverConfig.start_date} &bull; {serverConfig.n_days} days &bull; {serverConfig.controller_mode.toUpperCase()}
              </div>
            )}
          </div>

          {/* Controller select */}
          <div className="card">
            <div className="card__title">Controller</div>
            <div className="speed-btns">
              <button
                className={`btn${state.controllerMode === 'mpc' ? ' btn--active' : ''}`}
                onClick={() => handleControllerSwitch('mpc')} style={{ flex: 1 }}
                title="Physics-Informed SINDy MPC controller">
                MPC
              </button>
              <button
                className={`btn${state.controllerMode === 'llm' ? ' btn--active' : ''}`}
                onClick={() => handleControllerSwitch('llm')} style={{ flex: 1 }}
                title="Large Language Model autonomous controller">
                LLM
              </button>
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
              {state.controllerMode === 'mpc'
                ? 'Physics-Informed SINDy MPC with OOD detection.'
                : 'LLM autonomously decides all actuators from sensor data.'}
            </div>
          </div>

          {/* AI Supervisor (MPC only) */}
          {state.controllerMode === 'mpc' && (
            <div className="card">
              <div className="card__title">AI Supervisor</div>
              <div className="pause-row">
                <button
                  className={`btn${state.agentEnabled ? ' btn--active' : ' btn--warning'}`}
                  onClick={handleAgentToggle} style={{ minWidth: 110 }}>
                  {state.agentEnabled ? '\u2705 Enabled' : '\u274c Disabled'}
                </button>
                <span style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {state.agentEnabled ? 'LLM active' : 'Auto-approve'}
                </span>
              </div>
            </div>
          )}

          {/* OOD Monitor (MPC only) */}
          {state.controllerMode === 'mpc' && (
            <div className="card">
              <div className="card__title">OOD Monitor</div>
              <div className="ood-center">
                <div className="ood-value"
                  style={{ color: state.inDistribution === false ? 'var(--red)' : 'var(--text)' }}>
                  {ood?.mahalanobis_distance?.toFixed(2) ?? '\u2014'}
                </div>
                <div className="ood-sub">Mahalanobis distance</div>
                <span className={`ood-badge ${state.inDistribution === false ? 'ood-badge--ood' : 'ood-badge--safe'}`}>
                  {state.inDistribution === false ? 'OUT OF DIST.' : 'IN DISTRIBUTION'}
                </span>
              </div>
            </div>
          )}

          {/* Decision log */}
          <div className="card" style={{ flex: 1 }}>
            {state.controllerMode === 'mpc' ? (
              <>
                <div className="card__title">Supervisor Decisions</div>
                <div className="log-scroll">
                  {state.supervisorLog.length === 0
                    ? <div className="no-data">Waiting for decisions&hellip;</div>
                    : state.supervisorLog.map((e, i) => <LogEntry key={i} entry={e} />)}
                </div>
              </>
            ) : (
              <>
                <div className="card__title">LLM Actions</div>
                <div className="log-scroll">
                  {state.llmLog.length === 0
                    ? <div className="no-data">Waiting for LLM decisions&hellip;</div>
                    : state.llmLog.map((e, i) => <LLMLogEntry key={i} entry={e} />)}
                </div>
              </>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
