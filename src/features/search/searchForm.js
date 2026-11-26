// Owner: Ali. Pure helpers for the search form (no React).
export const MAX_WINDOW_HOURS = 48   // the API accepts a window of at most 48 hours

const pad = (n) => String(n).padStart(2, '0')
// value for <input type="datetime-local"> (browser local time)
export const toLocalInput = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
export function defaultWindow(now = new Date()) {
  return { departAfter: toLocalInput(new Date(now.getTime() + 30 * 60000)), departBefore: toLocalInput(new Date(now.getTime() + 4 * 3600000)) }
}

export function validateSearch(v, routeInfo) {
  const e = {}
  if (!routeInfo?.route) e.route = 'Draw your route on the map first.'
  const a = new Date(v.departAfter).getTime(), b = new Date(v.departBefore).getTime()
  if (Number.isNaN(a)) e.departAfter = 'Choose the earliest departure time.'
  if (Number.isNaN(b)) e.departBefore = 'Choose the latest departure time.'
  if (!e.departAfter && !e.departBefore) {
    if (b <= a) e.departBefore = 'The latest time must be after the earliest time.'
    else if (b - a > MAX_WINDOW_HOURS * 3600000) e.departBefore = `The window can be at most ${MAX_WINDOW_HOURS} hours.`
  }
  return e
}

export const buildSearchBody = (v, route) => ({
  route,
  depart_after: new Date(v.departAfter).toISOString(),
  depart_before: new Date(v.departBefore).toISOString(),
  limit: 20,
})
