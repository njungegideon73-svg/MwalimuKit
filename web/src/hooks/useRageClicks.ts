import { useEffect, useRef } from 'react';

const RAGE_CLICK_THRESHOLD = 7;
const RAGE_CLICK_WINDOW_MS = 3000;

function getStableSelector(el: HTMLElement): string {
  if (el.hasAttribute('data-testid')) {
    return `[data-testid="${el.getAttribute('data-testid')}"]`;
  }

  const tag = el.tagName.toLowerCase();
  const id = el.id ? `#${el.id}` : '';
  const classes = Array.from(el.classList)
    .filter(c => !c.startsWith('animate-'))
    .slice(0, 2)
    .map(c => `.${c}`)
    .join('');

  let text = '';
  if (tag === 'button' || tag === 'a' || tag === 'input') {
    text = el.textContent?.trim().slice(0, 30) || el.getAttribute('aria-label')?.trim().slice(0, 30) || '';
    if (text) text = `"${text}"`;
  }

  const parent = el.parentElement;
  let parentSelector = '';
  if (parent && parent !== document.body) {
    const parentTag = parent.tagName.toLowerCase();
    const parentClasses = Array.from(parent.classList)
      .filter(c => !c.startsWith('animate-'))
      .slice(0, 1)
      .map(c => `.${c}`)
      .join('');
    parentSelector = `${parentTag}${parentClasses} > `;
  }

  return `${parentSelector}${tag}${id}${classes}${text}`.trim();
}

export function useRageClicks() {
  const clicksRef = useRef<Map<string, number[]>>(new Map());

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!(target instanceof HTMLElement)) return;

      const tag = target.tagName.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      const selector = getStableSelector(target);
      const now = Date.now();
      const clicks = clicksRef.current.get(selector) || [];
      clicks.push(now);

      const recent = clicks.filter(t => now - t <= RAGE_CLICK_WINDOW_MS);
      clicksRef.current.set(selector, recent);

      if (recent.length >= RAGE_CLICK_THRESHOLD) {
        window.dispatchEvent(
          new CustomEvent('rage-click', {
            detail: { selector, count: recent.length, timestamp: now },
          }),
        );
        clicksRef.current.set(selector, []);
      }
    };

    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, []);
}
