import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export const getPortfolioSummary = () => api.get('/portfolio/summary')
export const getPositions = (platform = 'all', asset_type = 'all') => 
  api.get('/portfolio/positions', { params: { platform, asset_type } })
export const deletePosition = (id) => api.delete(`/portfolio/positions/${id}`)
export const clearPositions = (accountId) => api.post('/portfolio/positions/clear', null, { params: { account_id: accountId } })
export const refreshQuotes = () => api.post('/portfolio/refresh')

export const getAccounts = () => api.get('/accounts')
export const updateAccount = (id, data) => api.put(`/accounts/${id}`, data)
export const syncAccount = (id) => api.post(`/accounts/${id}/sync`)
export const syncAllAccounts = () => api.post('/accounts/sync-all')

export const getAlertRules = () => api.get('/alerts')
export const createAlertRule = (data) => api.post('/alerts', data)
export const deleteAlertRule = (id) => api.delete(`/alerts/${id}`)

export const getNotifications = () => api.get('/notifications')
export const updateNotification = (channel, data) => api.put(`/notifications/${channel}`, data)
export const testNotification = (channel) => api.post('/notifications/test', null, { params: { channel } })

export default api
