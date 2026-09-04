import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, Info, Shield, CheckCircle2, Sparkles } from 'lucide-react';
import { SeverityBadge } from './SeverityBadge';

function ExplanationCard({ explanation }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="studio-card overflow-hidden">
      <div
        className="flex items-center justify-between p-3.5 cursor-pointer select-none hover:bg-white/[0.02]"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-3 min-w-0 pr-2">
          <SeverityBadge severity={explanation.severity} />
          <div className="min-w-0">
            <div className="text-xs font-semibold text-slate-200 truncate">
              {explanation.title}
            </div>
            <div className="text-[11px] text-slate-500 font-mono mt-0.5">
              {explanation.check_id}
            </div>
          </div>
        </div>
        <button className="text-slate-500 hover:text-slate-300 p-1 flex-shrink-0">
          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </button>
      </div>

      {expanded && (
        <div className="px-4 py-3 bg-black/20 border-t border-white/[0.06] text-xs space-y-2.5 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            <div className="p-2.5 rounded-md bg-white/[0.03] border border-white/[0.05]">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
                <Info size={11} className="text-sky-400" />
                <span>What it means</span>
              </div>
              <div className="text-slate-300 leading-relaxed text-[12px]">{explanation.what_it_means}</div>
            </div>

            <div className="p-2.5 rounded-md bg-white/[0.03] border border-white/[0.05]">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
                <Shield size={11} className="text-rose-400" />
                <span>Potential impact</span>
              </div>
              <div className="text-slate-300 leading-relaxed text-[12px]">{explanation.potential_impact}</div>
            </div>
          </div>

          <div className="p-2.5 rounded-md bg-emerald-950/20 border border-emerald-500/20">
            <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 mb-1 flex items-center gap-1.5">
              <CheckCircle2 size={11} />
              <span>Remediation Advice</span>
            </div>
            <div className="text-emerald-200/90 leading-relaxed text-[12px]">{explanation.remediation_advice}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export function AIAnalysisPanel({ analysis, isLoading }) {
  if (isLoading) {
    return (
      <div className="studio-card p-10 text-center">
        <div className="inline-block w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mb-3" />
        <div className="text-xs font-mono text-slate-400">Synthesizing threat model & fix recommendations...</div>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="space-y-3 animate-fade-in">
      {/* Mock notice if applicable */}
      {analysis.is_mock && (
        <div className="px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-300/90 font-mono">
          <AlertTriangle size={14} className="text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="leading-snug">{analysis.mock_notice}</div>
        </div>
      )}

      {/* Explanations list */}
      {analysis.explanations?.length > 0 ? (
        <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
          {analysis.explanations.map((exp, i) => (
            <ExplanationCard key={`${exp.check_id}-${i}`} explanation={exp} />
          ))}
        </div>
      ) : (
        <div className="studio-card p-8 text-center text-slate-500 text-xs">
          No explanations returned.
        </div>
      )}

      {/* Assumptions */}
      {analysis.assumptions?.length > 0 && (
        <div className="studio-card p-3 text-xs bg-black/20">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1.5">
            <Sparkles size={11} className="text-indigo-400" />
            <span>AI Reasoning Assumptions</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-slate-400 text-[11.5px] font-mono">
            {analysis.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
