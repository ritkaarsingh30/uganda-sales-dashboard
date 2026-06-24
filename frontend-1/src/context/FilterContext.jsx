import { createContext, useContext, useState, useEffect } from 'react'

const FilterContext = createContext(null)

export function FilterProvider({ children, availableMonths }) {
  const [selectedMonths, setSelectedMonths] = useState(null)

  useEffect(() => { setSelectedMonths(null) }, [availableMonths])

  const activeMonths = selectedMonths === null
    ? availableMonths
    : availableMonths.filter(m => selectedMonths.has(m))

  function toggleMonth(month) {
    setSelectedMonths(prev => {
      const next = new Set(prev || availableMonths)
      next.has(month) ? next.delete(month) : next.add(month)
      if (next.size === 0 || next.size === availableMonths.length) return null
      return next
    })
  }

  function setPreset(months) {
    const valid = months.filter(m => availableMonths.includes(m))
    if (valid.length === 0 || valid.length === availableMonths.length) {
      setSelectedMonths(null)
    } else {
      setSelectedMonths(new Set(valid))
    }
  }

  function clearFilter() { setSelectedMonths(null) }

  function isMonthSelected(month) {
    return selectedMonths === null || selectedMonths.has(month)
  }

  return (
    <FilterContext.Provider value={{
      selectedMonths, activeMonths, isFiltered: selectedMonths !== null,
      toggleMonth, setPreset, clearFilter, isMonthSelected,
    }}>
      {children}
    </FilterContext.Provider>
  )
}

export function useFilter() {
  return useContext(FilterContext)
}
