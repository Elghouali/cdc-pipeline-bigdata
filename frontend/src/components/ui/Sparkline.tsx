interface SparklineProps {
  data: number[];
  color: string;
  width?: number;
  height?: number;
  strokeWidth?: number;
}

export function Sparkline({ data, color, width = 100, height = 32, strokeWidth = 1.5 }: SparklineProps) {
  if (data.length < 2) return null;

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pad = 2;
  const usableH = height - pad * 2;

  const pts = data.map((v, i) => ({
    x: (i / (data.length - 1)) * width,
    y: pad + usableH - ((v - min) / range) * usableH,
  }));

  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`;
  // Derive a stable, unique-per-color gradient ID (safe for multiple instances on one page)
  const gradId = `sg-${color.replace(/[^a-zA-Z0-9]/g, '').slice(0, 10)}`;

  const lastPt = pts[pts.length - 1];

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="overflow-visible"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lastPt.x} cy={lastPt.y} r={2.5} fill={color} />
      <circle cx={lastPt.x} cy={lastPt.y} r={4} fill={color} fillOpacity="0.2" />
    </svg>
  );
}
