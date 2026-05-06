export interface TelemetryPayload {
  step: number;
  timestamp_sim: number;
  t_in: number;
  co2: number;
  rh: number;
  T_out: number;
  rad: number;
  co2_out: number;
  sin_h: number;
  cos_h: number;
}

export interface ActionPayload {
  step: number;
  approved: boolean;
  uBoil: number;
  uCO2: number;
  uThScr: number;
  uVent: number;
  uLamp: number;
  uBlScr: number;
}

export interface OODMetrics {
  step: number;
  mahalanobis_distance: number;
  max_residual: number;
  in_distribution: boolean;
  threshold_used: number;
}

export interface SupervisorVerdict {
  step: number;
  decision: 'APPROVE' | 'REJECT' | 'OVERRIDE';
  override_action: ActionPayload | null;
  reason: string;
  confidence: number;
}

export interface LLMActionPayload {
  step: number;
  reasoning: string;
  uBoil: number;
  uCO2: number;
  uThScr: number;
  uVent: number;
  uLamp: number;
  uBlScr: number;
}

export interface SimConfig {
  env_id: string;
  start_date: string;
  n_days: number;
  period: number;
  controller_mode: 'mpc' | 'llm';
  agent_enabled: boolean;
  speed_multiplier: number;
  mpc_horizon: number;
  llm_call_interval: number;
  llm_history_window: number;
}

export interface SimStatus {
  running: boolean;
  paused: boolean;
  step: number;
  config: SimConfig;
  latest_telemetry: TelemetryPayload | null;
  latest_action: ActionPayload | null;
  latest_ood: OODMetrics | null;
}

export interface DashboardState {
  connected: boolean;
  timestamps: string[];
  steps: number[];
  t_in: number[];
  T_out: number[];
  co2: number[];
  rh: number[];
  rad: number[];
  mahal: number[];
  oodThreshold: number;
  inDistribution: boolean | null;
  agentEnabled: boolean;
  controllerMode: 'mpc' | 'llm';
  latestTelemetry: TelemetryPayload | null;
  latestOOD: OODMetrics | null;
  uBoil: number[];
  uCO2: number[];
  uThScr: number[];
  uVent: number[];
  uLamp: number[];
  uBlScr: number[];
  latestAction: ActionPayload | null;
  supervisorLog: SupervisorVerdict[];
  llmLog: LLMActionPayload[];
  // Simulation control
  simRunning: boolean;
  simPaused: boolean;
  simStep: number;
  serverConnected: boolean;
}
