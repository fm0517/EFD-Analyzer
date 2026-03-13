"""
Draw.io to SVG Converter

Converts .drawio files (mxfile format) to SVG by parsing the mxGraphModel structure
and rendering vertices (shapes) and edges (arrows/connectors).
"""

import xml.etree.ElementTree as ET
import html
import math
import re
from pathlib import Path


def parse_drawio_file(drawio_path: str) -> ET.Element:
    """Parse the drawio file and extract the mxGraphModel."""
    tree = ET.parse(drawio_path)
    root = tree.getroot()
    
    # Find the diagram element
    diagram = root.find('diagram')
    if diagram is None:
        raise ValueError("No diagram element found in drawio file")
    
    # Find the mxGraphModel
    mx_graph_model = diagram.find('mxGraphModel')
    if mx_graph_model is None:
        raise ValueError("No mxGraphModel element found in diagram")
    
    return mx_graph_model


def extract_elements(mx_graph_model: ET.Element) -> tuple[list[dict], list[dict]]:
    """Extract vertices and edges from the mxGraphModel."""
    root_element = mx_graph_model.find('root')
    if root_element is None:
        return [], []
    
    vertices = []
    edges = []
    
    for cell in root_element.findall('mxCell'):
        style = cell.get('style', '')
        vertex = cell.get('vertex', '0')
        edge = cell.get('edge', '0')
        
        # Get geometry
        geometry_elem = cell.find('mxGeometry')
        if geometry_elem is None:
            continue
        
        # Skip vertex elements with relative geometry (edge labels positioned along parent edge)
        if vertex == '1' and geometry_elem.get('relative') == '1':
            continue
        
        x = float(geometry_elem.get('x', 0))
        y = float(geometry_elem.get('y', 0))
        width = float(geometry_elem.get('width', 100))
        height = float(geometry_elem.get('height', 30))
        
        # Get label/value
        value = cell.get('value', '')
        
        # Parse style attributes
        style_attrs = parse_style(style)
        
        if vertex == '1':
            vertices.append({
                'id': cell.get('id'),
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'value': value,
                'style': style_attrs,
                'raw_style': style
            })
        elif edge == '1':
            # Get source and target
            source = cell.get('source')
            target = cell.get('target')
            
            # Get waypoints if any
            points = []
            geometry_xml = cell.find('mxGeometry')
            if geometry_xml is not None:
                array_elem = geometry_xml.find('Array')
                if array_elem is not None:
                    for point_elem in array_elem.findall('mxPoint'):
                        px = float(point_elem.get('x', 0))
                        py = float(point_elem.get('y', 0))
                        points.append((px, py))
            
            # Extract sourcePoint and targetPoint from geometry
            source_point = None
            target_point = None
            if geometry_xml is not None:
                for pt in geometry_xml.findall('mxPoint'):
                    pt_as = pt.get('as', '')
                    if pt_as == 'sourcePoint':
                        spx = pt.get('x')
                        spy = pt.get('y')
                        if spx is not None and spy is not None:
                            source_point = (float(spx), float(spy))
                    elif pt_as == 'targetPoint':
                        tpx = pt.get('x')
                        tpy = pt.get('y')
                        if tpx is not None and tpy is not None:
                            target_point = (float(tpx), float(tpy))

            edges.append({
                'id': cell.get('id'),
                'source': source,
                'target': target,
                'value': value,
                'style': style_attrs,
                'raw_style': style,
                'points': points,
                'geometry': geometry_elem,
                'source_point': source_point,
                'target_point': target_point
            })
    
    return vertices, edges


def parse_style(style_str: str) -> dict:
    """Parse style string into a dictionary."""
    if not style_str:
        return {}
    
    attrs = {}
    for part in style_str.split(';'):
        if '=' in part:
            key, value = part.split('=', 1)
            attrs[key.strip()] = value.strip()
    return attrs


def get_vertex_coordinates(vertex: dict, vertices_map: dict) -> tuple[float, float, float, float]:
    """Get the drawing coordinates for a vertex."""
    return vertex['x'], vertex['y'], vertex['width'], vertex['height']


def get_edge_coordinates(edge: dict, vertices_map: dict) -> list[tuple[float, float]]:
    """Calculate edge coordinates based on source, target, and waypoints."""
    source_id = edge['source']
    target_id = edge['target']
    
    # Determine source point
    source_pt = None
    if source_id and source_id in vertices_map:
        source = vertices_map[source_id]
        sx, sy, sw, sh = source['x'], source['y'], source['width'], source['height']
        source_pt = get_connection_point(sx, sy, sw, sh, edge['style'], is_source=True)
    elif edge.get('source_point'):
        source_pt = edge['source_point']
    
    # Determine target point
    target_pt = None
    if target_id and target_id in vertices_map:
        target = vertices_map[target_id]
        tx, ty, tw, th = target['x'], target['y'], target['width'], target['height']
        target_pt = get_connection_point(tx, ty, tw, th, edge['style'], is_source=False)
    elif edge.get('target_point'):
        target_pt = edge['target_point']
    
    if source_pt is None or target_pt is None:
        return []
    
    points = [source_pt]
    
    # Add waypoints if present
    if edge['points']:
        for wp in edge['points']:
            points.append(wp)
    
    points.append(target_pt)
    
    return points


def get_connection_point(x: float, y: float, w: float, h: float, 
                         style: dict, is_source: bool) -> tuple[float, float]:
    """Get the connection point on a shape based on style attributes."""
    # Check for exit/entry attributes
    if is_source:
        exit_x = float(style.get('exitX', 0.5))
        exit_y = float(style.get('exitY', 0.5))
        cx = x + w * exit_x
        cy = y + h * exit_y
    else:
        entry_x = float(style.get('entryX', 0.5))
        entry_y = float(style.get('entryY', 0.5))
        cx = x + w * entry_x
        cy = y + h * entry_y
    
    return (cx, cy)


def determine_shape_type(style: dict) -> str:
    """Determine the SVG shape type based on style attributes."""
    shape = style.get('shape', '')
    
    if shape == 'step':
        return 'step'
    elif shape == 'mxgraph.flowchart.terminator':
        return 'terminator'
    elif style.get('rounded', '0') == '1':
        return 'rounded_rect'
    else:
        return 'rect'


def create_step_path(x: float, y: float, w: float, h: float, size: float = 10) -> str:
    """Create SVG path for step shape (pentagon arrow pointing right)."""
    return f"M {x},{y} L {x + w - size},{y} L {x + w},{y + h / 2} L {x + w - size},{y + h} L {x},{y + h} Z"


def create_terminator_path(x: float, y: float, w: float, h: float) -> str:
    """Create SVG path for terminator shape (pill/stadium with semicircular ends)."""
    ry = h / 2
    rx = min(ry, w / 2)
    return (f"M {x + rx},{y} L {x + w - rx},{y} "
            f"A {rx},{ry} 0 0,1 {x + w - rx},{y + h} "
            f"L {x + rx},{y + h} "
            f"A {rx},{ry} 0 0,1 {x + rx},{y} Z")


def create_rounded_rect_path(x: float, y: float, w: float, h: float, 
                              rx: float = 10, ry: float = 10) -> str:
    """Create SVG path for rounded rectangle."""
    return f"M {x + rx},{y} L {x + w - rx},{y} Q {x + w},{y} {x + w},{y + ry} L {x + w},{y + h - ry} Q {x + w},{y + h} {x + w - rx},{y + h} L {x + rx},{y + h} Q {x},{y + h} {x},{y + h - ry} L {x},{y + ry} Q {x},{y} {x + rx},{y} Z"


def create_rect_path(x: float, y: float, w: float, h: float) -> str:
    """Create SVG path for rectangle."""
    return f"M {x},{y} L {x + w},{y} L {x + w},{y + h} L {x},{y + h} Z"


def get_stroke_color(style: dict) -> str:
    """Get stroke color from style."""
    color = style.get('strokeColor', '#000000')
    if color == 'default':
        return '#000000'
    return '#' + color if not color.startswith('#') else color


def get_fill_color(style: dict) -> str:
    """Get fill color from style."""
    color = style.get('fillColor', 'none')
    if color == 'none':
        return 'none'
    return '#' + color if not color.startswith('#') else color


def get_font_color(style: dict) -> str:
    """Get font color from style."""
    color = style.get('fontColor', '#000000')
    return '#' + color if not color.startswith('#') else color


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text, keeping only the text content."""
    if not text:
        return ''
    # Decode HTML entities first
    text = html.unescape(text)
    # Replace <br>, <br/>, <br /> with newline markers
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def escape_xml_text(text: str) -> str:
    """Escape special XML characters in text."""
    if not text:
        return ''
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text


def create_svg_content(vertices: list[dict], edges: list[dict], 
                       padding: float = 20) -> str:
    """Create the SVG content from vertices and edges."""
    # Calculate bounding box
    all_x = []
    all_y = []
    
    for v in vertices:
        all_x.extend([v['x'], v['x'] + v['width']])
        all_y.extend([v['y'], v['y'] + v['height']])
    
    if not all_x or not all_y:
        min_x, min_y, max_x, max_y = 0, 0, 800, 600
    else:
        min_x = min(all_x) - padding
        min_y = min(all_y) - padding
        max_x = max(all_x) + padding
        max_y = max(all_y) + padding
    
    width = max_x - min_x
    height = max_y - min_y
    
    # Create vertices map for edge lookup
    vertices_map = {v['id']: v for v in vertices}
    
    # Build SVG
    svg_parts = []
    
    # SVG header
    svg_parts.append(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="{min_x} {min_y} {width} {height}">\n'
    )
    
    # Add styles
    svg_parts.append('''
    <defs>
      <marker id="arrowhead-block" markerWidth="10" markerHeight="10" 
              refX="9" refY="3" orient="auto">
        <polygon points="0 0, 10 3, 0 6" fill="#000000" />
      </marker>
      <marker id="arrowhead-open" markerWidth="10" markerHeight="10" 
              refX="9" refY="3" orient="auto">
        <polyline points="0 0, 10 3, 0 6" fill="none" stroke="#000000" stroke-width="1"/>
      </marker>
    </defs>
    <style>
      .shape { stroke-width: 2; }
      .edge { stroke-width: 1.5; fill: none; }
      .label { font-family: Arial, sans-serif; font-size: 10px; text-anchor: middle; dominant-baseline: middle; }
    </style>
    ''')
    
    # Draw edges first (so they appear behind vertices)
    svg_parts.append('  <g id="edges">\n')
    
    for edge in edges:
        points = get_edge_coordinates(edge, vertices_map)
        if len(points) < 2:
            continue
        
        style = edge['style']
        stroke_color = get_stroke_color(style)
        
        # Determine arrowhead style
        end_arrow = style.get('endArrow', 'block')
        is_dashed = style.get('dashed', '0') == '1'
        
        # Create path
        path_d = f"M {points[0][0]},{points[0][1]}"
        for px, py in points[1:]:
            path_d += f" L {px},{py}"
        
        # Check if orthogonal edge style
        if style.get('edgeStyle') == 'orthogonalEdgeStyle' or style.get('orthogonalLoop', '0') == '1':
            # Use orthogonal path with waypoints
            path_d = f"M {points[0][0]},{points[0][1]}"
            for px, py in points[1:]:
                path_d += f" L {px},{py}"
        
        marker_end = ''
        if end_arrow == 'block':
            marker_end = ' marker-end="url(#arrowhead-block)"'
        elif end_arrow == 'open':
            marker_end = ' marker-end="url(#arrowhead-open)"'
        
        dash_array = ' stroke-dasharray="5,5"' if is_dashed else ''
        
        svg_parts.append(
            f'    <path d="{path_d}" class="edge" '
            f'stroke="{stroke_color}"{marker_end}{dash_array} />\n'
        )
        
        # Add edge label if present
        edge_value = edge.get('value', '')
        if edge_value:
            clean_value = strip_html_tags(edge_value)
            if clean_value:
                # Calculate label position (middle of edge)
                mid_idx = len(points) // 2
                lx = (points[mid_idx][0] + points[min(mid_idx + 1, len(points) - 1)][0]) / 2
                ly = (points[mid_idx][1] + points[min(mid_idx + 1, len(points) - 1)][1]) / 2
                
                font_color = get_font_color(style)
                escaped_value = escape_xml_text(clean_value)
                svg_parts.append(
                    f'    <text x="{lx}" y="{ly}" class="label" fill="{font_color}">{escaped_value}</text>\n'
                )
    
    svg_parts.append('  </g>\n')
    
    # Draw vertices
    svg_parts.append('  <g id="vertices">\n')
    
    for vertex in vertices:
        x, y, w, h = get_vertex_coordinates(vertex, vertices_map)
        style = vertex['style']
        raw_style = vertex.get('raw_style', '')
        value = vertex.get('value', '')
        
        # Check if this is a text-only or edge-label shape (no visible border)
        is_text_only = raw_style.startswith('text;') or raw_style.startswith('edgeLabel;')
        
        shape_type = determine_shape_type(style)
        stroke_color = get_stroke_color(style)
        fill_color = get_fill_color(style)
        
        svg_parts.append(f'    <g id="{vertex["id"]}">\n')
        
        # Only draw shape path for non-text-only elements
        if not is_text_only:
            # Create shape path
            if shape_type == 'step':
                size = float(style.get('size', 10))
                path_d = create_step_path(x, y, w, h, size)
            elif shape_type == 'terminator':
                path_d = create_terminator_path(x, y, w, h)
            elif shape_type == 'rounded_rect':
                path_d = create_rounded_rect_path(x, y, w, h)
            else:
                path_d = create_rect_path(x, y, w, h)
            
            svg_parts.append(
                f'      <path d="{path_d}" class="shape" '
                f'stroke="{stroke_color}" fill="{fill_color}" />\n'
            )
        
        # Add label
        if value:
            font_color = get_font_color(style)
            label_x = x + w / 2
            label_y = y + h / 2
            
            # Strip all HTML tags, keeping text content
            clean_value = strip_html_tags(value)
            
            # Handle line breaks in labels
            lines = clean_value.split('\n')
            lines = [l for l in lines if l.strip()]  # remove blank lines
            if len(lines) > 1:
                line_height = 13
                for i, line in enumerate(lines):
                    escaped_line = escape_xml_text(line.strip())
                    ly = label_y - (len(lines) - 1) * line_height / 2 + i * line_height
                    svg_parts.append(
                        f'      <text x="{label_x}" y="{ly}" class="label" fill="{font_color}">{escaped_line}</text>\n'
                    )
            else:
                escaped_value = escape_xml_text(clean_value)
                svg_parts.append(
                    f'      <text x="{label_x}" y="{label_y}" class="label" fill="{font_color}">{escaped_value}</text>\n'
                )
        
        svg_parts.append('    </g>\n')
    
    svg_parts.append('  </g>\n')
    svg_parts.append('</svg>\n')
    
    return ''.join(svg_parts)


def convert_drawio_to_svg(drawio_path: str, svg_path: str) -> None:
    """Main function to convert a drawio file to SVG."""
    print(f"Reading drawio file: {drawio_path}")
    
    # Parse the drawio file
    mx_graph_model = parse_drawio_file(drawio_path)
    
    print("Extracting elements...")
    vertices, edges = extract_elements(mx_graph_model)
    print(f"  Found {len(vertices)} vertices and {len(edges)} edges")
    
    print("Creating SVG content...")
    svg_content = create_svg_content(vertices, edges)
    
    print(f"Writing SVG file: {svg_path}")
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    print("Conversion complete!")


if __name__ == '__main__':
    # Get the script directory
    script_dir = Path(__file__).parent
    
    # Define input and output paths
    drawio_path = script_dir.parent / 'data' / 'SingaPort_EFD.drawio'
    svg_path = script_dir.parent / 'data' / 'SingaPort_EFD.svg'
    
    convert_drawio_to_svg(str(drawio_path), str(svg_path))
