import { useState } from "react";
import { useImage } from "@/hooks/useImage";
import { GAME_TYPES, typeColor } from "@/lib/theme";

interface ThumbProps {
  type: string;
  name: string;
  /** Height in px; games are portrait (3:4), everything else is round. */
  size?: number;
  urgent?: boolean;
  className?: string;
}

/** Picture of an entity with a quiet placeholder (initial on the type colour). */
export function Thumb({ type, name, size = 40, urgent, className = "" }: ThumbProps) {
  const url = useImage(type, name, urgent);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [logo, setLogo] = useState(false); // wide or tall picture of a non-game entity: show it whole
  const portrait = GAME_TYPES.has(type);
  // looking the picture up, or downloading it
  const loading = url === undefined || (!!url && !loaded && !failed);
  const color = typeColor(type);
  const style = {
    height: size,
    width: portrait ? Math.round(size * 0.75) : size,
    backgroundColor: logo && loaded ? "#ece8dd" : `${color}26`,
    color,
  };
  return (
    <div
      className={`relative flex-shrink-0 overflow-hidden ${portrait ? "rounded-[3px]" : "rounded-full"} ${className}`}
      style={style}
    >
      {loading && (
        <span
          className="absolute left-1/2 top-1/2 animate-spin rounded-full border-2 border-current border-t-transparent opacity-70"
          style={{
            width: Math.max(10, size * 0.32),
            height: Math.max(10, size * 0.32),
            marginLeft: -Math.max(10, size * 0.32) / 2,
            marginTop: -Math.max(10, size * 0.32) / 2,
          }}
          role="status"
          aria-label="Carico la foto"
        />
      )}
      {!loaded && !loading && (
        <span
          className="absolute inset-0 flex items-center justify-center font-serif"
          style={{ fontSize: size * 0.42 }}
        >
          {name.trim().charAt(0).toUpperCase()}
        </span>
      )}
      {url && (
        <img
          src={url}
          alt=""
          loading="lazy"
          onError={() => setFailed(true)}
          onLoad={(e) => {
            const { naturalWidth: w, naturalHeight: h } = e.currentTarget;
            if (!portrait && w && h && (w / h > 1.3 || w / h < 0.77)) setLogo(true);
            setLoaded(true);
            setFailed(false);
          }}
          className={`absolute inset-0 h-full w-full transition-opacity duration-300 ${
            logo ? "object-contain p-[14%]" : "object-cover"
          } ${loaded ? "opacity-100" : "opacity-0"}`}
        />
      )}
    </div>
  );
}
