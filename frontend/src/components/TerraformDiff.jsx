import { useState } from 'react';
import { Copy, Check, Download, Split, FileCode } from 'lucide-react';

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };
  return (
    <button onClick={handleCopy} className="btn-studio-secondary text-xs py-1 px-2.5" title="Copy to clipboard">
      {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
      <span>{copied ? 'Copied' : 'Copy'}</span>
    </button>
  );
}

function DownloadButton({ text, filename = 'remediated_main.tf' }) {
  const handleDownload = () => {
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <button onClick={handleDownload} className="btn-studio-secondary text-xs py-1 px-2.5" title="Download file">
      <Download size={13} />
      <span>Download</span>
    </button>
  );
}

export function TerraformDiff({ original, corrected, isLoading }) {
  const [activeTab, setActiveTab] = useState('split');

  if (isLoading) {
    return (
      <div className="studio-card p-8 text-center">
        <div className="inline-block w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mb-3" />
        <div className="text-xs font-mono text-slate-400">Synthesizing remediated HCL...</div>
      </div>
    );
  }

  if (!corrected) return null;

  return (
    <div className="space-y-3 animate-fade-in">
      {/* Control bar */}
      <div className="flex items-center justify-between pb-1">
        <div className="flex items-center gap-1 p-0.5 bg-black/40 border border-white/[0.08] rounded-lg">
          <button
            className={`tab-studio ${activeTab === 'split' ? 'active' : ''}`}
            onClick={() => setActiveTab('split')}
          >
            <Split size={13} />
            <span>Split View</span>
          </button>
          <button
            className={`tab-studio ${activeTab === 'corrected' ? 'active' : ''}`}
            onClick={() => setActiveTab('corrected')}
          >
            <FileCode size={13} />
            <span>Remediated</span>
          </button>
          <button
            className={`tab-studio ${activeTab === 'original' ? 'active' : ''}`}
            onClick={() => setActiveTab('original')}
          >
            <span>Original</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <CopyButton text={activeTab === 'original' ? original : corrected} />
          {activeTab !== 'original' && <DownloadButton text={corrected} />}
        </div>
      </div>

      {/* Split view */}
      {activeTab === 'split' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div className="studio-card overflow-hidden">
            <div className="px-3.5 py-2 bg-black/30 border-b border-white/[0.06] flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>original.tf</span>
              <span className="text-rose-400/80">Unsecured</span>
            </div>
            <pre className="p-3.5 text-[11.5px] font-mono leading-relaxed text-slate-400 overflow-x-auto max-h-[380px]">
              {original}
            </pre>
          </div>

          <div className="studio-card overflow-hidden border-emerald-500/20">
            <div className="px-3.5 py-2 bg-emerald-950/20 border-b border-emerald-500/20 flex items-center justify-between text-[11px] font-mono text-emerald-300">
              <span>remediated.tf</span>
              <span className="text-emerald-400 font-semibold">AI Generated Fix</span>
            </div>
            <pre className="p-3.5 text-[11.5px] font-mono leading-relaxed text-emerald-100 overflow-x-auto max-h-[380px] bg-emerald-950/[0.05]">
              {corrected}
            </pre>
          </div>
        </div>
      )}

      {/* Remediated Only */}
      {activeTab === 'corrected' && (
        <div className="studio-card overflow-hidden border-emerald-500/20">
          <div className="px-3.5 py-2 bg-emerald-950/20 border-b border-emerald-500/20 flex items-center justify-between text-[11px] font-mono text-emerald-300">
            <span>remediated.tf (AI Corrected)</span>
            <span className="text-emerald-400">Ready for Verification</span>
          </div>
          <pre className="p-4 text-[12px] font-mono leading-relaxed text-emerald-100 overflow-x-auto max-h-[420px]">
            {corrected}
          </pre>
        </div>
      )}

      {/* Original Only */}
      {activeTab === 'original' && (
        <div className="studio-card overflow-hidden">
          <div className="px-3.5 py-2 bg-black/30 border-b border-white/[0.06] flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>original.tf</span>
            <span className="text-rose-400">Baseline Input</span>
          </div>
          <pre className="p-4 text-[12px] font-mono leading-relaxed text-slate-300 overflow-x-auto max-h-[420px]">
            {original}
          </pre>
        </div>
      )}
    </div>
  );
}

export { CopyButton };
