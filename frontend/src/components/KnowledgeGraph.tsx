import { useRef, useCallback, useEffect, useState, useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { Crosshair, Eraser, Eye, EyeOff, Focus, Link2, Lock, Network, Search, Trash2, Unlock, X } from "lucide-react";
import type { GraphData, GraphNode } from "@/types";
import { GAME_TYPES, IMAGE_TYPES, typeColor, typeLabel } from "@/lib/theme";
import { peekImage, requestImage } from "@/lib/imageQueue";

interface KnowledgeGraphProps {
  data: GraphData;
  loading?: boolean;
  onNodeClick: (nodeId: string) => void;
  highlightNode?: string | null;
  onNodeRightClick?: (node: GraphNode, x: number, y: number) => void;
  /** Nodes hidden one by one from the context menu, and how to bring them back. */
  hiddenCount?: number;
  onRestoreHidden?: () => void;
  /** Keep only these nodes on the canvas / hide these nodes. */
  onKeepOnly?: (ids: string[]) => void;
  onHideMany?: (ids: string[]) => void;
  /** Empty the whole canvas (results, extra nodes, hidden nodes). */
  onClear?: () => void;
  /** Delete nodes from the scene for good (hiding keeps them recoverable). */
  onDeleteMany?: (ids: string[]) => void;
  /** Delete every hidden node; `typeHiddenIds` are the ones hidden through the legend. */
  onDeleteHidden?: (typeHiddenIds: string[]) => void;
}

const BG = "#14130f";
const INK = "#ece8dd";
const BRICK = "#d4573b";
const FONT = '"IBM Plex Sans", system-ui, sans-serif';
/** Past this many nodes only games are fetched and the O(n²) collision is skipped. */
const BIG_GRAPH = 150;

const endId = (e: string | GraphNode) => (typeof e === "string" ? e : e.id);
/** Relations the reasoner derives (sharesDeveloperWith...): drawn dashed, never labelled. */
const isDerived = (label?: string) => /^shar(e|ed)/.test(label ?? "");
/** zoomToFit would blow a single node up to the whole screen. */
const MAX_FIT_ZOOM = 1.8;

// Decoded images, shared by every node that uses the same url
const decoded = new Map<string, HTMLImageElement | null>();
function decode(url: string, onLoaded: () => void): HTMLImageElement | null {
  if (decoded.has(url)) return decoded.get(url) ?? null;
  decoded.set(url, null);
  const img = new Image();
  img.onload = () => {
    decoded.set(url, img);
    onLoaded();
  };
  img.src = url;
  return null;
}

/** Drawn size in graph units: games are portrait, the rest round. */
function shape(type: string) {
  if (GAME_TYPES.has(type)) return { w: 34, h: 46, r: 0 };
  switch (type) {
    case "Developer":
    case "Publisher":
    case "Platform":
    case "Franchise":
    case "GameEngine":
      return { w: 0, h: 0, r: 17 };
    case "Character":
      return { w: 0, h: 0, r: 12 };
    default:
      return { w: 0, h: 0, r: 7 };
  }
}
const hitRadius = (type: string) => {
  const s = shape(type);
  return s.r || Math.hypot(s.w, s.h) / 2;
};

export function KnowledgeGraph({
  data,
  loading,
  onNodeClick,
  highlightNode,
  onNodeRightClick,
  hiddenCount = 0,
  onRestoreHidden,
  onKeepOnly,
  onHideMany,
  onClear,
  onDeleteMany,
  onDeleteHidden,
}: KnowledgeGraphProps) {
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [hovered, setHovered] = useState<string | null>(null);
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());
  const [frozen, setFrozen] = useState(false);
  const [find, setFind] = useState("");
  const [showDerived, setShowDerived] = useState(true);
  // a second node clicked while another one is in focus: we show how the two are related
  const [secondary, setSecondary] = useState<string | null>(null);
  const [alertOff, setAlertOff] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set()); // multi-selection (shift+click)
  const labelBoxes = useRef<number[][]>([]); // edge labels drawn this frame, to avoid overlaps
  const [, setTick] = useState(0);
  const repaint = useCallback(() => setTick((t) => t + 1), []);
  const longPressFired = useRef(false);
  const fit = useCallback((ms: number) => {
    const g = graphRef.current;
    if (!g) return;
    g.zoomToFit(ms, 60);
    setTimeout(() => {
      if (g.zoom() > MAX_FIT_ZOOM) g.zoom(MAX_FIT_ZOOM, 200);
    }, ms + 40);
  }, []);

  // ── data filtered by the legend ──────────────────────────────────────────
  const filtered = useMemo<GraphData>(() => {
    if (!hiddenTypes.size && showDerived) return data;
    const ids = new Set(data.nodes.filter((n) => !hiddenTypes.has(n.type)).map((n) => n.id));
    return {
      nodes: data.nodes.filter((n) => ids.has(n.id)),
      links: data.links.filter(
        (l) =>
          ids.has(endId(l.source)) &&
          ids.has(endId(l.target)) &&
          (showDerived || !isDerived(l.label)),
      ),
    };
  }, [data, hiddenTypes, showDerived]);

  useEffect(() => setSecondary(null), [highlightNode]);
  useEffect(() => setAlertOff(false), [hiddenCount, hiddenTypes.size]);

  const typeCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const n of data.nodes) m.set(n.type, (m.get(n.type) ?? 0) + 1);
    m.delete("Unknown");
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [data.nodes]);

  // neighbours of the node in focus (hover wins over selection): everything else is dimmed
  const focusId = hovered ?? highlightNode ?? null;
  const neighbours = useMemo(() => {
    if (!focusId) return null;
    const s = new Set<string>([focusId]);
    for (const l of filtered.links) {
      const a = endId(l.source);
      const b = endId(l.target);
      if (a === focusId) s.add(b);
      if (b === focusId) s.add(a);
    }
    return s;
  }, [focusId, filtered.links]);

  // ── pictures: asked through the shared queue, painted as they arrive ─────
  useEffect(() => {
    const big = data.nodes.length > BIG_GRAPH;
    for (const n of data.nodes.slice(0, 400)) {
      if (!IMAGE_TYPES.has(n.type) || (big && !GAME_TYPES.has(n.type))) continue;
      requestImage(n.type, n.label).then((url) => {
        if (url) decode(url, repaint);
        repaint();
      });
    }
  }, [data.nodes, repaint]);

  useEffect(() => {
    // the node under the pointer or selected goes to the front of the queue
    const n = data.nodes.find((x) => x.id === focusId);
    if (n && IMAGE_TYPES.has(n.type))
      requestImage(n.type, n.label, true).then((url) => {
        if (url) decode(url, repaint);
        repaint();
      });
  }, [focusId, data.nodes, repaint]);

  // ── size, forces, fit ────────────────────────────────────────────────────
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let prev = 0;
    const ro = new ResizeObserver(([e]) => {
      const { width, height } = e.contentRect;
      setSize({ width, height });
      if (prev === 0 && width > 0 && data.nodes.length)
        setTimeout(() => fit(300), 120);
        setTimeout(() => fit(300), 600);
      prev = width;
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [data.nodes.length, fit]);

  useEffect(() => {
    const fg = graphRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(-420);
    const link = fg.d3Force("link");
    link?.distance(95);
    link?.strength(0.08);

    let nodes: any[] = [];
    const collide: any = (alpha: number) => {
      if (nodes.length > BIG_GRAPH) return;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = (b.x ?? 0) - (a.x ?? 0);
          const dy = (b.y ?? 0) - (a.y ?? 0);
          const dist = Math.hypot(dx, dy) || 1;
          const min = hitRadius(a.type) + hitRadius(b.type) + 14;
          if (dist < min) {
            const push = ((min - dist) / dist) * alpha * 0.9;
            a.x -= dx * push;
            a.y -= dy * push;
            b.x += dx * push;
            b.y += dy * push;
          }
        }
      }
    };
    collide.initialize = (ns: any[]) => (nodes = ns);
    fg.d3Force("collision", collide);
  }, []);

  // new nodes (expansion) start next to a neighbour instead of at the origin
  const prevIds = useRef<Set<string>>(new Set());
  useEffect(() => {
    const before = prevIds.current;
    if (before.size) {
      const byId = new Map(data.nodes.map((n) => [n.id, n]));
      for (const n of data.nodes) {
        if (before.has(n.id) || n.x !== undefined) continue;
        const l = data.links.find(
          (k) =>
            (endId(k.source) === n.id && before.has(endId(k.target))) ||
            (endId(k.target) === n.id && before.has(endId(k.source))),
        );
        const nb = l && byId.get(endId(l.source) === n.id ? endId(l.target) : endId(l.source));
        if (nb?.x !== undefined && nb.y !== undefined) {
          const a = Math.random() * Math.PI * 2;
          n.x = nb.x + Math.cos(a) * 50;
          n.y = nb.y + Math.sin(a) * 50;
        }
      }
    }
    prevIds.current = new Set(data.nodes.map((n) => n.id));
  }, [data]);

  const prevData = useRef(data);
  useEffect(() => {
    if (data !== prevData.current && data.nodes.length) {
      prevData.current = data;
      const t = setTimeout(() => fit(400), 450);
      return () => clearTimeout(t);
    }
  }, [data]);

  // centre on the node chosen elsewhere (result list, side panel)
  const lastFocus = useRef<string | null>(null);
  useEffect(() => {
    if (highlightNode && highlightNode !== lastFocus.current) {
      const n = data.nodes.find((x) => x.id === highlightNode);
      if (n?.x !== undefined && n.y !== undefined) {
        graphRef.current?.centerAt(n.x, n.y, 350);
        graphRef.current?.zoom(1.6, 350);
      }
    }
    lastFocus.current = highlightNode ?? null;
  }, [highlightNode, data.nodes]);

  // freeze / resume the layout
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg) return;
    if (frozen) fg.pauseAnimation?.();
    else fg.resumeAnimation?.();
  }, [frozen]);

  const graphSize = filtered.nodes.length;

  // ── painting ─────────────────────────────────────────────────────────────
  const paintNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, k: number) => {
      const n = node as GraphNode;
      const color = typeColor(n.type);
      const s = shape(n.type);
      const dim = neighbours && !neighbours.has(n.id);
      const isFocus = n.id === focusId;
      ctx.globalAlpha = dim ? 0.18 : 1;

      // far away: just a dot
      if (k < 0.45) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 3 / Math.max(k, 0.2) / 2, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.globalAlpha = 1;
        return;
      }

      const url = IMAGE_TYPES.has(n.type) ? peekImage(n.type, n.label) : undefined;
      const img = url ? decode(url, repaint) : null;
      const x = node.x;
      const y = node.y;

      ctx.save();
      ctx.beginPath();
      if (s.r) ctx.arc(x, y, s.r, 0, 2 * Math.PI);
      else ctx.roundRect(x - s.w / 2, y - s.h / 2, s.w, s.h, 2.5);
      ctx.fillStyle = BG;
      ctx.fill();
      ctx.clip();
      const bw = s.r ? s.r * 2 : s.w;
      const bh = s.r ? s.r * 2 : s.h;
      if (img) {
        const ratio = img.width / img.height;
        const whole = !GAME_TYPES.has(n.type) && (ratio > 1.3 || ratio < 0.77); // logos: show them entirely
        if (whole) {
          ctx.fillStyle = "#ece8dd";
          ctx.fillRect(x - bw / 2, y - bh / 2, bw, bh);
          const sc = Math.min((bw * 0.72) / img.width, (bh * 0.72) / img.height);
          ctx.drawImage(img, x - (img.width * sc) / 2, y - (img.height * sc) / 2, img.width * sc, img.height * sc);
        } else {
          // object-fit: cover
          const sc = Math.max(bw / img.width, bh / img.height);
          ctx.drawImage(img, x - (img.width * sc) / 2, y - (img.height * sc) / 2, img.width * sc, img.height * sc);
        }
      } else {
        ctx.fillStyle = `${color}33`;
        ctx.fillRect(x - bw / 2, y - bh / 2, bw, bh);
        if (s.r > 8 || s.w) {
          ctx.fillStyle = color;
          ctx.font = `${Math.round(bh * 0.46)}px "Newsreader", Georgia, serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(n.label.trim().charAt(0).toUpperCase(), x, y + 1);
        } else {
          ctx.fillStyle = color;
          ctx.fillRect(x - bw / 2, y - bh / 2, bw, bh);
        }
      }
      ctx.restore();

      // outline: type colour, brick when selected, ink when hovered
      ctx.beginPath();
      if (s.r) ctx.arc(x, y, s.r, 0, 2 * Math.PI);
      else ctx.roundRect(x - s.w / 2, y - s.h / 2, s.w, s.h, 2.5);
      const picked = selected.has(n.id);
      const second = n.id === secondary;
      ctx.lineWidth = (isFocus || picked || second ? 2.4 : 1.2) / Math.min(k, 2);
      ctx.strokeStyle = picked || n.id === highlightNode ? BRICK : second || n.id === hovered ? INK : color;
      ctx.stroke();

      // label: when zoomed in, or for the node in focus and its neighbours
      const showLabel =
        isFocus || second || selected.has(n.id) || k > (graphSize > 60 ? 1.2 : 0.55) || (neighbours?.has(n.id) && k > 0.5);
      if (showLabel) {
        const fs = Math.max(4.5, Math.min(11 / k, 9));
        ctx.font = `${isFocus ? 600 : 400} ${fs}px ${FONT}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        const text = n.label.length > 22 ? `${n.label.slice(0, 21)}…` : n.label;
        const ty = y + (s.r || s.h / 2) + 3;
        ctx.lineWidth = 3 / k;
        ctx.strokeStyle = BG;
        ctx.strokeText(text, x, ty);
        ctx.fillStyle = INK;
        ctx.fillText(text, x, ty);
      }
      ctx.globalAlpha = 1;
    },
    [neighbours, focusId, highlightNode, hovered, repaint, graphSize, selected, secondary],
  );

  const paintLink = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, k: number) => {
      const a = link.source;
      const b = link.target;
      if (a?.x === undefined || b?.x === undefined) return;
      const on = neighbours && (a.id === focusId || b.id === focusId);
      // the two nodes being compared: every relation between them is labelled, derived ones too
      const pair =
        !!secondary &&
        !!highlightNode &&
        ((a.id === highlightNode && b.id === secondary) || (b.id === highlightNode && a.id === secondary));
      // relations derived by the reasoner (sharesDeveloperWith...) are many: dashed, labelled only for a pair
      const derived = isDerived(link.label);
      ctx.globalAlpha = pair ? 1 : neighbours && !on ? 0.06 : derived && !on ? 0.5 : 1;
      ctx.beginPath();
      if (derived) ctx.setLineDash([4 / k, 3 / k]);
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.lineWidth = (pair ? 2.2 : on ? 1.6 : 0.8) / Math.min(k, 2);
      ctx.strokeStyle = pair || on ? BRICK : "rgba(236,232,221,0.22)";
      ctx.stroke();
      ctx.setLineDash([]);
      if (pair || (on && !derived && k > 0.7)) {
        // fixed 11px on screen, on a dark pill; skipped when it would cover another label
        // (the pair's labels are never skipped: they are moved down instead)
        const fs = 11 / k;
        ctx.font = `${fs}px "IBM Plex Mono", monospace`;
        const w = ctx.measureText(link.label).width + 8 / k;
        const h = fs + 5 / k;
        const mx = (a.x + b.x) / 2;
        let my = (a.y + b.y) / 2;
        const hit = (y: number) =>
          labelBoxes.current.some((o) => mx - w / 2 < o[2] && mx + w / 2 > o[0] && y - h / 2 < o[3] && y + h / 2 > o[1]);
        if (pair) for (let i = 0; i < 6 && hit(my); i++) my += h;
        if (pair || !hit(my)) {
          labelBoxes.current.push([mx - w / 2, my - h / 2, mx + w / 2, my + h / 2]);
          ctx.fillStyle = "rgba(20,19,15,0.95)";
          ctx.fillRect(mx - w / 2, my - h / 2, w, h);
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillStyle = pair ? INK : "#d9d4c6";
          ctx.fillText(link.label, mx, my + 0.5 / k);
        }
      }
      ctx.globalAlpha = 1;
    },
    [neighbours, focusId, secondary, highlightNode],
  );

  // ── interaction ──────────────────────────────────────────────────────────
  const lastClick = useRef({ id: "", t: 0 });
  const handleClick = useCallback(
    (node: any, ev?: MouseEvent) => {
      if (longPressFired.current) {
        longPressFired.current = false;
        return;
      }
      if (ev && (ev.shiftKey || ev.ctrlKey || ev.metaKey)) {
        // multi-selection: add or remove, without moving the view or opening the panel
        setSelected((p) => {
          const n = new Set(p);
          if (n.has(node.id)) n.delete(node.id);
          else n.add(node.id);
          return n;
        });
        return;
      }
      setSelected(new Set());
      const now = Date.now();
      const double = lastClick.current.id === node.id && now - lastClick.current.t < 350;
      lastClick.current = { id: node.id, t: now };
      const linkedToFocus =
        !!highlightNode &&
        node.id !== highlightNode &&
        filtered.links.some((l) => {
          const a = endId(l.source);
          const b = endId(l.target);
          return (a === highlightNode && b === node.id) || (b === highlightNode && a === node.id);
        });
      if (linkedToFocus && !double) {
        setSecondary(node.id); // see how it relates to the focus, without moving the focus
        return;
      }
      setSecondary(null);
      onNodeClick(node.id);
      graphRef.current?.centerAt(node.x, node.y, 300);
      graphRef.current?.zoom(1.6, 300);
      // double click on the node already in focus: relations menu (to expand it)
      if (double && node.id === highlightNode && onNodeRightClick && graphRef.current) {
        const p = graphRef.current.graph2ScreenCoords(node.x, node.y);
        const r = containerRef.current!.getBoundingClientRect();
        onNodeRightClick(node as GraphNode, r.left + p.x + 24, r.top + p.y);
      }
    },
    [onNodeClick, onNodeRightClick, highlightNode, filtered.links],
  );

  const handleRightClick = useCallback(
    (node: any, e: MouseEvent) => {
      e.preventDefault();
      onNodeRightClick?.(node as GraphNode, e.clientX, e.clientY);
    },
    [onNodeRightClick],
  );

  // long press = context menu on touch screens (capture phase, before d3-drag)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let sx = 0;
    let sy = 0;
    const down = (e: PointerEvent) => {
      if (e.pointerType !== "touch" || !graphRef.current) return;
      sx = e.clientX;
      sy = e.clientY;
      const r = el.getBoundingClientRect();
      const g = graphRef.current.screen2GraphCoords(sx - r.left, sy - r.top);
      let best: any = null;
      let bd = Infinity;
      for (const n of filtered.nodes) {
        const d = Math.hypot((n.x ?? 0) - g.x, (n.y ?? 0) - g.y);
        if (d < hitRadius(n.type) * 1.6 && d < bd) {
          best = n;
          bd = d;
        }
      }
      if (!best) return;
      longPressFired.current = false;
      timer = setTimeout(() => {
        longPressFired.current = true;
        onNodeRightClick?.(best as GraphNode, sx, sy);
      }, 500);
    };
    const move = (e: PointerEvent) => {
      if (timer && Math.hypot(e.clientX - sx, e.clientY - sy) > 20) {
        clearTimeout(timer);
        timer = null;
      }
    };
    const up = () => {
      if (timer) clearTimeout(timer);
      timer = null;
    };
    const o = { capture: true } as const;
    el.addEventListener("pointerdown", down, o);
    el.addEventListener("pointermove", move, o);
    el.addEventListener("pointerup", up, o);
    el.addEventListener("pointercancel", up, o);
    return () => {
      el.removeEventListener("pointerdown", down, o);
      el.removeEventListener("pointermove", move, o);
      el.removeEventListener("pointerup", up, o);
      el.removeEventListener("pointercancel", up, o);
      if (timer) clearTimeout(timer);
    };
  }, [filtered.nodes, onNodeRightClick]);

  const toggleType = (t: string) =>
    setHiddenTypes((p) => {
      const n = new Set(p);
      if (n.has(t)) n.delete(t);
      else n.add(t);
      return n;
    });

  const matches = useMemo(() => {
    const q = find.trim().toLowerCase();
    if (q.length < 2) return [];
    return data.nodes.filter((n) => n.label.toLowerCase().includes(q)).slice(0, 6);
  }, [find, data.nodes]);

  const releasePins = () => {
    for (const n of data.nodes as any[]) {
      n.fx = undefined;
      n.fy = undefined;
    }
    graphRef.current?.d3ReheatSimulation?.();
  };

  const empty = filtered.nodes.length === 0;
  const hiddenByType = hiddenTypes.size > 0;
  const showAll = () => {
    setHiddenTypes(new Set());
    onRestoreHidden?.();
  };
  const hiddenTotal = hiddenCount + data.nodes.filter((n) => hiddenTypes.has(n.type)).length;

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden bg-paper">
      {empty && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          {loading ? (
            <div className="flex gap-3" aria-label="Carico il grafo">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-3 w-3 animate-shimmer rounded-full bg-mute"
                  style={{ animationDelay: `${i * 0.25}s` }}
                />
              ))}
            </div>
          ) : hiddenCount > 0 || hiddenByType ? (
            <p className="font-serif text-2xl text-mute">Tutti i nodi sono nascosti</p>
          ) : (
            <p className="font-serif text-2xl text-mute">Il grafo apparirà qui</p>
          )}
        </div>
      )}

      <ForceGraph2D
        ref={graphRef}
        graphData={filtered}
        width={size.width}
        height={size.height}
        backgroundColor={BG}
        nodeCanvasObject={paintNode}
        nodeCanvasObjectMode={() => "replace"}
        linkCanvasObject={paintLink}
        linkCanvasObjectMode={() => "replace"}
        onNodeClick={handleClick}
        onBackgroundClick={() => setSelected(new Set())}
        onRenderFramePre={() => {
          labelBoxes.current = [];
        }}
        onNodeRightClick={handleRightClick}
        onNodeHover={(node: any) => setHovered(node?.id ?? null)}
        onNodeDragEnd={(node: any) => {
          node.fx = node.x;
          node.fy = node.y;
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const r = hitRadius(node.type) + 3;
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={0.9}
        d3VelocityDecay={0.4}
        d3AlphaDecay={0.03}
        warmupTicks={60}
        cooldownTicks={140}
      />

      {/* legend with counts: click to hide a type */}
      {typeCounts.length > 0 && (
        <ul className="absolute bottom-3 left-3 z-20 max-h-[60%] space-y-0.5 overflow-y-auto bg-paper/85 py-1 pr-3">
          {typeCounts.map(([t, c]) => (
            <li key={t}>
              <button
                onClick={() => toggleType(t)}
                className={`flex w-full items-center gap-2 py-0.5 text-left text-[12px] transition-opacity ${hiddenTypes.has(t) ? "opacity-40" : ""}`}
                aria-pressed={!hiddenTypes.has(t)}
              >
                <span className="h-2 w-2 rounded-full" style={{ background: typeColor(t) }} />
                <span>{typeLabel(t)}</span>
                <span className="ml-auto pl-3 font-mono text-[11px] text-mute">{c}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* act on the selection (shift+click) or on the node in focus */}
      {(selected.size > 0 || highlightNode) && !empty && (onKeepOnly || onHideMany) && (
        <div className="absolute left-3 top-3 z-20 flex w-max max-w-[calc(100%-260px)] flex-wrap items-center gap-1 whitespace-nowrap rounded-sm border border-rule bg-panel px-2 py-1.5 text-sm shadow-[0_12px_32px_-8px_rgba(0,0,0,0.6)] animate-fade-in">
          <span className="px-2 text-mute">
            {selected.size > 0 ? `${selected.size} selezionat${selected.size === 1 ? "o" : "i"}` : "1 nodo"}
          </span>
          {(() => {
            const ids = selected.size > 0 ? [...selected] : highlightNode ? [highlightNode] : [];
            const withNeighbours = () => {
              const keep = new Set(ids);
              for (const l of filtered.links) {
                if (isDerived(l.label)) continue; // derived links tie every game together
                const a = endId(l.source);
                const b = endId(l.target);
                if (ids.includes(a)) keep.add(b);
                if (ids.includes(b)) keep.add(a);
              }
              return [...keep];
            };
            const done = () => setSelected(new Set());
            return (
              <>
                <button
                  className="btn !px-2.5 !py-1"
                  title="Tieni solo questi nodi e nascondi tutti gli altri"
                  onClick={() => {
                    onKeepOnly?.(ids);
                    done();
                  }}
                >
                  <Focus className="h-3.5 w-3.5" /> Isola
                </button>
                <button
                  className="btn !px-2.5 !py-1"
                  title="Tieni questi nodi e i loro vicini diretti"
                  onClick={() => {
                    onKeepOnly?.(withNeighbours());
                    done();
                  }}
                >
                  <Network className="h-3.5 w-3.5" /> Isola con vicini
                </button>
                <button
                  className="btn !px-2.5 !py-1"
                  title="Nascondi questi nodi (si possono rimostrare)"
                  onClick={() => {
                    onHideMany?.(ids);
                    done();
                  }}
                >
                  <EyeOff className="h-3.5 w-3.5" /> Nascondi
                </button>
                <button
                  className="btn !px-2.5 !py-1"
                  title="Elimina questi nodi dalla scena"
                  onClick={() => {
                    onDeleteMany?.(ids);
                    done();
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" /> Elimina
                </button>
                {selected.size > 0 && (
                  <button className="btn !px-2 !py-1" onClick={done} aria-label="Deseleziona">
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </>
            );
          })()}
          {selected.size === 0 && (
            <span className="hidden pl-2 text-[11px] text-mute lg:inline">Maiusc + clic per sceglierne altri</span>
          )}
        </div>
      )}

      {/* what is hidden: bring it back, delete it for good, or just close this notice */}
      {(hiddenCount > 0 || hiddenByType) && !alertOff && (
        <div className="absolute bottom-14 left-1/2 z-20 flex -translate-x-1/2 items-center gap-3 rounded-sm border border-rule bg-panel py-2 pl-3.5 pr-2 text-sm shadow-[0_12px_32px_-8px_rgba(0,0,0,0.6)] animate-fade-in">
          <span className="text-mute">
            {hiddenCount > 0 && `${hiddenCount} ${hiddenCount === 1 ? "nodo nascosto" : "nodi nascosti"}`}
            {hiddenCount > 0 && hiddenByType && " · "}
            {hiddenByType && `${hiddenTypes.size} ${hiddenTypes.size === 1 ? "tipo nascosto" : "tipi nascosti"}`}
          </span>
          <button onClick={showAll} className="font-medium text-brick hover:underline">
            Mostra tutto
          </button>
          <button
            onClick={() => {
              onDeleteHidden?.(data.nodes.filter((n) => hiddenTypes.has(n.type)).map((n) => n.id));
              setHiddenTypes(new Set());
            }}
            className="text-mute hover:text-ink hover:underline"
            title="Elimina definitivamente i nodi nascosti dalla scena"
          >
            Elimina
          </button>
          <button
            onClick={() => setAlertOff(true)}
            className="rounded-sm p-1 text-mute hover:bg-raised hover:text-ink"
            aria-label="Chiudi l'avviso"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* find a node */}
      {data.nodes.length > 0 && (
        <div className="absolute right-3 top-3 w-56">
          <div className="flex items-center gap-2 border-b border-rule bg-paper/85 px-1 py-1.5">
            <Search className="h-3.5 w-3.5 text-mute" />
            <input
              value={find}
              onChange={(e) => setFind(e.target.value)}
              placeholder="Trova nel grafo"
              className="w-full bg-transparent text-sm placeholder:text-mute focus:outline-none"
              aria-label="Trova un nodo nel grafo"
            />
          </div>
          {matches.length > 0 && (
            <ul className="border border-t-0 border-rule bg-panel">
              {matches.map((m) => (
                <li key={m.id}>
                  <button
                    className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-sm hover:bg-raised"
                    onClick={() => {
                      onNodeClick(m.id);
                      setFind("");
                    }}
                  >
                    <span className="h-2 w-2 rounded-full" style={{ background: typeColor(m.type) }} />
                    <span className="truncate">{m.label}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="absolute bottom-3 right-3 flex items-center gap-1">
        <span className="mr-2 font-mono text-[11px] text-mute">
          {filtered.nodes.length} nodi · {filtered.links.length} relazioni
        </span>
        {(hiddenCount > 0 || hiddenByType) && (
          <button onClick={showAll} className="btn !px-2.5 !py-1.5" title="Mostra di nuovo i nodi nascosti">
            <Eye className="h-3.5 w-3.5" /> Nascosti ({hiddenTotal})
          </button>
        )}
        {onClear && (data.nodes.length > 0 || hiddenCount > 0) && (
          <button onClick={onClear} className="btn !px-2.5 !py-1.5" title="Svuota il grafo e i risultati">
            <Eraser className="h-3.5 w-3.5" /> Svuota
          </button>
        )}
        <button
          onClick={() => setShowDerived((v) => !v)}
          className={`btn !px-2.5 !py-1.5 ${showDerived ? "" : "opacity-60"}`}
          title="Relazioni derivate dal reasoner (stesso sviluppatore, publisher o serie)"
          aria-pressed={showDerived}
        >
          <Link2 className="h-3.5 w-3.5" /> Derivate
        </button>
        <button
          onClick={() => fit(400)}
          className="btn !px-2 !py-1.5"
          title="Adatta alla vista"
          aria-label="Adatta alla vista"
        >
          <Crosshair className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => {
            if (frozen) releasePins();
            setFrozen((f) => !f);
          }}
          className="btn !px-2 !py-1.5"
          title={frozen ? "Riavvia il layout" : "Blocca il layout"}
          aria-label={frozen ? "Riavvia il layout" : "Blocca il layout"}
        >
          {frozen ? <Unlock className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  );
}
