export const MONTH_CONFIG = {
  jan: { label: 'January',   short: 'Jan', cls: 'jan', color: 'var(--jan)', sectionCls: 'jan-s', prev: null,  monthNum: 1  },
  feb: { label: 'February',  short: 'Feb', cls: 'feb', color: 'var(--feb)', sectionCls: 'feb-s', prev: 'jan', monthNum: 2  },
  mar: { label: 'March',     short: 'Mar', cls: 'mar', color: 'var(--mar)', sectionCls: 'mar-s', prev: 'feb', monthNum: 3  },
  apr: { label: 'April',     short: 'Apr', cls: 'apr', color: 'var(--apr)', sectionCls: 'apr-s', prev: 'mar', monthNum: 4  },
  may: { label: 'May',       short: 'May', cls: 'may', color: 'var(--may)', sectionCls: 'may-s', prev: 'apr', monthNum: 5  },
  jun: { label: 'June',      short: 'Jun', cls: 'jun', color: 'var(--jun)', sectionCls: 'jun-s', prev: 'may', monthNum: 6  },
  jul: { label: 'July',      short: 'Jul', cls: 'jul', color: 'var(--jul)', sectionCls: 'jun-s', prev: 'jun', monthNum: 7  },
  aug: { label: 'August',    short: 'Aug', cls: 'aug', color: 'var(--aug)', sectionCls: 'aug-s', prev: 'jul', monthNum: 8  },
  sep: { label: 'September', short: 'Sep', cls: 'sep', color: 'var(--sep)', sectionCls: 'sep-s', prev: 'aug', monthNum: 9  },
  oct: { label: 'October',   short: 'Oct', cls: 'oct', color: 'var(--oct)', sectionCls: 'oct-s', prev: 'sep', monthNum: 10 },
  nov: { label: 'November',  short: 'Nov', cls: 'nov', color: 'var(--nov)', sectionCls: 'nov-s', prev: 'oct', monthNum: 11 },
  dec: { label: 'December',  short: 'Dec', cls: 'dec', color: 'var(--dec)', sectionCls: 'dec-s', prev: 'nov', monthNum: 12 },
}

export const MONTH_KEYS = Object.keys(MONTH_CONFIG)

export function calcChange(curr, prev) {
  if (!curr || !prev) return null
  return ((curr - prev) / prev) * 100
}

export function fmtChange(change) {
  if (change === null) return ''
  return change >= 0 ? `▲ +${change.toFixed(1)}%` : `▼ ${change.toFixed(1)}%`
}

export function changeDir(change) {
  if (change === null) return 'na'
  return change >= 0 ? 'up' : 'dn'
}

export const DELEGATE_COLS = [
  { key: 'name',          label: 'MR'          },
  { key: 'territory',     label: 'Territory'   },
  { key: 'total_calls',   label: 'Total Calls' },
  { key: 'prescriber',    label: 'Prescribers' },
  { key: 'pharmacy',      label: 'Pharmacy'    },
  { key: 'drs_converted', label: 'DRs Conv.'   },
  { key: 'days_worked',   label: 'Days'        },
  { key: 'avg_per_day',   label: 'Avg/Day'     },
  { key: 'orders_eur',    label: 'Orders (EUR)'},
  { key: 'ctc_eur',       label: 'CTC (USD)'   },
  { key: 'ctc_ratio',     label: 'CTC Ratio'   },
]
