interface MetricCardProps {
  icon: React.ElementType;
  iconColor: string;
  iconBgColor: string;
  value: string;
  label: string;
  sublabel?: string;
  sublabelColor?: string;
  isClickable?: boolean;
  isSelected?: boolean;
  glowColor?: string;
  onClick?: () => void;
}

/**
 * A reusable metric card component for displaying stats.
 * Can be static or clickable with selection state. Optional `sublabel`
 * renders a smaller line under the primary label (e.g. a timestamp).
 */
export function MetricCard({
  icon: Icon,
  iconColor,
  iconBgColor,
  value,
  label,
  sublabel,
  sublabelColor = 'text-muted-foreground',
  isClickable = false,
  isSelected = false,
  glowColor = '',
  onClick,
}: MetricCardProps) {
  const baseClasses =
    'p-4 border rounded-lg bg-card/30 transition-all duration-200';

  const body = (
    <>
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 ${iconBgColor} rounded-lg`}>
          <Icon className={`h-5 w-5 ${iconColor}`} />
        </div>
      </div>
      <p className="text-2xl font-semibold text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground mt-1">
        {label}
        {sublabel ? (
          <span className={`ml-1.5 ${sublabelColor}`}>({sublabel})</span>
        ) : null}
      </p>
    </>
  );

  if (isClickable) {
    return (
      <button
        onClick={onClick}
        className={`${baseClasses} text-left cursor-pointer
          ${
            isSelected
              ? `border-zinc-600 ${glowColor}`
              : 'border-border/60 hover:border-border hover:shadow-[0_0_10px_rgba(255,255,255,0.1)]'
          }
        `}
      >
        {body}
      </button>
    );
  }

  return <div className={`${baseClasses} border-border/60`}>{body}</div>;
}
