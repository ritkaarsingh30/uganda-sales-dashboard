import axios from 'axios'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const BASE = import.meta.env.VITE_API_URL || '/api'
const get  = url => axios.get(BASE + url).then(r => r.data)
const post = url => axios.post(BASE + url).then(r => r.data)

export const useAvailableMonths = () =>
  useQuery({ queryKey: ['health'], queryFn: () => get('/health'), staleTime: 60000,
    select: d => d.months_loaded || [] })

export const useOverview   = () => useQuery({ queryKey: ['overview'],   queryFn: () => get('/overview')   })
export const useProducts   = () => useQuery({ queryKey: ['products'],   queryFn: () => get('/products')   })
export const useDelegates  = () => useQuery({ queryKey: ['delegates'],  queryFn: () => get('/delegates')  })
export const useExpenses   = () => useQuery({ queryKey: ['expenses'],   queryFn: () => get('/expenses')   })
export const useActivities = () => useQuery({ queryKey: ['activities'], queryFn: () => get('/activities') })
export const useInsights          = () => useQuery({ queryKey: ['insights'],            queryFn: () => get('/insights')            })
export const useDelegateInsights  = () => useQuery({ queryKey: ['insights','delegates'], queryFn: () => get('/insights/delegates')  })
export const useActivityInsights  = () => useQuery({ queryKey: ['insights','activities'],queryFn: () => get('/insights/activities') })
export const useMonth      = m  => useQuery({ queryKey: ['month', m],   queryFn: () => get(`/months/${m}`), enabled: !!m })

export function useRefreshData() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => post('/data/refresh'),
    onSuccess:  () => qc.invalidateQueries(),
  })
}

export function useRefreshInsights() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => post('/insights/refresh'),
    onSuccess: d => qc.setQueryData(['insights'], d),
  })
}

export function useRefreshDelegateInsights() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => post('/insights/delegates/refresh'),
    onSuccess: d => qc.setQueryData(['insights', 'delegates'], d),
  })
}

export function useRefreshActivityInsights() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => post('/insights/activities/refresh'),
    onSuccess: d => qc.setQueryData(['insights', 'activities'], d),
  })
}
