import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export const getDimensions = () =>
  http.get('/budget/dimensions').then((r) => r.data)

export const getAnalysis = (params) =>
  http.get('/budget/analysis', { params }).then((r) => r.data)

export const getImports = () => http.get('/budget/imports').then((r) => r.data)

export const getCompetitorDimensions = () =>
  http.get('/competitor/dimensions').then((r) => r.data)

export const getCompetitorCarriers = (params) =>
  http.get('/competitor/carriers', { params }).then((r) => r.data)

export const getCompetitorZones = (params) =>
  http.get('/competitor/zones', { params }).then((r) => r.data)

export const getCompetitorCompare = (params) =>
  http.get('/competitor/compare', { params }).then((r) => r.data)

export const importActual = (file, defaultYear) => {
  const fd = new FormData()
  fd.append('file', file)
  if (defaultYear) fd.append('default_year', defaultYear)
  return http.post('/budget/import/actual', fd).then((r) => r.data)
}

export const importWorkbook = (file, replace = true) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('replace', replace)
  return http.post('/budget/import/workbook', fd).then((r) => r.data)
}

export const importBudget = (file, caliber, year) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('caliber', caliber)
  fd.append('year', year)
  return http.post('/budget/import/budget', fd).then((r) => r.data)
}
