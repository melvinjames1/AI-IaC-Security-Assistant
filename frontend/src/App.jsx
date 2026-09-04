import { useState, useEffect, useCallback } from 'react';
import {
  Shield, ShieldCheck, Activity, Upload, Play, Sparkles, RotateCcw,
  AlertCircle, CheckCircle, Info, Clock, Cpu, ChevronRight,
  GitBranch, Terminal, ExternalLink, Copy, Check, Filter, Layers
} from 'lucide-react';
import { api } from './services/api';
import { FindingsList } from './components/FindingsList';
import { AIAnalysisPanel } from './components/AIAnalysisPanel';
import { TerraformDiff } from './components/TerraformDiff';
import { ScoreComparison, ScoreRing } from './components/ScoreDisplay';

const EXAMPLE_LABELS = {
  'vulnerable-s3': 'S3 Bucket',
  'vulnerable-security-group': 'Security Group',
  'vulnerable-iam': 'IAM Policy',
};

function Spinner({ size = 16 }) {
  return (
    <div
      className="animate-spin rounded-full border-2 border-indigo-400 border-t-transparent flex-shrink-0"
      style={{ width: size, height: size }}
    />
  );
}

export default function App() {
  // System states
  const [health, setHealth] = useState(null);
  const [examples, setExamples] = useState({});
  const [activePreset, setActivePreset] = useState('');

  // Code input
  const [terraformCode, setTerraformCode] = useState('');
  const [copiedCmd, setCopiedCmd] = useState(false);

  // Operations
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState('');

  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analysisError, setAnalysisError] = useState('');

  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifyError, setVerifyError] = useState('');

  // Studio tab state ('findings' | 'remediation' | 'verification')
  const [activeTab, setActiveTab] = useState('findings');

  // Load health and examples on mount
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: 'error' }));
    api.examples().then(data => {
      const ex = data.examples || {};
      setExamples(ex);
      // Auto-load vulnerable-s3 by default for instant gratification
      if (ex['vulnerable-s3']) {
        setTerraformCode(ex['vulnerable-s3']);
        setActivePreset('vulnerable-s3');
      }
    }).catch(() => {});
  }, []);

  const loadPreset = (key) => {
    if (examples[key]) {
      setTerraformCode(examples[key]);
      setActivePreset(key);
      setScanResult(null);
      setAnalysis(null);
      setVerifyResult(null);
      setScanError('');
      setAnalysisError('');
      setVerifyError('');
      setActiveTab('findings');
    }
  };

  // Run Checkov scan
  const handleScan = async () => {
    if (!terraformCode.trim()) {
      setScanError('Please enter Terraform configuration code to scan.');
      return;
    }
    setScanning(true);
    setScanError('');
    setScanResult(null);
    setAnalysis(null);
    setVerifyResult(null);
    setActiveTab('findings');

    try {
      const result = await api.scan(terraformCode);
      setScanResult(result);
    } catch (e) {
      setScanError(e.message || 'Scan execution failed.');
    } finally {
      setScanning(false);
    }
  };

  // Keyboard shortcut: Cmd/Ctrl + Enter to scan
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleScan();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [terraformCode]);

  // Run AI analysis
  const handleAnalyze = async () => {
    if (!scanResult) return;
    setAnalyzing(true);
    setAnalysisError('');
    setAnalysis(null);
    setVerifyResult(null);
    setActiveTab('remediation');

    try {
      const result = await api.analyze(terraformCode, scanResult.findings);
      setAnalysis(result);
    } catch (e) {
      setAnalysisError(e.message || 'AI remediation failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Run Checkov verification on corrected code
  const handleVerify = async () => {
    if (!analysis?.corrected_terraform || !scanResult) return;
    setVerifying(true);
    setVerifyError('');
    setVerifyResult(null);
    setActiveTab('verification');

    try {
      const result = await api.verify(
        analysis.corrected_terraform,
        scanResult.findings,
        scanResult.score,
      );
      setVerifyResult(result);
    } catch (e) {
      setVerifyError(e.message || 'Verification scan failed.');
    } finally {
      setVerifying(false);
    }
  };

  const handleReset = () => {
    setTerraformCode('');
    setActivePreset('');
    setScanResult(null);
    setAnalysis(null);
    setVerifyResult(null);
    setScanError('');
    setAnalysisError('');
    setVerifyError('');
    setActiveTab('findings');
  };

  const copyCommand = () => {
    navigator.clipboard.writeText('checkov -d . --framework terraform');
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  const lineCount = terraformCode ? terraformCode.split('\n').length : 0;
  const failedCount = scanResult ? scanResult.findings.filter(f => f.severity !== 'PASSED').length : 0;

  return (
    <div className="min-h-screen bg-[#090a0f] text-slate-200 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-white">
      {/* ── Top Navigation Bar (Ragas / Modern Studio style) ── */}
      <header className="border-b border-white/[0.08] bg-[#0c0e14]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          {/* Brand Logo & Version */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-slate-100 shadow-inner">
              <Shield size={18} className="text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-slate-100 tracking-tight">AI-IaC Guard</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400 border border-white/[0.08]">
                  v1.0.0
                </span>
              </div>
              <div className="text-[11px] text-slate-500 hidden sm:block">
                Generative AI for Automated IaC Security
              </div>
            </div>
          </div>

          {/* Center Terminal Command Pill (Ragas style) */}
          <button
            onClick={copyCommand}
            className="terminal-pill hidden md:inline-flex"
            title="Click to copy CLI command"
          >
            <Terminal size={12} className="text-slate-400" />
            <span className="text-slate-400">user@guard:~$</span>
            <span className="text-slate-200">checkov --framework terraform</span>
            {copiedCmd ? (
              <Check size={12} className="text-emerald-400 ml-1" />
            ) : (
              <Copy size={12} className="text-slate-500 ml-1 hover:text-slate-300" />
            )}
          </button>

          {/* Right Status & Controls */}
          <div className="flex items-center gap-3">
            {health && (
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono">
                <span className={`w-1.5 h-1.5 rounded-full ${health.checkov_available ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-rose-400'}`} />
                <span className="text-slate-400 hidden lg:inline">Scanner:</span>
                <span className="text-slate-300">{health.checkov_available ? 'Checkov ready' : 'Scanner offline'}</span>
                <span className="text-slate-600">|</span>
                <span className="text-slate-400 hidden lg:inline">LLM:</span>
                <span className={health.llm_mock_mode ? 'text-amber-400' : 'text-indigo-400'}>
                  {health.llm_mock_mode ? 'mock mode' : health.llm_provider}
                </span>
              </div>
            )}

            <button
              onClick={handleReset}
              className="btn-studio-secondary text-xs py-1 px-2.5"
              title="Reset all inputs and scans"
            >
              <RotateCcw size={13} />
              <span className="hidden sm:inline">Reset</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Studio Workbench (Split Screen Studio) ── */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* ── Left Pane: Terraform Source Editor (5 Cols) ── */}
        <div className="lg:col-span-5 studio-panel p-4 flex flex-col gap-3">
          {/* Header with Preset Scenario Selector */}
          <div className="flex items-center justify-between gap-2 pb-1 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-medium text-slate-300 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-indigo-400" />
                main.tf
              </span>
              <span className="text-[11px] font-mono text-slate-500">
                ({lineCount} lines)
              </span>
            </div>

            {/* Upload .tf button */}
            <label className="text-[11px] font-mono text-slate-400 hover:text-slate-200 cursor-pointer inline-flex items-center gap-1 px-2 py-1 rounded hover:bg-white/[0.04] transition-colors">
              <Upload size={12} />
              <span>Upload .tf</span>
              <input
                type="file"
                accept=".tf"
                className="hidden"
                onChange={e => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const reader = new FileReader();
                  reader.onload = ev => {
                    setTerraformCode(ev.target.result);
                    setActivePreset('');
                  };
                  reader.readAsText(file);
                  e.target.value = '';
                }}
              />
            </label>
          </div>

          {/* Quick Scenario Chips */}
          <div className="flex flex-wrap items-center gap-1.5 py-1">
            <span className="text-[11px] font-mono text-slate-500 mr-1">Vulnerable Scenarios:</span>
            {['vulnerable-s3', 'vulnerable-security-group', 'vulnerable-iam'].map(key => (
              <button
                key={key}
                onClick={() => loadPreset(key)}
                className={`text-[11px] font-mono px-2 py-0.5 rounded transition-all ${
                  activePreset === key
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                    : 'bg-white/[0.04] text-slate-400 hover:text-slate-200 border border-white/[0.06]'
                }`}
              >
                {EXAMPLE_LABELS[key] || key}
              </button>
            ))}
          </div>

          {/* Code Editor */}
          <div className="editor-container">
            <textarea
              id="terraform-input"
              value={terraformCode}
              onChange={e => setTerraformCode(e.target.value)}
              placeholder="# Paste Terraform code here or select a scenario above..."
              className="editor-textarea min-h-[460px]"
              spellCheck={false}
              disabled={scanning}
            />
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-between gap-3 pt-2">
            <button
              id="btn-analyze"
              onClick={handleScan}
              disabled={scanning || !terraformCode.trim()}
              className="btn-studio-primary"
            >
              {scanning ? (
                <>
                  <Spinner size={14} />
                  <span>Scanning with Checkov...</span>
                </>
              ) : (
                <>
                  <Play size={14} className="fill-current" />
                  <span>Scan with Checkov</span>
                  <span className="text-[10px] font-mono opacity-60 ml-1">⌘↵</span>
                </>
              )}
            </button>

            {scanResult && (
              <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
                <span>Score:</span>
                <span className="text-slate-200 font-bold">{Math.round(scanResult.score.score)}/100</span>
              </div>
            )}
          </div>

          {scanError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/25 text-xs text-rose-300 flex items-start gap-2">
              <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
              <span>{scanError}</span>
            </div>
          )}
        </div>

        {/* ── Right Pane: Interactive Security Studio (7 Cols) ── */}
        <div className="lg:col-span-7 studio-panel p-4 flex flex-col gap-4 min-h-[580px]">

          {/* Navigation Segment Tabs */}
          <div className="flex items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
            <div className="flex items-center gap-1 p-0.5 bg-black/40 border border-white/[0.08] rounded-lg">
              <button
                className={`tab-studio ${activeTab === 'findings' ? 'active' : ''}`}
                onClick={() => setActiveTab('findings')}
              >
                <Shield size={13} />
                <span>1. Findings</span>
                {scanResult && (
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-white/10 text-slate-200">
                    {failedCount}
                  </span>
                )}
              </button>

              <button
                className={`tab-studio ${activeTab === 'remediation' ? 'active' : ''}`}
                onClick={() => setActiveTab('remediation')}
                disabled={!scanResult}
              >
                <Sparkles size={13} />
                <span>2. AI Remediation</span>
              </button>

              <button
                className={`tab-studio ${activeTab === 'verification' ? 'active' : ''}`}
                onClick={() => setActiveTab('verification')}
                disabled={!verifyResult && !analysis}
              >
                <ShieldCheck size={13} />
                <span>3. Scorecard & Verify</span>
              </button>
            </div>

            {/* Workflow Progress Breadcrumb */}
            <div className="text-[11px] font-mono text-slate-500 hidden sm:flex items-center gap-1">
              <span className={activeTab === 'findings' ? 'text-indigo-400 font-medium' : ''}>DETECT</span>
              <span>→</span>
              <span className={activeTab === 'remediation' ? 'text-indigo-400 font-medium' : ''}>REMEDIATE</span>
              <span>→</span>
              <span className={activeTab === 'verification' ? 'text-emerald-400 font-medium' : ''}>VERIFY</span>
            </div>
          </div>

          {/* Tab 1: Findings Studio */}
          {activeTab === 'findings' && (
            <div className="space-y-4 animate-fade-in">
              {scanning ? (
                <div className="studio-card p-16 text-center space-y-3">
                  <Spinner size={24} />
                  <div className="text-xs font-mono text-slate-300">
                    Spawning Checkov subprocess on isolated temporary directory...
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Evaluating AWS CIS benchmarks and static analysis rules
                  </div>
                </div>
              ) : scanResult ? (
                <div className="space-y-4">
                  {/* Summary Metric Header */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-black/30 border border-white/[0.06] rounded-lg p-3">
                      <div className="text-[10px] font-mono uppercase text-slate-500">Initial Score</div>
                      <div className="text-2xl font-mono font-bold text-slate-200 mt-0.5">
                        {Math.round(scanResult.score.score)}<span className="text-xs text-slate-500">/100</span>
                      </div>
                    </div>
                    <div className="bg-black/30 border border-white/[0.06] rounded-lg p-3">
                      <div className="text-[10px] font-mono uppercase text-slate-500">Failed Checks</div>
                      <div className="text-2xl font-mono font-bold text-rose-400 mt-0.5">
                        {failedCount}
                      </div>
                    </div>
                    <div className="bg-black/30 border border-white/[0.06] rounded-lg p-3">
                      <div className="text-[10px] font-mono uppercase text-slate-500">Passed Checks</div>
                      <div className="text-2xl font-mono font-bold text-emerald-400 mt-0.5">
                        {scanResult.score.passed}
                      </div>
                    </div>
                    <div className="bg-black/30 border border-white/[0.06] rounded-lg p-3">
                      <div className="text-[10px] font-mono uppercase text-slate-500">Checkov Engine</div>
                      <div className="text-xs font-mono font-semibold text-slate-300 mt-2 truncate">
                        v{scanResult.checkov_version || '3.3.16'}
                      </div>
                    </div>
                  </div>

                  {/* Findings list with search & severity filters */}
                  <FindingsList findings={scanResult.findings} showPassed={true} />

                  {/* Next Step Action Button */}
                  {failedCount > 0 && (
                    <div className="pt-2 flex items-center justify-between border-t border-white/[0.06]">
                      <div className="text-xs text-slate-400">
                        Ready to synthesize fixed configuration with AI?
                      </div>
                      <button
                        id="btn-generate-ai"
                        onClick={handleAnalyze}
                        disabled={analyzing}
                        className="btn-studio-primary"
                      >
                        {analyzing ? (
                          <>
                            <Spinner size={14} />
                            <span>Generating AI Fix...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles size={14} />
                            <span>Generate AI Remediation →</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="studio-card p-16 text-center space-y-3">
                  <Shield size={32} className="mx-auto text-slate-600 stroke-1" />
                  <div className="text-sm font-medium text-slate-300">No Scan Results Yet</div>
                  <div className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                    Click <strong>Scan with Checkov</strong> on the left or load a vulnerable scenario to begin static analysis.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: AI Remediation & Diff */}
          {activeTab === 'remediation' && (
            <div className="space-y-4 animate-fade-in">
              {/* Honest Security Disclaimer */}
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-300/90 font-mono">
                <Info size={14} className="text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong>Unverified AI Code:</strong> The remediated configuration below was generated by the LLM. It must be re-evaluated by Checkov to prove vulnerability reduction.
                </div>
              </div>

              {/* Code Diff Viewer */}
              <TerraformDiff
                original={terraformCode}
                corrected={analysis?.corrected_terraform}
                isLoading={analyzing}
              />

              {/* Threat model & reasoning panel */}
              <AIAnalysisPanel analysis={analysis} isLoading={analyzing} />

              {/* Verify Fix CTA */}
              {analysis?.corrected_terraform && (
                <div className="pt-3 flex items-center justify-between border-t border-white/[0.06]">
                  <div className="text-xs text-slate-400">
                    Re-run Checkov scanner against the AI-corrected code:
                  </div>
                  <button
                    id="btn-verify"
                    onClick={handleVerify}
                    disabled={verifying}
                    className="btn-studio-success"
                  >
                    {verifying ? (
                      <>
                        <Spinner size={14} />
                        <span>Re-scanning with Checkov...</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck size={14} />
                        <span>Verify Fix with Checkov →</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Verification & Scorecard */}
          {activeTab === 'verification' && (
            <div className="space-y-4 animate-fade-in">
              {verifying ? (
                <div className="studio-card p-16 text-center space-y-3">
                  <Spinner size={24} />
                  <div className="text-xs font-mono text-slate-300">
                    Executing secondary Checkov scan on remediated Terraform...
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Computing Before/After metric deltas and verifying resolved checks
                  </div>
                </div>
              ) : verifyResult ? (
                <div className="space-y-4">
                  {/* Clean Scorecard Comparison */}
                  <ScoreComparison
                    before={verifyResult.original_score}
                    after={verifyResult.new_score}
                    improvement={verifyResult.improvement_percentage}
                    verdict={verifyResult.verdict}
                  />

                  {/* Re-scanned Findings List */}
                  <div className="pt-2">
                    <div className="text-xs font-mono uppercase text-slate-400 mb-2 flex items-center justify-between">
                      <span>Post-Verification Audit Results</span>
                      <span className="text-slate-500 font-normal">
                        {verifyResult.resolved_count} checks resolved
                      </span>
                    </div>
                    <FindingsList findings={verifyResult.new_findings} showPassed={true} />
                  </div>
                </div>
              ) : (
                <div className="studio-card p-16 text-center space-y-3">
                  <ShieldCheck size={32} className="mx-auto text-slate-600 stroke-1" />
                  <div className="text-sm font-medium text-slate-300">Verification Pending</div>
                  <div className="text-xs text-slate-500">
                    Generate an AI remediation in Step 2, then click <strong>Verify Fix</strong>.
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </main>

      {/* ── Studio Footer ── */}
      <footer className="border-t border-white/[0.06] bg-[#0c0e14] py-4 mt-auto text-center text-xs text-slate-500 font-mono">
        <div className="max-w-[1600px] mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            AI-IaC Guard · Generative AI for Automated IaC Security · Static Analysis Only
          </div>
          <div className="text-[11px] text-slate-600">
            No real AWS cloud infrastructure is ever provisioned.
          </div>
        </div>
      </footer>
    </div>
  );
}
