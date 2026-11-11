import productRaw from '../../assets/ValorAI.svg?raw';
import companyRaw from '../../assets/Nulfinance_Inc.svg?raw';

/** Graphite ink follows currentColor; the sage symbol stays #7E9F8C. */
function prepare(raw: string, name: string | null) {
  const viewBox = raw.match(/viewBox="([^"]+)"/)?.[1] ?? '0 0 1 1';
  const inner = raw
    .replace(/<\?xml[\s\S]*?\?>/, '')
    .replace(/<svg\b[^>]*>/, '')
    .replace(/<\/svg>\s*$/, '')
    .replace(/<title[\s\S]*?<\/title>/, '')
    .replace(/<desc[\s\S]*?<\/desc>/, '')
    .replaceAll('#242830', 'currentColor');
  const a11y = name ? `role="img" aria-label="${name}"` : 'aria-hidden="true"';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" fill="none" ${a11y} focusable="false">${inner}</svg>`;
}

const productSvg = prepare(productRaw, null);
const companySvg = prepare(companyRaw, 'Nulfinance Inc.');

export function ProductMark() {
  return <span className="brand-mark" dangerouslySetInnerHTML={{ __html: productSvg }} />;
}

export function CompanyMark() {
  return <span className="company-mark" dangerouslySetInnerHTML={{ __html: companySvg }} />;
}
