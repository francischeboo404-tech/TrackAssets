export function checkRechartsContainers(): {ok: boolean; problems: Array<{width:number;height:number,el:HTMLElement}>} {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return { ok: true, problems: [] };
  }

  const nodes = Array.from(document.querySelectorAll<HTMLElement>('.recharts-responsive-container'));
  const problems: Array<{width:number;height:number,el:HTMLElement}> = [];

  nodes.forEach((el) => {
    const rect = el.getBoundingClientRect();
    const w = Math.round(rect.width);
    const h = Math.round(rect.height);
    if (w <= 0 || h <= 0) {
      problems.push({ width: w, height: h, el });
    }
  });

  if (problems.length) {
    // Log details to console for developer visibility
    console.error('[chartSizeChecker] Detected zero-size Recharts containers:', problems.map(p => ({ width: p.width, height: p.height } )));
  }

  return { ok: problems.length === 0, problems };
}

export default checkRechartsContainers;
