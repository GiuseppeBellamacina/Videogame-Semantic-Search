import { useRef, useCallback, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { Crosshair } from "lucide-react";
import type { GraphData, GraphNode } from "@/types";
import { searchGameImage } from "@/lib/api";

interface KnowledgeGraphProps {
  data: GraphData;
  onNodeClick: (nodeId: string) => void;
  highlightNode?: string | null;
  onNodeRightClick?: (node: GraphNode, x: number, y: number) => void;
}

const NODE_COLORS: Record<string, string> = {
  VideoGame: "#6366f1",
  Developer: "#f59e0b",
  Publisher: "#10b981",
  Genre: "#ef4444",
  Platform: "#3b82f6",
  Character: "#ec4899",
  Franchise: "#8b5cf6",
  Award: "#f97316",
  GameEngine: "#14b8a6",
  Unknown: "#6b7280",
};

// Image cache to avoid reloading (imageUrl → HTMLImageElement)
const imageCache = new Map<string, HTMLImageElement | null>();

// label → imageUrl (or null if tried+failed) — persists across renders/searches
const labelImageUrlCache = new Map<string, string | null>();

// Track in-flight fetch requests to avoid duplicates
const fetchingLabels = new Set<string>();

function loadImage(
  url: string,
  onLoaded?: () => void,
): HTMLImageElement | null {
  if (imageCache.has(url)) return imageCache.get(url) ?? null;
  imageCache.set(url, null);
  const img = new Image();
  img.onload = () => {
    imageCache.set(url, img);
    onLoaded?.();
  };
  img.onerror = () => {
    imageCache.set(url, null);
  };
  img.src = url;
  return null;
}

export function KnowledgeGraph({
  data,
  onNodeClick,
  highlightNode,
  onNodeRightClick,
}: KnowledgeGraphProps) {
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  // Throttle zoom-triggered fetches: don't re-fetch more than once per 800ms
  const lastZoomFetchRef = useRef<number>(0);

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height });
      }
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Apply collision force to prevent node overlap
  useEffect(() => {
    if (!graphRef.current) return;
    // Strong many-body repulsion for wide spreading
    graphRef.current.d3Force("charge")?.strength(-600);
    // Longer link distance to spread connected nodes
    graphRef.current.d3Force("link")?.distance(160);
    graphRef.current.d3Force("collision", {
      initialize(nodes: any[]) {
        this._nodes = nodes;
      },
      _nodes: [] as any[],
      force(alpha: number) {
        const nodes = this._nodes;
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const a = nodes[i],
              b = nodes[j];
            const dx = (b.x ?? 0) - (a.x ?? 0);
            const dy = (b.y ?? 0) - (a.y ?? 0);
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            // Use half-diagonal of the bounding rect for VideoGame nodes
            const halfA =
              a.type === "VideoGame"
                ? Math.sqrt((a.size * 2.8) ** 2 + (a.size * 4.0) ** 2) / 2
                : a.size || 8;
            const halfB =
              b.type === "VideoGame"
                ? Math.sqrt((b.size * 2.8) ** 2 + (b.size * 4.0) ** 2) / 2
                : b.size || 8;
            const minDist = halfA + halfB + 20;
            if (dist < minDist) {
              const push = ((minDist - dist) / dist) * alpha * 0.9;
              const fx = dx * push,
                fy = dy * push;
              if (a.x !== undefined) {
                a.x -= fx;
                a.y -= fy;
              }
              if (b.x !== undefined) {
                b.x += fx;
                b.y += fy;
              }
            }
          }
        }
      },
    });
  }, []);

  // Zoom to fit when data changes
  useEffect(() => {
    if (graphRef.current && data.nodes.length > 0) {
      setTimeout(() => {
        graphRef.current?.zoomToFit(400, 60);
      }, 500);
    }
  }, [data]);

  // Fetch fallback images only for clicked/zoomed VideoGame nodes
  // forceApi=true → hit the API if not cached; false → only apply what is already cached
  const fetchImageForNode = useCallback(
    async (node: GraphNode, forceApi = false) => {
      if (node.type !== "VideoGame" || node.imageUrl) return;

      // Always check local cache first — no API call needed
      if (labelImageUrlCache.has(node.label)) {
        const cached = labelImageUrlCache.get(node.label);
        if (cached) {
          node.imageUrl = cached;
          loadImage(cached, () => graphRef.current?.refresh());
        }
        return;
      }

      // Cache miss — only call the API when explicitly allowed
      if (!forceApi) return;
      if (fetchingLabels.has(node.label)) return;

      fetchingLabels.add(node.label);
      try {
        const result = await searchGameImage(node.label);
        if (result.imageUrl) {
          labelImageUrlCache.set(node.label, result.imageUrl);
          node.imageUrl = result.imageUrl;
          loadImage(result.imageUrl, () => graphRef.current?.refresh());
        }
        // no imageUrl → don't cache, allow retry later
      } catch {
        // do not cache errors — allow retry next time
      } finally {
        fetchingLabels.delete(node.label);
      }
    },
    [],
  );

  // For every VideoGame node: check cache immediately; call API only if autoFetchImage
  useEffect(() => {
    const gameNodes = data.nodes.filter((n) => n.type === "VideoGame");
    for (const node of gameNodes) {
      fetchImageForNode(node, node.autoFetchImage === true);
    }
  }, [data, fetchImageForNode]);

  const handleNodeRightClick = useCallback(
    (node: any, event: MouseEvent) => {
      event.preventDefault();
      if (onNodeRightClick) {
        onNodeRightClick(node as GraphNode, event.clientX, event.clientY);
      }
    },
    [onNodeRightClick],
  );

  const handleNodeClick = useCallback(
    (node: any) => {
      onNodeClick(node.id);
      // Always force API on click
      fetchImageForNode(node as GraphNode, true);
      // Center on clicked node
      if (graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 300);
        graphRef.current.zoom(2.5, 300);
      }
    },
    [onNodeClick, fetchImageForNode],
  );

  // On zoom, fetch images for visible game nodes when zoomed in enough
  const handleZoom = useCallback(
    ({ k }: { k: number }) => {
      if (k <= 1.8) return;
      const now = Date.now();
      if (now - lastZoomFetchRef.current < 800) return;
      lastZoomFetchRef.current = now;

      const pending = data.nodes.filter(
        (n) =>
          n.type === "VideoGame" &&
          !n.imageUrl &&
          !labelImageUrlCache.has(n.label) &&
          !fetchingLabels.has(n.label),
      );
      // Force API for up to 5 nodes per zoom burst
      for (const node of pending.slice(0, 5)) {
        fetchImageForNode(node, true);
      }
    },
    [data.nodes, fetchImageForNode],
  );

  const paintNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.label || "";
      const size = node.size || 8;
      const color = node.color || NODE_COLORS[node.type] || NODE_COLORS.Unknown;
      const isHighlighted =
        node.id === highlightNode || node.id === hoveredNode;
      const fontSize = Math.max(10 / globalScale, 2);
      const isGame = node.type === "VideoGame";

      if (isGame) {
        const w = size * 2.8;
        const h = size * 4.0;
        const r = size * 0.5;
        const rx = node.x - w / 2;
        const ry = node.y - h / 2;

        // Glow
        if (isHighlighted) {
          ctx.beginPath();
          ctx.roundRect(rx - 4, ry - 4, w + 8, h + 8, r + 2);
          ctx.fillStyle = `${color}40`;
          ctx.fill();
        }

        // Try to draw image
        let imageDrawn = false;
        if (node.imageUrl) {
          const img = loadImage(node.imageUrl);
          if (img && img.complete && img.naturalWidth > 0) {
            ctx.save();
            ctx.beginPath();
            ctx.roundRect(rx, ry, w, h, r);
            ctx.clip();
            ctx.drawImage(img, rx, ry, w, h);
            ctx.restore();
            ctx.beginPath();
            ctx.roundRect(rx, ry, w, h, r);
            ctx.strokeStyle = isHighlighted ? "#ffffff" : color;
            ctx.lineWidth = isHighlighted ? 2.5 : 1.5;
            ctx.stroke();
            imageDrawn = true;
          }
        }

        if (!imageDrawn) {
          // Solid rect with label centered inside
          ctx.beginPath();
          ctx.roundRect(rx, ry, w, h, r);
          ctx.fillStyle = isHighlighted ? color : `${color}cc`;
          ctx.fill();
          ctx.strokeStyle = isHighlighted ? "#ffffff" : color;
          ctx.lineWidth = isHighlighted ? 2 : 0.5;
          ctx.stroke();

          ctx.font = `${isHighlighted ? "bold " : ""}${fontSize}px Inter, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillStyle = isHighlighted ? "#ffffff" : "#e5e7eb";
          const maxLen = 18;
          const displayLabel =
            label.length > maxLen ? label.slice(0, maxLen) + "…" : label;
          ctx.fillText(displayLabel, node.x, node.y);
          return;
        }

        // Label below image rect
        if (globalScale > 0.7 || isHighlighted) {
          ctx.font = `${isHighlighted ? "bold " : ""}${fontSize}px Inter, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = isHighlighted ? "#ffffff" : "#e5e7eb";
          const maxLen = 20;
          const displayLabel =
            label.length > maxLen ? label.slice(0, maxLen) + "…" : label;
          ctx.fillText(displayLabel, node.x, ry + h + 2);
        }
        return;
      }

      // ── Circular nodes for all other types ───────────────────────────────

      // Draw glow for highlighted nodes
      if (isHighlighted) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}40`;
        ctx.fill();
      }

      // Draw node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = isHighlighted ? color : `${color}cc`;
      ctx.fill();
      ctx.strokeStyle = isHighlighted ? "#ffffff" : `${color}`;
      ctx.lineWidth = isHighlighted ? 2 : 0.5;
      ctx.stroke();

      // Draw label
      if (globalScale > 0.7 || isHighlighted) {
        ctx.font = `${isHighlighted ? "bold " : ""}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = isHighlighted ? "#ffffff" : "#e5e7eb";
        const maxLen = 20;
        const displayLabel =
          label.length > maxLen ? label.slice(0, maxLen) + "…" : label;
        ctx.fillText(displayLabel, node.x, node.y + size + 2);
      }
    },
    [highlightNode, hoveredNode],
  );

  const paintLink = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const start = link.source;
      const end = link.target;
      if (
        !start ||
        !end ||
        typeof start === "string" ||
        typeof end === "string"
      )
        return;

      // Draw link line
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.strokeStyle = "#374151";
      ctx.lineWidth = 0.8;
      ctx.stroke();

      // Draw link label on hover
      if (
        globalScale > 1.5 &&
        (start.id === hoveredNode || end.id === hoveredNode)
      ) {
        const midX = (start.x + end.x) / 2;
        const midY = (start.y + end.y) / 2;
        const fontSize = Math.max(8 / globalScale, 2);
        ctx.font = `${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#9ca3af";
        ctx.fillText(link.label || "", midX, midY);
      }
    },
    [hoveredNode],
  );

  if (!data.nodes.length) {
    return (
      <div
        ref={containerRef}
        className="h-full w-full relative overflow-hidden flex items-center justify-center text-gray-600"
      >
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
              />
            </svg>
          </div>
          <p className="text-sm">
            Il grafo di conoscenza apparirà qui dopo una ricerca
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-full w-full relative overflow-hidden">
      {/* Legend */}
      <div className="absolute top-3 left-3 z-10 bg-gray-900/90 backdrop-blur-sm border border-gray-700 rounded-lg p-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {Object.entries(NODE_COLORS)
            .filter(([k]) => k !== "Unknown")
            .map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5">
                {type === "VideoGame" ? (
                  <div
                    className="w-2 h-3.5 rounded-sm flex-shrink-0"
                    style={{ backgroundColor: color }}
                  />
                ) : (
                  <div
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: color }}
                  />
                )}
                <span className="text-[10px] text-gray-400">{type}</span>
              </div>
            ))}
        </div>
      </div>

      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="#030712"
        nodeCanvasObject={paintNode}
        linkCanvasObject={paintLink}
        onNodeClick={handleNodeClick}
        onNodeRightClick={handleNodeRightClick}
        onNodeHover={(node: any) => setHoveredNode(node?.id || null)}
        onZoom={handleZoom}
        nodePointerAreaPaint={(
          node: any,
          color: string,
          ctx: CanvasRenderingContext2D,
        ) => {
          const size = node.size || 8;
          if (node.type === "VideoGame") {
            const w = size * 2.8 + 8;
            const h = size * 4.0 + 8;
            ctx.beginPath();
            ctx.roundRect(node.x - w / 2, node.y - h / 2, w, h, size * 0.5);
            ctx.fillStyle = color;
            ctx.fill();
          } else {
            ctx.beginPath();
            ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }
        }}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={0.85}
        nodeVal={(node: any) =>
          // Highlighted node gets a much higher val so ForceGraph renders it last (on top)
          node.id === highlightNode || node.id === hoveredNode
            ? (node.size || 8) * 100
            : node.size || 8
        }
        d3VelocityDecay={0.2}
        d3AlphaDecay={0.01}
        warmupTicks={100}
        cooldownTicks={200}
      />

      {/* Bottom-right controls */}
      <div className="absolute bottom-3 right-3 flex items-center gap-2">
        <button
          onClick={() => graphRef.current?.zoomToFit(400, 60)}
          title="Recentra grafo"
          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-900/90 backdrop-blur-sm border border-gray-700 rounded-lg text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
        >
          <Crosshair className="w-3.5 h-3.5" />
          <span className="text-xs">Recentra</span>
        </button>
        <div className="bg-gray-900/90 backdrop-blur-sm border border-gray-700 rounded-lg px-3 py-1.5">
          <span className="text-xs text-gray-400">
            {data.nodes.length} nodi · {data.links.length} relazioni
          </span>
        </div>
      </div>
    </div>
  );
}
