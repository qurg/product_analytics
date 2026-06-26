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
