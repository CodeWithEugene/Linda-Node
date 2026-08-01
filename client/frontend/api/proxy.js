const allowedPrefixes = new Set(['api', 'cap', 'integration'])

function requestedPath(value) {
  const path = Array.isArray(value) ? value[0] : value
  if (typeof path !== 'string') return null
  const [prefix] = path.split('/')
  return allowedPrefixes.has(prefix) ? path : null
}

async function readBody(request) {
  const chunks = []
  for await (const chunk of request) chunks.push(chunk)
  return chunks.length ? Buffer.concat(chunks) : undefined
}

export const config = { api: { bodyParser: false } }

export default async function handler(request, response) {
  const backendOrigin = process.env.LINDA_API_ORIGIN?.replace(/\/+$/, '')
  const path = requestedPath(request.query.path)

  if (!backendOrigin) {
    response.status(503).json({ error: { code: 'API_NOT_CONFIGURED', message: 'The Linda API origin is not configured for this deployment.' } })
    return
  }
  if (!path) {
    response.status(400).json({ error: { code: 'INVALID_PROXY_PATH', message: 'This proxy path is not allowed.' } })
    return
  }

  const target = new URL(`${backendOrigin}/${path}`)
  const source = new URL(request.url || '/', `https://${request.headers.host || 'localhost'}`)
  target.search = source.search
  const headers = new Headers()
  for (const name of ['accept', 'content-type', 'cookie', 'if-none-match', 'if-modified-since', 'user-agent']) {
    const value = request.headers[name]
    if (typeof value === 'string') headers.set(name, value)
  }
  headers.set('x-forwarded-host', request.headers.host || '')
  headers.set('x-forwarded-proto', 'https')

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method || 'GET') ? undefined : await readBody(request),
      redirect: 'manual',
    })
    for (const name of ['cache-control', 'content-disposition', 'content-type', 'etag', 'last-modified']) {
      const value = upstream.headers.get(name)
      if (value) response.setHeader(name, value)
    }
    const cookies = upstream.headers.getSetCookie?.() || (upstream.headers.get('set-cookie') ? [upstream.headers.get('set-cookie')] : [])
    if (cookies.length) response.setHeader('set-cookie', cookies)
    response.status(upstream.status).send(Buffer.from(await upstream.arrayBuffer()))
  } catch {
    response.status(502).json({ error: { code: 'API_UNAVAILABLE', message: 'The Linda API could not be reached.' } })
  }
}
