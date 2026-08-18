interface ChartData {
  type: 'bar' | 'line' | 'pie';
  labels: string[];
  values: number[];
  title?: string;
}

interface SimpleChartProps {
  data: ChartData | string;
}

function parseChartData(data: SimpleChartProps['data']): ChartData | null {
  if (typeof data === 'string') {
    try {
      return JSON.parse(data) as ChartData;
    } catch {
      return null;
    }
  }
  return data;
}

export function SimpleChart({ data }: SimpleChartProps) {
  const chart = parseChartData(data);
  if (!chart) return null;

  const maxValue = Math.max(...chart.values, 1);

  if (chart.type === 'bar') {
    return (
      <div className="my-3 p-4 bg-gray-50 rounded-lg">
        {chart.title && <p className="text-sm font-medium text-gray-700 mb-2 text-center">{chart.title}</p>}
        <div className="flex items-end justify-between gap-2 h-32">
          {chart.values.map((val, i) => (
            <div key={i} className="flex flex-col items-center flex-1">
              <div className="text-xs text-gray-600 mb-1">{val}</div>
              <div
                className="w-full bg-primary-500 rounded-t"
                style={{ height: `${(val / maxValue) * 100}%`, minHeight: '4px' }}
              />
              <div className="text-xs text-gray-500 mt-1 truncate w-full text-center">{chart.labels[i]}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (chart.type === 'line') {
    const points = chart.values.map((val, i) => {
      const x = (i / Math.max(chart.values.length - 1, 1)) * 100;
      const y = 100 - (val / maxValue) * 100;
      return `${x},${y}`;
    }).join(' ');

    return (
      <div className="my-3 p-4 bg-gray-50 rounded-lg">
        {chart.title && <p className="text-sm font-medium text-gray-700 mb-2 text-center">{chart.title}</p>}
        <svg viewBox="0 0 100 100" className="w-full h-32">
          <polyline
            fill="none"
            stroke="#2563eb"
            strokeWidth="3"
            points={points}
          />
          {chart.values.map((val, i) => {
            const x = (i / Math.max(chart.values.length - 1, 1)) * 100;
            const y = 100 - (val / maxValue) * 100;
            return (
              <circle key={i} cx={x} cy={y} r="3" fill="#2563eb" />
            );
          })}
        </svg>
        <div className="flex justify-between mt-1">
          {chart.labels.map((label, i) => (
            <span key={i} className="text-xs text-gray-500">{label}</span>
          ))}
        </div>
      </div>
    );
  }

  if (chart.type === 'pie') {
    const total = chart.values.reduce((a, b) => a + b, 0);
    let cumulative = 0;
    const colors = ['#2563eb', '#16a34a', '#dc2626', '#f59e0b', '#8b5cf6', '#ec4899'];

    return (
      <div className="my-3 p-4 bg-gray-50 rounded-lg">
        {chart.title && <p className="text-sm font-medium text-gray-700 mb-2 text-center">{chart.title}</p>}
        <div className="flex items-center gap-4">
          <svg viewBox="0 0 32 32" className="w-24 h-24">
            {chart.values.map((val, i) => {
              const angle = (val / total) * 360;
              const startAngle = cumulative;
              cumulative += angle;
              const endAngle = cumulative;
              const largeArc = angle > 180 ? 1 : 0;
              const x1 = 16 + 16 * Math.cos((startAngle - 90) * Math.PI / 180);
              const y1 = 16 + 16 * Math.sin((startAngle - 90) * Math.PI / 180);
              const x2 = 16 + 16 * Math.cos((endAngle - 90) * Math.PI / 180);
              const y2 = 16 + 16 * Math.sin((endAngle - 90) * Math.PI / 180);
              const path = angle >= 360
                ? `M 16 16 m -16 0 a 16 16 0 1 1 32 0 a 16 16 0 1 1 -32 0`
                : `M 16 16 L ${x1} ${y1} A 16 16 0 ${largeArc} 1 ${x2} ${y2} Z`;
              return (
                <path key={i} d={path} fill={colors[i % colors.length]} stroke="white" strokeWidth="0.5" />
              );
            })}
          </svg>
          <div className="flex-1">
            {chart.labels.map((label, i) => (
              <div key={i} className="flex items-center gap-2 text-xs mb-1">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: colors[i % colors.length] }} />
                <span className="text-gray-700">{label}: {chart.values[i]}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
