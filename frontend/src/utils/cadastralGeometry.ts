/**
 * Cadastral Boundary Geometry and Geodesic Engine
 *
 * Implements high-precision geodesic calculations (Haversine distance,
 * metric equirectangular local projection, Gauss shoelace area,
 * and conformal SVG viewport scaling) for WGS-84 cadastral parcel vertices.
 */

export interface CadastralVertex {
  vertexNumber: number;
  latitude: number;
  longitude: number;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  isClosed: boolean;
  validVertices: CadastralVertex[];
} 

export interface MetricPoint {
  vertexNumber: number;
  x: number; // meters from centroid
  y: number; // meters from centroid (North is +y)
  latitude: number;
  longitude: number;
}

export interface SvgPoint {
  vertexNumber: number;
  x: number; // SVG pixel coordinate
  y: number; // SVG pixel coordinate (0 is top, y inverted)
  latitude: number;
  longitude: number;
}

export interface SegmentDimension {
  fromVertex: number;
  toVertex: number;
  lengthMeters: number;
  midpointSvg: { x: number; y: number };
  angleDegrees: number;
}

export interface CadastralMetrics {
  perimeterMeters: number;
  perimeterFeet: number;
  areaSqMeters: number;
  areaSqFeet: number;
  areaAcres: number;
  areaCents: number;
  centroid: { latitude: number; longitude: number };
  boundingBox: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
  };
}

export interface SvgProjectionResult {
  svgPoints: SvgPoint[];
  pathData: string;
  segments: SegmentDimension[];
  scaleMetersPerPixel: number;
  viewBox: string;
  width: number;
  height: number;
}

export interface MultiParcelInput {
  id: string;
  surveyNumber: string;
  subdivision?: string;
  color?: string;
  vertices: CadastralVertex[];
  landType?: string;
  extentHectares?: string;
  extentAres?: string;
  owners?: string[];
}

export interface ProjectedParcel {
  id: string;
  surveyNumber: string;
  subdivision?: string;
  color: string;
  vertices: CadastralVertex[];
  svgPoints: SvgPoint[];
  pathData: string;
  segments: SegmentDimension[];
  metrics: CadastralMetrics;
  centroidSvg: { x: number; y: number };
}

export interface MultiParcelSvgResult {
  projectedParcels: ProjectedParcel[];
  combinedMetrics: {
    totalAreaSqMeters: number;
    totalAreaSqFeet: number;
    totalAreaAcres: number;
    totalAreaCents: number;
    totalPerimeterMeters: number;
    totalVerticesCount: number;
    globalCentroid: { latitude: number; longitude: number };
  };
  scaleMetersPerPixel: number;
  viewBox: string;
  width: number;
  height: number;
}

const PARCEL_COLOR_PALETTE = [
  { stroke: '#059669', fill: 'rgba(16, 185, 129, 0.22)', text: '#065f46', bg: '#ecfdf5', badge: '#10b981' }, // Emerald
  { stroke: '#2563eb', fill: 'rgba(59, 130, 246, 0.22)', text: '#1e40af', bg: '#eff6ff', badge: '#3b82f6' }, // Blue
  { stroke: '#d97706', fill: 'rgba(245, 158, 11, 0.22)', text: '#92400e', bg: '#fffbeb', badge: '#f59e0b' }, // Amber
  { stroke: '#9333ea', fill: 'rgba(168, 85, 247, 0.22)', text: '#6b21a8', bg: '#faf5ff', badge: '#a855f7' }, // Purple
  { stroke: '#e11d48', fill: 'rgba(244, 63, 94, 0.22)', text: '#9f1239', bg: '#fff1f2', badge: '#f43f5e' }, // Rose
  { stroke: '#0891b2', fill: 'rgba(6, 182, 212, 0.22)', text: '#155e75', bg: '#ecfeff', badge: '#06b6d4' }, // Cyan
];

const EARTH_RADIUS_METERS = 6378137.0; // WGS-84 semi-major axis

/**
 * Validates extracted boundary coordinates according to cadastral GIS standards.
 */
export function validateBoundaryVertices(vertices: CadastralVertex[]): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  const validVertices: CadastralVertex[] = [];

  if (!vertices || !Array.isArray(vertices) || vertices.length === 0) {
    return {
      isValid: false,
      errors: ['No boundary vertices provided.'],
      warnings: [],
      isClosed: false,
      validVertices: [],
    };
  }

  for (let i = 0; i < vertices.length; i++) {
    const v = vertices[i];
    if (v === null || v === undefined) {
      warnings.push(`Vertex at index ${i} is null/undefined and was skipped.`);
      continue;
    }

    const lat = Number(v.latitude);
    const lon = Number(v.longitude);
    const num = v.vertexNumber ?? (i + 1);

    if (isNaN(lat) || isNaN(lon) || !isFinite(lat) || !isFinite(lon)) {
      errors.push(`Vertex #${num} contains non-numeric or infinite coordinates.`);
      continue;
    }

    if (lat < -90 || lat > 90) {
      errors.push(`Vertex #${num} latitude (${lat}) is outside valid WGS-84 range [-90, 90].`);
      continue;
    }

    if (lon < -180 || lon > 180) {
      errors.push(`Vertex #${num} longitude (${lon}) is outside valid WGS-84 range [-180, 180].`);
      continue;
    }

    // Detect duplicate consecutive points
    if (validVertices.length > 0) {
      const prev = validVertices[validVertices.length - 1];
      if (Math.abs(prev.latitude - lat) < 1e-8 && Math.abs(prev.longitude - lon) < 1e-8) {
        warnings.push(`Vertex #${num} is identical to previous vertex #${prev.vertexNumber}; skipped duplicate.`);
        continue;
      }
    }

    validVertices.push({
      vertexNumber: num,
      latitude: lat,
      longitude: lon,
    });
  }

  if (validVertices.length < 3) {
    errors.push(`Minimum 3 valid non-collinear vertices are required to form a polygon (found ${validVertices.length}).`);
  }

  // Check if first and last vertices are identical (closed representation)
  let isClosed = false;
  if (validVertices.length >= 3) {
    const first = validVertices[0];
    const last = validVertices[validVertices.length - 1];
    if (Math.abs(first.latitude - last.latitude) < 1e-7 && Math.abs(first.longitude - last.longitude) < 1e-7) {
      isClosed = true;
    }
  }

  return {
    isValid: errors.length === 0 && validVertices.length >= 3,
    errors,
    warnings,
    isClosed,
    validVertices,
  };
}

/**
 * Calculates accurate geodesic distance in meters between two WGS-84 coordinates
 * using the Haversine formula.
 */
export function calculateHaversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const toRad = Math.PI / 180.0;
  const phi1 = lat1 * toRad;
  const phi2 = lat2 * toRad;
  const deltaPhi = (lat2 - lat1) * toRad;
  const deltaLambda = (lon2 - lon1) * toRad;

  const a =
    Math.sin(deltaPhi / 2.0) * Math.sin(deltaPhi / 2.0) +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2.0) * Math.sin(deltaLambda / 2.0);

  const c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(1.0 - a));
  return EARTH_RADIUS_METERS * c;
}

/**
 * Projects ordered WGS-84 coordinates into local metric coordinates (x, y in meters)
 * centered on the parcel centroid using an equirectangular projection.
 * North is +y, East is +x.
 */
export function projectToLocalMetric(vertices: CadastralVertex[]): {
  metricPoints: MetricPoint[];
  centroid: { latitude: number; longitude: number };
} {
  if (vertices.length === 0) {
    return { metricPoints: [], centroid: { latitude: 0, longitude: 0 } };
  }

  // Calculate arithmetic centroid
  let sumLat = 0;
  let sumLon = 0;
  for (const v of vertices) {
    sumLat += v.latitude;
    sumLon += v.longitude;
  }
  const lat0 = sumLat / vertices.length;
  const lon0 = sumLon / vertices.length;

  const toRad = Math.PI / 180.0;
  const lat0Rad = lat0 * toRad;
  const cosLat0 = Math.cos(lat0Rad);

  const metricPoints: MetricPoint[] = vertices.map((v) => {
    const deltaLonRad = (v.longitude - lon0) * toRad;
    const deltaLatRad = (v.latitude - lat0) * toRad;

    const x = EARTH_RADIUS_METERS * deltaLonRad * cosLat0;
    const y = EARTH_RADIUS_METERS * deltaLatRad;

    return {
      vertexNumber: v.vertexNumber,
      x,
      y,
      latitude: v.latitude,
      longitude: v.longitude,
    };
  });

  return {
    metricPoints,
    centroid: { latitude: lat0, longitude: lon0 },
  };
}

/**
 * Calculates comprehensive cadastral metrics:
 * - Perimeter (sum of geodesic distances in meters and feet)
 * - Area via Gauss Shoelace formula on metric coordinates (sq.m, sq.ft, acres, cents)
 * - Centroid and Bounding Box
 */
export function calculateCadastralMetrics(vertices: CadastralVertex[]): CadastralMetrics {
  if (vertices.length < 3) {
    return {
      perimeterMeters: 0,
      perimeterFeet: 0,
      areaSqMeters: 0,
      areaSqFeet: 0,
      areaAcres: 0,
      areaCents: 0,
      centroid: { latitude: 0, longitude: 0 },
      boundingBox: { minLat: 0, maxLat: 0, minLon: 0, maxLon: 0 },
    };
  }

  // Calculate Geodesic Perimeter
  let perimeterMeters = 0;
  const n = vertices.length;
  for (let i = 0; i < n; i++) {
    const curr = vertices[i];
    const next = vertices[(i + 1) % n];
    perimeterMeters += calculateHaversineDistance(
      curr.latitude,
      curr.longitude,
      next.latitude,
      next.longitude
    );
  }

  // Project to metric for planar Gauss Shoelace area
  const { metricPoints, centroid } = projectToLocalMetric(vertices);

  let shoelaceSum = 0;
  for (let i = 0; i < n; i++) {
    const p1 = metricPoints[i];
    const p2 = metricPoints[(i + 1) % n];
    shoelaceSum += p1.x * p2.y - p2.x * p1.y;
  }
  const areaSqMeters = Math.abs(shoelaceSum) / 2.0;

  // Conversions
  const areaSqFeet = areaSqMeters * 10.7639104;
  const areaAcres = areaSqMeters / 4046.85642;
  // Tamil Nadu cadastral standard: 1 Cent = 435.6 sq.ft = 40.46856 sq.m (100 cents = 1 acre)
  const areaCents = areaSqMeters / 40.4685642;

  // Bounding box
  let minLat = vertices[0].latitude;
  let maxLat = vertices[0].latitude;
  let minLon = vertices[0].longitude;
  let maxLon = vertices[0].longitude;
  for (let i = 1; i < n; i++) {
    if (vertices[i].latitude < minLat) minLat = vertices[i].latitude;
    if (vertices[i].latitude > maxLat) maxLat = vertices[i].latitude;
    if (vertices[i].longitude < minLon) minLon = vertices[i].longitude;
    if (vertices[i].longitude > maxLon) maxLon = vertices[i].longitude;
  }

  return {
    perimeterMeters: Number(perimeterMeters.toFixed(2)),
    perimeterFeet: Number((perimeterMeters * 3.28084).toFixed(2)),
    areaSqMeters: Number(areaSqMeters.toFixed(2)),
    areaSqFeet: Number(areaSqFeet.toFixed(1)),
    areaAcres: Number(areaAcres.toFixed(3)),
    areaCents: Number(areaCents.toFixed(2)),
    centroid,
    boundingBox: { minLat, maxLat, minLon, maxLon },
  };
}

/**
 * Projects local metric parcel vertices into an SVG viewport with uniform scaling
 * preserving relative angles and aspect ratio.
 * Inverts Y so that geographic North points directly upwards (+Y in metric -> lower Y in SVG).
 */
export function projectToSvg(
  vertices: CadastralVertex[],
  viewportWidth = 800,
  viewportHeight = 600,
  padding = 70
): SvgProjectionResult {
  if (vertices.length < 3) {
    return {
      svgPoints: [],
      pathData: '',
      segments: [],
      scaleMetersPerPixel: 1,
      viewBox: `0 0 ${viewportWidth} ${viewportHeight}`,
      width: viewportWidth,
      height: viewportHeight,
    };
  }

  const { metricPoints } = projectToLocalMetric(vertices);

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const p of metricPoints) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }

  const metricWidth = Math.max(maxX - minX, 1.0);
  const metricHeight = Math.max(maxY - minY, 1.0);

  const availableWidth = Math.max(viewportWidth - 2 * padding, 100);
  const availableHeight = Math.max(viewportHeight - 2 * padding, 100);

  // Maintain uniform scale on both axes (equal scale)
  const scale = Math.min(availableWidth / metricWidth, availableHeight / metricHeight);

  // Center polygon inside available canvas
  const projectedWidth = metricWidth * scale;
  const projectedHeight = metricHeight * scale;
  const offsetX = padding + (availableWidth - projectedWidth) / 2.0;
  const offsetY = padding + (availableHeight - projectedHeight) / 2.0;

  const svgPoints: SvgPoint[] = metricPoints.map((p) => {
    const px = offsetX + (p.x - minX) * scale;
    // Invert Y for screen coordinates (in metric, max Y is North; in SVG, 0 is top)
    const py = viewportHeight - (offsetY + (p.y - minY) * scale);
    return {
      vertexNumber: p.vertexNumber,
      x: Number(px.toFixed(2)),
      y: Number(py.toFixed(2)),
      latitude: p.latitude,
      longitude: p.longitude,
    };
  });

  // Construct closed SVG path data
  const pathParts: string[] = [];
  if (svgPoints.length > 0) {
    pathParts.push(`M ${svgPoints[0].x} ${svgPoints[0].y}`);
    for (let i = 1; i < svgPoints.length; i++) {
      pathParts.push(`L ${svgPoints[i].x} ${svgPoints[i].y}`);
    }
    pathParts.push('Z');
  }
  const pathData = pathParts.join(' ');

  // Compute boundary segment dimensions
  const segments: SegmentDimension[] = [];
  const n = svgPoints.length;
  for (let i = 0; i < n; i++) {
    const curr = svgPoints[i];
    const next = svgPoints[(i + 1) % n];
    const lengthMeters = calculateHaversineDistance(
      curr.latitude,
      curr.longitude,
      next.latitude,
      next.longitude
    );

    const midX = (curr.x + next.x) / 2.0;
    const midY = (curr.y + next.y) / 2.0;
    const angleRad = Math.atan2(next.y - curr.y, next.x - curr.x);
    let angleDegrees = (angleRad * 180.0) / Math.PI;
    // Normalize text readability angle
    if (angleDegrees > 90) angleDegrees -= 180;
    if (angleDegrees < -90) angleDegrees += 180;

    segments.push({
      fromVertex: curr.vertexNumber,
      toVertex: next.vertexNumber,
      lengthMeters: Number(lengthMeters.toFixed(2)),
      midpointSvg: { x: Number(midX.toFixed(2)), y: Number(midY.toFixed(2)) },
      angleDegrees: Number(angleDegrees.toFixed(1)),
    });
  }

  const scaleMetersPerPixel = scale > 0 ? 1.0 / scale : 1.0;

  return {
    svgPoints,
    pathData,
    segments,
    scaleMetersPerPixel: Number(scaleMetersPerPixel.toFixed(4)),
    viewBox: `0 0 ${viewportWidth} ${viewportHeight}`,
    width: viewportWidth,
    height: viewportHeight,
  };
}

/**
 * Generates formatted CSV content containing all ordered boundary vertices.
 */
export function generateCoordinatesCsv(
  vertices: CadastralVertex[],
  propertyTitle = 'Property'
): string {
  const lines = [
    `# RED Cadastral Boundary Coordinates Export`,
    `# Property: ${propertyTitle}`,
    `# Datum: WGS-84 (EPSG:4326)`,
    `# Total Vertices: ${vertices.length}`,
    `# Exported At: ${new Date().toISOString()}`,
    `vertex_number,latitude,longitude`,
  ];

  for (const v of vertices) {
    lines.push(`${v.vertexNumber},${v.latitude.toFixed(6)},${v.longitude.toFixed(6)}`);
  }

  return lines.join('\n');
}

/**
 * Projects multiple survey parcels into a single unified SVG canvas.
 * Computes global centroid across all parcels, uniform scale, individual paths,
 * segment lengths, parcel centroid badges, and combined totals.
 */
export function projectMultiParcelsToSvg(
  parcels: MultiParcelInput[],
  viewportWidth = 840,
  viewportHeight = 580,
  padding = 80
): MultiParcelSvgResult {
  const validParcels = parcels.filter(
    (p) => p.vertices && Array.isArray(p.vertices) && p.vertices.length >= 3
  );

  if (validParcels.length === 0) {
    return {
      projectedParcels: [],
      combinedMetrics: {
        totalAreaSqMeters: 0,
        totalAreaSqFeet: 0,
        totalAreaAcres: 0,
        totalAreaCents: 0,
        totalPerimeterMeters: 0,
        totalVerticesCount: 0,
        globalCentroid: { latitude: 0, longitude: 0 },
      },
      scaleMetersPerPixel: 1,
      viewBox: `0 0 ${viewportWidth} ${viewportHeight}`,
      width: viewportWidth,
      height: viewportHeight,
    };
  }

  // 1. Calculate global centroid across ALL vertices of ALL valid parcels
  let totalLat = 0;
  let totalLon = 0;
  let totalVerticesCount = 0;

  validParcels.forEach((p) => {
    p.vertices.forEach((v) => {
      totalLat += v.latitude;
      totalLon += v.longitude;
      totalVerticesCount++;
    });
  });

  const lat0 = totalLat / totalVerticesCount;
  const lon0 = totalLon / totalVerticesCount;
  const toRad = Math.PI / 180.0;
  const cosLat0 = Math.cos(lat0 * toRad);

  // 2. Project each parcel's vertices to metric coordinates relative to global centroid (lat0, lon0)
  const parcelMetricMap = validParcels.map((p, idx) => {
    const metricPoints: MetricPoint[] = p.vertices.map((v) => {
      const x = EARTH_RADIUS_METERS * (v.longitude - lon0) * toRad * cosLat0;
      const y = EARTH_RADIUS_METERS * (v.latitude - lat0) * toRad;
      return {
        vertexNumber: v.vertexNumber,
        x,
        y,
        latitude: v.latitude,
        longitude: v.longitude,
      };
    });

    const metrics = calculateCadastralMetrics(p.vertices);
    const chosenColor = p.color || PARCEL_COLOR_PALETTE[idx % PARCEL_COLOR_PALETTE.length].stroke;

    return {
      parcel: p,
      color: chosenColor,
      metricPoints,
      metrics,
    };
  });

  // 3. Compute global metric bounding box across ALL parcels
  let globalMinX = Infinity;
  let globalMaxX = -Infinity;
  let globalMinY = Infinity;
  let globalMaxY = -Infinity;

  parcelMetricMap.forEach((item) => {
    item.metricPoints.forEach((pt) => {
      if (pt.x < globalMinX) globalMinX = pt.x;
      if (pt.x > globalMaxX) globalMaxX = pt.x;
      if (pt.y < globalMinY) globalMinY = pt.y;
      if (pt.y > globalMaxY) globalMaxY = pt.y;
    });
  });

  const metricWidth = Math.max(globalMaxX - globalMinX, 1.0);
  const metricHeight = Math.max(globalMaxY - globalMinY, 1.0);

  const availableWidth = Math.max(viewportWidth - 2 * padding, 100);
  const availableHeight = Math.max(viewportHeight - 2 * padding, 100);

  const scale = Math.min(availableWidth / metricWidth, availableHeight / metricHeight);

  const projectedWidth = metricWidth * scale;
  const projectedHeight = metricHeight * scale;
  const offsetX = padding + (availableWidth - projectedWidth) / 2.0;
  const offsetY = padding + (availableHeight - projectedHeight) / 2.0;

  // 4. Project each parcel to SVG points and paths
  let combinedAreaSqMeters = 0;
  let combinedPerimeterMeters = 0;

  const projectedParcels: ProjectedParcel[] = parcelMetricMap.map((item) => {
    const p = item.parcel;
    combinedAreaSqMeters += item.metrics.areaSqMeters;
    combinedPerimeterMeters += item.metrics.perimeterMeters;

    const svgPoints: SvgPoint[] = item.metricPoints.map((pt) => {
      const px = offsetX + (pt.x - globalMinX) * scale;
      const py = viewportHeight - (offsetY + (pt.y - globalMinY) * scale);
      return {
        vertexNumber: pt.vertexNumber,
        x: Number(px.toFixed(2)),
        y: Number(py.toFixed(2)),
        latitude: pt.latitude,
        longitude: pt.longitude,
      };
    });

    const pathParts: string[] = [];
    if (svgPoints.length > 0) {
      pathParts.push(`M ${svgPoints[0].x} ${svgPoints[0].y}`);
      for (let i = 1; i < svgPoints.length; i++) {
        pathParts.push(`L ${svgPoints[i].x} ${svgPoints[i].y}`);
      }
      pathParts.push('Z');
    }
    const pathData = pathParts.join(' ');

    // Calculate segments
    const segments: SegmentDimension[] = [];
    const n = svgPoints.length;
    for (let i = 0; i < n; i++) {
      const curr = svgPoints[i];
      const next = svgPoints[(i + 1) % n];
      const lengthMeters = calculateHaversineDistance(
        curr.latitude,
        curr.longitude,
        next.latitude,
        next.longitude
      );
      const midX = (curr.x + next.x) / 2.0;
      const midY = (curr.y + next.y) / 2.0;
      const angleRad = Math.atan2(next.y - curr.y, next.x - curr.x);
      let angleDegrees = (angleRad * 180.0) / Math.PI;
      if (angleDegrees > 90) angleDegrees -= 180;
      if (angleDegrees < -90) angleDegrees += 180;

      segments.push({
        fromVertex: curr.vertexNumber,
        toVertex: next.vertexNumber,
        lengthMeters: Number(lengthMeters.toFixed(2)),
        midpointSvg: { x: Number(midX.toFixed(2)), y: Number(midY.toFixed(2)) },
        angleDegrees: Number(angleDegrees.toFixed(1)),
      });
    }

    // Centroid in SVG space
    let sumX = 0;
    let sumY = 0;
    svgPoints.forEach((sp) => {
      sumX += sp.x;
      sumY += sp.y;
    });
    const centroidSvg = {
      x: Number((sumX / svgPoints.length).toFixed(2)),
      y: Number((sumY / svgPoints.length).toFixed(2)),
    };

    return {
      id: p.id,
      surveyNumber: p.surveyNumber,
      subdivision: p.subdivision,
      color: item.color,
      vertices: p.vertices,
      svgPoints,
      pathData,
      segments,
      metrics: item.metrics,
      centroidSvg,
    };
  });

  const totalAreaSqFeet = combinedAreaSqMeters * 10.7639104;
  const totalAreaAcres = combinedAreaSqMeters / 4046.85642;
  const totalAreaCents = combinedAreaSqMeters / 40.4685642;
  const scaleMetersPerPixel = scale > 0 ? 1.0 / scale : 1.0;

  return {
    projectedParcels,
    combinedMetrics: {
      totalAreaSqMeters: Number(combinedAreaSqMeters.toFixed(2)),
      totalAreaSqFeet: Number(totalAreaSqFeet.toFixed(1)),
      totalAreaAcres: Number(totalAreaAcres.toFixed(3)),
      totalAreaCents: Number(totalAreaCents.toFixed(2)),
      totalPerimeterMeters: Number(combinedPerimeterMeters.toFixed(2)),
      totalVerticesCount,
      globalCentroid: { latitude: lat0, longitude: lon0 },
    },
    scaleMetersPerPixel: Number(scaleMetersPerPixel.toFixed(4)),
    viewBox: `0 0 ${viewportWidth} ${viewportHeight}`,
    width: viewportWidth,
    height: viewportHeight,
  };
}

