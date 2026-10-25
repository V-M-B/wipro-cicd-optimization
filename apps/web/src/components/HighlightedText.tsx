import { highlight } from '../lib/search';

export function HighlightedText({ text, query }: { text: string; query: string }) {
  return (
    <>
      {highlight(text, query).map((segment, i) =>
        segment.match ? <mark key={i}>{segment.text}</mark> : <span key={i}>{segment.text}</span>,
      )}
    </>
  );
}
