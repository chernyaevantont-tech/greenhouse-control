import { useState, useCallback, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import type { ChartOptions, ChartDataset } from 'chart.js';
import { useMqtt } from './useMqtt';
import type { SupervisorVerdict, LLMActionPayload } from './types';

// -- Constants ---------------------------------------------------------------
const BROKER_URL     = `ws://${window.location.hostname}:9001`;
const WINDOW_OPTIONS = [60, 120, 300, 600] as const;
const SPEED_OPTIONS  = [0.25, 0.5, 1, 2, 5, 10] as const;

const SP = {
  temp: { lo: 18,  hi: 22,   set: 20  },
  co2:  { lo: 600, hi: 1000, set: 800 },
  rh:   { lo: 40,  hi: 85,   set: 85  },
} as const;

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
      labels: { boxWidth: 12, color: '#8b949e', font: { size: 11 } },
    },
    tooltip: {
      backgroundColor: '#1c2128',
      borderColor: '#30363d',
      borderWidth: 1,
      titleColor: '#e6edf3',
      bodyColor: '#8b949e',
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
    label, data,
    borderColor: color,
    backgroundColor: fill ? `${color}28` : 'transparent',
    borderWidth: 2,
    pointRadius: 0,
    tension: 0.3,
    fill,
  } as ChartDataset<'line'>;
}

function flatLds(label: string, n: number, value: number, color: string): ChartDataset<'line'> {
  return {
    label,
    data: Array(n).fill(value) as number[],
    borderColor: color,
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderDash: [5, 5],
    pointRadius: 0,
    fill: false,
    tension: 0,
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

// -- Main App ----------------------------------------------------------------
export default function App() {
  const { state, publishControl, publishAgentControl, publishControllerSelect, publishReset } = useMqtt(BROKER_URL);
  const [windowSize,      setWindowSize]      = useState<number>(120);
  const [activeTab,       setActiveTab]       = useState<Tab>('thermals');
  const [paused,          setPaused]          = useState(false);
  const [speed,           setSpeed]           = useState(1);
  const [agentOn,         setAgentOn]         = useState(false);
  const [controllerMode,  setControllerMode]  = useState<'mpc' | 'llm'>('mpc');

  // Sync initial states to backend on first connect
  useEffect(() => {
    if (state.connected) {
      publishAgentControl({ enabled: agentOn });
      publishControllerSelect({ mode: controllerMode });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.connected]);

  const handlePause = useCallback(() => {
    const next = !paused;
    setPaused(next);
    publishControl({ paused: next, speed_multiplier: speed });
  }, [paused, speed, publishControl]);

  const handleSpeed = useCallback((s: number) => {
    setSpeed(s);
    setPaused(false);
    publishControl({ paused: false, speed_multiplier: s });
  }, [publishControl]);

  const handleAgentToggle = useCallback(() => {
    const next = !agentOn;
    setAgentOn(next);
    publishAgentControl({ enabled: next });
  }, [agentOn, publishAgentControl]);

  const handleControllerSwitch = useCallback((mode: 'mpc' | 'llm') => {
    setControllerMode(mode);
    publishControllerSelect({ mode });
  }, [publishControllerSelect]);

  const handleReset = useCallback(() => {
    publishReset({ requested: true });
  }, [publishReset]);

  const n      = windowSize;
  const labels = state.timestamps.slice(-n);
  const tel    = state.latestTelemetry;
  const ood    = state.latestOOD;

  return (
    <div className="layout">

      <header className="header">
        <StatusDot on={state.connected} />
        <h1 className="header__title">Greenhouse Control</h1>
        <span className="header__subtitle">Live Dashboard</span>
        <span className="header__step">Step: <b>{tel?.step ?? '\u2014'}</b></span>
      </header>

      <div className="metrics-bar">
        <MetricCard label="Indoor Temp"  value={tel?.t_in  ?? null} unit="\u00b0C"   lo={SP.temp.lo} hi={SP.temp.hi} />
        <MetricCard label="CO\u2082"          value={tel?.co2   ?? null} unit="ppm"  lo={SP.co2.lo}  hi={SP.co2.hi} />
        <MetricCard label="Humidity"     value={tel?.rh    ?? null} unit="%"    lo={SP.rh.lo}   hi={SP.rh.hi} />
        <MetricCard label="Outdoor Temp" value={tel?.T_out ?? null} unit="\u00b0C" />
        <MetricCard label="Solar Rad"    value={tel?.rad   ?? null} unit="W/m\u00b2" />
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

            {activeTab === 'thermals' && (<>
              <ChartCard title="Temperature" height={280}>
                <Line options={chartOpts('\u00b0C')} data={{ labels, datasets: [
                  lds('t_in (\u00b0C)', state.t_in.slice(-n), '#58a6ff', true),
                  flatLds(`Min ${SP.temp.lo}`, labels.length, SP.temp.lo, '#8b949e'),
                  flatLds(`Max ${SP.temp.hi}`, labels.length, SP.temp.hi, '#8b949e'),
                  flatLds(`SP ${SP.temp.set}`,  labels.length, SP.temp.set, '#3fb950'),
                ]}} />
              </ChartCard>
              <ChartCard title="CO\u2082 Concentration" height={240}>
                <Line options={chartOpts('ppm')} data={{ labels, datasets: [
                  lds('CO\u2082 (ppm)', state.co2.slice(-n), '#3fb950', true),
                  flatLds(`Min ${SP.co2.lo}`, labels.length, SP.co2.lo, '#8b949e'),
                  flatLds(`Max ${SP.co2.hi}`, labels.length, SP.co2.hi, '#8b949e'),
                  flatLds(`SP ${SP.co2.set}`,  labels.length, SP.co2.set, '#58a6ff'),
                ]}} />
              </ChartCard>
              <ChartCard title="Relative Humidity" height={200}>
                <Line options={chartOpts('%')} data={{ labels, datasets: [
                  lds('RH (%)', state.rh.slice(-n), '#bc8cff', true),
                  flatLds(`Min ${SP.rh.lo}`, labels.length, SP.rh.lo, '#8b949e'),
                  flatLds(`Max ${SP.rh.hi}`, labels.length, SP.rh.hi, '#8b949e'),
                  flatLds(`SP ${SP.rh.set}`,  labels.length, SP.rh.set, '#d29922'),
                ]}} />
              </ChartCard>
            </>)}

            {activeTab === 'actuators' && (<>
              <ChartCard title="Heating &amp; CO\u2082" height={260}>
                <Line options={chartOpts('signal [0\u20131]', 0, 1)} data={{ labels, datasets: [
                  lds('Boiler',     state.uBoil.slice(-n), '#f85149'),
                  lds('CO\u2082 inject', state.uCO2.slice(-n),  '#3fb950'),
                ]}} />
              </ChartCard>
              <ChartCard title="Screens &amp; Ventilation" height={260}>
                <Line options={chartOpts('signal [0\u20131]', 0, 1)} data={{ labels, datasets: [
                  lds('Thermal screen',  state.uThScr.slice(-n), '#58a6ff'),
                  lds('Ventilation',     state.uVent.slice(-n),  '#bc8cff'),
                  lds('Blackout screen', state.uBlScr.slice(-n), '#8b949e'),
                ]}} />
              </ChartCard>
              <ChartCard title="Lighting" height={200}>
                <Line options={chartOpts('signal [0\u20131]', 0, 1)} data={{ labels, datasets: [
                  lds('Lamps', state.uLamp.slice(-n), '#d29922', true),
                ]}} />
              </ChartCard>
            </>)}

            {activeTab === 'weather' && (<>
              <ChartCard title="Outdoor Temperature" height={300}>
                <Line options={chartOpts('\u00b0C')} data={{ labels, datasets: [
                  lds('T_out (\u00b0C)', state.T_out.slice(-n), '#bc8cff', true),
                ]}} />
              </ChartCard>
              <ChartCard title="Solar Radiation" height={300}>
                <Line options={chartOpts('W/m\u00b2', 0)} data={{ labels, datasets: [
                  lds('Radiation (W/m\u00b2)', state.rad.slice(-n), '#d29922', true),
                ]}} />
              </ChartCard>
            </>)}

            {activeTab === 'ood' && (
              <ChartCard title={`Mahalanobis Distance (threshold = ${state.oodThreshold})`} height={400}>
                <Line options={chartOpts('distance', 0)} data={{ labels, datasets: [
                  lds('Mahalanobis', state.mahal.slice(-n), '#d29922', true),
                  flatLds(`Threshold ${state.oodThreshold}`, labels.length, state.oodThreshold, '#f85149'),
                ]}} />
              </ChartCard>
            )}
          </div>
        </div>

        <div className="sidebar">

          <div className="card">
            <div className="card__title">Simulation Controls</div>
            <div className="pause-row">
              <button
                className={`btn btn--warning${paused ? ' btn--active' : ''}`}
                onClick={handlePause}
                style={{ minWidth: 96 }}
              >
                {paused ? '\u25b6 Resume' : '\u23f8 Pause'}
              </button>
              <span style={{ color: 'var(--muted)', fontSize: 12 }}>
                {paused ? 'Paused' : `${speed}× speed`}
              </span>
            </div>
            <div className="speed-section-label">Speed multiplier:</div>
            <div className="speed-btns">
              {SPEED_OPTIONS.map(s => (
                <button key={s}
                  className={`btn${speed === s && !paused ? ' btn--active' : ''}`}
                  disabled={paused}
                  onClick={() => handleSpeed(s)}
                >
                  {s}×
                </button>
              ))}
            </div>
            <div style={{ marginTop: 10 }}>
              <button
                className="btn btn--warning"
                onClick={handleReset}
                style={{ width: '100%' }}
                title="Restart the simulation episode from the beginning"
              >
                &#x21BA; Restart Simulation
              </button>
            </div>
          </div>

          <div className="card">
            <div className="card__title">Controller</div>
            <div className="speed-btns">
              <button
                className={`btn${controllerMode === 'mpc' ? ' btn--active' : ''}`}
                onClick={() => handleControllerSwitch('mpc')}
                style={{ flex: 1 }}
                title="Physics-Informed SINDy MPC controller"
              >
                MPC
              </button>
              <button
                className={`btn${controllerMode === 'llm' ? ' btn--active' : ''}`}
                onClick={() => handleControllerSwitch('llm')}
                style={{ flex: 1 }}
                title="Large Language Model autonomous controller"
              >
                LLM
              </button>
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
              {controllerMode === 'mpc'
                ? 'Physics-Informed SINDy MPC with OOD detection.'
                : 'LLM autonomously decides all actuators from sensor data.'}
            </div>
          </div>

          {controllerMode === 'mpc' && (
            <div className="card">
              <div className="card__title">AI Supervisor</div>
              <div className="pause-row">
                <button
                  className={`btn${agentOn ? ' btn--active' : ' btn--warning'}`}
                  onClick={handleAgentToggle}
                  style={{ minWidth: 110 }}
                >
                  {agentOn ? '\u2705 Enabled' : '\u274c Disabled'}
                </button>
                <span style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {agentOn ? 'LLM active' : 'Auto-approve'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
                When disabled, all MPC actions are approved automatically.
              </div>
            </div>
          )}

          {controllerMode === 'mpc' && (
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

          <div className="card" style={{ flex: 1 }}>
            {controllerMode === 'mpc' ? (
              <>
                <div className="card__title">Supervisor Decisions</div>
                <div className="log-scroll">
                  {state.supervisorLog.length === 0
                    ? <div className="no-data">Waiting for decisions\u2026</div>
                    : state.supervisorLog.map((e, i) => <LogEntry key={i} entry={e} />)
                  }
                </div>
              </>
            ) : (
              <>
                <div className="card__title">LLM Actions</div>
                <div className="log-scroll">
                  {state.llmLog.length === 0
                    ? <div className="no-data">Waiting for LLM decisions\u2026</div>
                    : state.llmLog.map((e, i) => <LLMLogEntry key={i} entry={e} />)
                  }
                </div>
              </>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
