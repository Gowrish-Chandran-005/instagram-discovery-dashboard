import React, { useState, useEffect } from 'react';
import './App.css';

function ProfileCard({ profile }) {
  // Format numbers nicely
  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A';
    return Number(num).toLocaleString();
  };

  return (
    <div className="profile-card">
      <div className="profile-image-container">
        <img 
          src={profile.profile_image || 'https://via.placeholder.com/120?text=No+Image'} 
          alt={`${profile.username} profile`} 
          className="profile-image" 
          onError={(e) => { e.target.src = 'https://via.placeholder.com/120?text=No+Image'; }}
        />
      </div>
      <div className="profile-info">
        <h3 className="profile-username">@{profile.username}</h3>
        
        <div className="profile-stats">
          <span><strong>{formatNumber(profile.posts)}</strong> posts</span>
          <span><strong>{formatNumber(profile.followers)}</strong> followers</span>
          <span><strong>{formatNumber(profile.following)}</strong> following</span>
        </div>
        
        <div className="profile-bio">
          {profile.bio || 'No bio available'}
        </div>
        
        {profile.website && (
          <div className="profile-website">
            🔗 <a href={profile.website} target="_blank" rel="noreferrer">{profile.website}</a>
          </div>
        )}
        
        <p className="profile-methods">
          Extraction Methods: {profile.extraction_methods?.join(', ') || 'None'}
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const [keyword, setKeyword] = useState('posters');
  const [loading, setLoading] = useState(false);
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');

  // Auto-update progress message to simulate extraction steps
  useEffect(() => {
    let interval;
    if (loading) {
      const messages = [
        'Searching DuckDuckGo for Instagram profiles...',
        'Discovering new usernames...',
        'Filtering and removing duplicates...',
        'Extracting metadata (this may take a few minutes)...',
        'Extracting metadata (this may take a few minutes)...',
        'Still extracting, please wait...',
      ];
      let i = 0;
      setProgressMsg(messages[0]);
      interval = setInterval(() => {
        i++;
        if (i < messages.length) {
          setProgressMsg(messages[i]);
        }
      }, 8000);
    }
    return () => clearInterval(interval);
  }, [loading]);

  async function handleSearch(e) {
    e.preventDefault();
    if (!keyword.trim()) return;

    setLoading(true);
    setError(null);
    setProfiles([]);
    setHasSearched(false);
    
    // Set a timeout of 10 minutes to prevent infinite loading
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);

    try {
      const url = `http://localhost:5000/search?keyword=${encodeURIComponent(keyword.trim())}&headless=1`;
      const res = await fetch(url, { signal: controller.signal });

      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        throw new Error(`Invalid JSON response from backend: ${text.slice(0, 100)}...`);
      }

      // Allow either success=true or the presence of profiles to mark success
      if (!res.ok) {
        const msg = data.error || JSON.stringify(data);
        throw new Error(`Backend error: ${msg}`);
      }
      
      // Even if ok, we should check if there was a server error disguised as success
      if (data.error && !data.success) {
        throw new Error(`Backend error: ${data.error}`);
      }

      setProfiles(data.profiles || []);
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

  return (
    <div className="container">
      <h1>Instagram Discovery Dashboard</h1>
      
      <form onSubmit={handleSearch} className="search-form">
        <input 
          value={keyword} 
          onChange={e => setKeyword(e.target.value)} 
          className="search-input"
          placeholder="Enter keyword (e.g. posters, sarees, boutique)..."
          disabled={loading}
        />
        <button type="submit" className="search-button" disabled={loading || !keyword.trim()}>
          {loading ? 'Searching...' : 'Discover & Extract'}
        </button>
      </form>

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p><strong>Running extraction pipeline...</strong></p>
          <p style={{ color: '#5f6368' }}>{progressMsg}</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && hasSearched && profiles.length === 0 && (
        <div className="no-results">
          <h3>No profiles found</h3>
          <p>We couldn't find any relevant Instagram profiles for "{keyword}". Try another keyword.</p>
        </div>
      )}

      {!loading && profiles.length > 0 && (
        <div>
          <h2>Discovered Profiles ({profiles.length})</h2>
          {profiles.map((p, i) => (
            <ProfileCard profile={p} key={i} />
          ))}
        </div>
      )}
    </div>
  );
}
