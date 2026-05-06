import { useState, useEffect, useRef, useCallback } from 'react';
import type {
  DashboardState,
  SimConfig,
  SimStatus,
  TelemetryPayload,
  ActionPayload,
  OODMetrics,
  SupervisorVerdict,
  LLMActionPayload,
} from './types';

const MAX_BUF = 600;
const API_BASE = '/api';

function roll<T>(arr: T[], item: T): T[] {
  if (arr.length >= MAX_BUF) return [...arr.slice(1), item];
  return [...arr, item];
}

function simToHHMM(tsSeconds: number): string {
  const h = Math.floor((tsSeconds % 86400) / 3600);
  const m = Math.floor((tsSeconds % 3600) / 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

const INIT: DashboardState = {
  connected: false,
  timestamps: [], steps: [], t_in: [], T_out: [], co2: [], rh: [], rad: [], mahal: [],
  oodThreshold: 6.0, inDistribution: null, agentEnabled: false,
  controllerMode: 'mpc',
  latestTelemetry: null, latestOOD: null,
  uBoil: [], uCO2: [], uThScr: [], uVent: [], uLamp: [], uBlScr: [],
  latestAction: null,
  supervisorLog: [],
  llmLog: [],
  simRunning: false,
  simPaused: false,
  simStep: 0,
  serverConnected: false,
};

export function useApi() {
  const [state, setState] = useState<DashboardState>(INIT);
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---------- SSE connection ----------
  const connectSSE = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
    }
    const es = new EventSource(`${API_BASE}/events`);
    esRef.current = es;

    es.onopen = () => {
      setState(s => ({ ...s, serverConnected: true }));
    };

    es.onerror = () => {
      setState(s => ({ ...s, serverConnected: false }));
      es.close();
      // Reconnect after 3 s
      retryRef.current = setTimeout(connectSSE, 3000);
    };

    es.onmessage = (ev) => {
      let envelope: { type: string; data: unknown };
      try { envelope = JSON.parse(ev.data); } catch { return; }
      const { type, data } = envelope;

      setState(prev => {
        switch (type) {
          case 'telemetry': {
            const p = data as TelemetryPayload;
            return {
              ...prev,
              serverConnected: true,
              simRunning: true,
              timestamps: roll(prev.timestamps, simToHHMM(p.timestamp_sim ?? 0)),
              steps: roll(prev.steps, p.step),
              t_in:  roll(prev.t_in,  p.t_in),
              T_out: roll(prev.T_out, p.T_out),
              co2:   roll(prev.co2,   p.co2),
              rh:    roll(prev.rh,    p.rh),
              rad:   roll(prev.rad,   p.rad ?? 0),
              latestTelemetry: p,
              simStep: p.step,
            };
          }
          case 'action': {
            const p = data as ActionPayload;
            return {
              ...prev,
              uBoil:  roll(prev.uBoil,  p.uBoil  ?? 0),
              uCO2:   roll(prev.uCO2,   p.uCO2   ?? 0),
              uThScr: roll(prev.uThScr, p.uThScr ?? 0),
              uVent:  roll(prev.uVent,  p.uVent  ?? 0),
              uLamp:  roll(prev.uLamp,  p.uLamp  ?? 0),
              uBlScr: roll(prev.uBlScr, p.uBlScr ?? 0),
              latestAction: p,
            };
          }
          case 'ood': {
            const p = data as OODMetrics;
            return {
              ...prev,
              mahal:          roll(prev.mahal, p.mahalanobis_distance ?? 0),
              oodThreshold:   p.threshold_used ?? 6.0,
              inDistribution: p.in_distribution ?? true,
              latestOOD: p,
            };
          }
          case 'verdict': {
            const p = data as SupervisorVerdict;
            return { ...prev, supervisorLog: [p, ...prev.supervisorLog].slice(0, 50) };
          }
          case 'llm_action': {
            const p = data as LLMActionPayload;
            return { ...prev, llmLog: [p, ...prev.llmLog].slice(0, 50) };
          }
          case 'reset': {
            return {
              ...prev,
              timestamps: [], steps: [], t_in: [], T_out: [], co2: [], rh: [], rad: [], mahal: [],
              uBoil: [], uCO2: [], uThScr: [], uVent: [], uLamp: [], uBlScr: [],
              latestTelemetry: null, latestOOD: null, latestAction: null,
              supervisorLog: [], llmLog: [],
              simStep: 0,
            };
          }
          case 'episode_done': {
            return { ...prev, simRunning: false };
          }
          case 'heartbeat': {
            return { ...prev, serverConnected: true };
          }
          default:
            return prev;
        }
      });
    };
  }, []);

  // Poll /api/status on mount and after start/stop to sync control state
  const refreshStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      if (!res.ok) return;
      const status: SimStatus = await res.json();
      setState(s => ({
        ...s,
        serverConnected: true,
        simRunning: status.running,
        simPaused: status.paused,
        simStep: status.step,
        controllerMode: status.config.controller_mode,
        agentEnabled: status.config.agent_enabled,
      }));
    } catch {
      setState(s => ({ ...s, serverConnected: false }));
    }
  }, []);

  useEffect(() => {
    connectSSE();
    refreshStatus();
    const interval = setInterval(refreshStatus, 5000);
    return () => {
      clearInterval(interval);
      if (retryRef.current) clearTimeout(retryRef.current);
      esRef.current?.close();
    };
  }, [connectSSE, refreshStatus]);

  // ---------- API actions ----------

  const post = useCallback(async (path: string, body?: unknown) => {
    await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    await refreshStatus();
  }, [refreshStatus]);

  const startSim    = useCallback(() => post('/start'), [post]);
  const stopSim     = useCallback(() => post('/stop'), [post]);
  const resetSim    = useCallback(() => post('/reset', { requested: true }), [post]);

  const setControl  = useCallback(
    (paused: boolean, speed: number) => post('/control', { paused, speed_multiplier: speed }),
    [post],
  );

  const setController = useCallback(
    (mode: 'mpc' | 'llm') => {
      setState(s => ({ ...s, controllerMode: mode }));
      post('/controller', { mode });
    },
    [post],
  );

  const setAgent = useCallback(
    (enabled: boolean) => {
      setState(s => ({ ...s, agentEnabled: enabled }));
      post('/agent', { enabled });
    },
    [post],
  );

  const updateConfig = useCallback(
    (config: SimConfig) => post('/config', config),
    [post],
  );

  const fetchConfig = useCallback(async (): Promise<SimConfig | null> => {
    try {
      const res = await fetch(`${API_BASE}/config`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }, []);

  return {
    state,
    startSim,
    stopSim,
    resetSim,
    setControl,
    setController,
    setAgent,
    updateConfig,
    fetchConfig,
  };
}
