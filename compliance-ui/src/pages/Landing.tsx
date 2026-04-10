import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Activity, ArrowRight, Zap, Target } from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen relative collection overflow-hidden bg-[#0B132B] flex flex-col items-center justify-center">
      {/* Background Particles (CSS base) */}
      <div className="absolute inset-0 pointer-events-none z-0">
        <div className="absolute w-[600px] h-[600px] bg-primary/20 rounded-full blur-[150px] top-[-100px] left-[-200px]"></div>
        <div className="absolute w-[500px] h-[500px] bg-glow/20 rounded-full blur-[150px] bottom-[-200px] right-[-100px]"></div>
      </div>
      
      {/* Content */}
      <div className="z-10 flex flex-col items-center text-center max-w-4xl px-6">
        <motion.div 
          initial={{ scale: 0 }} 
          animate={{ scale: 1 }} 
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
          className="mb-8 p-4 bg-primary/10 rounded-2xl border border-primary/30 shadow-[0_0_50px_rgba(0,212,255,0.3)]"
        >
          <ShieldCheck className="w-16 h-16 text-primary" />
        </motion.div>
        
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-6xl md:text-8xl font-black tracking-tight text-white mb-6 drop-shadow-lg"
        >
          RegIntel<span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-500">AI</span>
        </motion.h1>
        
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-xl md:text-2xl text-white/70 mb-12 max-w-2xl leading-relaxed"
        >
          The next-generation autonomous compliance intelligence engine. 
          Upload regulatory documents and let AI agents instantly map policies, evaluate risks, and draft updates.
        </motion.p>
        
        <motion.div
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ delay: 0.6 }}
           className="flex flex-col sm:flex-row gap-6 w-full justify-center items-center"
        >
          <button 
            onClick={() => navigate('/dashboard')}
            className="group relative px-8 py-4 bg-gradient-to-r from-primary to-blue-600 hover:from-primary hover:to-blue-500 rounded-2xl font-bold text-lg flex items-center gap-3 transition-all hover:scale-105 shadow-[0_0_30px_rgba(0,212,255,0.4)] hover:shadow-[0_0_50px_rgba(0,212,255,0.6)]"
          >
            Start Analysis
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </motion.div>

        {/* Feature Highlights */}
        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24"
        >
          <div className="flex flex-col items-center gap-3 p-6 glass-card border border-white/5 bg-white/5 rounded-2xl">
              <Zap className="w-8 h-8 text-primary" />
              <h3 className="text-lg font-bold text-white">Instant Parsing</h3>
              <p className="text-sm text-white/50 text-center">Neural extraction of changes</p>
          </div>
          <div className="flex flex-col items-center gap-3 p-6 glass-card border border-white/5 bg-white/5 rounded-2xl">
              <Activity className="w-8 h-8 text-risk" />
              <h3 className="text-lg font-bold text-white">Risk Scoring</h3>
              <p className="text-sm text-white/50 text-center">Determine impact severity instantly</p>
          </div>
          <div className="flex flex-col items-center gap-3 p-6 glass-card border border-white/5 bg-white/5 rounded-2xl">
              <Target className="w-8 h-8 text-accent" />
              <h3 className="text-lg font-bold text-white">Policy Drafts</h3>
              <p className="text-sm text-white/50 text-center">Auto-generated remediation</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
