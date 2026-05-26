import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Sparkles } from 'lucide-react';

export default function HeroSearch({ onSearch, loading }) {
  const [keyword, setKeyword] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (keyword.trim() && !loading) {
      onSearch(keyword.trim());
    }
  };

  const suggestions = ['boutique', 'posters', 'jewelry', 'streetwear', 'handmade'];

  return (
    <motion.div 
      className="hero-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
    >
      <motion.h1 
        className="hero-title"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        Discover Instagram Profiles with AI
      </motion.h1>
      
      <p className="hero-subtitle">
        Enter a niche keyword to automatically discover, filter, and extract high-quality Instagram profiles using our hybrid Playwright & AI analysis pipeline.
      </p>

      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-wrapper">
          <Search className="search-icon" size={20} />
          <input 
            type="text"
            className="search-input"
            placeholder="E.g., boutique, handmade jewelry, posters..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            disabled={loading}
          />
        </div>
        <button type="submit" className="search-btn" disabled={loading || !keyword.trim()}>
          {loading ? (
            <>
              <div className="spinner"></div> Searching
            </>
          ) : (
            <>
              <Sparkles size={18} /> Discover
            </>
          )}
        </button>
      </form>
      
      {!loading && (
        <motion.div 
          className="mt-4 flex justify-center gap-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', justifyContent: 'center' }}
        >
          {suggestions.map(s => (
            <button 
              key={s} 
              className="badge" 
              style={{ cursor: 'pointer', border: 'none', color: 'var(--text-muted)' }}
              onClick={() => { setKeyword(s); onSearch(s); }}
            >
              {s}
            </button>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}
