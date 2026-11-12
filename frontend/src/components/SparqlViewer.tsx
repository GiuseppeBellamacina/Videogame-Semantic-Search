import { useState } from "react";
import { Check, Copy, Pencil } from "lucide-react";

interface SparqlViewerProps {
  sparql: string;
  /** Still being generated or run. */
  live?: boolean;
  success?: boolean;
  /** Load the query in the editor. */
  onEdit?: (sparql: string) => void;
}

export function SparqlViewer({ sparql, live, success = true, onEdit }: SparqlViewerProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  if (!sparql) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(sparql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  const kind = /^\s*(?:PREFIX[^\n]*\n)*\s*CONSTRUCT/i.test(sparql) ? "CONSTRUCT" : "SELECT";

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setOpen(!open)}
          className="label flex items-center gap-2 hover:text-ink"
          aria-expanded={open}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${live ? "animate-shimmer bg-petrol" : success ? "bg-petrol" : "bg-brick"}`}
          />
          Query SPARQL · {kind}
          <span className="text-brick">{open ? "nascondi" : "mostra"}</span>
        </button>
        <span className="flex items-center gap-3">
          {onEdit && !live && (
            <button onClick={() => onEdit(sparql)} className="flex items-center gap-1 text-xs text-mute hover:text-brick" title="Apri la query nell'editor">
              <Pencil className="h-3.5 w-3.5" /> Modifica
            </button>
          )}
          {open && (
            <button onClick={copy} className="flex items-center gap-1 text-xs text-mute hover:text-ink">
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Copiata" : "Copia"}
            </button>
          )}
        </span>
      </div>
      {open && (
        <pre className="mt-2 max-h-72 overflow-auto bg-black/40 p-3 font-mono text-[11.5px] leading-relaxed text-mute">
          {sparql}
        </pre>
      )}
    </div>
  );
}
