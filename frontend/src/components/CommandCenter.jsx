import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import { Users, Flame, DollarSign, Award, RefreshCw, ExternalLink, School } from 'lucide-react';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.origin.includes('5173')
    ? 'http://localhost:8000'
    : (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000'));

const BAR_COLORS = ['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#10b981'];

export default function CommandCenter() {
  const [stats, setStats] = useState({
    total_registered: 0,
    target: 500,
    progress_percentage: 0,
    viral_coefficient: 0.0,
    blended_cac_inr: 2000.0,
    seed_count: 0,
    viral_count: 0,
    rewards_unlocked: 0,
    colleges: {}
  });

  const [feed, setFeed] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      try {
        const [statsRes, feedRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/stats`),
          fetch(`${API_BASE_URL}/api/feed`)
        ]);

        if (!statsRes.ok || !feedRes.ok) {
          throw new Error('Backend HTTP error');
        }

        const statsData = await statsRes.json();
        const feedData = await feedRes.json();

        if (isMounted) {
          setStats(statsData);
          setFeed(feedData.feed || []);
          setLastUpdated(new Date());
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        console.error('Command Center Polling Error:', err);
        if (isMounted) {
          setError('Backend offline or connecting...');
        }
      }
    };

    // Initial fetch + 3-second polling interval
    fetchData();
    const intervalId = setInterval(fetchData, 3000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  // Format colleges dictionary for Recharts bar chart
  const chartData = Object.entries(stats.colleges || {}).map(([college, count]) => ({
    name: college,
    registrations: count
  }));

  const progressPercent = Math.min(
    100,
    Math.round((stats.total_registered / (stats.target || 500)) * 100)
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 selection:bg-blue-600 selection:text-white">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Bar */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="px-3 py-1 bg-blue-600/20 text-blue-400 text-xs font-semibold rounded-full border border-blue-500/30 uppercase tracking-wider">
                NxtWave Growth Challenge
              </span>
              <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-medium rounded-full border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                Live Polling (3s)
              </span>
              {error && (
                <span className="px-2.5 py-0.5 bg-amber-500/10 text-amber-400 text-xs rounded border border-amber-500/20">
                  {error}
                </span>
              )}
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold text-white mt-2 tracking-tight">
              AI Workshop Referral Command Center
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Real-time Google Sheets CRM &amp; Viral Growth Telemetry • Target: <span className="font-semibold text-slate-200">500 Students</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-lg border border-slate-800 transition"
            >
              Swagger Docs <ExternalLink size={13} />
            </a>
            <div className="text-right">
              <span className="text-xs text-slate-500 font-mono block">
                {lastUpdated ? `Sync: ${lastUpdated.toLocaleTimeString()}` : 'Connecting...'}
              </span>
            </div>
          </div>
        </header>

        {/* =========================================================================
            SECTION 1: TOP KPI CARDS
           ========================================================================= */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Card 1: Total Registered */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl shadow-blue-950/20 relative overflow-hidden">
            <div className="flex justify-between items-start text-xs font-semibold uppercase text-slate-400">
              <span className="flex items-center gap-1.5">
                <Users size={16} className="text-blue-400" />
                Total Registered
              </span>
              <span className="text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-900/50 font-mono">
                Goal: 500
              </span>
            </div>
            <div className="text-4xl font-black text-white mt-4 tracking-tight">
              {stats.total_registered}
            </div>
            <div className="w-full bg-slate-800 h-2.5 rounded-full mt-4 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all duration-700"
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
            <div className="text-xs text-slate-400 mt-3 flex justify-between font-medium">
              <span>{progressPercent}% Completed</span>
              <span>{Math.max(0, 500 - stats.total_registered)} remaining</span>
            </div>
          </div>

          {/* Card 2: Viral Coefficient (K-Factor) */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl shadow-emerald-950/20 relative overflow-hidden">
            <div className="flex justify-between items-start text-xs font-semibold uppercase text-slate-400">
              <span className="flex items-center gap-1.5">
                <Flame size={16} className="text-emerald-400" />
                Viral Coefficient (K)
              </span>
              <span className="text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-900/50 font-mono">
                Target: &gt; 1.2
              </span>
            </div>
            <div className="text-4xl font-black text-emerald-400 mt-4 tracking-tight">
              {stats.viral_coefficient.toFixed(2)}
            </div>
            <div className="text-xs text-slate-400 mt-3 flex items-center gap-3">
              <span>Seed: <b className="text-white font-mono">{stats.seed_count}</b></span>
              <span>•</span>
              <span>Viral: <b className="text-emerald-400 font-mono">{stats.viral_count}</b></span>
            </div>
            <div className="text-xs text-emerald-400/90 mt-2 font-medium">
              {stats.viral_coefficient >= 1.0 ? '🚀 Viral loop expanding organically' : '🌱 Seeding initial campus cohorts'}
            </div>
          </div>

          {/* Card 3: Blended CAC */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl shadow-amber-950/20 relative overflow-hidden">
            <div className="flex justify-between items-start text-xs font-semibold uppercase text-slate-400">
              <span className="flex items-center gap-1.5">
                <DollarSign size={16} className="text-amber-400" />
                Blended CAC
              </span>
              <span className="text-amber-400 bg-amber-950 px-2 py-0.5 rounded border border-amber-900/50 font-mono">
                Budget: ₹2,000
              </span>
            </div>
            <div className="text-4xl font-black text-amber-400 mt-4 tracking-tight">
              ₹{(stats.blended_cac_inr || stats.blended_cac || 0).toFixed(2)}
            </div>
            <div className="text-xs text-slate-400 mt-3">
              Standard Meta Ad CAC: <span className="line-through text-slate-500">₹176</span>
            </div>
            <div className="text-xs text-amber-400/90 mt-2 font-medium">
              Saves ~95% customer acquisition spend
            </div>
          </div>

        </section>

        {/* =========================================================================
            SECTION 2: RECHARTS BAR CHART (COLLEGE LEADERBOARD)
           ========================================================================= */}
        <section className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <School size={18} className="text-blue-400" />
                Campus Registration Leaderboard
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Distribution of engineering student sign-ups across colleges
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
              {chartData.length} Colleges Active
            </span>
          </div>

          <div className="h-72 w-full">
            {chartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                Waiting for incoming college registrations...
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <XAxis
                    dataKey="name"
                    stroke="#64748b"
                    fontSize={12}
                    tickLine={false}
                    interval={0}
                    angle={-10}
                    textAnchor="end"
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      color: '#f8fafc',
                      fontSize: '12px',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
                    }}
                    cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
                  />
                  <Bar
                    dataKey="registrations"
                    radius={[6, 6, 0, 0]}
                    animationDuration={600}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        {/* =========================================================================
            SECTION 3: LIVE INBOUND REGISTRATION FEED (GOOGLE SHEET TABLE)
           ========================================================================= */}
        <section className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <RefreshCw size={18} className="text-emerald-400" />
                Live Inbound Registration Feed
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time stream of the last 10 Google Sheet CRM entries (Target Sheet: <code className="text-blue-400 font-mono">NxtWave_Registration_CRM</code>)
              </p>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              Auto-polled every 3s
            </span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800/80">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="p-3.5">Student Name</th>
                  <th className="p-3.5">College</th>
                  <th className="p-3.5">Phone Number</th>
                  <th className="p-3.5">My Referral Code</th>
                  <th className="p-3.5">Referred By</th>
                  <th className="p-3.5 text-center">Referrals Driven</th>
                  <th className="p-3.5">Timestamp (UTC)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {feed.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">
                      No registrations in CRM yet. Send a message to your WhatsApp bot or run{' '}
                      <code className="text-blue-400">python demo.py</code>!
                    </td>
                  </tr>
                ) : (
                  feed.map((row, i) => (
                    <tr key={i} className="hover:bg-slate-800/40 transition">
                      <td className="p-3.5 font-semibold text-white font-sans">
                        {row.Name || 'Student'}
                      </td>
                      <td className="p-3.5 text-slate-300 font-sans">
                        {row.College || 'N/A'}
                      </td>
                      <td className="p-3.5 text-slate-400">
                        {row.Phone_Number ? row.Phone_Number.slice(0, 6) + '****' : (row.Phone ? row.Phone.slice(0, 6) + '****' : 'WhatsApp')}
                      </td>
                      <td className="p-3.5">
                        <span className="px-2.5 py-1 bg-blue-950 text-blue-400 rounded-md border border-blue-800/50 font-bold">
                          {row.My_Referral_Code}
                        </span>
                      </td>
                      <td className="p-3.5">
                        {row.Referred_By ? (
                          <span className="text-emerald-400 font-semibold">{row.Referred_By}</span>
                        ) : (
                          <span className="text-slate-600">Organic / Seed</span>
                        )}
                      </td>
                      <td className="p-3.5 text-center">
                        <span
                          className={`px-2.5 py-1 rounded-md font-bold ${
                            row.Total_Referrals >= 3
                              ? 'bg-purple-950 text-purple-300 border border-purple-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {row.Total_Referrals}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-500">
                        {row.Timestamp}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </div>
  );
}
