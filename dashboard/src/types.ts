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

export interface SimControl {
  paused: boolean;
  speed_multiplier: number;
}

export interface AgentControl {
  enabled: boolean;
}

export interface DashboardState {
  connected: boolean;
  timestamps: string[];   // HH:MM derived from timestamp_sim
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
}
