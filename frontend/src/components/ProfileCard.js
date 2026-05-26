import React from 'react';
import { motion } from 'framer-motion';
import { Verified, ExternalLink, Users, Image as ImageIcon, Flame } from 'lucide-react';

export default function ProfileCard({ profile, index }) {
  const formatNumber = (num) => {
    if (num === null || num === undefined) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return Number(num).toLocaleString();
  };

  const isVerified = profile.followers > 50000 || profile.confidence > 100;
  
  // Calculate relevance color
  const relScore = profile.relevance || 0;
  let relColor = 'var(--success)';
  if (relScore < 0.4) relColor = 'var(--danger)';
  else if (relScore < 0.7) relColor = 'var(--warning)';

  return (
    <motion.div 
      className="profile-card glass"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      whileHover={{ y: -5 }}
    >
      <div className="card-header">
        <div className="profile-avatar-container">
          <img 
            src={profile.profile_image || 'https://via.placeholder.com/150?text=No+Image'} 
            alt={profile.username}
            className="profile-avatar"
            onError={(e) => { e.target.src = 'https://via.placeholder.com/150?text=No+Image'; }}
          />
        </div>
        <div style={{ position: 'absolute', top: '10px', right: '10px' }}>
           <span className="relevance-score" style={{ color: 'white', fontWeight: 600, fontSize: '0.9rem', background: 'rgba(0,0,0,0.5)', padding: '2px 8px', borderRadius: '12px' }}>
              <Flame size={14} color={relColor} /> {Math.round(relScore * 100)}% Match
           </span>
        </div>
      </div>
      
      <div className="card-body">
        <div className="profile-name-row">
          <h3 className="profile-username">@{profile.username}</h3>
          {isVerified && <Verified className="verified-badge" fill="currentColor" color="var(--bg-dark)" />}
        </div>
        
        <p className="profile-bio">{profile.bio || 'No bio available'}</p>
        
        <div className="stats-row">
          <div className="stat-item">
            <span className="stat-num">{formatNumber(profile.followers)}</span>
            <span className="stat-lbl">Followers</span>
          </div>
          <div className="stat-item">
            <span className="stat-num">{formatNumber(profile.following)}</span>
            <span className="stat-lbl">Following</span>
          </div>
          <div className="stat-item">
            <span className="stat-num">{formatNumber(profile.posts)}</span>
            <span className="stat-lbl">Posts</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <a href={`https://instagram.com/${profile.username}`} target="_blank" rel="noreferrer" style={{ color: 'var(--secondary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.9rem' }}>
            <ExternalLink size={14} /> Instagram Profile
          </a>
          
          {profile.website && (
            <a href={profile.website} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.9rem' }}>
              <ExternalLink size={14} /> {profile.website.replace(/^https?:\/\/(www\.)?/, '').slice(0, 30)}...
            </a>
          )}
        </div>
      </div>

      <div className="card-footer" style={{ padding: '1rem 1.5rem', borderTop: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.2)' }}>
        <div className="extraction-source">
           <span className={`badge badge-${profile.field_sources?.username === 'cache' ? 'cache' : 'bing'}`}>
             {profile.field_sources?.username === 'cache' ? 'Cached' : 'Live Extracted'}
           </span>
        </div>
        <div className="confidence-indicator" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
           <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Quality</span>
           <div style={{ width: '40px', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
             <div style={{ width: `${Math.min(profile.confidence || 0, 100)}%`, height: '100%', background: 'var(--primary)' }}></div>
           </div>
        </div>
      </div>
    </motion.div>
  );
}
