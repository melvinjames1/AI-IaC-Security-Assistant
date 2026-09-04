import { SeverityBadge } from './SeverityBadge';
import { ChevronDown, ChevronRight, ExternalLink, Search, ShieldAlert, Check } from 'lucide-react';
import { useState } from 'react';

function FindingRow({ finding }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="studio-card overflow-hidden">
      <div
        className="flex items-center justify-between p-3.5 cursor-pointer select-none hover:bg-white/[0.02]"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-3 min-w-0 pr-2">
          <SeverityBadge severity={finding.severity} />
          <div className="min-w-0">
            <div className="text-xs font-semibold text-slate-200 truncate">
              {finding.title || finding.check_id}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5 font-mono flex items-center gap-2">
              <span className="text-indigo-400/90">{finding.check_id}</span>
              <span>·</span>
              <span className="text-slate-400 truncate max-w-[200px]">{finding.resource || 'N/A'}</span>
              <span>·</span>
              <span>{finding.file}{finding.line ? `:${finding.line}` : ''}</span>
            </div>
          </div>
        </div>
        <button className="text-slate-500 hover:text-slate-300 p-1 flex-shrink-0 transition-colors">
          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </button>
      </div>

      {expanded && (
        <div className="px-4 py-3 bg-black/20 border-t border-white/[0.06] text-xs space-y-2 animate-fade-in">
          {finding.description && (
            <p className="text-slate-300 leading-relaxed">{finding.description}</p>
          )}
          {finding.guideline && (
            <div className="pt-1">
              <a
                href={finding.guideline}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300 underline underline-offset-2"
                onClick={e => e.stopPropagation()}
              >
                <span>Documentation & Guideline</span>
                <ExternalLink size={11} />
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function FindingsList({ findings, showPassed = false }) {
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [search, setSearch] = useState('');

  const failed = findings.filter(f => f.severity !== 'PASSED');
  const passed = findings.filter(f => f.severity === 'PASSED');

  const filtered = (showPassed ? findings : failed).filter(f => {
    if (severityFilter !== 'ALL' && f.severity !== severityFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        f.check_id?.toLowerCase().includes(q) ||
        f.title?.toLowerCase().includes(q) ||
        f.resource?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const counts = {
    CRITICAL: failed.filter(f => f.severity === 'CRITICAL').length,
    HIGH: failed.filter(f => f.severity === 'HIGH').length,
    MEDIUM: failed.filter(f => f.severity === 'MEDIUM').length,
    LOW: failed.filter(f => f.severity === 'LOW').length,
    PASSED: passed.length,
  };

  return (
    <div className="space-y-3">
      {/* Search & Severity Filters */}
      <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setSeverityFilter('ALL')}
            className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium transition-all ${
              severityFilter === 'ALL'
                ? 'bg-white/10 text-white border border-white/20'
                : 'text-slate-400 hover:text-slate-200 border border-transparent'
            }`}
          >
            ALL ({showPassed ? findings.length : failed.length})
          </button>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => {
            const count = counts[sev];
            if (count === 0) return null;
            return (
              <button
                key={sev}
                onClick={() => setSeverityFilter(severityFilter === sev ? 'ALL' : sev)}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium transition-all ${
                  severityFilter === sev
                    ? 'bg-white/10 text-white border border-white/20'
                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                {sev} ({count})
              </button>
            );
          })}
          {showPassed && counts.PASSED > 0 && (
            <button
              onClick={() => setSeverityFilter(severityFilter === 'PASSED' ? 'ALL' : 'PASSED')}
              className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium text-emerald-400 transition-all ${
                severityFilter === 'PASSED'
                  ? 'bg-emerald-500/15 border border-emerald-500/30'
                  : 'hover:text-emerald-300 border border-transparent'
              }`}
            >
              PASSED ({counts.PASSED})
            </button>
          )}
        </div>

        {/* Search input */}
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="search"
            placeholder="Filter checks..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full sm:w-48 pl-8 pr-3 py-1 bg-white/[0.04] border border-white/[0.08] focus:border-indigo-500/50 rounded-md text-xs text-slate-200 placeholder-slate-500 outline-none transition-colors"
          />
        </div>
      </div>

      {/* Findings items */}
      {filtered.length === 0 ? (
        <div className="studio-card p-8 text-center text-slate-500 text-xs">
          {search || severityFilter !== 'ALL' ? 'No checks match your current filter.' : 'No findings detected.'}
        </div>
      ) : (
        <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
          {filtered.map((f, i) => (
            <FindingRow key={`${f.check_id}-${i}`} finding={f} />
          ))}
        </div>
      )}
    </div>
  );
}
