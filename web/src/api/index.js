import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export const getCompetitorDimensions = () =>
  http.get('/competitor/dimensions').then((r) => r.data)

export const getCompetitorCarriers = (params) =>
  http.get('/competitor/carriers', { params }).then((r) => r.data)

export const getCompetitorZones = (params) =>
  http.get('/competitor/zones', { params }).then((r) => r.data)

export const getCompetitorCompare = (params) =>
  http.get('/competitor/compare', { params }).then((r) => r.data)

// 目标成本
export const getCostLanes = (params) =>
  http.get('/cost/lanes', { params }).then((r) => r.data)
export const getCostTrend = (params) =>
  http.get('/cost/trend', { params }).then((r) => r.data)
export const getCostCurrent = (params) =>
  http.get('/cost/current', { params }).then((r) => r.data)
export const getCostLastPeriod = (params) =>
  http.get('/cost/last_period', { params }).then((r) => r.data)
export const saveCostBatch = (body) =>
  http.post('/cost/track/batch', body).then((r) => r.data)
export const deleteCostTrack = (tid) =>
  http.delete(`/cost/track/${tid}`).then((r) => r.data)
export const updateCostTrack = (tid, body) =>
  http.put(`/cost/track/${tid}`, body).then((r) => r.data)
export const saveCostLane = (body) =>
  http.post('/cost/lanes', body).then((r) => r.data)
export const updateCostLane = (id, body) =>
  http.put(`/cost/lanes/${id}`, body).then((r) => r.data)
