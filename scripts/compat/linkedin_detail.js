// Compatibility extraction for LinkedIn's newer job layout. Serialized into the
// upstream OpenCLI browser evaluator; do not capture module/global state here.
export function extractModernJob(document, currentUrl) {
  const clean = (value) => String(value || '').replace(/[\u00a0\u202f]+/g, ' ').replace(/\s+/g, ' ').trim();
  const url = new URL(currentUrl);
  if (url.hostname !== 'linkedin.com' && !url.hostname.endsWith('.linkedin.com')) return null;
  const id = url.pathname.match(/^\/jobs\/view\/(\d+)\/?$/)?.[1]
    || (/^\/jobs\/(search|search-results)\/?$/.test(url.pathname) && url.searchParams.get('currentJobId'));
  if (!id || !/^\d+$/.test(id)) return null;
  const parts = clean(document.title).replace(/\s*\|\s*LinkedIn$/i, '').split(/\s+\|\s+/);
  if (parts.length < 2 || !parts[0] || !parts.at(-1)) return null;
  const heading = [...document.querySelectorAll('h2,h3,[role="heading"]')]
    .find(el => /^(About the job|Om stillingen|职位简介)$/i.test(clean(el.textContent)));
  let root = heading?.parentElement;
  let box;
  // Nearest ancestor that contains the actual description, never the entire page.
  for (let depth = 0; root && depth < 5; depth++, root = root.parentElement) {
    if (['BODY','HTML','MAIN'].includes(root.tagName)) break;
    box = root.querySelector('[data-testid="expandable-text-box"]');
    if (box) break;
  }
  if (!box) return null;
  root.querySelector('[data-testid="expandable-text-button"]')?.click();
  // Collapsed boxes contain the full text in the DOM; innerText can omit it.
  const description = clean(box.textContent);
  if (description.length < 80) return null;
  return {
    title: parts.slice(0, -1).join(' | '), company: parts.at(-1), description,
    url: `https://www.linkedin.com/jobs/view/${id}`,
    location: '', workplace_type: '', job_type: '', listed: '', applicants: '',
    apply_url: '', company_url: '',
  };
}
