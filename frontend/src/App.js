import React, { useState } from 'react';

function ProfileCard({ profile }) {
  return (
    <div style={{ border: '1px solid #ddd', padding: 12, marginBottom: 12, borderRadius: 6 }}>
      <h3>@{profile.username}</h3>
      <div style={{ display: 'flex', gap: 12 }}>
        <img src={profile.profile_image || ''} alt="profile" style={{ width: 96, height: 96, objectFit: 'cover' }} />
        <div>
          <p><strong>Bio:</strong> {profile.bio}</p>
          <p><strong>Followers:</strong> {profile.followers?.toLocaleString()}</p>
          <p><strong>Following:</strong> {profile.following?.toLocaleString()}</p>
          <p><strong>Posts:</strong> {profile.posts?.toLocaleString()}</p>
          <p><strong>Website:</strong> <a href={profile.website} target="_blank" rel="noreferrer">{profile.website}</a></p>
          <p><strong>Methods:</strong> {profile.extraction_methods?.join(', ')}</p>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [keyword, setKeyword] = useState('posters');
  const [loading, setLoading] = useState(false);
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState(null);

  async function handleSearch(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setProfiles([]);
    try {
      const url = `http://localhost:5000/search?keyword=${encodeURIComponent(keyword)}&headless=1`;
      const res = await fetch(url);

      // Read response as text first to handle non-JSON errors
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        throw new Error(`Invalid JSON response from backend: ${text.slice(0, 200)}`);
      }

      if (!res.ok) {
        const msg = data.error || JSON.stringify(data);
        throw new Error(`Backend error: ${msg}`);
      }

      setProfiles(data.profiles || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '24px auto', fontFamily: 'Arial, sans-serif' }}>
      <h1>Instagram Discovery Dashboard</h1>
      <form onSubmit={handleSearch} style={{ marginBottom: 16 }}>
        <input value={keyword} onChange={e => setKeyword(e.target.value)} style={{ padding: 8, width: '60%' }} />
        <button type="submit" style={{ padding: '8px 12px', marginLeft: 8 }} disabled={loading}>{loading ? 'Running...' : 'Search'}</button>
      </form>

      {loading && <p>Running discovery and extraction... this may take a few minutes.</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {profiles.length > 0 && (
        <div>
          <h2>Profiles</h2>
          {profiles.map((p, i) => (
            <ProfileCard profile={p} key={i} />
          ))}
        </div>
      )}
    </div>
  );
}
