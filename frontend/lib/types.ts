export interface ContributorLabel {
  name: string;
  value: number;
  tag: 'boost' | 'ok' | 'drag';
}

export interface ScoreInsight {
  one_liner: string;
  contributors: ContributorLabel[];
}

export interface ReasoningStep {
  label: string;
  text: string;
}

export interface ActionItem {
  title: string;
  detail: string;
  priority: 'high' | 'medium' | 'low';
  tag: string;
}

export interface ChartAnnotation {
  text: string;
}

export interface TrendAnnotation {
  icon: string;
  text: string;
}

export interface AIInsight {
  date: string;
  score_insights: Record<string, ScoreInsight>;
  reasoning_chain: ReasoningStep[];
  actions: ActionItem[];
  vital_annotations: Record<string, ChartAnnotation>;
  trend_annotations: Record<string, TrendAnnotation>;
  good_looks_like: Record<string, string>;
}

export interface SleepContributors {
  deep_sleep: number | null;
  efficiency: number | null;
  latency: number | null;
  rem_sleep: number | null;
  restfulness: number | null;
  timing: number | null;
  total_sleep: number | null;
}

export interface ReadinessContributors {
  activity_balance: number | null;
  body_temperature: number | null;
  hrv_balance: number | null;
  previous_day_activity: number | null;
  previous_night: number | null;
  recovery_index: number | null;
  resting_heart_rate: number | null;
  sleep_balance: number | null;
  sleep_regularity: number | null;
}

export interface ActivityContributors {
  meet_daily_targets: number | null;
  move_every_hour: number | null;
  recovery_time: number | null;
  stay_active: number | null;
  training_frequency: number | null;
  training_volume: number | null;
}

export interface DailySleep {
  day: string;
  score: number | null;
  contributors: SleepContributors | null;
  total_sleep_duration: number | null;
  rem_sleep_duration: number | null;
  deep_sleep_duration: number | null;
  average_hrv: number | null;
  average_heart_rate: number | null;
  average_breath: number | null;
  lowest_heart_rate: number | null;
  temperature_deviation: number | null;
  bedtime_start: string | null;
  bedtime_end: string | null;
}

export interface DailyReadiness {
  day: string;
  score: number | null;
  contributors: ReadinessContributors | null;
  temperature_deviation: number | null;
}

export interface DailyActivity {
  day: string;
  score: number | null;
  contributors: ActivityContributors | null;
  steps: number | null;
  active_calories: number | null;
}

export interface DashboardResponse {
  latest: {
    day: string;
    sleep: DailySleep;
    readiness: DailyReadiness | null;
    activity: DailyActivity | null;
  };
  deltas: {
    sleep_delta?: number;
    readiness_delta?: number;
    activity_delta?: number;
  };
  insight: AIInsight | null;
}

export interface TrendPoint {
  day: string;
  value: number;
}

export interface TrendsResponse {
  sleep_score: TrendPoint[];
  average_hrv: TrendPoint[];
  lowest_heart_rate: TrendPoint[];
}

export interface BaselinePoint {
  day: string;
  metric: string;
  avg_7d: number | null;
  avg_30d: number | null;
  avg_90d: number | null;
  std_30d: number | null;
}

export interface WorkoutPoint {
  day: string;
  activity: string;
  calories: number;
}

export interface ReadinessPoint {
  day: string;
  readiness: number;
}

export interface WorkoutRecoveryResponse {
  workouts: WorkoutPoint[];
  readiness: ReadinessPoint[];
  activity_types: string[];
  excluded_count: number;
}

export interface PullStatusResponse {
  status: 'idle' | 'running' | 'completed' | 'failed';
  output: string;
}

export interface RawExport {
  date: string;
  file_count: number;
  pulled_at: string | null;
}

export interface DataStatusResponse {
  raw_exports: RawExport[];
  processed_range: { earliest: string; latest: string } | null;
}
