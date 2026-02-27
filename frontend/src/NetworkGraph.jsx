import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function NetworkGraph({ data }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!data || !data.nodes || !data.links) return;

    // 1. Setup Dimensions & SVG
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;
    
    // Clear previous graph to prevent duplicates on React hot-reload
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .style("cursor", "grab");

    // 2. Add Zoom & Pan
    const g = svg.append("g");
    
    const zoom = d3.zoom()
      .scaleExtent([0.5, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
      
    svg.call(zoom);
    // Center the graph initially
    svg.call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8));

    // 3. Define Arrowheads for directional transactions
    svg.append("defs").selectAll("marker")
      .data(["normal", "risk"])
      .enter().append("marker")
      .attr("id", d => `arrow-${d}`)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25) // Distance from node center
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("fill", d => d === 'risk' ? '#f43f5e' : '#cbd5e1')
      .attr("d", "M0,-5L10,0L0,5");

    // 4. Setup Physics Simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-400)) // Repulsion
      .force("collide", d3.forceCollide().radius(30)) // Prevent overlap
      .force("x", d3.forceX())
      .force("y", d3.forceY());

    // 5. Draw Links (Edges)
    const link = g.append("g")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke", d => d.isRisk ? "#f43f5e" : "#cbd5e1")
      .attr("stroke-width", d => d.value ? Math.sqrt(d.value) : 2)
      .attr("stroke-dasharray", d => d.isDashed ? "5,5" : "none")
      .attr("marker-end", d => d.isRisk ? "url(#arrow-risk)" : "url(#arrow-normal)");

    // 6. Draw Nodes (Vertices)
    const node = g.append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .call(drag(simulation));

    // Node Circles
    node.append("circle")
      .attr("r", d => d.isCentral ? 20 : 16)
      .attr("fill", "#ffffff")
      .attr("stroke", d => {
        if (d.riskLevel === 'critical') return '#f43f5e'; // Rose
        if (d.riskLevel === 'warning') return '#fb923c';  // Orange
        return '#cbd5e1'; // Slate
      })
      .attr("stroke-width", d => d.isCentral ? 3 : 2)
      .attr("class", "shadow-lg cursor-pointer transition-all hover:stroke-indigo-600");

    // Node Icons (Using basic text/emojis for D3 SVG compatibility)
    node.append("text")
      .text(d => d.icon || "🏢")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "central")
      .attr("font-size", "14px");

    // Node Labels
    node.append("text")
      .text(d => d.label)
      .attr("x", 0)
      .attr("y", d => d.isCentral ? 30 : 25)
      .attr("text-anchor", "middle")
      .attr("fill", "#475569")
      .attr("font-size", "10px")
      .attr("font-weight", "600")
      .attr("font-family", "Inter, sans-serif")
      .clone(true).lower() // White outline for readability
      .attr("fill", "none")
      .attr("stroke", "white")
      .attr("stroke-width", 3);

    // 7. Simulation Tick Updates
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // 8. Drag Behavior setup
    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
        d3.select(svgRef.current).style("cursor", "grabbing");
      }
      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
        d3.select(svgRef.current).style("cursor", "grab");
      }
      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }

    // Cleanup on unmount
    return () => simulation.stop();
  }, [data]);

  return (
    <div ref={containerRef} className="w-full h-full absolute inset-0">
      <svg ref={svgRef} className="w-full h-full focus:outline-none"></svg>
    </div>
  );
}