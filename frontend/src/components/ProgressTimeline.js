import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Database, Fingerprint, Activity, CheckCircle2 } from 'lucide-react';

const steps = [
  { id: 1, label: "Checking Cache", icon: Database },
  { id: 2, label: "Searching Bing/Fallback", icon: Search },
  { id: 3, label: "Bypassing Anti-Bot", icon: Fingerprint },
  { id: 4, label: "Extracting Metadata", icon: Activity },
  { id: 5, label: "Applying Relevance Filters", icon: CheckCircle2 }
];

export default function ProgressTimeline({ isActive, isComplete }) {
  const [activeStep, setActiveStep] = useState(1);

  useEffect(() => {
    let interval;
    if (isActive && !isComplete) {
      interval = setInterval(() => {
        setActiveStep(prev => {
          if (prev < 4) return prev + 1;
          return prev;
        });
      }, 4000); // Simulate progress every 4s
    } else if (isComplete) {
      setActiveStep(5);
    }
    return () => clearInterval(interval);
  }, [isActive, isComplete]);

  if (!isActive && !isComplete) return null;

  return (
    <motion.div 
      className="timeline-container glass"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
    >
      <h3 style={{ marginBottom: '1.5rem', color: 'white' }}>Extraction Progress</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'flex-start', paddingLeft: '2rem' }}>
        {steps.map((step, index) => {
          const StepIcon = step.icon;
          const isCurrent = activeStep === step.id && !isComplete;
          const isDone = activeStep > step.id || isComplete;
          
          return (
            <motion.div 
              key={step.id}
              className={`timeline-step ${isCurrent ? 'active' : ''} ${isDone ? 'completed' : ''}`}
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: index * 0.2 }}
            >
              {isCurrent ? (
                <div className="spinner" style={{ color: 'var(--primary)' }}></div>
              ) : (
                <StepIcon size={20} color={isDone ? 'var(--success)' : 'currentColor'} />
              )}
              <span>{step.label}</span>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
