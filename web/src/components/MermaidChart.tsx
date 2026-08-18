import { useEffect, useRef } from 'react';

interface MermaidChartProps {
  code: string;
}

export function MermaidChart({ code }: MermaidChartProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !code) return;
    let cancelled = false;

    const render = async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({ startOnLoad: false, theme: 'default' });
        const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`;
        ref.current!.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;
        await mermaid.run({ querySelector: `#${id}` });
      } catch {
        ref.current!.innerHTML = `<pre class="text-xs text-gray-500 bg-gray-50 p-2 rounded">${code}</pre>`;
      }
      if (cancelled) return;
    };

    render();

    return () => {
      cancelled = true;
    };
  }, [code]);

  if (!code) return null;

  return <div ref={ref} className="my-3 flex justify-center" />;
}
