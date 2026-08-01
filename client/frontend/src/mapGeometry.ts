export const positionsFor = (geometry: GeoJSON.Geometry): GeoJSON.Position[] => geometry.type === 'Polygon'
  ? geometry.coordinates.flat(1)
  : geometry.type === 'MultiPolygon'
    ? geometry.coordinates.flat(2)
    : []

export const areaCentroid = (geometry: GeoJSON.Geometry): [number, number] | null => {
  const positions = positionsFor(geometry)
  if (!positions.length) return null
  const [longitude, latitude] = positions.reduce(([totalLongitude, totalLatitude], [lng, lat]) => [totalLongitude + lng, totalLatitude + lat], [0, 0])
  return [longitude / positions.length, latitude / positions.length]
}
