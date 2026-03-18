import { useState, useEffect, useCallback } from 'react'
import { fetchJSON, subscribeSSE } from './api.js'
import ForceGraph3D from 'react-force-graph-3d'

// ====================================================================
// 主应用
// ====================================================================

export default function App() {
    const [page, setPage] = useState('dashboard')
    const [settingsSubPage, setSettingsSubPage] = useState('entities') // 设定库子页面
    const [settingsExpanded, setSettingsExpanded] = useState(false) // 设定库展开状态，默认收起
    const [projectInfo, setProjectInfo] = useState(null)
    const [refreshKey, setRefreshKey] = useState(0)
    const [connected, setConnected] = useState(false)

    const loadProjectInfo = useCallback(() => {
        fetchJSON('/api/project/info')
            .then(setProjectInfo)
            .catch(() => setProjectInfo(null))
    }, [])

    useEffect(() => { loadProjectInfo() }, [loadProjectInfo, refreshKey])

    // SSE 订阅
    useEffect(() => {
        const unsub = subscribeSSE(
            () => {
                setRefreshKey(k => k + 1)
            },
            {
                onOpen: () => setConnected(true),
                onError: () => setConnected(false),
            },
        )
        return () => { unsub(); setConnected(false) }
    }, [])

    const title = projectInfo?.project_info?.title || '未加载'

    // 处理导航点击
    const handleNavClick = (item) => {
        if (item.children) {
            // 点击父菜单，切换展开状态
            setSettingsExpanded(!settingsExpanded)
        } else {
            setPage(item.id)
        }
    }

    // 处理子菜单点击
    const handleSubNavClick = (subItem, parentId) => {
        setPage(parentId)
        setSettingsSubPage(subItem.id)
        setSettingsExpanded(true)
    }

    // 判断当前页面是否在设定库下（检查settingsSubPage而不是page）
    const isInSettings = ['entities', 'items', 'powers', 'maps', 'others'].includes(settingsSubPage)

    return (
        <div className="app-layout">
            <aside className="sidebar">
                <div className="sidebar-header">
                    <h1>PIXEL WRITER HUB</h1>
                    <div className="subtitle">{title}</div>
                </div>
                <nav className="sidebar-nav">
                    {NAV_ITEMS.map(item => (
                        <div key={item.id} className="nav-group">
                            <button
                                className={`nav-item ${!item.children && page === item.id ? 'active' : ''} ${item.children ? 'has-children' : ''}`}
                                onClick={() => handleNavClick(item)}
                            >
                                <span className="icon">{item.icon}</span>
                                <span>{item.label}</span>
                                {item.children && <span className={`nav-arrow ${settingsExpanded ? 'expanded' : ''}`}>▶</span>}
                            </button>
                            {item.children && settingsExpanded && (
                                <div className="nav-children">
                                    {item.children.map(subItem => (
                                        <button
                                            key={subItem.id}
                                            className={`nav-item nav-child ${page === subItem.id || (isInSettings && settingsSubPage === subItem.id) ? 'active' : ''}`}
                                            onClick={() => handleSubNavClick(subItem, item.id)}
                                        >
                                            <span className="icon">{subItem.icon}</span>
                                            <span>{subItem.label}</span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </nav>
                <div className="live-indicator">
                    <span className={`live-dot ${connected ? '' : 'disconnected'}`} />
                    {connected ? '实时同步中' : '未连接'}
                </div>
            </aside>

            <main className="main-content">
                {page === 'dashboard' && <DashboardPage data={projectInfo} key={refreshKey} />}
                {page === 'settings' && settingsSubPage === 'entities' && <EntitiesPage key={refreshKey} />}
                {page === 'settings' && settingsSubPage === 'powers' && <PowersPage key={refreshKey} />}
                {page === 'settings' && settingsSubPage === 'items' && <ItemsPage key={refreshKey} />}
                {page === 'settings' && settingsSubPage === 'maps' && <MapsPage key={refreshKey} />}
                {page === 'settings' && settingsSubPage === 'others' && <OthersPage key={refreshKey} />}
                {page === 'graph' && <GraphPage key={refreshKey} />}
                {page === 'chapters' && <ChaptersPage key={refreshKey} />}
                {page === 'files' && <FilesPage />}
                {page === 'reading' && <ReadingPowerPage key={refreshKey} />}
            </main>
        </div>
    )
}

const NAV_ITEMS = [
    { id: 'dashboard', icon: '📊', label: '数据总览' },
    { id: 'settings', icon: '📚', label: '设定库', children: [
        { id: 'entities', icon: '👤', label: '角色库' },
        { id: 'items', icon: '🎁', label: '道具库' },
        { id: 'powers', icon: '⚡', label: '功法库' },
        { id: 'maps', icon: '🗺️', label: '地图库' },
        { id: 'others', icon: '📦', label: '其他库' },
    ]},
    { id: 'graph', icon: '🕸️', label: '关系图谱' },
    { id: 'chapters', icon: '📝', label: '章节一览' },
    { id: 'files', icon: '📁', label: '文档浏览' },
    { id: 'reading', icon: '🔥', label: '追读力' },
]

const FULL_DATA_GROUPS = [
    { key: 'entities', title: '实体', columns: ['id', 'canonical_name', 'type', 'tier', 'first_appearance', 'last_appearance'], domain: 'core' },
    { key: 'chapters', title: '章节', columns: ['chapter', 'title', 'word_count', 'location', 'characters'], domain: 'core' },
    { key: 'scenes', title: '场景', columns: ['chapter', 'scene_index', 'location', 'time', 'summary'], domain: 'core' },
    { key: 'aliases', title: '别名', columns: ['alias', 'entity_id', 'entity_type'], domain: 'core' },
    { key: 'stateChanges', title: '状态变化', columns: ['entity_id', 'field', 'old_value', 'new_value', 'chapter'], domain: 'core' },
    { key: 'relationships', title: '关系', columns: ['from_entity', 'to_entity', 'type', 'chapter', 'description'], domain: 'network' },
    { key: 'relationshipEvents', title: '关系事件', columns: ['from_entity', 'to_entity', 'type', 'chapter', 'event_type', 'description'], domain: 'network' },
    { key: 'readingPower', title: '追读力', columns: ['chapter', 'hook_type', 'hook_strength', 'is_transition', 'override_count', 'debt_balance'], domain: 'network' },
    { key: 'overrides', title: 'Override 合约', columns: ['chapter', 'constraint_type', 'constraint_id', 'due_chapter', 'status'], domain: 'network' },
    { key: 'debts', title: '追读债务', columns: ['id', 'debt_type', 'current_amount', 'interest_rate', 'due_chapter', 'status'], domain: 'network' },
    { key: 'debtEvents', title: '债务事件', columns: ['debt_id', 'event_type', 'amount', 'chapter', 'note'], domain: 'network' },
    { key: 'reviewMetrics', title: '审查指标', columns: ['start_chapter', 'end_chapter', 'overall_score', 'severity_counts', 'created_at'], domain: 'quality' },
    { key: 'invalidFacts', title: '无效事实', columns: ['source_type', 'source_id', 'reason', 'status', 'chapter_discovered'], domain: 'quality' },
    { key: 'checklistScores', title: '写作清单评分', columns: ['chapter', 'template', 'score', 'completion_rate', 'completed_items', 'total_items'], domain: 'quality' },
    { key: 'ragQueries', title: 'RAG 查询日志', columns: ['query_type', 'query', 'results_count', 'latency_ms', 'chapter', 'created_at'], domain: 'ops' },
    { key: 'toolStats', title: '工具调用统计', columns: ['tool_name', 'success', 'retry_count', 'error_code', 'chapter', 'created_at'], domain: 'ops' },
]

const FULL_DATA_DOMAINS = [
    { id: 'overview', label: '总览' },
    { id: 'core', label: '基础档案' },
    { id: 'network', label: '关系与剧情' },
    { id: 'quality', label: '质量审查' },
    { id: 'ops', label: 'RAG 与工具' },
]


// ====================================================================
// 页面 1：数据总览
// ====================================================================

function DashboardPage({ data }) {
    if (!data) return <div className="loading">加载中…</div>

    const [entityStats, setEntityStats] = useState([])

    useEffect(() => {
        fetchJSON('/api/entities/statistics').then(setEntityStats).catch(() => { })
    }, [])

    const info = data.project_info || {}
    const progress = data.progress || {}
    const protagonist = data.protagonist_state || {}
    const strand = data.plot_threads?.strand_tracker || data.strand_tracker || {}
    const foreshadowing = data.plot_threads?.foreshadowing || []

    const totalWords = progress.total_words || 0
    const targetWords = info.target_words || 2000000
    const pct = targetWords > 0 ? Math.min(100, (totalWords / targetWords * 100)).toFixed(1) : 0

    // 从统计数据中计算重要角色数量（非装饰/龙套的角色）
    const importantCount = entityStats.filter(s => s.type === '角色' && s.tier !== '装饰' && s.tier !== '龙套').reduce((sum, s) => sum + s.count, 0)

    const unresolvedForeshadow = foreshadowing.filter(f => {
        const s = (f.status || '').toLowerCase()
        return s !== '已回收' && s !== '已兑现' && s !== 'resolved'
    })

    // Strand 历史统计
    const history = strand.history || []
    const strandCounts = { quest: 0, fire: 0, constellation: 0 }
    history.forEach(h => { if (strandCounts[h.strand] !== undefined) strandCounts[h.strand]++ })
    const total = history.length || 1

    return (
        <>
            <div className="page-header">
                <h2>📊 数据总览</h2>
                <span className="card-badge badge-blue">{info.genre || '未知题材'}</span>
            </div>

            <div className="dashboard-grid">
                <div className="card stat-card">
                    <span className="stat-label">总字数</span>
                    <span className="stat-value">{formatNumber(totalWords)}</span>
                    <span className="stat-sub">目标 {formatNumber(targetWords)} 字 · {pct}%</span>
                    <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${pct}%` }} />
                    </div>
                </div>

                <div className="card stat-card">
                    <span className="stat-label">当前章节</span>
                    <span className="stat-value">第 {progress.current_chapter || 0} 章</span>
                    <span className="stat-sub">目标 {info.target_chapters || '?'} 章 · 卷 {progress.current_volume || 1}</span>
                </div>

                <div className="card stat-card">
                    <span className="stat-label">主角状态</span>
                    <span className="stat-value plain">{protagonist.name || '未设定'}</span>
                    <span className="stat-sub">
                        {protagonist.power?.realm || '未知境界'}
                        {protagonist.location?.current ? ` · ${protagonist.location.current}` : ''}
                    </span>
                </div>

                <div className="card stat-card">
                    <span className="stat-label">未回收伏笔</span>
                    <span className="stat-value" style={{ color: unresolvedForeshadow.length > 10 ? 'var(--accent-red)' : 'var(--accent-amber)' }}>
                        {unresolvedForeshadow.length}
                    </span>
                    <span className="stat-sub">总计 {foreshadowing.length} 条伏笔</span>
                </div>

                <div className="card stat-card">
                    <span className="stat-label">重要角色</span>
                    <span className="stat-value" style={{ color: '#1890ff' }}>{importantCount}</span>
                    <span className="stat-sub">核心+重要+次要角色</span>
                </div>
            </div>

            {/* Strand Weave 比例 */}
            <div className="card dashboard-section-card">
                <div className="card-header">
                    <span className="card-title">Strand Weave 节奏分布</span>
                    <span className="card-badge badge-purple">{strand.current_dominant || '?'}</span>
                </div>
                <div className="strand-bar">
                    <div className="segment strand-quest" style={{ width: `${(strandCounts.quest / total * 100).toFixed(1)}%` }} />
                    <div className="segment strand-fire" style={{ width: `${(strandCounts.fire / total * 100).toFixed(1)}%` }} />
                    <div className="segment strand-constellation" style={{ width: `${(strandCounts.constellation / total * 100).toFixed(1)}%` }} />
                </div>
                <div className="strand-legend">
                    <span>🔵 Quest {(strandCounts.quest / total * 100).toFixed(0)}%</span>
                    <span>🔴 Fire {(strandCounts.fire / total * 100).toFixed(0)}%</span>
                    <span>🟣 Constellation {(strandCounts.constellation / total * 100).toFixed(0)}%</span>
                </div>
            </div>

            {/* 伏笔列表 */}
            {unresolvedForeshadow.length > 0 ? (
                <div className="card dashboard-section-card">
                    <div className="card-header">
                        <span className="card-title">⚠️ 待回收伏笔 (Top 20)</span>
                    </div>
                    <div className="table-wrap">
                        <table className="data-table">
                            <thead><tr><th>内容</th><th>状态</th><th>埋设章</th></tr></thead>
                            <tbody>
                                {unresolvedForeshadow.slice(0, 20).map((f, i) => (
                                    <tr key={i}>
                                        <td className="truncate" style={{ maxWidth: 400 }}>{f.content || f.description || '—'}</td>
                                        <td><span className="card-badge badge-amber">{f.status || '未知'}</span></td>
                                        <td>{f.chapter || f.planted_chapter || '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : null}

            <MergedDataView />
        </>
    )
}


// ====================================================================
// 页面 2：设定词典
// ====================================================================

function EntitiesPage() {
    const [entities, setEntities] = useState([])
    const [tierFilter, setTierFilter] = useState('')
    const [selected, setSelected] = useState(null)
    const [entityDetail, setEntityDetail] = useState(null)
    const [changes, setChanges] = useState([])
    const [lightboxImage, setLightboxImage] = useState(null)

    useEffect(() => {
        fetchJSON('/api/entities').then(setEntities).catch(() => { })
    }, [])

    useEffect(() => {
        if (selected) {
            // 获取实体详情（包含图片信息）
            fetchJSON(`/api/entities/${selected.id}`).then(setEntityDetail).catch(() => setEntityDetail(null))
            // 获取状态变化历史
            fetchJSON('/api/state-changes', { entity: selected.id, limit: 30 }).then(setChanges).catch(() => setChanges([]))
        }
    }, [selected])

    // 辅助函数：将数据库的tier值转换为显示值（装饰 -> 龙套）
    const getTierDisplay = (tier) => {
        if (tier === '装饰') return '龙套'
        return tier
    }

    // 辅助函数：将显示值转换回数据库值（龙套 -> 装饰）
    const getTierValue = (displayTier) => {
        if (displayTier === '龙套') return '装饰'
        return displayTier
    }

    // 获取唯一的层级值（将装饰和龙套合并为龙套）
    const tierSet = new Set(entities.map(e => getTierDisplay(e.tier)))
    const tiers = [...tierSet].sort()
    let filteredEntities = tierFilter ? entities.filter(e => getTierDisplay(e.tier) === tierFilter) : entities

    return (
        <>
            <div className="page-header">
                <h2>👤 角色库</h2>
                <span className="card-badge badge-green">{filteredEntities.length} / {entities.length} 个角色</span>
            </div>

            <div className="filter-group">
                <span className="filter-label">层级:</span>
                <button className={`filter-btn ${tierFilter === '' ? 'active' : ''}`} onClick={() => setTierFilter('')}>全部</button>
                {tiers.map(t => (
                    <button key={t} className={`filter-btn ${tierFilter === t ? 'active' : ''} ${t === '龙套' ? 'filter-btn-minor' : ''}`} onClick={() => setTierFilter(t)}>
                        {t}
                    </button>
                ))}
            </div>

            <div className="split-layout">
                <div className="split-main">
                    <div className="card">
                        <div className="table-wrap">
                            <table className="data-table">
                                <thead><tr><th>名称</th><th>层级</th><th>首现</th><th>末现</th><th>设定图</th></tr></thead>
                                <tbody>
                                    {filteredEntities.map(e => (
                                        <tr
                                            key={e.id}
                                            role="button"
                                            tabIndex={0}
                                            className={`entity-row ${selected?.id === e.id ? 'selected' : ''}`}
                                            onKeyDown={evt => (evt.key === 'Enter' || evt.key === ' ') && (evt.preventDefault(), setSelected(e))}
                                            onClick={() => setSelected(e)}
                                        >
                                            <td className={e.is_protagonist ? 'entity-name protagonist' : 'entity-name'}>
                                                {e.canonical_name} {e.is_protagonist ? '⭐' : ''}
                                            </td>
                                            <td><span className={getTierDisplay(e.tier) === '龙套' ? 'card-badge badge-gray' : 'card-badge badge-blue'}>{getTierDisplay(e.tier)}</span></td>
                                            <td>{e.first_appearance || '—'}</td>
                                            <td>{e.last_appearance || '—'}</td>
                                            <td>{e.image_path ? '📷' : ''}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {selected && entityDetail && (
                    <div className="split-side">
                        <div className="card">
                            <div className="card-header">
                                <span className="card-title">{selected.canonical_name}</span>
                                <span className={`card-badge ${getTierDisplay(selected.tier) === '龙套' ? 'badge-gray' : 'badge-purple'}`}>{getTierDisplay(selected.tier)}</span>
                            </div>

                            {/* 角色设定图展示 */}
                            {entityDetail.images && entityDetail.images.length > 0 && (
                                <div className="character-images">
                                    <div className="character-images-title">设定图</div>
                                    <div className="character-images-grid">
                                        {entityDetail.images.map((img, idx) => (
                                            <div key={idx} className="character-image-wrapper">
                                                <img
                                                    src={`/api/files?path=${encodeURIComponent(img)}`}
                                                    alt={`设定图 ${idx + 1}`}
                                                    className="character-image"
                                                    onClick={() => setLightboxImage(img)}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="entity-detail">
                                <p><strong>类型：</strong>{selected.type}</p>
                                <p><strong>ID：</strong><code>{selected.id}</code></p>
                                {selected.desc && <p className="entity-desc">{selected.desc}</p>}
                                {selected.current_json && (
                                    <div className="entity-current-block">
                                        <strong>当前状态：</strong>
                                        <pre className="entity-json">
                                            {formatJSON(selected.current_json)}
                                        </pre>
                                    </div>
                                )}
                            </div>
                            {changes.length > 0 ? (
                                <div className="entity-history">
                                    <div className="card-title">状态变化历史</div>
                                    <div className="table-wrap">
                                        <table className="data-table">
                                            <thead><tr><th>章</th><th>字段</th><th>变化</th></tr></thead>
                                            <tbody>
                                                {changes.map((c, i) => (
                                                    <tr key={i}>
                                                        <td>{c.chapter}</td>
                                                        <td>{c.field}</td>
                                                        <td>{c.old_value} → {c.new_value}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : null}
                        </div>
                    </div>
                )}
            </div>

            {/* 灯箱 */}
            {lightboxImage && (
                <div className="lightbox" onClick={() => setLightboxImage(null)}>
                    <img
                        src={`/api/files?path=${encodeURIComponent(lightboxImage)}`}
                        alt="大图"
                        className="lightbox-image"
                        onClick={(e) => e.stopPropagation()}
                    />
                    <button className="lightbox-close" onClick={() => setLightboxImage(null)}>✕</button>
                </div>
            )}
        </>
    )
}


// ====================================================================
// 页面 3：功法库
// ====================================================================

function PowersPage() {
    const [powers, setPowers] = useState([])
    const [typeFilter, setTypeFilter] = useState('')
    const [selected, setSelected] = useState(null)
    const [detail, setDetail] = useState(null)

    useEffect(() => {
        fetchJSON('/api/powers').then(setPowers).catch(() => { })
    }, [])

    useEffect(() => {
        if (selected) {
            fetchJSON(`/api/powers/${selected.id}`).then(setDetail).catch(() => setDetail(null))
        }
    }, [selected])

    const types = [...new Set(powers.map(p => p.power_type))].sort()
    let filteredPowers = typeFilter ? powers.filter(p => p.power_type === typeFilter) : powers

    return (
        <>
            <div className="page-header">
                <h2>⚡ 功法库</h2>
                <span className="card-badge badge-green">{filteredPowers.length} / {powers.length} 个功法</span>
            </div>

            <div className="filter-group">
                <button className={`filter-btn ${typeFilter === '' ? 'active' : ''}`} onClick={() => setTypeFilter('')}>全部</button>
                {types.map(t => (
                    <button key={t} className={`filter-btn ${typeFilter === t ? 'active' : ''}`} onClick={() => setTypeFilter(t)}>{t}</button>
                ))}
            </div>

            <div className="split-layout">
                <div className="split-main">
                    <div className="card">
                        <div className="table-wrap">
                            <table className="data-table">
                                <thead><tr><th>名称</th><th>类型</th><th>层级</th><th>境界</th></tr></thead>
                                <tbody>
                                    {filteredPowers.map(p => (
                                        <tr
                                            key={p.id}
                                            role="button"
                                            tabIndex={0}
                                            className={`entity-row ${selected?.id === p.id ? 'selected' : ''}`}
                                            onKeyDown={evt => (evt.key === 'Enter' || evt.key === ' ') && (evt.preventDefault(), setSelected(p))}
                                            onClick={() => setSelected(p)}
                                        >
                                            <td className="entity-name">{p.name}</td>
                                            <td><span className="card-badge badge-blue">{p.power_type}</span></td>
                                            <td><span className={p.tier === '核心' ? 'card-badge badge-purple' : p.tier === '重要' ? 'card-badge badge-amber' : ''}>{p.tier}</span></td>
                                            <td>{p.cultivation_level || '—'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {selected && detail && (
                    <div className="split-side">
                        <div className="card">
                            <div className="card-header">
                                <span className="card-title">{detail.name}</span>
                                <span className="card-badge badge-purple">{detail.power_type}</span>
                            </div>
                            <div className="entity-detail">
                                <p><strong>ID：</strong><code>{detail.id}</code></p>
                                <p><strong>类型：</strong>{detail.power_type}</p>
                                <p><strong>层级：</strong>{detail.tier}</p>
                                <p><strong>属性：</strong>{detail.element || '—'}</p>
                                <p><strong>境界要求：</strong>{detail.cultivation_level || '—'}</p>
                                {detail.content && <div className="entity-desc" style={{marginTop: 12}}>{detail.content}</div>}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </>
    )
}


// ====================================================================
// 页面 4：道具库（包含丹药）
// ====================================================================

function ItemsPage() {
    const [items, setItems] = useState([])
    const [typeFilter, setTypeFilter] = useState('')
    const [selected, setSelected] = useState(null)
    const [detail, setDetail] = useState(null)
    const [lightboxImage, setLightboxImage] = useState(null)

    useEffect(() => {
        fetchJSON('/api/items').then(setItems).catch(() => { })
    }, [])

    useEffect(() => {
        if (selected) {
            fetchJSON(`/api/items/${selected.id}`).then(setDetail).catch(() => setDetail(null))
        }
    }, [selected])

    const types = [...new Set(items.map(i => i.category))].sort()
    let filteredItems = typeFilter ? items.filter(i => i.category === typeFilter) : items

    return (
        <>
            <div className="page-header">
                <h2>🎁 道具库</h2>
                <span className="card-badge badge-green">{filteredItems.length} / {items.length} 个道具</span>
            </div>

            <div className="filter-group">
                <button className={`filter-btn ${typeFilter === '' ? 'active' : ''}`} onClick={() => setTypeFilter('')}>全部</button>
                {types.map(t => (
                    <button key={t} className={`filter-btn ${typeFilter === t ? 'active' : ''}`} onClick={() => setTypeFilter(t)}>{t}</button>
                ))}
            </div>

            <div className="split-layout">
                <div className="split-main">
                    <div className="card">
                        <div className="table-wrap">
                            <table className="data-table">
                                <thead><tr><th>名称</th><th>类别</th><th>层级</th><th>稀有度</th></tr></thead>
                                <tbody>
                                    {filteredItems.map(i => (
                                        <tr
                                            key={i.id}
                                            role="button"
                                            tabIndex={0}
                                            className={`entity-row ${selected?.id === i.id ? 'selected' : ''}`}
                                            onKeyDown={evt => (evt.key === 'Enter' || evt.key === ' ') && (evt.preventDefault(), setSelected(i))}
                                            onClick={() => setSelected(i)}
                                        >
                                            <td className="entity-name">{i.name}</td>
                                            <td><span className="card-badge badge-blue">{i.category}</span></td>
                                            <td><span className={i.tier === '核心' ? 'card-badge badge-purple' : i.tier === '重要' ? 'card-badge badge-amber' : ''}>{i.tier}</span></td>
                                            <td><span className={i.rarity === '极品' ? 'card-badge badge-amber' : i.rarity === '仙品' ? 'card-badge badge-purple' : ''}>{i.rarity || '—'}</span></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {selected && detail && (
                    <div className="split-side">
                        <div className="card">
                            <div className="card-header">
                                <span className="card-title">{detail.name}</span>
                                <span className="card-badge badge-blue">{detail.category}</span>
                            </div>

                            {detail.image_path && (
                                <div className="item-image-container" style={{marginBottom: 12}}>
                                    <img
                                        src={`/api/files?path=${encodeURIComponent(detail.image_path)}`}
                                        alt={detail.name}
                                        className="item-image"
                                        style={{maxWidth: '100%', maxHeight: 200, cursor: 'pointer', borderRadius: 4}}
                                        onClick={() => setLightboxImage(detail.image_path)}
                                    />
                                </div>
                            )}

                            <div className="entity-detail">
                                <p><strong>ID：</strong><code>{detail.id}</code></p>
                                <p><strong>类别：</strong>{detail.category}</p>
                                <p><strong>层级：</strong>{detail.tier}</p>
                                <p><strong>稀有度：</strong>{detail.rarity || '—'}</p>
                                {detail.content && (
                                    <div className="detail-content" style={{marginTop: 12, maxHeight: 300, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6}}>
                                        {detail.content}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {lightboxImage && (
                <div className="lightbox" onClick={() => setLightboxImage(null)}>
                    <img
                        src={`/api/files?path=${encodeURIComponent(lightboxImage)}`}
                        alt="大图"
                        className="lightbox-image"
                        onClick={(e) => e.stopPropagation()}
                    />
                    <button className="lightbox-close" onClick={() => setLightboxImage(null)}>✕</button>
                </div>
            )}
        </>
    )
}


// ====================================================================
// 页面 4b：地图库
// ====================================================================

function MapsPage() {
    const [maps, setMaps] = useState([])
    const [typeFilter, setTypeFilter] = useState('')
    const [selected, setSelected] = useState(null)
    const [detail, setDetail] = useState(null)
    const [lightboxImage, setLightboxImage] = useState(null)

    useEffect(() => {
        fetchJSON('/api/maps').then(setMaps).catch(() => { })
    }, [])

    useEffect(() => {
        if (selected) {
            fetchJSON(`/api/maps/${selected.id}`).then(setDetail).catch(() => setDetail(null))
        }
    }, [selected])

    const types = [...new Set(maps.map(m => m.map_type))].sort()
    let filteredMaps = typeFilter ? maps.filter(m => m.map_type === typeFilter) : maps
    const totalCount = maps.length
    const filteredCount = filteredMaps.length

    return (
        <>
            <div className="page-header">
                <h2>🗺️ 地图库</h2>
                <span className="card-badge badge-green">{filteredCount} / {totalCount} 个地图</span>
            </div>

            <div className="filter-group">
                <button className={`filter-btn ${typeFilter === '' ? 'active' : ''}`} onClick={() => setTypeFilter('')}>全部</button>
                {types.map(t => (
                    <button key={t} className={`filter-btn ${typeFilter === t ? 'active' : ''}`} onClick={() => setTypeFilter(t)}>{t}</button>
                ))}
            </div>

            <div className="split-layout">
                <div className="split-main">
                    <div className="table-wrap">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>名称</th>
                                    <th>类型</th>
                                    <th>层级</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredMaps.map(map => (
                                    <tr
                                        key={map.id}
                                        className={selected?.id === map.id ? 'selected' : ''}
                                        onClick={() => setSelected(map)}
                                    >
                                        <td>{map.name}</td>
                                        <td>{map.map_type}</td>
                                        <td>{map.tier}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {selected && detail && (
                    <div className="split-side">
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">{selected.name}</h3>
                                <span className="card-badge badge-blue">{selected.map_type}</span>
                            </div>

                            {detail.image_path && (
                                <div className="map-image-container">
                                    <img
                                        src={`/api/files?path=${encodeURIComponent(detail.image_path)}`}
                                        alt={selected.name}
                                        className="map-image"
                                        onClick={() => setLightboxImage(detail.image_path)}
                                    />
                                </div>
                            )}

                            <div className="detail-info">
                                <p><strong>类型：</strong>{detail.map_type}</p>
                                <p><strong>层级：</strong>{detail.tier}</p>
                                {detail.description && (
                                    <div className="detail-content" style={{marginTop: 8, maxHeight: 300, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6}}>
                                        {detail.description}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {lightboxImage && (
                <div className="lightbox" onClick={() => setLightboxImage(null)}>
                    <img
                        src={`/api/files?path=${encodeURIComponent(lightboxImage)}`}
                        alt="大图"
                        className="lightbox-image"
                        onClick={(e) => e.stopPropagation()}
                    />
                    <button className="lightbox-close" onClick={() => setLightboxImage(null)}>✕</button>
                </div>
            )}
        </>
    )
}

// ====================================================================
// 页面 4c：其他设定库（世界观、力量体系、金手指等）
// ====================================================================

function OthersPage() {
    const [items, setItems] = useState([])
    const [typeFilter, setTypeFilter] = useState('')
    const [selected, setSelected] = useState(null)
    const [detail, setDetail] = useState(null)

    useEffect(() => {
        fetchJSON('/api/others').then(setItems).catch(() => { })
    }, [])

    useEffect(() => {
        if (selected) {
            // 从others API获取详情
            fetchJSON(`/api/others/${selected.id}`).then(setDetail).catch(() => setDetail(null))
        }
    }, [selected])

    const types = [...new Set(items.map(i => i.category))].sort()
    let filteredItems = typeFilter ? items.filter(i => i.category === typeFilter) : items

    return (
        <>
            <div className="page-header">
                <h2>📦 其他库</h2>
                <span className="card-badge badge-green">{filteredItems.length} / {items.length} 个设定</span>
            </div>

            <div className="filter-group">
                <button className={`filter-btn ${typeFilter === '' ? 'active' : ''}`} onClick={() => setTypeFilter('')}>全部</button>
                {types.map(t => (
                    <button key={t} className={`filter-btn ${typeFilter === t ? 'active' : ''}`} onClick={() => setTypeFilter(t)}>{t}</button>
                ))}
            </div>

            <div className="split-layout">
                <div className="split-main">
                    <div className="card">
                        <div className="table-wrap">
                            <table className="data-table">
                                <thead><tr><th>名称</th><th>类别</th></tr></thead>
                                <tbody>
                                    {filteredItems.map(i => (
                                        <tr
                                            key={i.id}
                                            role="button"
                                            tabIndex={0}
                                            className={`entity-row ${selected?.id === i.id ? 'selected' : ''}`}
                                            onKeyDown={evt => (evt.key === 'Enter' || evt.key === ' ') && (evt.preventDefault(), setSelected(i))}
                                            onClick={() => setSelected(i)}
                                        >
                                            <td className="entity-name">{i.name}</td>
                                            <td><span className="card-badge badge-purple">{i.category}</span></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div className="split-side">
                    {selected && detail && (
                        <div className="card">
                            <h3>{detail.name || selected.name}</h3>
                            <div className="detail-meta">
                                <span className="card-badge badge-purple">{detail.category || selected.category}</span>
                            </div>
                            <div className="detail-body">
                                {detail.content ? (
                                    <div className="detail-content" style={{maxHeight: 400, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6}}>
                                        {detail.content}
                                    </div>
                                ) : (
                                    <p>{selected.description || '暂无描述'}</p>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    )
}


// ====================================================================
// 页面 5：3D 宇宙关系图谱
// ====================================================================

function GraphPage() {
    const [relationships, setRelationships] = useState([])
    const [graphData, setGraphData] = useState({ nodes: [], links: [] })

    useEffect(() => {
        Promise.all([
            fetchJSON('/api/relationships', { limit: 1000 }),
            fetchJSON('/api/entities'),
        ]).then(([rels, ents]) => {
            setRelationships(rels)
            const typeColors = {
                '角色': '#4f8ff7', '地点': '#34d399', '星球': '#22d3ee', '神仙': '#f59e0b',
                '势力': '#8b5cf6', '招式': '#ef4444', '法宝': '#ec4899'
            }
            const relatedIds = new Set()
            rels.forEach(r => { relatedIds.add(r.from_entity); relatedIds.add(r.to_entity) })
            const entityMap = {}
            ents.forEach(e => { entityMap[e.id] = e })

            const nodes = [...relatedIds].map(id => ({
                id,
                name: entityMap[id]?.canonical_name || id,
                val: (entityMap[id]?.tier === 'S' ? 8 : entityMap[id]?.tier === 'A' ? 5 : 2),
                color: typeColors[entityMap[id]?.type] || '#5c6078'
            }))
            const links = rels.map(r => ({
                source: r.from_entity,
                target: r.to_entity,
                name: r.type
            }))
            setGraphData({ nodes, links })
        }).catch(() => { })
    }, [])

    return (
        <>
            <div className="page-header">
                <h2>🕸️ 关系图谱</h2>
                <span className="card-badge badge-blue">{relationships.length} 条引力链接</span>
            </div>
            <div className="card graph-shell">
                <ForceGraph3D
                    graphData={graphData}
                    nodeLabel="name"
                    nodeColor="color"
                    nodeRelSize={6}
                    linkColor={() => 'rgba(127, 90, 240, 0.35)'}
                    linkWidth={1}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleWidth={1.5}
                    linkDirectionalParticleSpeed={d => 0.005 + Math.random() * 0.005}
                    backgroundColor="#fffaf0"
                    showNavInfo={false}
                />
            </div>
        </>
    )
}



// ====================================================================
// 页面 6：章节一览
// ====================================================================

function ChaptersPage() {
    const [chapters, setChapters] = useState([])

    useEffect(() => {
        fetchJSON('/api/chapters').then(setChapters).catch(() => { })
    }, [])

    const totalWords = chapters.reduce((s, c) => s + (c.word_count || 0), 0)

    return (
        <>
            <div className="page-header">
                <h2>📝 章节一览</h2>
                <span className="card-badge badge-green">{chapters.length} 章 · {formatNumber(totalWords)} 字</span>
            </div>
            <div className="card">
                <div className="table-wrap">
                    <table className="data-table">
                        <thead><tr><th>章节</th><th>标题</th><th>字数</th><th>地点</th><th>角色</th></tr></thead>
                        <tbody>
                            {chapters.map(c => (
                                <tr key={c.chapter}>
                                    <td className="chapter-no">第 {c.chapter} 章</td>
                                    <td>{c.title || '—'}</td>
                                    <td>{formatNumber(c.word_count || 0)}</td>
                                    <td>{c.location || '—'}</td>
                                    <td className="truncate chapter-characters">{c.characters || '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {chapters.length === 0 ? <div className="empty-state"><div className="empty-icon">📭</div><p>暂无章节数据</p></div> : null}
            </div>
        </>
    )
}


// ====================================================================
// 页面 7：文档浏览
// ====================================================================

function FilesPage() {
    const [tree, setTree] = useState({})
    const [selectedPath, setSelectedPath] = useState(null)
    const [content, setContent] = useState('')

    useEffect(() => {
        fetchJSON('/api/files/tree').then(setTree).catch(() => { })
    }, [])

    useEffect(() => {
        if (selectedPath) {
            fetchJSON('/api/files/read', { path: selectedPath })
                .then(d => setContent(d.content))
                .catch(() => setContent('[读取失败]'))
        }
    }, [selectedPath])

    useEffect(() => {
        if (selectedPath) return
        const first = findFirstFilePath(tree)
        if (first) setSelectedPath(first)
    }, [tree, selectedPath])

    return (
        <>
            <div className="page-header">
                <h2>📁 文档浏览</h2>
            </div>
            <div className="file-layout">
                <div className="file-tree-pane">
                    {Object.entries(tree).map(([folder, items]) => (
                        <div key={folder} className="folder-block">
                            <div className="folder-title">📂 {folder}</div>
                            <ul className="file-tree">
                                <TreeNodes items={items} selected={selectedPath} onSelect={setSelectedPath} />
                            </ul>
                        </div>
                    ))}
                </div>
                <div className="file-content-pane">
                    {selectedPath ? (
                        <div>
                            <div className="selected-path">{selectedPath}</div>
                            <div className="file-preview">{content}</div>
                        </div>
                    ) : (
                        <div className="empty-state"><div className="empty-icon">📄</div><p>选择左侧文件以预览内容</p></div>
                    )}
                </div>
            </div>
        </>
    )
}


// ====================================================================
// 页面 8：追读力
// ====================================================================

function ReadingPowerPage() {
    const [data, setData] = useState([])

    useEffect(() => {
        fetchJSON('/api/reading-power', { limit: 50 }).then(setData).catch(() => { })
    }, [])

    return (
        <>
            <div className="page-header">
                <h2>🔥 追读力分析</h2>
                <span className="card-badge badge-amber">{data.length} 章数据</span>
            </div>
            <div className="card">
                <div className="table-wrap">
                    <table className="data-table">
                        <thead><tr><th>章节</th><th>钩子类型</th><th>钩子强度</th><th>过渡章</th><th>Override</th><th>债务余额</th></tr></thead>
                        <tbody>
                            {data.map(r => (
                                <tr key={r.chapter}>
                                    <td className="chapter-no">第 {r.chapter} 章</td>
                                    <td>{r.hook_type || '—'}</td>
                                    <td>
                                        <span className={`card-badge ${r.hook_strength === 'strong' ? 'badge-green' : r.hook_strength === 'weak' ? 'badge-red' : 'badge-amber'}`}>
                                            {r.hook_strength || '—'}
                                        </span>
                                    </td>
                                    <td>{r.is_transition ? '✅' : '—'}</td>
                                    <td>{r.override_count || 0}</td>
                                    <td className={r.debt_balance > 0 ? 'debt-positive' : 'debt-normal'}>{(r.debt_balance || 0).toFixed(2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {data.length === 0 ? <div className="empty-state"><div className="empty-icon">🔥</div><p>暂无追读力数据</p></div> : null}
            </div>
        </>
    )
}

function findFirstFilePath(tree) {
    const roots = Object.values(tree || {})
    for (const items of roots) {
        const p = walkFirstFile(items)
        if (p) return p
    }
    return null
}

function walkFirstFile(items) {
    if (!Array.isArray(items)) return null
    for (const item of items) {
        if (item?.type === 'file' && item?.path) return item.path
        if (item?.type === 'dir' && Array.isArray(item.children)) {
            const p = walkFirstFile(item.children)
            if (p) return p
        }
    }
    return null
}


// ====================================================================
// 数据总览内嵌：全量数据视图
// ====================================================================

function MergedDataView() {
    const [loading, setLoading] = useState(true)
    const [payload, setPayload] = useState({})
    const [domain, setDomain] = useState('overview')

    useEffect(() => {
        let disposed = false

        async function loadAll() {
            setLoading(true)
            const requests = [
                ['entities', fetchJSON('/api/entities')],
                ['chapters', fetchJSON('/api/chapters')],
                ['scenes', fetchJSON('/api/scenes', { limit: 200 })],
                ['relationships', fetchJSON('/api/relationships', { limit: 300 })],
                ['relationshipEvents', fetchJSON('/api/relationship-events', { limit: 200 })],
                ['readingPower', fetchJSON('/api/reading-power', { limit: 100 })],
                ['reviewMetrics', fetchJSON('/api/review-metrics', { limit: 50 })],
                ['stateChanges', fetchJSON('/api/state-changes', { limit: 120 })],
                ['aliases', fetchJSON('/api/aliases')],
                ['overrides', fetchJSON('/api/overrides', { limit: 120 })],
                ['debts', fetchJSON('/api/debts', { limit: 120 })],
                ['debtEvents', fetchJSON('/api/debt-events', { limit: 150 })],
                ['invalidFacts', fetchJSON('/api/invalid-facts', { limit: 120 })],
                ['ragQueries', fetchJSON('/api/rag-queries', { limit: 150 })],
                ['toolStats', fetchJSON('/api/tool-stats', { limit: 200 })],
                ['checklistScores', fetchJSON('/api/checklist-scores', { limit: 120 })],
            ]

            const entries = await Promise.all(
                requests.map(async ([key, p]) => {
                    try {
                        const val = await p
                        return [key, val]
                    } catch {
                        return [key, []]
                    }
                }),
            )
            if (!disposed) {
                setPayload(Object.fromEntries(entries))
                setLoading(false)
            }
        }

        loadAll()
        return () => { disposed = true }
    }, [])

    if (loading) return <div className="loading">加载全量数据中…</div>

    const groups = domain === 'overview'
        ? FULL_DATA_GROUPS
        : FULL_DATA_GROUPS.filter(g => g.domain === domain)
    const totalRows = FULL_DATA_GROUPS.reduce((sum, g) => sum + (payload[g.key] || []).length, 0)
    const nonEmptyGroups = FULL_DATA_GROUPS.filter(g => (payload[g.key] || []).length > 0).length
    const maxChapter = FULL_DATA_GROUPS.reduce((max, g) => {
        const rows = payload[g.key] || []
        rows.slice(0, 120).forEach(r => {
            const c = extractChapter(r)
            if (c > max) max = c
        })
        return max
    }, 0)
    const domainStats = FULL_DATA_DOMAINS.filter(d => d.id !== 'overview').map(d => {
        const ds = FULL_DATA_GROUPS.filter(g => g.domain === d.id)
        const rowCount = ds.reduce((sum, g) => sum + (payload[g.key] || []).length, 0)
        const filled = ds.filter(g => (payload[g.key] || []).length > 0).length
        return { ...d, rowCount, filled, total: ds.length }
    })

    return (
        <>
            <div className="page-header section-page-header">
                <h2>🧪 全量数据视图</h2>
                <span className="card-badge badge-cyan">{FULL_DATA_GROUPS.length} 类数据源</span>
            </div>

            <div className="demo-summary-grid">
                <div className="card stat-card">
                    <span className="stat-label">总记录数</span>
                    <span className="stat-value">{formatNumber(totalRows)}</span>
                    <span className="stat-sub">当前返回的全部数据行</span>
                </div>
                <div className="card stat-card">
                    <span className="stat-label">已覆盖数据源</span>
                    <span className="stat-value plain">{nonEmptyGroups}/{FULL_DATA_GROUPS.length}</span>
                    <span className="stat-sub">有数据的表 / 总表数</span>
                </div>
                <div className="card stat-card">
                    <span className="stat-label">最新章节触达</span>
                    <span className="stat-value plain">{maxChapter > 0 ? `第 ${maxChapter} 章` : '—'}</span>
                    <span className="stat-sub">按可识别 chapter 字段估算</span>
                </div>
                <div className="card stat-card">
                    <span className="stat-label">当前视图</span>
                    <span className="stat-value plain">{FULL_DATA_DOMAINS.find(d => d.id === domain)?.label}</span>
                    <span className="stat-sub">{groups.length} 个数据分组</span>
                </div>
            </div>

            <div className="demo-domain-tabs">
                {FULL_DATA_DOMAINS.map(item => (
                    <button
                        key={item.id}
                        className={`demo-domain-tab ${domain === item.id ? 'active' : ''}`}
                        onClick={() => setDomain(item.id)}
                    >
                        {item.label}
                    </button>
                ))}
            </div>

            {domain === 'overview' ? (
                <div className="demo-domain-grid">
                    {domainStats.map(ds => (
                        <div className="card" key={ds.id}>
                            <div className="card-header">
                                <span className="card-title">{ds.label}</span>
                                <span className="card-badge badge-purple">{ds.filled}/{ds.total}</span>
                            </div>
                            <div className="domain-stat-number">{formatNumber(ds.rowCount)}</div>
                            <div className="stat-sub">该数据域总记录数</div>
                        </div>
                    ))}
                </div>
            ) : null}

            {groups.map(g => {
                const count = (payload[g.key] || []).length
                return (
                    <div className="card demo-group-card" key={g.key}>
                        <div className="card-header">
                            <span className="card-title">{g.title}</span>
                            <span className={`card-badge ${count > 0 ? 'badge-blue' : 'badge-amber'}`}>{count} 条</span>
                        </div>
                        <MiniTable
                            rows={payload[g.key] || []}
                            columns={g.columns}
                            pageSize={12}
                        />
                    </div>
                )
            })}
        </>
    )
}

function MiniTable({ rows, columns, pageSize = 12 }) {
    const [page, setPage] = useState(1)

    useEffect(() => {
        setPage(1)
    }, [rows, columns, pageSize])

    if (!rows || rows.length === 0) {
        return <div className="empty-state compact"><p>暂无数据</p></div>
    }

    const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
    const safePage = Math.min(page, totalPages)
    const start = (safePage - 1) * pageSize
    const list = rows.slice(start, start + pageSize)

    return (
        <>
            <div className="table-wrap">
                <table className="data-table">
                    <thead>
                        <tr>{columns.map(c => <th key={c}>{c}</th>)}</tr>
                    </thead>
                    <tbody>
                        {list.map((row, i) => (
                            <tr key={i}>
                                {columns.map(c => (
                                    <td key={c} className="truncate" style={{ maxWidth: 240 }}>
                                        {formatCell(row?.[c])}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="table-pagination">
                <button
                    className="page-btn"
                    type="button"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={safePage <= 1}
                >
                    上一页
                </button>
                <span className="page-info">
                    第 {safePage} / {totalPages} 页 · 共 {rows.length} 条
                </span>
                <button
                    className="page-btn"
                    type="button"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={safePage >= totalPages}
                >
                    下一页
                </button>
            </div>
        </>
    )
}

function extractChapter(row) {
    if (!row || typeof row !== 'object') return 0
    const candidates = [
        row.chapter,
        row.start_chapter,
        row.end_chapter,
        row.chapter_discovered,
        row.first_appearance,
        row.last_appearance,
    ]
    for (const c of candidates) {
        const n = Number(c)
        if (Number.isFinite(n) && n > 0) return n
    }
    return 0
}


// ====================================================================
// 子组件：文件树递归
// ====================================================================

function TreeNodes({ items, selected, onSelect, depth = 0 }) {
    const [expanded, setExpanded] = useState({})
    if (!items || items.length === 0) return null

    return items.map((item, i) => {
        const key = item.path || `${depth}-${i}`
        if (item.type === 'dir') {
            const isOpen = expanded[key]
            return (
                <li key={key}>
                    <div
                        className="tree-item"
                        role="button"
                        tabIndex={0}
                        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setExpanded(prev => ({ ...prev, [key]: !prev[key] })))}
                        onClick={() => setExpanded(prev => ({ ...prev, [key]: !prev[key] }))}
                    >
                        <span className="tree-icon">{isOpen ? '📂' : '📁'}</span>
                        <span>{item.name}</span>
                    </div>
                    {isOpen && item.children && (
                        <ul className="tree-children">
                            <TreeNodes items={item.children} selected={selected} onSelect={onSelect} depth={depth + 1} />
                        </ul>
                    )}
                </li>
            )
        }
        return (
            <li key={key}>
                <div
                    className={`tree-item ${selected === item.path ? 'active' : ''}`}
                    role="button"
                    tabIndex={0}
                    onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onSelect(item.path))}
                    onClick={() => onSelect(item.path)}
                >
                    <span className="tree-icon">📄</span>
                    <span>{item.name}</span>
                </div>
            </li>
        )
    })
}


// ====================================================================
// 辅助：数字格式化
// ====================================================================

function formatNumber(n) {
    if (n >= 10000) return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(n / 10000) + ' 万'
    return new Intl.NumberFormat('zh-CN').format(n)
}

function formatJSON(str) {
    try {
        return JSON.stringify(JSON.parse(str), null, 2)
    } catch {
        return str
    }
}

function formatCell(v) {
    if (v === null || v === undefined) return '—'
    if (typeof v === 'boolean') return v ? 'true' : 'false'
    if (typeof v === 'object') {
        try {
            return JSON.stringify(v)
        } catch {
            return String(v)
        }
    }
    const s = String(v)
    return s.length > 180 ? `${s.slice(0, 180)}...` : s
}
