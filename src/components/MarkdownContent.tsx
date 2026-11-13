import { Fragment, type ReactNode } from 'react';

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let idx = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    const key = `${keyPrefix}-${idx++}`;

    if (token.startsWith('`') && token.endsWith('`')) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith('**') && token.endsWith('**')) {
      nodes.push(<strong key={key}>{renderInline(token.slice(2, -2), `${key}-b`)}</strong>);
    } else if (token.startsWith('*') && token.endsWith('*')) {
      nodes.push(<em key={key}>{renderInline(token.slice(1, -1), `${key}-i`)}</em>);
    } else if (token.startsWith('[')) {
      const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      if (linkMatch) {
        const [, label, rawUrl] = linkMatch;
        const url = rawUrl.trim();
        if (/^https?:\/\//i.test(url)) {
          nodes.push(
            <a key={key} href={url} target="_blank" rel="noopener noreferrer">
              {label}
            </a>,
          );
        } else {
          nodes.push(label);
        }
      } else {
        nodes.push(token);
      }
    }

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  return trimmed.split('|').map((cell) => cell.trim());
}

function isTableSeparator(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.includes('|')) return false;
  const cells = splitTableRow(trimmed);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function isBlockStart(line: string): boolean {
  const t = line.trim();
  return (
    t === '' ||
    /^#{1,4}\s+/.test(t) ||
    /^(-{3,}|\*{3,})$/.test(t) ||
    t.startsWith('> ') ||
    t === '>' ||
    /^[-*]\s+/.test(t) ||
    /^\d+\.\s+/.test(t)
  );
}

export function MarkdownContent({ content }: { content: string }) {
  const lines = content.replace(/\r\n?/g, '\n').split('\n');
  const blocks: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const raw = lines[i];
    const trimmed = raw.trim();

    if (trimmed === '') {
      i += 1;
      continue;
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
      blocks.push(<hr key={`hr-${i}`} />);
      i += 1;
      continue;
    }

    // Headings (offset by +1 so ## becomes h3 inside modal whose title is h2)
    const headingMatch = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text = headingMatch[2].trim();
      const key = `h-${i}`;
      const inline = renderInline(text, key);
      if (level <= 2) {
        blocks.push(<h3 key={key}>{inline}</h3>);
      } else if (level === 3) {
        blocks.push(<h4 key={key}>{inline}</h4>);
      } else {
        blocks.push(<h5 key={key}>{inline}</h5>);
      }
      i += 1;
      continue;
    }

    // Table
    if (trimmed.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = splitTableRow(trimmed);
      const startLine = i;
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim() !== '') {
        rows.push(splitTableRow(lines[i]));
        i += 1;
      }
      blocks.push(
        <div key={`tbl-${startLine}`} className="md-table-wrap">
          <table>
            <thead>
              <tr>
                {headers.map((cell, ci) => (
                  <th key={ci}>{renderInline(cell, `th-${startLine}-${ci}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri}>
                  {headers.map((_, ci) => (
                    <td key={ci}>{renderInline(row[ci] ?? '', `td-${startLine}-${ri}-${ci}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('>')) {
      const startLine = i;
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i += 1;
      }
      const quoteParagraphs = quoteLines.join('\n').split(/\n{2,}/);
      blocks.push(
        <blockquote key={`bq-${startLine}`}>
          {quoteParagraphs.map((para, pi) => (
            <p key={pi}>{renderInline(para.replace(/\n/g, ' '), `bq-${startLine}-${pi}`)}</p>
          ))}
        </blockquote>,
      );
      continue;
    }

    // Unordered list
    if (/^[-*]\s+/.test(trimmed)) {
      const startLine = i;
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i += 1;
      }
      blocks.push(
        <ul key={`ul-${startLine}`}>
          {items.map((item, li) => (
            <li key={li}>{renderInline(item, `ul-${startLine}-${li}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered list
    if (/^\d+\.\s+/.test(trimmed)) {
      const startLine = i;
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i += 1;
      }
      blocks.push(
        <ol key={`ol-${startLine}`}>
          {items.map((item, li) => (
            <li key={li}>{renderInline(item, `ol-${startLine}-${li}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // Paragraph
    const startLine = i;
    const paraLines: string[] = [];
    while (i < lines.length) {
      const current = lines[i];
      if (isBlockStart(current)) break;
      if (current.trim().includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) break;
      paraLines.push(current.trim());
      i += 1;
    }
    if (paraLines.length > 0) {
      blocks.push(
        <p key={`p-${startLine}`}>
          {renderInline(paraLines.join(' '), `p-${startLine}`)}
        </p>,
      );
    } else {
      // Fallback safeguard to ensure forward progress
      blocks.push(<Fragment key={`raw-${i}`}>{renderInline(trimmed, `raw-${i}`)}</Fragment>);
      i += 1;
    }
  }

  return <div className="lesson-markdown">{blocks}</div>;
}
