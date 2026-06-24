export const COLORS = {
  jan: { solid: '#fb923c', alpha: 'rgba(251,146,60,0.78)',  soft: 'rgba(251,146,60,0.14)'  },
  feb: { solid: '#a78bfa', alpha: 'rgba(167,139,250,0.78)', soft: 'rgba(167,139,250,0.14)' },
  mar: { solid: '#38bdf8', alpha: 'rgba(56,189,248,0.78)',  soft: 'rgba(56,189,248,0.14)'  },
  apr: { solid: '#7c3aed', alpha: 'rgba(124,58,237,0.78)',  soft: 'rgba(124,58,237,0.14)'  },
  may: { solid: '#14b8a6', alpha: 'rgba(20,184,166,0.78)',  soft: 'rgba(20,184,166,0.14)'  },
  jun: { solid: '#f59e0b', alpha: 'rgba(245,158,11,0.78)',  soft: 'rgba(245,158,11,0.14)'  },
  jul: { solid: '#ec4899', alpha: 'rgba(236,72,153,0.78)',  soft: 'rgba(236,72,153,0.14)'  },
  aug: { solid: '#f43f5e', alpha: 'rgba(244,63,94,0.78)',   soft: 'rgba(244,63,94,0.14)'   },
  sep: { solid: '#06b6d4', alpha: 'rgba(6,182,212,0.78)',   soft: 'rgba(6,182,212,0.14)'   },
  oct: { solid: '#eab308', alpha: 'rgba(234,179,8,0.78)',   soft: 'rgba(234,179,8,0.14)'   },
  nov: { solid: '#60a5fa', alpha: 'rgba(96,165,250,0.78)',  soft: 'rgba(96,165,250,0.14)'  },
  dec: { solid: '#34d399', alpha: 'rgba(52,211,153,0.78)',  soft: 'rgba(52,211,153,0.14)'  },
  danger:  { solid: '#f43f5e', alpha: 'rgba(244,63,94,0.78)',   soft: 'rgba(244,63,94,0.14)'   },
  good:    { solid: '#22c55e', alpha: 'rgba(34,197,94,0.78)',   soft: 'rgba(34,197,94,0.14)'   },
  warn:    { solid: '#f59e0b', alpha: 'rgba(245,158,11,0.78)',  soft: 'rgba(245,158,11,0.14)'  },
  neutral: { solid: '#a39ec2', alpha: 'rgba(163,158,194,0.55)', soft: 'rgba(163,158,194,0.14)' },
}

export const PALETTE = [
  '#7c3aed', '#14b8a6', '#f59e0b', '#ec4899',
  '#38bdf8', '#22c55e', '#a78bfa', '#f43f5e',
  '#2dd4bf', '#fbbf24', '#fb923c', '#60a5fa',
]

export function monthColor(key) {
  return COLORS[key] || COLORS.neutral
}

// Vertical canvas gradient — use as a dataset.backgroundColor function for area/bar fills.
export function gradientFill(hexOrRgba, alphaTop = 0.45, alphaBottom = 0.02) {
  return (context) => {
    const { chart } = context
    const { ctx, chartArea } = chart
    if (!chartArea) return 'transparent'
    const toRgba = (a) => {
      if (hexOrRgba.startsWith('#')) {
        const r = parseInt(hexOrRgba.slice(1, 3), 16)
        const g = parseInt(hexOrRgba.slice(3, 5), 16)
        const b = parseInt(hexOrRgba.slice(5, 7), 16)
        return `rgba(${r},${g},${b},${a})`
      }
      return hexOrRgba.replace(/[\d.]+\)$/, `${a})`)
    }
    const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
    gradient.addColorStop(0, toRgba(alphaTop))
    gradient.addColorStop(1, toRgba(alphaBottom))
    return gradient
  }
}

export function baseOptions(overrides = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend:  { labels: { color: '#7b7396', font: { size: 11, family: "'Inter', sans-serif" }, usePointStyle: true, pointStyle: 'circle', boxWidth: 7, boxHeight: 7 } },
      tooltip: {
        backgroundColor: '#1f1740',
        titleColor: '#ffffff',
        titleFont: { weight: '700' },
        bodyColor: '#d8d2f5',
        borderColor: 'rgba(124,58,237,0.35)',
        borderWidth: 1,
        cornerRadius: 10,
        padding: 11,
        displayColors: true,
        boxPadding: 4,
      },
    },
    scales: {
      x: { ticks: { color: '#9d96bb', font: { size: 11 } }, grid: { color: 'rgba(124,58,237,0.07)' }, border: { display: false } },
      y: { ticks: { color: '#9d96bb', font: { size: 11 } }, grid: { color: 'rgba(124,58,237,0.07)' }, border: { display: false } },
    },
    ...overrides,
  }
}

export function baseOptionsNoScale(overrides = {}) {
  const opts = baseOptions(overrides)
  delete opts.scales
  return opts
}
