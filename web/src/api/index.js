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
export const getCostLanes = (biz_type = '海运') =>
  http.get('/cost/lanes', { params: { biz_type } }).then((r) => r.data)
export const getCostTrend = (biz_type = '海运') =>
  http.get('/cost/trend', { params: { biz_type } }).then((r) => r.data)
export const getCostCurrent = (biz_type = '海运') =>
  http.get('/cost/current', { params: { biz_type } }).then((r) => r.data)
export const getCostLastPeriod = (biz_type = '海运') =>
  http.get('/cost/last_period', { params: { biz_type } }).then((r) => r.data)
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
