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
  const portrait = GAME_TYPES.has(type);
  const color = typeColor(type);
  const style = {
    height: size,
    width: portrait ? Math.round(size * 0.75) : size,
    backgroundColor: `${color}26`,
    color,
  };
  return (
    <div
      className={`relative flex-shrink-0 overflow-hidden ${portrait ? "rounded-[3px]" : "rounded-full"} ${className}`}
      style={style}
    >
      <span
        className="absolute inset-0 flex items-center justify-center font-serif"
        style={{ fontSize: size * 0.42 }}
      >
        {name.trim().charAt(0).toUpperCase()}
      </span>
      {url && (
        <img
          src={url}
          alt=""
          loading="lazy"
          onLoad={() => setLoaded(true)}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
        />
      )}
    </div>
  );
}
