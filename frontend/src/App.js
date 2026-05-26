import React, { useState, useEffect } from 'react';
import Papa from 'papaparse';
import { Download, FileJson } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import './App.css';
import HeroSearch from './components/HeroSearch';
import ProgressTimeline from './components/ProgressTimeline';
import ProfileCard from './components/ProfileCard';
import AnalyticsDashboard from './components/AnalyticsDashboard';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchMetrics, setSearchMetrics] = useState(null);

  // Search History State
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const savedHistory = localStorage.getItem('insta_search_history');
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error('Failed to parse history', e);
      }
    }
  }, []);

  const saveToHistory = (keyword, count) => {
    const newHistory = [{ keyword, count, date: new Date().toISOString() }, ...history.filter(h => h.keyword !== keyword)].slice(0, 5);
    setHistory(newHistory);
    localStorage.setItem('insta_search_history', JSON.stringify(newHistory));
  };

  async function handleSearch(keyword) {
    if (!keyword.trim()) return;

    setLoading(true);
    setError(null);
    setProfiles([]);
    setSearchMetrics(null);
    setHasSearched(false);
    
    // Set a timeout of 10 minutes to prevent infinite loading
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);

    try {
      const url = `http://localhost:5000/search?keyword=${encodeURIComponent(keyword.trim())}&headless=1`;
      const res = await fetch(url, { signal: controller.signal });
      const data = await res.json();

      if (!res.ok || (data.error && !data.success)) {
        throw new Error(data.error || 'Unknown backend error');
      }

      setProfiles(data.profiles || []);
      setSearchMetrics({
        source: data.source,
        performance: data.performance,
        failed_count: data.failed_count
      });
      
      saveToHistory(keyword, (data.profiles || []).length);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out. The extraction process took too long.');
      } else {
        setError(err.message);
      }
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
      setHasSearched(true);
    }
  }

  // --- EXPORT FUNCTIONS ---
  const exportToCSV = () => {
    if (!profiles.length) return;
    const csvData = profiles.map(p => ({
      Username: p.username,
      Followers: p.followers,
      Following: p.following,
      Posts: p.posts,
      Bio: p.bio,
      Website: p.website,
      Confidence: p.confidence,
      Relevance: Math.round((p.relevance || 0) * 100) + '%',
      Methods: p.extraction_methods?.join(', ')
    }));
    
    const csv = Papa.unparse(csvData);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `instagram_profiles_${new Date().getTime()}.csv`;
    link.click();
  };

  const exportToJSON = () => {
    if (!profiles.length) return;
    const blob = new Blob([JSON.stringify(profiles, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `instagram_profiles_${new Date().getTime()}.json`;
    link.click();
  };

  return (
    <>
      <div className="bg-blob blob-1"></div>
      <div className="bg-blob blob-2"></div>
      
      <div className="app-container">
        <HeroSearch onSearch={handleSearch} loading={loading} />
        
        <ProgressTimeline isActive={loading} isComplete={!loading && hasSearched} />

        <AnimatePresence>
          {error && (
            <motion.div 
              className="glass" 
              style={{ padding: '1.5rem', color: 'var(--danger)', marginBottom: '2rem', borderLeft: '4px solid var(--danger)' }}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
            >
              <strong>Extraction Error:</strong> {error}
            </motion.div>
          )}
        </AnimatePresence>

        {hasSearched && profiles.length === 0 && !loading && !error && (
          <motion.div className="no-results glass" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h3>No profiles found</h3>
            <p>We couldn't find any high-quality Instagram profiles. Try adjusting your keyword.</p>
          </motion.div>
        )}

        {profiles.length > 0 && !loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <AnalyticsDashboard profiles={profiles} searchMetrics={searchMetrics} />
            
            <div className="profiles-header mt-8">
              <h2>Discovered Profiles <span className="text-muted">({profiles.length})</span></h2>
              
              <div className="actions-group">
                <button onClick={exportToCSV} className="btn-secondary">
                  <Download size={16} /> Export CSV
                </button>
                <button onClick={exportToJSON} className="btn-secondary">
                  <FileJson size={16} /> Export JSON
                </button>
              </div>
            </div>

            <div className="profiles-grid">
              {profiles.map((p, i) => (
                <ProfileCard profile={p} key={p.username || i} index={i} />
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </>
  );
}
