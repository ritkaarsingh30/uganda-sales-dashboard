import SectionLabel from '../components/SectionLabel.jsx'

const TEAM = [
  { id: 'MR_001', name: 'MBALANGU GEORGE',     territory: 'Kampala' },
  { id: 'MR_002', name: 'Aisha S',              territory: 'Kiruddu' },
  { id: 'MR_003', name: 'Simon Nduggu',         territory: 'Mengo'   },
  { id: 'MR_004', name: 'AKANKUNDA Rachelle',   territory: 'Mbarara' },
  { id: 'MR_005', name: 'Okodi Daniel',         territory: 'Kampala' },
  { id: 'MR_006', name: 'Sarvesh Mallah',       territory: 'Kampala' },
]

const PRODUCTS = [
  { id: 'P_001', name: 'Bio C',         category: 'TABLET', rate: '€2.00'  },
  { id: 'P_002', name: 'Bio CZN',       category: 'TABLET', rate: '€2.20'  },
  { id: 'P_003', name: 'CALD-K2',       category: 'TABLET', rate: '€4.00'  },
  { id: 'P_004', name: 'Bio Reno',      category: 'TABLET', rate: '€38.00' },
  { id: 'P_005', name: 'Bio Keton',     category: 'TABLET', rate: '€18.00' },
  { id: 'P_006', name: 'Bio Joints',    category: 'TABLET', rate: '€6.00'  },
  { id: 'P_007', name: 'Bio Man',       category: 'TABLET', rate: '€4.50'  },
  { id: 'P_008', name: 'Bio Vision',    category: 'TABLET', rate: '€3.75'  },
  { id: 'P_009', name: 'Bio Mega',      category: 'TABLET', rate: '€1.75'  },
  { id: 'P_010', name: 'Bio Neo',       category: 'TABLET', rate: '€2.25'  },
  { id: 'P_011', name: 'Bio Tic',       category: 'TABLET', rate: '€2.50'  },
  { id: 'P_012', name: 'Bio Mobi',      category: 'TABLET', rate: '€2.50'  },
  { id: 'P_013', name: 'Bio Prostate',  category: 'TABLET', rate: '€6.75'  },
  { id: 'P_014', name: 'Bio PEA Forte', category: 'TABLET', rate: '€8.00'  },
  { id: 'P_015', name: 'Curcumin 95',   category: 'TABLET', rate: '€18.00' },
  { id: 'P_016', name: 'CoQ10',         category: 'TABLET', rate: '€20.00' },
  { id: 'P_017', name: 'Bio Nerv',      category: 'TABLET', rate: '€4.00'  },
  { id: 'P_018', name: 'Bio Liver',     category: 'TABLET', rate: '€5.00'  },
  { id: 'P_019', name: 'BioMax HP',     category: 'TABLET', rate: '€24.00' },
  { id: 'P_020', name: 'Linazee-M 500', category: 'TABLET', rate: '€4.50'  },
  { id: 'P_021', name: 'Linazee-5',     category: 'TABLET', rate: '€4.00'  },
]

const TERRITORIES = [
  { id: 'ZONE_KAMPALA',  name: 'Kampala'  },
  { id: 'ZONE_KIRUDDU',  name: 'Kiruddu'  },
  { id: 'ZONE_MENGO',    name: 'Mengo'    },
  { id: 'ZONE_MBARARA',  name: 'Mbarara'  },
]

export default function NomenclatureTab() {
  return (
    <div>
      <SectionLabel tag="TEAM ROSTER" text="Medical Representatives" />
      <div className="tbl-card" style={{ marginBottom: 20 }}>
        <div className="tbl-scroll">
<table>
          <thead>
            <tr><th>MR ID</th><th>Name</th><th>Territory</th></tr>
          </thead>
          <tbody>
            {TEAM.map(mr => (
              <tr key={mr.id}>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>{mr.id}</td>
                <td>{mr.name}</td>
                <td><span className="badge n">{mr.territory}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
</div>
      </div>

      <SectionLabel tag="PRODUCT PORTFOLIO" text="21 Products (All Tablets)" />
      <div className="tbl-card" style={{ marginBottom: 20 }}>
        <div className="tbl-scroll">
<table>
          <thead>
            <tr><th>Product ID</th><th>Name</th><th>Category</th><th>Rate (EUR)</th></tr>
          </thead>
          <tbody>
            {PRODUCTS.map(p => (
              <tr key={p.id}>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--purple)' }}>{p.id}</td>
                <td>{p.name}</td>
                <td><span className="badge j">{p.category}</span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{p.rate}</td>
              </tr>
            ))}
          </tbody>
        </table>
</div>
      </div>

      <SectionLabel tag="TERRITORIES" text="Sales Zones" />
      <div className="tbl-card" style={{ marginBottom: 20 }}>
        <div className="tbl-scroll">
<table>
          <thead>
            <tr><th>Zone ID</th><th>Name</th></tr>
          </thead>
          <tbody>
            {TERRITORIES.map(t => (
              <tr key={t.id}>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--teal)' }}>{t.id}</td>
                <td>{t.name}</td>
              </tr>
            ))}
          </tbody>
        </table>
</div>
      </div>

      <SectionLabel tag="CURRENCY" text="Conversion Reference" />
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: '0.85rem', lineHeight: 2 }}>
          <div><strong>UGX → EUR:</strong> <span style={{ fontFamily: 'var(--font-mono)' }}>÷ 3,800</span></div>
          <div><strong>Budget figures:</strong> Activity budgets reported in UGX; expense amounts in USD (≈ EUR)</div>
          <div><strong>Sales figures:</strong> Already in EUR (Price × Units)</div>
        </div>
      </div>
    </div>
  )
}
