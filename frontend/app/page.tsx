"use client";

import { useEffect, useState, useCallback } from "react";
import Header from "@/components/Header";
import DataStatus from "@/components/DataStatus";
import ScoreCardsRow from "@/components/ScoreCardsRow";
import AIBriefing from "@/components/AIBriefing";
import Vitals from "@/components/Vitals";
import WorkoutRecovery from "@/components/WorkoutRecovery";
import TrendCharts from "@/components/TrendCharts";
import SectionDivider from "@/components/SectionDivider";
import {
  fetchDashboard,
  fetchTrends,
  fetchBaselines,
  fetchWorkouts,
  refreshInsight,
  fetchDataStatus,
} from "@/lib/api";
import type {
  DashboardResponse,
  TrendsResponse,
  BaselinePoint,
  WorkoutRecoveryResponse,
  DataStatusResponse,
} from "@/lib/types";

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [baselines, setBaselines] = useState<BaselinePoint[]>([]);
  const [workouts, setWorkouts] = useState<WorkoutRecoveryResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [dash, tr, bl, wo, ds] = await Promise.all([
        fetchDashboard(),
        fetchTrends(30),
        fetchBaselines("sleep_score"),
        fetchWorkouts(30),
        fetchDataStatus(),
      ]);
      setDashboard(dash);
      setTrends(tr);
      setBaselines(bl);
      setWorkouts(wo);
      setDataStatus(ds);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = useCallback(async () => {
    const newInsight = await refreshInsight();
    setDashboard((prev) =>
      prev ? { ...prev, insight: newInsight } : prev
    );
  }, []);

  const handlePullComplete = useCallback(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <main className="min-h-screen max-w-6xl mx-auto px-6 py-10">
        <div className="animate-pulse space-y-8">
          <div>
            <div className="h-12 w-64 bg-warm-200 rounded-lg" />
            <div className="h-5 w-40 bg-warm-200 rounded mt-2" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-80 bg-white rounded-xl shadow-sm" />
            ))}
          </div>
          <div className="h-64 bg-white rounded-xl shadow-sm" />
          <div className="h-48 bg-white rounded-xl shadow-sm" />
          <div className="h-96 bg-white rounded-xl shadow-sm" />
        </div>
      </main>
    );
  }

  if (error || !dashboard) {
    return (
      <main className="min-h-screen max-w-6xl mx-auto px-6 py-10">
        <h1 className="text-5xl font-bold tracking-tight text-warm-900">
          ByeSamosa
        </h1>
        <div className="mt-8 p-6 bg-white rounded-xl shadow-sm border border-warm-200/50">
          <p className="text-warm-800">
            {error || "No data found. Import Oura data first."}
          </p>
          <p className="mt-2 text-sm text-warm-800/60">
            Run:{" "}
            <code className="bg-warm-100 px-2 py-0.5 rounded text-sm">
              python -m byesamosa.pipeline import --raw-dir data/raw/YYYY-MM-DD
            </code>
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen max-w-6xl mx-auto px-6 py-10">
      <Header day={dashboard.latest.day} onRefresh={handleRefresh} />

      <DataStatus data={dataStatus} onPullComplete={handlePullComplete} />

      <ScoreCardsRow data={dashboard} />

      <SectionDivider />

      {dashboard.insight && <AIBriefing insight={dashboard.insight} />}

      <SectionDivider />

      <Vitals data={dashboard} />

      <SectionDivider />

      {workouts && workouts.workouts.length > 0 && (
        <>
          <WorkoutRecovery data={workouts} />
          <SectionDivider />
        </>
      )}

      {trends && (
        <TrendCharts
          trends={trends}
          baselines={baselines}
          insight={dashboard.insight}
        />
      )}
    </main>
  );
}
