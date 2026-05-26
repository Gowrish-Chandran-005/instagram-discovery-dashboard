import React from 'react';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import { Users, Target, Activity, Search } from 'lucide-react';

export default function AnalyticsDashboard({ profiles, searchMetrics }) {
  if (!profiles || profiles.length === 0) return null;

  // Compute stats
  const totalFollowers = profiles.reduce((acc, p) => acc + (p.followers || 0), 0);
  const avgConfidence = profiles.reduce((acc, p) => acc + (p.confidence || 0), 0) / profiles.length;
  
  // Prepare distribution data
  const distData = profiles.slice(0, 10).map(p => ({
    name: p.username.substring(0, 10),
    followers: p.followers || 0,
    relevance: Math.round((p.relevance || 0) * 100)
  }));

  const COLORS = ['#6366f1', '#ec4899', '#8b5cf6', '#10b981'];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
      style={{ marginTop: '2rem' }}
    >
      <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Activity color="var(--primary)" /> Discovery Analytics
      </h2>
      
      <div className="analytics-grid">
        <div className="stat-card glass-panel">
          <div className="stat-label"><Users size={16}/> Total Profiles</div>
          <div className="stat-value">{profiles.length}</div>
        </div>
        <div className="stat-card glass-panel">
          <div className="stat-label"><Search size={16}/> Discovery Source</div>
          <div className="stat-value" style={{ textTransform: 'capitalize', color: searchMetrics?.source === 'cache' ? 'var(--accent)' : 'var(--success)' }}>
            {searchMetrics?.source || 'Live'}
          </div>
        </div>
        <div className="stat-card glass-panel">
          <div className="stat-label"><Target size={16}/> Avg Quality Score</div>
          <div className="stat-value">{Math.round(avgConfidence)} / 100</div>
        </div>
        <div className="stat-card glass-panel">
          <div className="stat-label"><Activity size={16}/> Time Taken</div>
          <div className="stat-value">{searchMetrics?.performance?.time_taken_seconds || 0}s</div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-container glass-panel">
          <h3 className="chart-title">Followers Distribution (Top 10)</h3>
          <ResponsiveContainer width="100%" height="80%">
            <BarChart data={distData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
              <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickLine={false} />
              <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => value >= 1000 ? `${(value/1000).toFixed(0)}k` : value} />
              <Tooltip 
                cursor={{ fill: 'rgba(255,255,255,0.05)' }} 
                contentStyle={{ background: 'var(--bg-dark)', border: '1px solid var(--border-light)', borderRadius: '8px' }}
              />
              <Bar dataKey="followers" fill="url(#colorFollowers)" radius={[4, 4, 0, 0]} />
              <defs>
                <linearGradient id="colorFollowers" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.2}/>
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container glass-panel">
          <h3 className="chart-title">Relevance Match (%)</h3>
          <ResponsiveContainer width="100%" height="80%">
            <AreaChart data={distData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
              <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickLine={false} />
              <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-dark)', border: '1px solid var(--border-light)', borderRadius: '8px' }}
              />
              <Area type="monotone" dataKey="relevance" stroke="var(--secondary)" fillOpacity={1} fill="url(#colorRelevance)" />
              <defs>
                <linearGradient id="colorRelevance" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--secondary)" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="var(--secondary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </motion.div>
  );
}
