import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function NetworkGraph({ data }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!data || !data.nodes || !data.links) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;
    
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .style("cursor", "grab");

    // 1. Flowing Animation for Fraud Links
    svg.append("style").text(`
      @keyframes flow {
        from { stroke-dashoffset: 24; }
        to { stroke-dashoffset: 0; }
      }
      .flowing-line {
        stroke-dasharray: 12 6;
        animation: flow 0.6s linear infinite;
      }
    `);

    // 2. Build Lookup Dictionaries for 1-hop trading
    let linkedByIndex = {};
    data.links.forEach(d => {
      const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
      const targetId = typeof d.target === 'object' ? d.target.id : d.target;
      linkedByIndex[`${sourceId},${targetId}`] = true;
    });

    function isConnected(a, b) {
      return linkedByIndex[`${a.id},${b.id}`] || linkedByIndex[`${b.id},${a.id}`] || a.id === b.id;
    }

    // 3. Pre-calculate Fraud Ecosystems (To isolate specific loops)
    const riskAdj = {};
    data.links.forEach(l => {
      if (l.isRisk) {
        const s = typeof l.source === 'object' ? l.source.id : l.source;
        const t = typeof l.target === 'object' ? l.target.id : l.target;
        if (!riskAdj[s]) riskAdj[s] = [];
        if (!riskAdj[t]) riskAdj[t] = [];
        riskAdj[s].push(t);
        riskAdj[t].push(s); // Undirected so we find the whole connected ring
      }
    });

    const g = svg.append("g");
    const zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => g.attr("transform", event.transform));
      
    svg.call(zoom);
    svg.on("dblclick.zoom", null); 
    svg.on("click", resetHighlight); 
    svg.call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8));

    // 4. 🔥 UPGRADED ARROWHEADS (Bigger, sharper, custom sizes)
    svg.append("defs").selectAll("marker")
      .data(["normal", "risk"])
      .enter().append("marker")
      .attr("id", d => `arrow-${d}`)
      // userSpaceOnUse allows us to set absolute sizes ignoring stroke width
      .attr("markerUnits", "userSpaceOnUse") 
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 26) // Pushes arrow exactly to the edge of the circle
      .attr("refY", 0)
      .attr("markerWidth", d => d === 'risk' ? 16 : 10) // Huge arrow for risk
      .attr("markerHeight", d => d === 'risk' ? 16 : 10)
      .attr("orient", "auto")
      .append("path")
      .attr("fill", d => d === 'risk' ? '#f43f5e' : '#94a3b8')
      // Custom dart shape for a much sharper arrow
      .attr("d", "M0,-5 L10,0 L0,5 L3,0 Z"); 

    // 5. Setup Physics
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("collide", d3.forceCollide().radius(45))
      .force("x", d3.forceX())
      .force("y", d3.forceY());

    // 6. Draw Links with thicker strokes
    const link = g.append("g")
      .attr("fill", "none") 
      .selectAll("path")
      .data(data.links)
      .join("path")
      .attr("stroke", d => d.isRisk ? "#f43f5e" : "#cbd5e1")
      .attr("stroke-width", d => d.isRisk ? 3.5 : 1.5) // Much thicker fraud lines
      .attr("marker-end", d => d.isRisk ? "url(#arrow-risk)" : "url(#arrow-normal)")
      .attr("class", d => d.isRisk ? "flowing-line transition-opacity duration-300" : "transition-opacity duration-300"); 

    // 7. Draw Nodes
    const node = g.append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .attr("class", "transition-opacity duration-300")
      .call(drag(simulation));

    node.append("circle")
      .attr("r", 18)
      .attr("fill", "#ffffff")
      .attr("stroke", d => {
        if (d.riskLevel === 'critical') return '#f43f5e';
        if (d.riskLevel === 'warning') return '#fb923c';
        return '#cbd5e1';
      })
      .attr("stroke-width", d => d.riskLevel === 'critical' ? 3 : 2)
      .attr("class", "shadow-lg cursor-pointer transition-all hover:stroke-indigo-600");

    node.append("text")
      .text(d => d.icon || "🏢")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "central")
      .attr("font-size", "16px")
      .style("pointer-events", "none");

    node.append("text")
      .text(d => d.label)
      .attr("x", 0)
      .attr("y", 30)
      .attr("text-anchor", "middle")
      .attr("fill", "#1e293b")
      .attr("font-size", "11px")
      .attr("font-weight", "600")
      .attr("font-family", "Inter, sans-serif")
      .style("pointer-events", "none")
      .clone(true).lower()
      .attr("fill", "none")
      .attr("stroke", "white")
      .attr("stroke-width", 4);

    // 8. 🔥 SPECIFIC RING HIGHLIGHTING LOGIC 🔥
    let activeNode = null;

    node.on("click", function(event, d) {
      event.stopPropagation(); 
      if (activeNode === d.id) {
        resetHighlight();
      } else {
        activeNode = d.id;

        // If it's a critical node, find ONLY the nodes in ITS specific fraud ring
        const thisRingNodes = new Set();
        if (d.riskLevel === 'critical' && riskAdj[d.id]) {
          const queue = [d.id];
          thisRingNodes.add(d.id);
          
          while (queue.length > 0) {
            const curr = queue.shift();
            riskAdj[curr].forEach(neighbor => {
              if (!thisRingNodes.has(neighbor)) {
                thisRingNodes.add(neighbor);
                queue.push(neighbor);
              }
            });
          }
        }

        node.style("opacity", o => {
          if (thisRingNodes.size > 0) {
            return thisRingNodes.has(o.id) ? 1 : 0.05; // Dim the rest heavily
          }
          return isConnected(d, o) ? 1 : 0.05;
        });

        link.style("opacity", o => {
          const sId = typeof o.source === 'object' ? o.source.id : o.source;
          const tId = typeof o.target === 'object' ? o.target.id : o.target;

          if (thisRingNodes.size > 0) {
            // ONLY keep links that connect nodes within THIS specific ring
            return (o.isRisk && thisRingNodes.has(sId) && thisRingNodes.has(tId)) ? 1 : 0.02;
          }
          return (sId === d.id || tId === d.id) ? 1 : 0.02;
        });
      }
    });

    function resetHighlight() {
      activeNode = null;
      node.style("opacity", 1);
      link.style("opacity", 0.7);
    }

    // 9. Simulation Tick (Curved Lines)
    simulation.on("tick", () => {
      link.attr("d", d => {
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.5; 
        return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
      });
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // 10. Drag Behavior
    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
      return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
    }

    return () => simulation.stop();
  }, [data]);

  return (
    <div ref={containerRef} className="w-full h-full absolute inset-0">
      <svg ref={svgRef} className="w-full h-full focus:outline-none"></svg>
    </div>
  );
}