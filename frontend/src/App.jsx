import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import axios from 'axios'
import {
  Activity,
  AlertCircle,
  ArrowDownToLine,
  Check,
  ChevronDown,
  CircleHelp,
  FilePlus2,
  FileText,
  Filter,
  Fingerprint,
  Focus,
  LoaderCircle,
  MapPin,
  Network,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  UserRound,
  X,
} from 'lucide-react'
import './App.css'

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')
const API_BASE = `${API_ORIGIN}/api/v1`
const DEFAULT_CASE_ID = 'CASE_2026_094'
const ENTITY_STYLES = {
  CrimeCase: { color: '#e1a75a', icon: Fingerprint },
  Person: { color: '#ee7e75', icon: UserRound },
  Phone: { color: '#74a9e8', icon: Radio },
  Location: { color: '#61c2a5', icon: MapPin },
  IPAddress: { color: '#b294e2', icon: Network },
  EvidenceFile: { color: '#d093c6', icon: FileText },
}
const DEFAULT_TRAFFIC = {
  src_ip: '192.168.1.188',
  dst_ip: '198.51.100.22',
  duration: 0.05,
  src_bytes: 96,
  dst_bytes: 80,
  src_pkts: 2,
  dst_pkts: 1,
  is_tcp: 1,
  is_udp: 0,
  is_icmp: 0,
  is_common_port: 0,
  inter_arrival_time: 4.82,
  syn_count: 1,
  fin_count: 0,
  rst_count: 0,
}
const DEFAULT_FILE = {
  file_name: 'recovered_drive_dump.bin',
  hex_content: '4d 5a 90 00 03 00 00 00 04 00 00 00 ff ff 00 00 b8 00 00 00',
}

function messageFromError(error) {
  return error.response?.data?.detail || error.message || 'The request could not be completed.'
}

export default function App() {
  const graphContainer = useRef(null)
  const cyInstance = useRef(null)
  const activeCaseRef = useRef(DEFAULT_CASE_ID)
  const [cases, setCases] = useState([])
  const [caseId, setCaseId] = useState(DEFAULT_CASE_ID)
  const [graph, setGraph] = useState({ nodes: [], edges: [] })
  const [selectedNode, setSelectedNode] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [visibleTypes, setVisibleTypes] = useState(Object.keys(ENTITY_STYLES))
  const [showIngest, setShowIngest] = useState(false)
  const [showNewCase, setShowNewCase] = useState(false)
  const [activeTab, setActiveTab] = useState('narrative')
  const [narrative, setNarrative] = useState(
    'Suspect Elena Rostova contacted operative at +44 7933 112233 near Heathrow Airport. Host 198.51.100.99 initiated high-volume encrypted transmission.',
  )
  const [traffic, setTraffic] = useState(DEFAULT_TRAFFIC)
  const [fileEvidence, setFileEvidence] = useState(DEFAULT_FILE)
  const [caseForm, setCaseForm] = useState({ case_id: '', title: '', description: '' })
  const [busyAction, setBusyAction] = useState('')
  const [result, setResult] = useState(null)
  const [notice, setNotice] = useState('')

  const activeCase = cases.find((item) => item.case_id === caseId)
  const nodeCounts = useMemo(() => {
    const counts = {}
    graph.nodes.forEach((node) => {
      counts[node.type] = (counts[node.type] || 0) + 1
    })
    return counts
  }, [graph.nodes])

  const refreshGraph = useCallback(async (targetCase = caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${encodeURIComponent(targetCase)}/graph`)
    if (activeCaseRef.current !== targetCase) return
    setGraph(response.data)
    setSelectedNode((current) => response.data.nodes.find((node) => node.id === current?.id) || null)
  }, [caseId])

  const refreshCases = useCallback(async () => {
    const response = await axios.get(`${API_BASE}/cases`)
    setCases(response.data.cases)
    if (!response.data.cases.some((item) => item.case_id === caseId) && response.data.cases[0]) {
      activeCaseRef.current = response.data.cases[0].case_id
      setCaseId(response.data.cases[0].case_id)
    }
  }, [caseId])

  const refreshHealth = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/health`)
      setHealth(response.data)
    } catch {
      setHealth(null)
    }
  }, [])

  useEffect(() => {
    const cy = cytoscape({
      container: graphContainer.current,
      minZoom: 0.25,
      maxZoom: 2.5,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': '#64748b',
            color: '#e6edf4',
            'font-size': 10,
            'font-weight': 500,
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 9,
            'text-wrap': 'wrap',
            'text-max-width': 115,
            width: 34,
            height: 34,
            'border-width': 1.5,
            'border-color': '#152033',
            'overlay-opacity': 0,
          },
        },
        ...Object.entries(ENTITY_STYLES).map(([type, style]) => ({
          selector: `node[type = "${type}"]`,
          style: { 'background-color': style.color, 'border-color': '#f0f4f8', 'border-width': 1.5 },
        })),
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#526176',
            'target-arrow-color': '#526176',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(relation)',
            color: '#94a3b8',
            'font-size': 7,
            'text-rotation': 'autorotate',
            'text-background-color': '#0b111c',
            'text-background-opacity': 0.9,
            'text-background-padding': 2,
            'overlay-opacity': 0,
          },
        },
        {
          selector: 'edge[relation *= "MALICIOUS"]',
          style: { 'line-color': '#ed766f', 'target-arrow-color': '#ed766f', width: 2.5, 'line-style': 'dashed' },
        },
        {
          selector: ':selected',
          style: { 'border-color': '#fff', 'border-width': 3, 'overlay-color': '#fff', 'overlay-opacity': 0.12 },
        },
        {
          selector: '.filtered-out',
          style: { display: 'none' },
        },
      ],
      layout: { name: 'cose', animate: true, padding: 60, nodeRepulsion: 400000, idealEdgeLength: 110 },
    })
    cy.on('tap', 'node', (event) => setSelectedNode(event.target.data()))
    cy.on('tap', (event) => {
      if (event.target === cy) setSelectedNode(null)
    })
    cyInstance.current = cy
    return () => {
      cy.destroy()
      cyInstance.current = null
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const initialize = async () => {
      try {
        const [casesResponse, healthResponse] = await Promise.all([
          axios.get(`${API_BASE}/cases`),
          axios.get(`${API_BASE}/health`).catch(() => null),
        ])
        if (cancelled) return
        const availableCases = casesResponse.data.cases
        setCases(availableCases)
        setHealth(healthResponse?.data || null)
        const initialCase = availableCases.some((item) => item.case_id === DEFAULT_CASE_ID)
          ? DEFAULT_CASE_ID
          : availableCases[0]?.case_id
        if (initialCase) {
          activeCaseRef.current = initialCase
          if (initialCase !== DEFAULT_CASE_ID) setCaseId(initialCase)
          const graphResponse = await axios.get(`${API_BASE}/cases/${encodeURIComponent(initialCase)}/graph`)
          if (!cancelled && activeCaseRef.current === initialCase) setGraph(graphResponse.data)
        }
      } catch (loadError) {
        if (!cancelled) setError(messageFromError(loadError))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    initialize()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    const cy = cyInstance.current
    if (!cy) return
    cy.elements().remove()
    const nodes = graph.nodes.map((node) => ({
      data: { ...node, properties: node.properties || {} },
    }))
    const edges = graph.edges
      .filter((edge) => graph.nodes.some((node) => node.id === edge.source) && graph.nodes.some((node) => node.id === edge.target))
      .map((edge) => ({ data: { ...edge, id: edge.id || `${edge.source}-${edge.target}-${edge.relation}` } }))
    cy.add([...nodes, ...edges])
    if (nodes.length) cy.layout({ name: 'cose', animate: true, padding: 60, nodeRepulsion: 400000, idealEdgeLength: 110 }).run()
  }, [graph])

  useEffect(() => {
    const cy = cyInstance.current
    if (!cy) return
    const term = search.trim().toLowerCase()
    cy.nodes().forEach((node) => {
      const searchable = `${node.data('label')} ${node.data('type')} ${node.data('id')}`.toLowerCase()
      const shouldShow = visibleTypes.includes(node.data('type')) && (!term || searchable.includes(term))
      node.toggleClass('filtered-out', !shouldShow)
    })
    cy.edges().forEach((edge) => {
      const shouldShow = !edge.source().hasClass('filtered-out') && !edge.target().hasClass('filtered-out')
      edge.toggleClass('filtered-out', !shouldShow)
    })
  }, [search, visibleTypes, graph])

  const reload = async () => {
    setLoading(true)
    setError('')
    try {
      await Promise.all([refreshGraph(), refreshCases()])
      await refreshHealth()
    } catch (loadError) {
      setError(messageFromError(loadError))
    } finally {
      setLoading(false)
    }
  }

  const showError = (loadError) => setError(messageFromError(loadError))
  const submitIngestion = async (kind) => {
    setBusyAction(kind)
    setError('')
    setNotice('')
    setResult(null)
    try {
      let response
      if (kind === 'narrative') {
        response = await axios.post(`${API_BASE}/cases/extract-narrative`, {
          case_id: caseId,
          case_title: activeCase?.title || caseId,
          narrative_text: narrative,
        })
      } else if (kind === 'traffic') {
        response = await axios.post(`${API_BASE}/models/botnet/predict`, { ...traffic, case_id: caseId })
      } else {
        response = await axios.post(`${API_BASE}/models/file-classifier/predict`, { ...fileEvidence, case_id: caseId })
      }
      setResult(response.data)
      setNotice('Analysis complete. The case graph has been updated.')
      await Promise.all([refreshGraph(), refreshCases()])
    } catch (submitError) {
      showError(submitError)
    } finally {
      setBusyAction('')
    }
  }

  const submitNewCase = async (event) => {
    event.preventDefault()
    setBusyAction('case')
    setError('')
    try {
      const response = await axios.post(`${API_BASE}/cases`, caseForm)
      await refreshCases()
      activeCaseRef.current = response.data.case_id
      setCaseId(response.data.case_id)
      await refreshGraph(response.data.case_id)
      setShowNewCase(false)
      setCaseForm({ case_id: '', title: '', description: '' })
    } catch (submitError) {
      showError(submitError)
    } finally {
      setBusyAction('')
    }
  }

  const exportCase = () => {
    const payload = { case: activeCase, graph }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const downloadUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = `${caseId}-graph.json`
    link.click()
    URL.revokeObjectURL(downloadUrl)
  }

  const toggleType = (type) => {
    setVisibleTypes((current) => current.includes(type)
      ? current.filter((item) => item !== type)
      : [...current, type])
  }

  const connectedEdges = selectedNode
    ? graph.edges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id)
    : []

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Fingerprint size={19} /></div>
          <div>
            <div className="brand-name">Crime<span>Graph</span></div>
            <div className="brand-caption">AI INVESTIGATION WORKSPACE</div>
          </div>
        </div>
        <div className="case-switcher">
          <span className="case-label">ACTIVE CASE</span>
          <label className="select-wrap">
            <select value={caseId} onChange={async (event) => {
              const selectedCase = event.target.value
              activeCaseRef.current = selectedCase
              setCaseId(selectedCase)
              setLoading(true)
              setError('')
              try {
                await refreshGraph(selectedCase)
              } catch (loadError) {
                setError(messageFromError(loadError))
              } finally {
                if (activeCaseRef.current === selectedCase) setLoading(false)
              }
            }} aria-label="Active case">
              {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.title}</option>)}
            </select>
            <ChevronDown size={14} />
          </label>
          <button className="icon-button add-case-button" onClick={() => setShowNewCase(true)} title="Create case" aria-label="Create case"><Plus size={16} /></button>
        </div>
        <div className="top-actions">
          <div className={`connection-pill ${health ? 'is-online' : 'is-offline'}`}>
            <span className="status-dot" />
            {health ? 'API connected' : 'API unavailable'}
          </div>
          <button className="button button-quiet" onClick={reload} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
          </button>
          <button className="button button-quiet export-button" onClick={exportCase} disabled={!graph.nodes.length}>
            <ArrowDownToLine size={15} /> Export
          </button>
          <button className="button button-primary" onClick={() => { setError(''); setNotice(''); setResult(null); setShowIngest(true) }}>
            <FilePlus2 size={16} /> Add evidence
          </button>
        </div>
      </header>

      <section className="case-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> CASE OVERVIEW <span className="case-id">{caseId}</span></div>
          <h1>{activeCase?.title || 'Investigation workspace'}</h1>
          <p>{activeCase?.description || 'Review linked entities and evidence across this investigation.'}</p>
        </div>
        <div className="case-status"><span className="status-dot" /> {activeCase?.status || 'ACTIVE'} <span className="status-divider" /> UPDATED LIVE</div>
      </section>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={17} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={15} /></button>
        </div>
      )}
      {notice && (
        <div className="alert alert-success" role="status">
          <Check size={16} /><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss message"><X size={15} /></button>
        </div>
      )}

      <section className="metrics-row" aria-label="Case graph summary">
        <Metric icon={Network} label="Graph entities" value={graph.nodes.length} helper="Unique linked records" />
        <Metric icon={Activity} label="Relationships" value={graph.edges.length} helper="Observed connections" />
        <Metric icon={UserRound} label="People" value={nodeCounts.Person || 0} helper="Named person records" />
        <Metric icon={ShieldAlert} label="Evidence files" value={nodeCounts.EvidenceFile || 0} helper="Classified artifacts" />
        <div className="engine-status">
          <div className="engine-icon"><Shield size={17} /></div>
          <div><strong>Analysis engines</strong><span>{health?.models_ready ? Object.values(health.models_ready).filter(Boolean).length : 0} of 3 ready</span></div>
          <span className={`engine-dot ${health?.models_ready?.botnet_cnn_lstm && health?.models_ready?.file_classifier_mlp ? 'ready' : ''}`} />
        </div>
      </section>

      <section className="main-grid">
        <div className="graph-panel">
          <div className="panel-toolbar">
            <div className="panel-heading">
              <span className="panel-kicker">RELATIONSHIP MAP</span>
              <span className="panel-count">{graph.nodes.length} entities <i /> {graph.edges.length} links</span>
            </div>
            <div className="graph-tools">
              <label className="search-box">
                <Search size={15} />
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find entity..." aria-label="Search entities" />
                {search && <button onClick={() => setSearch('')} aria-label="Clear search"><X size={13} /></button>}
              </label>
              <button className="icon-button" onClick={() => cyInstance.current?.fit(undefined, 50)} title="Fit graph" aria-label="Fit graph"><Focus size={16} /></button>
            </div>
          </div>
          <div className={`graph-canvas ${loading ? 'is-loading' : ''}`}>
            <div className="graph-grid" />
            <div className="graph-wash" />
            <div className="graph-container" ref={graphContainer} />
            {loading && <div className="graph-loading"><LoaderCircle className="spin" size={20} /> Loading case graph</div>}
            {!loading && graph.nodes.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon"><Network size={22} /></div>
                <strong>No entities yet</strong>
                <span>Add case notes or evidence to start connecting information.</span>
                <button className="button button-primary" onClick={() => setShowIngest(true)}><Plus size={15} /> Add first evidence</button>
              </div>
            )}
            <div className="graph-note"><CircleHelp size={13} /> Select an entity to inspect its connections</div>
            <div className="graph-zoom">
              <button onClick={() => cyInstance.current?.zoom(cyInstance.current.zoom() * 1.15)} aria-label="Zoom in">+</button>
              <button onClick={() => cyInstance.current?.zoom(cyInstance.current.zoom() / 1.15)} aria-label="Zoom out">−</button>
            </div>
          </div>
          <div className="legend-bar">
            <div className="legend-title"><Filter size={13} /> FILTER</div>
            {Object.entries(ENTITY_STYLES).map(([type, style]) => (
              <button key={type} className={`legend-item ${visibleTypes.includes(type) ? 'active' : ''}`} onClick={() => toggleType(type)}>
                <span className="legend-dot" style={{ background: style.color }} />{type === 'IPAddress' ? 'IP address' : type === 'EvidenceFile' ? 'Evidence' : type === 'CrimeCase' ? 'Case' : type}
              </button>
            ))}
          </div>
        </div>

        <aside className="details-panel">
          <div className="details-heading">
            <div><span className="panel-kicker">{selectedNode ? 'ENTITY RECORD' : 'CASE FILE'}</span><h2>{selectedNode ? 'Entity details' : 'Investigation details'}</h2></div>
            {selectedNode && <button className="icon-button" onClick={() => { setSelectedNode(null); cyInstance.current?.elements().unselect() }} aria-label="Clear selection"><X size={15} /></button>}
          </div>
          {selectedNode ? (
            <div className="entity-details">
              <div className="entity-card">
                <div className="entity-type-icon" style={{ color: ENTITY_STYLES[selectedNode.type]?.color || '#94a3b8' }}>
                  {(() => { const Icon = ENTITY_STYLES[selectedNode.type]?.icon || Network; return <Icon size={19} /> })()}
                </div>
                <span className="entity-type">{selectedNode.type}</span>
                <h3>{selectedNode.label}</h3>
                <span className="entity-id">{selectedNode.id}</span>
              </div>
              <div className="detail-section">
                <div className="section-title">RECORDED ATTRIBUTES <span>{Object.keys(selectedNode.properties || {}).length}</span></div>
                {Object.entries(selectedNode.properties || {}).length ? (
                  <div className="property-list">
                    {Object.entries(selectedNode.properties || {}).map(([key, value]) => (
                      <div className="property-row" key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</strong></div>
                    ))}
                  </div>
                ) : <div className="muted-copy">No additional attributes recorded.</div>}
              </div>
              <div className="detail-section">
                <div className="section-title">DIRECT CONNECTIONS <span>{connectedEdges.length}</span></div>
                {connectedEdges.length ? (
                  <div className="connection-list">
                    {connectedEdges.map((edge) => {
                      const other = graph.nodes.find((node) => node.id === (edge.source === selectedNode.id ? edge.target : edge.source))
                      return <div className="connection-row" key={edge.id}><span className="connection-dot" style={{ background: ENTITY_STYLES[other?.type]?.color || '#718096' }} /><div><strong>{other?.label || edge.target}</strong><span>{edge.relation.replaceAll('_', ' ').toLowerCase()}</span></div><small>{Math.round((edge.confidence ?? 1) * 100)}%</small></div>
                    })}
                  </div>
                ) : <div className="muted-copy">No linked records yet.</div>}
              </div>
            </div>
          ) : (
            <>
              <div className="case-card">
                <div className="case-card-top"><div className="case-symbol"><Fingerprint size={19} /></div><span className="case-tag">OPEN</span></div>
                <h3>{activeCase?.title || caseId}</h3>
                <p>{activeCase?.description || 'No case description has been added.'}</p>
                <div className="case-card-id">{caseId}</div>
              </div>
              <div className="detail-section">
                <div className="section-title">ENTITY BREAKDOWN</div>
                <div className="breakdown-list">
                  {Object.entries(ENTITY_STYLES).map(([type, style]) => {
                    const Icon = style.icon
                    return <div className="breakdown-row" key={type}><span className="breakdown-kind"><Icon size={14} style={{ color: style.color }} />{type === 'EvidenceFile' ? 'Evidence' : type === 'IPAddress' ? 'IP addresses' : type === 'CrimeCase' ? 'Cases' : `${type}s`}</span><strong>{nodeCounts[type] || 0}</strong></div>
                  })}
                </div>
              </div>
              <div className="integrity-note"><Shield size={15} /><p><strong>Investigation support only</strong><br />Connections are leads for human review, not findings of guilt.</p></div>
            </>
          )}
          <div className="engine-card">
            <div className="section-title">AVAILABLE ANALYSIS</div>
            <EngineRow label="Narrative extraction" ready={health?.models_ready?.narrative_extractor} detail={health?.narrative_extractor_mode || 'Checking service'} />
            <EngineRow label="Traffic classifier" ready={health?.models_ready?.botnet_cnn_lstm} detail="CNN + LSTM" />
            <EngineRow label="File classifier" ready={health?.models_ready?.file_classifier_mlp} detail="TF-IDF + MLP" />
          </div>
        </aside>
      </section>
      <footer className="footer"><span>CRIME<span className="footer-accent">GRAPH AI</span> <i /> DIGITAL INVESTIGATION SUPPORT</span><span>{health?.database_mode || 'Waiting for API'} <i /> Local workspace</span></footer>

      {showIngest && (
        <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowIngest(false) }}>
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="ingest-title">
            <div className="modal-header">
              <div><span className="panel-kicker">CASE INTAKE</span><h2 id="ingest-title">Add evidence</h2></div>
              <button className="icon-button" onClick={() => setShowIngest(false)} aria-label="Close"><X size={17} /></button>
            </div>
            <div className="modal-tabs">
              <TabButton active={activeTab === 'narrative'} onClick={() => setActiveTab('narrative')} icon={FileText}>Case notes</TabButton>
              <TabButton active={activeTab === 'traffic'} onClick={() => setActiveTab('traffic')} icon={Radio}>Network flow</TabButton>
              <TabButton active={activeTab === 'file'} onClick={() => setActiveTab('file')} icon={ShieldAlert}>File bytes</TabButton>
            </div>
            {activeTab === 'narrative' && (
              <div className="form-content">
                <div className="form-description">Extract people, contact details, locations and network indicators from investigator notes. Add leads, not conclusions.</div>
                <label className="field-label" htmlFor="narrative">Narrative text <span>Required</span></label>
                <textarea id="narrative" className="text-field narrative-field" value={narrative} onChange={(event) => setNarrative(event.target.value)} placeholder="Paste case notes or a report excerpt..." maxLength={20000} />
                <div className="field-footnote">{narrative.length} / 20,000 characters · Uses {health?.narrative_extractor_mode || 'local extraction'}.</div>
              </div>
            )}
            {activeTab === 'traffic' && (
              <div className="form-content">
                <div className="form-description">Run a trained flow classifier on a single network record. The submitted flow is added to this case graph.</div>
                <div className="form-grid">
                  <FormField label="Source IP" value={traffic.src_ip} onChange={(value) => setTraffic({ ...traffic, src_ip: value })} />
                  <FormField label="Destination IP" value={traffic.dst_ip} onChange={(value) => setTraffic({ ...traffic, dst_ip: value })} />
                  <FormField label="Duration (seconds)" type="number" min="0" step="any" value={traffic.duration} onChange={(value) => setTraffic({ ...traffic, duration: Number(value) })} />
                  <FormField label="Source bytes" type="number" min="0" value={traffic.src_bytes} onChange={(value) => setTraffic({ ...traffic, src_bytes: Number(value) })} />
                  <FormField label="Destination bytes" type="number" min="0" value={traffic.dst_bytes} onChange={(value) => setTraffic({ ...traffic, dst_bytes: Number(value) })} />
                  <FormField label="Source packets" type="number" min="0" value={traffic.src_pkts} onChange={(value) => setTraffic({ ...traffic, src_pkts: Number(value) })} />
                  <FormField label="Destination packets" type="number" min="0" value={traffic.dst_pkts} onChange={(value) => setTraffic({ ...traffic, dst_pkts: Number(value) })} />
                  <label className="field-label">Protocol
                    <select className="text-input" value={traffic.is_tcp ? 'tcp' : traffic.is_udp ? 'udp' : 'icmp'} onChange={(event) => setTraffic({ ...traffic, is_tcp: Number(event.target.value === 'tcp'), is_udp: Number(event.target.value === 'udp'), is_icmp: Number(event.target.value === 'icmp') })}>
                      <option value="tcp">TCP</option><option value="udp">UDP</option><option value="icmp">ICMP</option>
                    </select>
                  </label>
                  <FormField label="Inter-arrival time" type="number" min="0" step="any" value={traffic.inter_arrival_time} onChange={(value) => setTraffic({ ...traffic, inter_arrival_time: Number(value) })} />
                  <FormField label="SYN count" type="number" min="0" value={traffic.syn_count} onChange={(value) => setTraffic({ ...traffic, syn_count: Number(value) })} />
                  <FormField label="FIN count" type="number" min="0" value={traffic.fin_count} onChange={(value) => setTraffic({ ...traffic, fin_count: Number(value) })} />
                  <FormField label="RST count" type="number" min="0" value={traffic.rst_count} onChange={(value) => setTraffic({ ...traffic, rst_count: Number(value) })} />
                  <label className="toggle-field"><input type="checkbox" checked={Boolean(traffic.is_common_port)} onChange={(event) => setTraffic({ ...traffic, is_common_port: Number(event.target.checked) })} /> Common destination port</label>
                </div>
              </div>
            )}
            {activeTab === 'file' && (
              <div className="form-content">
                <div className="form-description">Classify a hexadecimal byte sample. Bytes are sent to the local API for inference and are not stored; only the classification is attached to the graph.</div>
                <FormField label="Evidence file name" value={fileEvidence.file_name} onChange={(value) => setFileEvidence({ ...fileEvidence, file_name: value })} />
                <label className="field-label" htmlFor="hex-content">Hexadecimal bytes <span>Space separated</span></label>
                <textarea id="hex-content" className="text-field hex-field" value={fileEvidence.hex_content} onChange={(event) => setFileEvidence({ ...fileEvidence, hex_content: event.target.value })} placeholder="4d 5a 90 00 ..." maxLength={20000} />
                <div className="field-footnote">Paste a small header/sample as space-separated hex (max 10 KB).</div>
              </div>
            )}
            {error && <div className="modal-error"><AlertCircle size={15} />{error}</div>}
            {notice && <div className="modal-success"><Check size={15} />{notice}</div>}
            {result && <ResultCard kind={activeTab} result={result} />}
            <div className="modal-actions">
              <button className="button button-quiet" onClick={() => setShowIngest(false)}>Close</button>
              <button className="button button-primary" onClick={() => submitIngestion(activeTab)} disabled={Boolean(busyAction) || (activeTab === 'narrative' && narrative.trim().length < 10) || (activeTab === 'file' && !fileEvidence.hex_content.trim())}>
                {busyAction ? <LoaderCircle className="spin" size={15} /> : <Activity size={15} />}
                {busyAction ? 'Analyzing...' : activeTab === 'narrative' ? 'Extract entities' : activeTab === 'traffic' ? 'Classify flow' : 'Classify file'}
              </button>
            </div>
          </section>
        </div>
      )}

      {showNewCase && (
        <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowNewCase(false) }}>
          <form className="modal new-case-modal" onSubmit={submitNewCase} role="dialog" aria-modal="true" aria-labelledby="new-case-title">
            <div className="modal-header"><div><span className="panel-kicker">WORKSPACE</span><h2 id="new-case-title">Create a case</h2></div><button type="button" className="icon-button" onClick={() => setShowNewCase(false)} aria-label="Close"><X size={17} /></button></div>
            <div className="form-content">
              <FormField label="Case ID" value={caseForm.case_id} onChange={(value) => setCaseForm({ ...caseForm, case_id: value })} placeholder="e.g. CASE_2026_101" required pattern="[A-Za-z0-9_-]{3,64}" />
              <FormField label="Case title" value={caseForm.title} onChange={(value) => setCaseForm({ ...caseForm, title: value })} placeholder="Investigation title" required maxLength={120} />
              <label className="field-label" htmlFor="case-description">Description <span>Optional</span></label>
              <textarea id="case-description" className="text-field" value={caseForm.description} onChange={(event) => setCaseForm({ ...caseForm, description: event.target.value })} placeholder="What is this investigation about?" maxLength={1000} />
            </div>
            {error && <div className="modal-error"><AlertCircle size={15} />{error}</div>}
            <div className="modal-actions"><button type="button" className="button button-quiet" onClick={() => setShowNewCase(false)}>Cancel</button><button className="button button-primary" disabled={Boolean(busyAction)}>{busyAction ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />}Create case</button></div>
          </form>
        </div>
      )}
    </main>
  )
}

function Metric({ icon: Icon, label, value, helper }) {
  return <div className="metric-card"><div className="metric-icon"><Icon size={16} /></div><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{helper}</small></div></div>
}

function EngineRow({ label, ready, detail }) {
  return <div className="engine-row"><span className={`engine-status-dot ${ready ? 'ready' : ''}`} /><div><strong>{label}</strong><span>{detail}</span></div><small>{ready ? 'READY' : 'OFFLINE'}</small></div>
}

function TabButton({ active, onClick, icon: Icon, children }) {
  return <button className={`tab-button ${active ? 'active' : ''}`} onClick={onClick}><Icon size={15} />{children}</button>
}

function FormField({ label, value, onChange, type = 'text', ...props }) {
  return <label className="field-label">{label}<input className="text-input" type={type} value={value} onChange={(event) => onChange(event.target.value)} {...props} /></label>
}

function ResultCard({ kind, result }) {
  const title = kind === 'narrative'
    ? `${result.extracted_entities?.nodes?.length || 0} entities extracted`
    : kind === 'traffic' ? result.classification : result.predicted_file_type
  const detail = kind === 'narrative'
    ? `${result.extracted_entities?.relationships?.length || 0} relationships · ${result.extractor}`
    : kind === 'traffic' ? `Threat score ${(result.threat_score * 100).toFixed(1)}% · ${((result.confidence || 0) * 100).toFixed(1)}% confidence · ${result.model}`
    : `${(result.confidence * 100).toFixed(1)}% confidence · ${result.model}`
  return <div className="result-card"><div className="result-icon"><Check size={15} /></div><div><strong>{title}</strong><span>{detail}</span>{kind === 'file' && <small>{result.diagnostic_signatures.join(' · ')}</small>}</div></div>
}
