export const SEVERITY_CONFIG = {
  CRITICAL: {
    label: 'CRITICAL',
    badgeClass: 'sev-critical',
    dotColor: '#fb7185',
  },
  HIGH: {
    label: 'HIGH',
    badgeClass: 'sev-high',
    dotColor: '#fb923c',
  },
  MEDIUM: {
    label: 'MEDIUM',
    badgeClass: 'sev-medium',
    dotColor: '#fcd34d',
  },
  LOW: {
    label: 'LOW',
    badgeClass: 'sev-low',
    dotColor: '#7dd3fc',
  },
  INFO: {
    label: 'INFO',
    badgeClass: 'sev-unrated',
    dotColor: '#94a3b8',
  },
  UNRATED: {
    label: 'UNRATED',
    badgeClass: 'sev-unrated',
    dotColor: '#94a3b8',
  },
  PASSED: {
    label: 'PASSED',
    badgeClass: 'sev-passed',
    dotColor: '#34d399',
  },
};

export function SeverityBadge({ severity }) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.UNRATED;
  return (
    <span className={`sev-badge ${cfg.badgeClass}`}>
      <span
        className="w-1.5 h-1.5 rounded-full inline-block"
        style={{ backgroundColor: cfg.dotColor }}
      />
      {severity}
    </span>
  );
}
