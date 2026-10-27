export interface CitationSource {
  citation: string;
  title: string;
  id?: string;
  doi?: string | null;
  source_url?: string | null;
  original_url?: string | null;
  findings?: Array<{ source_url?: string | null; asset_id?: string }>;
}

export interface ArticleLink {
  title: string;
  href: string | null;
}
export type ArticleIndex = Record<string, ArticleLink>;

function externalUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export function articleHref(source: CitationSource): string | null {
  const doi = source.doi
    ?.trim()
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "")
    .replace(/^doi:\s*/i, "");
  if (doi && /^10\.\d{4,9}\/\S+$/.test(doi)) {
    return `https://doi.org/${encodeURIComponent(doi).replace(/%2F/gi, "/")}`;
  }
  for (const candidate of [
    source.source_url,
    ...(source.findings ?? []).map((f) => f.source_url),
  ]) {
    const url = externalUrl(candidate);
    if (url) return url;
  }
  if (source.original_url?.startsWith("/documents/"))
    return `/api${source.original_url}`;
  if (source.original_url?.startsWith("/api/documents/"))
    return source.original_url;
  const asset = source.findings?.find((f) => f.asset_id)?.asset_id;
  if (source.id && asset)
    return `/api/documents/${encodeURIComponent(source.id)}/assets/${encodeURIComponent(asset)}?inline=true`;
  return externalUrl(source.original_url);
}

export function sourceIndex(sources: CitationSource[]): ArticleIndex {
  return Object.fromEntries(
    sources.map((source) => [
      source.citation,
      {
        title: source.title,
        href: articleHref(source),
      },
    ]),
  );
}

export function citationParts(text: string, sources: ArticleIndex) {
  const parts: Array<{
    text: string;
    href?: string | null;
    citation?: string;
  }> = [];
  let start = 0;
  for (const match of text.matchAll(/\[?\b(D\d+)\b\]?/g)) {
    const index = match.index!;
    if (index > start) parts.push({ text: text.slice(start, index) });
    const source = sources[match[1]];
    parts.push(
      source
        ? { text: source.title, href: source.href, citation: match[1] }
        : { text: match[0] },
    );
    start = index + match[0].length;
  }
  if (start < text.length) parts.push({ text: text.slice(start) });
  return parts;
}

export function remainingReferences(
  citations: string[],
  text: string,
  sources: ArticleIndex,
) {
  const mentioned = new Set(
    citationParts(text, sources).map((part) => part.citation),
  );
  return [...new Set(citations)]
    .filter((id) => !mentioned.has(id))
    .map((id) => `[${id}]`)
    .join(" · ");
}
