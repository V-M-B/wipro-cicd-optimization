/** Trigger a browser download of text content. Kept separate so components can mock it in tests. */
export function downloadText(filename: string, content: string, mimeType = 'text/csv;charset=utf-8'): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** `orders-2024-01-05.csv` for the given date (UTC). */
export function exportFilename(prefix: string, date: Date, extension = 'csv'): string {
  return `${prefix}-${date.toISOString().slice(0, 10)}.${extension}`;
}
