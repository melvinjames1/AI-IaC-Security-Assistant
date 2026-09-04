import { Activity, ArrowUpRight, ArrowDownRight, ShieldCheck, AlertCircle } from 'lucide-react';

export function ScoreRing({ score, size = 110, label = '', sublabel = '' }) {
  const r = 42;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 80 ? '#34d399' :
    score >= 60 ? '#fbbf24' :
    score >= 40 ? '#fb923c' :
    '#fb7185';

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox="0 0 100 100"
          style={{ transform: 'rotate(-90deg)' }}
        >
          <circle
            cx="50" cy="50" r={r}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="7"
          />
          <circle
            cx="50" cy="50" r={r}
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              transition: 'stroke-dashoffset 1s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-mono font-bold leading-none tracking-tight"
            style={{ fontSize: size * 0.26, color }}
          >
            {Math.round(score)}
          </span>
          <span className="text-slate-500 font-mono text-[10px] mt-0.5">/ 100</span>
        </div>
      </div>
      {label && (
        <div className="text-center">
          <div className="text-xs font-medium text-slate-300">{label}</div>
          {sublabel && <div className="text-[11px] text-slate-500 font-mono mt-0.5">{sublabel}</div>}
        </div>
      )}
    </div>
  );
}

export function ScoreComparison({ before, after, improvement, verdict }) {
  const improved = improvement > 0;
  const regressed = improvement < 0;

  return (
    <div className="studio-card p-6 animate-fade-in space-y-6">
      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Baseline Card */}
        <div className="bg-black/30 border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-3">
            Initial Scan
          </div>
          <ScoreRing score={before.score} size={96} />
          <div className="mt-3 text-xs font-mono text-slate-400">
            {before.total_findings} check(s) flagged
          </div>
        </div>

        {/* Delta Card */}
        <div className="bg-black/30 border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center text-center">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-2">
            Improvement Delta
          </div>
          <div className={`text-4xl font-mono font-bold flex items-center gap-1 ${
            improved ? 'text-emerald-400' : regressed ? 'text-rose-400' : 'text-slate-400'
          }`}>
            {improved && <ArrowUpRight size={28} className="stroke-[2.5]" />}
            {regressed && <ArrowDownRight size={28} className="stroke-[2.5]" />}
            {improvement > 0 ? '+' : ''}{improvement.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-2">
            {improved ? 'Score improved after verification' : 'No net score change'}
          </div>
          <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
            <ShieldCheck size={13} />
            <span>Checkov Verified</span>
          </div>
        </div>

        {/* Verified Card */}
        <div className="bg-black/30 border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center">
          <div className="text-[11px] font-mono uppercase tracking-wider text-emerald-400 mb-3">
            Post-Remediation
          </div>
          <ScoreRing score={after.score} size={96} />
          <div className="mt-3 text-xs font-mono text-emerald-300/80">
            {after.total_findings} remaining finding(s)
          </div>
        </div>
      </div>

      {/* Honest Verdict Banner */}
      {verdict && (
        <div className="rounded-lg px-4 py-3 bg-white/[0.03] border border-white/[0.08] flex items-start gap-3">
          <ShieldCheck size={18} className="text-emerald-400 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-semibold text-slate-200">{verdict}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Verified by executing Checkov directly against the AI-remediated Terraform configuration.
            </div>
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="text-[11px] text-slate-500 font-mono flex items-center justify-center gap-1.5 text-center">
        <AlertCircle size={12} className="text-amber-400/80 flex-shrink-0" />
        <span>Project-specific metric only. Not an industry-standard security certificate. Never 100% secure.</span>
      </div>
    </div>
  );
}

export const ScoreDisplay = ScoreRing;
