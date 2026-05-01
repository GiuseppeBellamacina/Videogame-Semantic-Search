import { useRef, useCallback, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphData, GraphNode } from "@/types";
import { searchGameImage } from "@/lib/api";

interface KnowledgeGraphProps {
  data: GraphData;
  onNodeClick: (nodeId: string) => void;
  highlightNode?: string | null;
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

// Image cache to avoid reloading
const imageCache = new Map<string, HTMLImageElement | null>();

// Track failed URLs to avoid infinite retries
const failedUrls = new Set<string>();

// Track in-flight fetch requests to avoid duplicates
const fetchingLabels = new Set<string>();

function loadImage(
  url: string,
  onLoaded?: () => void,
): HTMLImageElement | null {
  if (imageCache.has(url)) return imageCache.get(url)!;
  if (failedUrls.has(url)) return null;
  // Mark as loading (null means loading/failed)
  imageCache.set(url, null);
  const img = new Image();
  img.onload = () => {
    imageCache.set(url, img);
    onLoaded?.();
  };
  img.onerror = () => {
    failedUrls.add(url);
    imageCache.set(url, null);
  };
  img.src = url;
  return null;
}

export function KnowledgeGraph({
  data,
  onNodeClick,
  highlightNode,
}: KnowledgeGraphProps) {
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
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
  const fetchImageForNode = useCallback(async (node: GraphNode) => {
    if (
      node.type === "VideoGame" &&
      !node.imageUrl &&
      !fetchingLabels.has(node.label) &&
      !failedUrls.has(node.label)
    ) {
      fetchingLabels.add(node.label);
      try {
        const result = await searchGameImage(node.label);
        if (result.imageUrl) {
          node.imageUrl = result.imageUrl;
          loadImage(result.imageUrl, () => graphRef.current?.refresh());
        } else {
          failedUrls.add(node.label);
        }
      } catch {
        failedUrls.add(node.label);
      } finally {
        fetchingLabels.delete(node.label);
      }
    }
  }, []);

  // Eagerly fetch images for all VideoGame nodes when graph is small (≤25 nodes total)
  useEffect(() => {
    if (data.nodes.length > 25) return;
    const gameNodes = data.nodes.filter((n) => n.type === "VideoGame");
    for (const node of gameNodes) {
      fetchImageForNode(node);
    }
  }, [data, fetchImageForNode]);

  const handleNodeClick = useCallback(
    (node: any) => {
      onNodeClick(node.id);
      // Fetch image on click
      fetchImageForNode(node as GraphNode);
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
      if (k > 1.8) {
        const gameNodes = data.nodes.filter(
          (n) =>
            n.type === "VideoGame" &&
            !n.imageUrl &&
            !fetchingLabels.has(n.label) &&
            !failedUrls.has(n.label),
        );
        // Fetch up to 5 at a time on zoom
        for (const node of gameNodes.slice(0, 5)) {
          fetchImageForNode(node);
        }
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

      // Draw glow for highlighted nodes
      if (isHighlighted) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}40`;
        ctx.fill();
      }

      // Try to draw image for VideoGame nodes
      let imageDrawn = false;
      if (node.type === "VideoGame" && node.imageUrl) {
        const img = loadImage(node.imageUrl);
        if (img && img.complete && img.naturalWidth > 0) {
          const imgSize = size * 2;
          ctx.save();
          // Clip to circle
          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
          ctx.clip();
          ctx.drawImage(
            img,
            node.x - imgSize / 2,
            node.y - imgSize / 2,
            imgSize,
            imgSize,
          );
          ctx.restore();
          // Draw border around image
          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
          ctx.strokeStyle = isHighlighted ? "#ffffff" : color;
          ctx.lineWidth = isHighlighted ? 2.5 : 1.5;
          ctx.stroke();
          imageDrawn = true;
        }
      }

      if (!imageDrawn) {
        // Draw node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
        ctx.fillStyle = isHighlighted ? color : `${color}cc`;
        ctx.fill();

        // Draw border
        ctx.strokeStyle = isHighlighted ? "#ffffff" : `${color}`;
        ctx.lineWidth = isHighlighted ? 2 : 0.5;
        ctx.stroke();
      }

      // Draw label
      if (globalScale > 0.7 || isHighlighted) {
        ctx.font = `${isHighlighted ? "bold " : ""}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = isHighlighted ? "#ffffff" : "#e5e7eb";

        // Truncate label if too long
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
      <div className="h-full flex items-center justify-center text-gray-600">
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
    <div ref={containerRef} className="h-full w-full relative">
      {/* Legend */}
      <div className="absolute top-3 left-3 z-10 bg-gray-900/90 backdrop-blur-sm border border-gray-700 rounded-lg p-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {Object.entries(NODE_COLORS)
            .filter(([k]) => k !== "Unknown")
            .map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
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
        onNodeHover={(node: any) => setHoveredNode(node?.id || null)}
        onZoom={handleZoom}
        nodePointerAreaPaint={(
          node: any,
          color: string,
          ctx: CanvasRenderingContext2D,
        ) => {
          ctx.beginPath();
          ctx.arc(node.x, node.y, (node.size || 8) + 4, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={0.85}
        d3VelocityDecay={0.3}
        d3AlphaDecay={0.02}
        warmupTicks={50}
        cooldownTicks={100}
      />

      {/* Node count badge */}
      <div className="absolute bottom-3 right-3 bg-gray-900/90 backdrop-blur-sm border border-gray-700 rounded-lg px-3 py-1.5">
        <span className="text-xs text-gray-400">
          {data.nodes.length} nodi · {data.links.length} relazioni
        </span>
      </div>
    </div>
  );
}
