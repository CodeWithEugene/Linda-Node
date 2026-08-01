import { describe, expect, it } from 'vitest'

import { areaCentroid } from './AreaMap'

describe('areaCentroid', () => {
  it('places an affected-area marker at the center of a GeoJSON polygon', () => {
    const result = areaCentroid({ type: 'Polygon', coordinates: [[[34.4, 0.5], [34.8, 0.5], [34.8, 1], [34.4, 1], [34.4, 0.5]]] })
    expect(result?.[0]).toBeCloseTo(34.56)
    expect(result?.[1]).toBeCloseTo(.7)
  })
})
