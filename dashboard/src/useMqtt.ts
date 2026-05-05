import { useState, useEffect, useRef, useCallback } from 'react';
import mqtt, { MqttClient } from 'mqtt';
import type { DashboardState, SimControl, AgentControl, ControllerSelect, SimReset } from './types';

const MAX_BUF = 600;

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
  oodThreshold: 6.0, inDistribution: null, agentEnabled: true,
  controllerMode: 'mpc',
  latestTelemetry: null, latestOOD: null,
  uBoil: [], uCO2: [], uThScr: [], uVent: [], uLamp: [], uBlScr: [],
  latestAction: null,
  supervisorLog: [],
  llmLog: [],
};

export function useMqtt(brokerUrl: string) {
  const [state, setState] = useState<DashboardState>(INIT);
  const clientRef = useRef<MqttClient | null>(null);

  useEffect(() => {
    const client = mqtt.connect(brokerUrl, {
      clientId: `gh_react_${Math.random().toString(16).slice(2)}`,
      reconnectPeriod: 3000,
      keepalive: 30,
    });
    clientRef.current = client;

    client.on('connect', () => {
      setState(s => ({ ...s, connected: true }));
      [
        'greenhouse/telemetry',
        'greenhouse/action/approved',
        'greenhouse/ood/metrics',
        'greenhouse/supervisor/verdict',
        'greenhouse/llm/action',
      ].forEach(t => client.subscribe(t, { qos: 1 }));
    });

    client.on('disconnect', () => setState(s => ({ ...s, connected: false })));
    client.on('close',      () => setState(s => ({ ...s, connected: false })));
    client.on('error',      () => setState(s => ({ ...s, connected: false })));

    client.on('message', (topic, raw) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let p: any;
      try { p = JSON.parse(raw.toString()); } catch { return; }

      setState(prev => {
        switch (topic) {
          case 'greenhouse/telemetry':
            return {
              ...prev,
              timestamps: roll(prev.timestamps, simToHHMM(p.timestamp_sim ?? 0)),
              steps: roll(prev.steps, p.step),
              t_in:  roll(prev.t_in,  p.t_in),
              T_out: roll(prev.T_out, p.T_out),
              co2:   roll(prev.co2,   p.co2),
              rh:    roll(prev.rh,    p.rh),
              rad:   roll(prev.rad,   p.rad ?? 0),
              latestTelemetry: p,
            };
          case 'greenhouse/action/approved':
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
          case 'greenhouse/ood/metrics':
            return {
              ...prev,
              mahal:          roll(prev.mahal, p.mahalanobis_distance ?? 0),
              oodThreshold:   p.threshold_used ?? 3.0,
              inDistribution: p.in_distribution ?? true,
              latestOOD: p,
            };
          case 'greenhouse/supervisor/verdict':
            return {
              ...prev,
              supervisorLog: [p, ...prev.supervisorLog].slice(0, 50),
            };
          case 'greenhouse/llm/action':
            return {
              ...prev,
              llmLog: [p, ...prev.llmLog].slice(0, 50),
            };
          default:
            return prev;
        }
      });
    });

    return () => {
      client.end(true);
      clientRef.current = null;
    };
  }, [brokerUrl]);

  const publishControl = useCallback((ctrl: SimControl) => {
    clientRef.current?.publish(
      'greenhouse/control/speed',
      JSON.stringify(ctrl),
      { qos: 1 },
    );
  }, []);

  const publishAgentControl = useCallback((ctrl: AgentControl) => {
    clientRef.current?.publish(
      'greenhouse/control/agent',
      JSON.stringify(ctrl),
      { qos: 1 },
    );
  }, []);

  const publishControllerSelect = useCallback((ctrl: ControllerSelect) => {
    clientRef.current?.publish(
      'greenhouse/control/controller',
      JSON.stringify(ctrl),
      { qos: 1 },
    );
  }, []);

  const publishReset = useCallback((payload: SimReset) => {
    clientRef.current?.publish(
      'greenhouse/control/reset',
      JSON.stringify(payload),
      { qos: 1 },
    );
  }, []);

  return { state, publishControl, publishAgentControl, publishControllerSelect, publishReset };
}
