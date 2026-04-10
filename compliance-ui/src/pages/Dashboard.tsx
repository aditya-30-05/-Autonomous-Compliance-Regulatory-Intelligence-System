import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  UploadCloud, Play, FileText, CheckCircle2, 
  AlertTriangle, ShieldAlert, ArrowRight, Download, 
  Bell, FileWarning, Eye, FileSignature 
} from 'lucide-react';

// --- Demo Data ---
const demoResults = {
  changes: [
    {
      id: 1,
      section: 'LCR Computation',
      oldText: 'LCR buffer should be maintained at 100%.',
      newText: 'LCR buffer must be raised to 110% effective immediately to avoid non-compliance penalties.'
    },
    {
      id: 2,
      section: 'Reporting Frequency',
      oldText: 'Submit compliance report on a quarterly basis.',
      newText: 'Submit compliance report on a monthly basis.'
    }
  ],
  policies: [
    { id: 1, title: 'Liquidity Risk Management Policy', confidence: 98, status: 'Needs Review' },
    { id: 2, title: 'Regulatory Reporting Framework', confidence: 91, status: 'Needs Review' },
    { id: 3, title: 'Stress Testing Guidelines', confidence: 76, status: 'Potential Impact' }
  ],
  updates: `Based on the latest RBI circular, the following updates are drafted for internal policies:\n\n1. Liquidity Risk Management Policy:\n   - Section 4.2 (LCR Minimum): Update the minimum LCR requirement from 100% to 110%.\n   - Ensure all treasury dashboards reflect this new threshold.\n\n2. Regulatory Reporting Framework:\n   - Change submission frequency from Quarterly to Monthly in the reporting calendar.`
};

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [progress, setProgress] = useState(0);

  // Drag & drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setIsDragActive(true);
    else setIsDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setShowResults(false);
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setShowResults(false);
    }
  };

  const handleRunAnalysis = () => {
    if (!file) return;
    setIsAnalyzing(true);
    setProgress(0);
    
    // Simulate progress
    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            setIsAnalyzing(false);
            setShowResults(true);
          }, 400);
          return 100;
        }
        return p + Math.floor(Math.random() * 15) + 5;
      });
    }, 300);
  };

  return (
    <div className="min-h-screen relative collection overflow-hidden">
      {/* Background Particles (CSS base) */}
      <div className="absolute inset-0 pointer-events-none z-0">
        <div className="absolute w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px] top-[-100px] left-[-100px]"></div>
        <div className="absolute w-[600px] h-[600px] bg-glow/10 rounded-full blur-[150px] bottom-[-200px] right-[-100px]"></div>
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          <div className="p-2 bg-primary/20 rounded-lg border border-primary/30">
            <ShieldAlert className="text-primary w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wide neon-text">RegIntel<span className="font-light text-white">AI</span></h1>
            <p className="text-xs text-white/50">Autonomous Compliance Intelligence</p>
          </div>
        </motion.div>
      </header>

      {/* Fake Alert Banner */}
      <motion.div 
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="w-full bg-risk/20 border-b border-risk/30 py-2 px-4 flex items-center justify-center gap-2 z-40 relative backdrop-blur-sm"
      >
        <Bell className="w-4 h-4 text-risk" />
        <span className="text-sm font-medium text-white/90">New RBI Circular Detected 2 hours ago (RBI/2026/18)</span>
      </motion.div>

      <main className="max-w-6xl mx-auto px-6 py-12 relative z-10 flex flex-col gap-10">
        
        {/* Upload & Action Section */}
        <section className="flex flex-col items-center justify-center gap-8">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl"
          >
            <div 
              className={`glass-card p-10 flex flex-col items-center justify-center border-2 border-dashed ${isDragActive ? 'border-primary bg-primary/5' : 'border-white/20'} transition-all relative overflow-hidden`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input type="file" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" accept=".pdf" />
              <motion.div
                animate={isDragActive ? { y: -10, scale: 1.1 } : { y: 0, scale: 1 }}
                transition={{ type: "spring" }}
              >
                <div className="p-4 bg-white/5 rounded-full mb-4">
                  <UploadCloud className={`w-10 h-10 ${isDragActive ? 'text-primary' : 'text-white/50'}`} />
                </div>
              </motion.div>
              <h3 className="text-xl font-semibold mb-2">
                {file ? <span className="text-primary">{file.name}</span> : 'Upload Regulatory Circular'}
              </h3>
              <p className="text-white/40 text-sm">Drag & drop your PDF here, or click to browse</p>
            </div>
          </motion.div>

          <AnimatePresence>
            {file && !showResults && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="w-full max-w-sm"
              >
                {!isAnalyzing ? (
                  <button 
                    onClick={handleRunAnalysis}
                    className="w-full py-4 text-lg font-bold rounded-xl bg-gradient-to-r from-primary to-blue-600 hover:from-primary hover:to-blue-500 neon-border flex items-center justify-center gap-2 transition-all transform hover:scale-[1.02]"
                  >
                    <Play className="w-5 h-5 fill-current" />
                    Run AI Analysis
                  </button>
                ) : (
                  <div className="w-full flex justify-center py-4">
                    {/* Animated Loader */}
                    <div className="flex flex-col items-center gap-4 w-full">
                      <div className="relative w-16 h-16">
                        <div className="absolute inset-0 border-4 border-white/10 rounded-full"></div>
                        <motion.div 
                          className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full"
                          animate={{ rotate: 360 }}
                          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                        ></motion.div>
                      </div>
                      <p className="text-primary font-medium animate-pulse">Analyzing with AI Agents...</p>
                      {/* Progress bar */}
                      <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                        <motion.div 
                          className="h-full bg-primary"
                          initial={{ width: 0 }}
                          animate={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Dashboard Section */}
        <AnimatePresence>
          {showResults && (
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 lg:grid-cols-3 gap-6"
            >
              
              {/* Left Column (Changes & Updates) */}
              <div className="lg:col-span-2 flex flex-col gap-6">
                
                {/* Detected Changes */}
                <motion.div 
                  initial={{ opacity: 0, x: -30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className="glass-card p-6"
                >
                  <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-4">
                    <Eye className="w-5 h-5 text-primary" />
                    <h2 className="text-xl font-semibold">Detected Changes</h2>
                  </div>
                  
                  <div className="space-y-6">
                    {demoResults.changes.map(change => (
                      <div key={change.id} className="bg-white/5 rounded-xl p-5 border border-white/5 hover:border-white/10 transition-colors">
                        <h4 className="text-sm font-semibold text-white/50 mb-3 tracking-wider uppercase">{change.section}</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="p-3 bg-risk/10 rounded-lg border border-risk/20">
                            <span className="text-xs text-risk font-bold mb-1 block">PREVIOUS</span>
                            <p className="text-sm text-white/70 line-through decoration-risk/50">{change.oldText}</p>
                          </div>
                          <div className="p-3 bg-accent/10 rounded-lg border border-accent/20 relative overflow-hidden group">
                            <div className="absolute inset-0 bg-accent/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <span className="text-xs text-accent font-bold mb-1 block">NEW REQUIREMENT</span>
                            <p className="text-sm text-white/90">{change.newText}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>

                {/* Suggested Updates */}
                <motion.div 
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="glass-card p-6"
                >
                  <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-4">
                    <FileSignature className="w-5 h-5 text-glow" />
                    <h2 className="text-xl font-semibold">AI Suggested Updates</h2>
                  </div>
                  
                  <div className="bg-black/40 rounded-xl p-5 border border-white/10 h-64 overflow-y-auto custom-scrollbar">
                    <pre className="font-sans text-sm text-white/80 whitespace-pre-wrap leading-relaxed">
                      {demoResults.updates}
                    </pre>
                  </div>
                </motion.div>

              </div>

              {/* Right Column (Policies & Risk) */}
              <div className="flex flex-col gap-6">

                {/* Risk Level Card */}
                <motion.div 
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.3 }}
                  className="glass-card p-6 bg-gradient-to-br from-risk/10 to-transparent border-risk/30"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <AlertTriangle className="w-5 h-5 text-risk" />
                    <h2 className="text-xl font-semibold">Overall Risk Level</h2>
                  </div>
                  
                  <div className="flex flex-col items-center justify-center py-6">
                    <motion.div 
                      animate={{ scale: [1, 1.05, 1], boxShadow: ["0 0 0px #e74c3c", "0 0 30px #e74c3c", "0 0 0px #e74c3c"] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="w-32 h-32 rounded-full border-4 border-risk flex items-center justify-center bg-risk/10 relative"
                    >
                      <span className="text-3xl font-black text-risk drop-shadow-[0_0_8px_rgba(231,76,60,0.8)]">HIGH</span>
                    </motion.div>
                    <p className="text-center text-sm text-white/60 mt-6">
                      Urgent policy modifications required to prevent compliance breaches.
                    </p>
                  </div>
                </motion.div>

                {/* Affected Policies Card */}
                <motion.div 
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 }}
                  className="glass-card p-6 flex-1"
                >
                  <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-4">
                    <FileWarning className="w-5 h-5 text-primary" />
                    <h2 className="text-xl font-semibold">Affected Policies</h2>
                  </div>

                  <div className="flex flex-col gap-3">
                    {demoResults.policies.map((policy, idx) => (
                      <motion.div 
                        key={policy.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 + (idx * 0.1) }}
                        whileHover={{ scale: 1.02, backgroundColor: "rgba(255,255,255,0.1)" }}
                        className="bg-white/5 p-4 rounded-xl border border-white/10 cursor-pointer flex items-center justify-between group"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-full ${policy.confidence > 90 ? 'bg-risk/20 text-risk' : 'bg-risk-medium/20 text-risk-medium'}`}>
                            <FileText className="w-4 h-4" />
                          </div>
                          <div>
                            <h4 className="text-sm font-medium text-white/90 group-hover:text-primary transition-colors">{policy.title}</h4>
                            <span className="text-xs text-white/50">{policy.confidence}% Match Confidence</span>
                          </div>
                        </div>
                        <ArrowRight className="w-4 h-4 text-white/30 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                      </motion.div>
                    ))}
                  </div>
                </motion.div>

              </div>

              {/* Report Gen Section */}
              <motion.div 
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
                className="lg:col-span-3 glass-card flex flex-col gap-6 p-6 mt-4 border-t-4 border-t-primary"
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
                  <div>
                    <h3 className="text-2xl font-bold flex items-center gap-3">
                      <FileText className="w-6 h-6 text-primary" />
                      Executive Compliance Report
                    </h3>
                    <p className="text-sm text-white/60 mt-1">Structured summary of regulatory changes and operational impact.</p>
                  </div>
                  <button className="px-6 py-3 bg-gradient-to-r from-primary to-blue-600 hover:from-primary hover:to-blue-500 rounded-xl font-medium flex items-center gap-2 transition-all neon-border">
                    <Download className="w-5 h-5" />
                    Download PDF Report
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-white/5 rounded-xl p-5 border border-white/10">
                    <h4 className="text-primary font-semibold mb-2 flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> Summary</h4>
                    <p className="text-sm text-white/80 leading-relaxed">
                      The RBI has issued a new circular mandating an increase in the Liquidity Coverage Ratio (LCR) buffer. The compliance frequency has been accelerated, necessitating immediate operational adjustments.
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-5 border border-white/10">
                    <h4 className="text-primary font-semibold mb-2 flex items-center gap-2"><Eye className="w-4 h-4" /> Changes</h4>
                    <p className="text-sm text-white/80 leading-relaxed">
                      LCR baseline raised from 100% to 110%. Reporting frequency shifted from Quarterly to Monthly intervals. Enforcement begins immediately.
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-5 border border-white/10">
                    <h4 className="text-primary font-semibold mb-2 flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> Impact</h4>
                    <p className="text-sm text-white/80 leading-relaxed">
                      High impact on Treasury limits. Existing automated regulatory reporting pipelines will fail validation due to the new monthly interval requirement.
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-5 border border-white/10">
                    <h4 className="text-primary font-semibold mb-2 flex items-center gap-2"><ShieldAlert className="w-4 h-4" /> Recommendations</h4>
                    <p className="text-sm text-white/80 leading-relaxed">
                      1. Adjust treasury limit thresholds immediately.<br/>
                      2. Reconfigure reporting chron jobs for monthly cycles.<br/>
                      3. Conduct a dry-run of the LCR stress tests with the 110% benchmark.
                    </p>
                  </div>
                </div>

              </motion.div>

            </motion.div>
          )}
        </AnimatePresence>

      </main>
    </div>
  );
}
