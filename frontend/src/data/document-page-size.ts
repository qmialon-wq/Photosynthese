export const DOCUMENT_PAGE_SIZE_KEY = "symbiose:documents-per-page:v1";
export const documentPageSizes = [4, 8, 12, 16] as const;
export type DocumentPageSize = (typeof documentPageSizes)[number];

export function documentPageSize(value: unknown): DocumentPageSize {
  const size = Number(value);
  return documentPageSizes.includes(size as DocumentPageSize)
    ? (size as DocumentPageSize)
    : 16;
}

export function restoreDocumentPageSize(): DocumentPageSize {
  try {
    return documentPageSize(localStorage.getItem(DOCUMENT_PAGE_SIZE_KEY));
  } catch {
    return 16;
  }
}

export function persistDocumentPageSize(size: DocumentPageSize) {
  try {
    localStorage.setItem(DOCUMENT_PAGE_SIZE_KEY, String(size));
  } catch {
    // Le contrôle reste utilisable lorsque le stockage du navigateur est bloqué.
  }
}
