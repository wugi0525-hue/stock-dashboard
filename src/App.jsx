import React, { useState, useEffect, useMemo } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Bar, Area } from 'recharts';
import { Activity, BarChart2, Search, ArrowUpRight, ArrowDownRight, Settings, FileText, Share2 } from 'lucide-react';
import './index.css';
import { collection, getDocs } from 'firebase/firestore';
import { db } from './firebase.js';

import Landing from './pages/Landing';

// ---- Dummy Data for presentation in case Firebase is not configured yet ----
const dummyData = Array.from({ length: 90 }).map((_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (90 - i));
  const basePrice = 150 + i * 1.5 + Math.random() * 20;
  const eps = basePrice / 15 + Math.random() * 2;
  const sectorPER = 18 + Math.random() * 2;
  return {
    date: date.toISOString().split('T')[0],
    price: basePrice,
    eps: eps,
    targetPrice: eps * sectorPER,
    perHighLine: eps * 25,
    perLowLine: eps * 12,
  };
});

const dummyRanking = [
  { rank: 1, ticker: 'NVDA', name: 'Nvidia', divergence: 125.4, sector: 'Technology' },
  { rank: 2, ticker: 'TSLA', name: 'Tesla', divergence: 85.2, sector: 'Consumer Cyclical' },
  { rank: 3, ticker: 'SMCI', name: 'Super Micro', divergence: 72.1, sector: 'Technology' },
  { rank: 4, ticker: 'AMD', name: 'AMD', divergence: 54.8, sector: 'Technology' },
  { rank: 5, ticker: 'META', name: 'Meta', divergence: 42.0, sector: 'Communication Services' },
];

// Main Dashboard Component
function Dashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isFirebaseLoaded, setIsFirebaseLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [dbData, setDbData] = useState([]);
  const [sectorData, setSectorData] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState('NVDA');
  const [showSectorLine, setShowSectorLine] = useState(false);

  const location = useLocation();
  const navigate = useNavigate();

  const handleAction = (actionName) => {
    alert(`${actionName} 기능이 실행되었습니다.`);
  };

  // --- Use Firebase or fallback to dummy ---
  useEffect(() => {
    const hasFirebaseConfig = import.meta.env.VITE_FIREBASE_API_KEY && import.meta.env.VITE_FIREBASE_API_KEY !== "dummy_key";

    if (!hasFirebaseConfig) {
      // 파이어베이스 키가 없으면 바로 더미 데이터로 넘어감 (무한 로딩 방지)
      setTimeout(() => {
        setIsFirebaseLoaded(false);
        setIsLoading(false);
      }, 800);
      return;
    }

    const loadFirebaseData = async () => {
      try {
        const [stockSnap, sectorSnap] = await Promise.all([
          getDocs(collection(db, "USA_Stocks")),
          getDocs(collection(db, "Sector_Trend"))
        ]);
        const fetchedStocks = [];
        stockSnap.forEach((doc) => fetchedStocks.push(doc.data()));
        const fetchedSectors = [];
        sectorSnap.forEach((doc) => fetchedSectors.push(doc.data()));

        if (fetchedStocks.length > 0) {
          setDbData(fetchedStocks);
          setSectorData(fetchedSectors);
          setIsFirebaseLoaded(true);
        }
      } catch (e) {
        console.warn("Firebase fetch failed, using dummy data.", e);
        setIsFirebaseLoaded(false);
      } finally {
        setIsLoading(false);
      }
    };

    loadFirebaseData();
  }, []);

  // Process chart data from raw Firebase data
  const rawChartData = isFirebaseLoaded && dbData.length > 0
    ? dbData.filter(d => d.Ticker === selectedTicker).sort((a, b) => new Date(a.Date) - new Date(b.Date))
    : [];

  let processedChartData = dummyData;
  let currentAnalystCount = 48; // default dummy

  if (rawChartData.length > 0) {
    // Determine dynamic column names from the actual data header
    const firstRow = rawChartData[0];
    const priceCol = ["Price", "Close"].find(c => c in firstRow) || "Price";
    const epsCol = ["NTM_EPS", "Implied EPS", "Implied_EPS", "EPS", "Est_EPS"].find(c => c in firstRow) || "EPS";
    const perCol = ["Implied PER", "NTM_PER", "PER", "Implied_PER"].find(c => c in firstRow) || "PER";
    const sectorVal = firstRow.Sector;

    // Calculate PER min/max for the bands
    const cleanPERs = rawChartData.map(d => Number(d[perCol])).filter(n => !isNaN(n) && n > 0);
    const minPER = cleanPERs.length > 0 ? Math.min(...cleanPERs) : 15;
    const maxPER = cleanPERs.length > 0 ? Math.max(...cleanPERs) : 25;

    // Filter relevant sector data
    const relatedSectors = sectorData.filter(s => s.Sector === sectorVal);
    const sectorPerCol = relatedSectors.length > 0 ? (["Sector PER", "Avg PER", "Sector_PER"].find(c => c in relatedSectors[0]) || "Sector_PER") : "";

    processedChartData = rawChartData.map(d => {
      const price = Number(d[priceCol]) || 0;
      let eps = Number(d[epsCol]);
      let per = Number(d[perCol]);
      if (isNaN(eps) && !isNaN(per) && per > 0) eps = price / per;
      if (isNaN(eps)) eps = 0;

      const sData = relatedSectors.find(s => s.Date === d.Date);
      const sectorPERVal = sData ? Number(sData[sectorPerCol]) : null;

      if (d.Analyst_Count) currentAnalystCount = d.Analyst_Count;

      let dateFmt = String(d.Date);
      if (dateFmt && dateFmt.includes("00:00:00")) dateFmt = dateFmt.split(" ")[0];

      return {
        date: dateFmt,
        price: price,
        eps: eps,
        targetPrice: sectorPERVal ? (eps * sectorPERVal) : null,
        perLowLine: eps * minPER,
        perHighLine: eps * maxPER,
      };
    });
  }
  const chartData = processedChartData;

  // Create Ranking Data
  let processedRankData = dummyRanking;
  if (isFirebaseLoaded && dbData.length > 0) {
    const tickers = [...new Set(dbData.map(d => d.Ticker))];
    const ranks = [];
    tickers.forEach(tk => {
      const tkData = dbData.filter(d => d.Ticker === tk).sort((a, b) => new Date(a.Date) - new Date(b.Date));
      if (tkData.length < 2) return;

      const first = tkData[0];
      const last = tkData[tkData.length - 1];

      const pCol = ["Price", "Close"].find(c => c in first) || "Price";
      const eCol = ["NTM_EPS", "Implied EPS", "Implied_EPS", "EPS", "Est_EPS"].find(c => c in first) || "EPS";
      const perCol = ["Implied PER", "NTM_PER", "PER", "Implied_PER"].find(c => c in first) || "PER";

      const p0 = Number(first[pCol]), p1 = Number(last[pCol]);
      let e0 = Number(first[eCol]), e1 = Number(last[eCol]);

      if (isNaN(e0) && !isNaN(Number(first[perCol])) && Number(first[perCol]) > 0) e0 = p0 / Number(first[perCol]);
      if (isNaN(e1) && !isNaN(Number(last[perCol])) && Number(last[perCol]) > 0) e1 = p1 / Number(last[perCol]);

      if (p0 && e0) {
        const priceChg = ((p1 - p0) / p0) * 100;
        const epsChg = ((e1 - e0) / Math.abs(e0)) * 100;
        ranks.push({
          ticker: tk,
          name: first.Name || tk,
          sector: first.Sector || '',
          divergence: Math.abs(priceChg - epsChg)
        });
      }
    });
    processedRankData = ranks.sort((a, b) => b.divergence - a.divergence).map((r, i) => ({ ...r, rank: i + 1 }));
  }
  const rankData = processedRankData;

  // Value Calculators for UI
  const currentPrice = chartData[chartData.length - 1]?.price || 0;
  const initialPrice = chartData[0]?.price || 1;
  const priceMomentum = (((currentPrice - initialPrice) / initialPrice) * 100).toFixed(1);

  const currentEps = chartData[chartData.length - 1]?.eps || 0;
  const initialEps = chartData[0]?.eps || 1;
  const epsMomentum = (((currentEps - initialEps) / Math.abs(initialEps)) * 100).toFixed(1);

  if (isLoading) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div className="loader"></div>
        <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>파이어베이스 연동 데이터를 가져오는 중...</p>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* PC / Tablet Top Header */}
      <header className="app-header">
        <div className="app-title">
          <Activity size={24} color="var(--accent-color)" />
          Stock Dashboard
        </div>
        <div className="filters-row" style={{ marginBottom: 0 }}>
          <select value={selectedTicker} onChange={e => setSelectedTicker(e.target.value)}>
            <option value="NVDA">Nvidia (NVDA)</option>
            <option value="TSLA">Tesla (TSLA)</option>
            <option value="AAPL">Apple (AAPL)</option>
            <option value="MSFT">Microsoft (MSFT)</option>
          </select>

          <div className="protected-actions">
            <button className="icon-button" onClick={() => handleAction('기록 관리')} title="기록 관리">
              <FileText size={20} />
            </button>
            <button className="icon-button" onClick={() => handleAction('리포트 송부하기')} title="리포트 송부">
              <Share2 size={20} />
            </button>
          </div>

          <div className="nav-item-pc" style={{ display: 'flex', gap: '20px', marginLeft: '20px' }}>
            {/* Desktop Navigation */}
            <button
              className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
              style={{ padding: 0 }}
            >
              상세분석
            </button>
            <button
              className={`nav-item ${activeTab === 'ranking' ? 'active' : ''}`}
              onClick={() => setActiveTab('ranking')}
              style={{ padding: 0 }}
            >
              랭킹
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'dashboard' ? (
          <div className="dashboard-view" style={{ animation: 'fadeIn 0.4s ease-out' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>다이내믹 밸류에이션 리포트</h2>

            <div className="grid-cards">
              <div className="metric-card">
                <div className="metric-title">현재 주가 모멘텀</div>
                <div className="metric-value">${currentPrice.toFixed(2)}</div>
                <div className={`metric-change ${priceMomentum >= 0 ? 'positive' : 'negative'}`}>
                  {priceMomentum >= 0 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                  {Math.abs(priceMomentum)}%
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-title">EPS 변화율 추이</div>
                <div className="metric-value">${currentEps.toFixed(2)}</div>
                <div className={`metric-change ${epsMomentum >= 0 ? 'positive' : 'negative'}`}>
                  {epsMomentum >= 0 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                  {Math.abs(epsMomentum)}%
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-title">애널리스트 커버리지</div>
                <div className="metric-value">{parseInt(currentAnalystCount)}명</div>
                <div className="metric-change neutral">
                  Market Consensus
                </div>
              </div>
            </div>

            {/* Price vs Bands Chart */}
            <div className="chart-container">
              <div className="chart-header">
                <div className="chart-title">주가 vs PER 밴드 트렌드</div>
                <div className="toggle-container" onClick={() => setShowSectorLine(!showSectorLine)}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>섹터 오버레이</span>
                  <div className={`toggle-switch ${showSectorLine ? 'active' : ''}`}>
                    <div className="toggle-thumb" />
                  </div>
                </div>
              </div>
              <div style={{ width: '100%', height: 350 }}>
                <ResponsiveContainer>
                  <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--accent-color)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--accent-color)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="date" stroke="var(--text-secondary)" tick={{ fontSize: 12 }} minTickGap={30} tickMargin={10} axisLine={false} tickLine={false} />
                    <YAxis stroke="var(--text-secondary)" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(val) => `$${val}`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'rgba(22,27,34,0.9)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                    />

                    {/* Lowest & Highest PER Bands */}
                    <Line type="monotone" dataKey="perLowLine" name="최저 PER 밴드" stroke="var(--success-color)" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                    <Line type="monotone" dataKey="perHighLine" name="최고 PER 밴드" stroke="var(--danger-color)" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />

                    {/* Sector Overlay */}
                    {showSectorLine && (
                      <Line type="monotone" dataKey="targetPrice" name="섹터 평균 적정가" stroke="#a78bfa" strokeWidth={2} dot={false} strokeDasharray="3 3" />
                    )}

                    {/* Stock Price Area/Line */}
                    <Area type="monotone" dataKey="price" name="현재 주가" stroke="var(--accent-color)" strokeWidth={3} fillOpacity={1} fill="url(#colorPrice)" activeDot={{ r: 6, fill: "var(--accent-color)", stroke: "#fff", strokeWidth: 2 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* EPS vs Price Comparative Chart */}
            <div className="chart-container">
              <div className="chart-title" style={{ marginBottom: '1.5rem' }}>Price vs EPS Growth</div>
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="date" stroke="var(--text-secondary)" tick={{ fontSize: 12 }} minTickGap={30} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="left" stroke="var(--accent-color)" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="right" orientation="right" stroke="var(--warning-color)" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', borderColor: 'var(--glass-border)', borderRadius: '12px' }} />
                    <Line yAxisId="left" type="monotone" dataKey="price" name="주가" stroke="var(--accent-color)" strokeWidth={2} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="eps" name="EPS 추이" stroke="var(--warning-color)" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>
        ) : (
          <div className="ranking-view" style={{ animation: 'fadeIn 0.4s ease-out' }}>
            <h2 style={{ marginBottom: '0.5rem', fontSize: '1.5rem' }}>🚀 괴리율 랭킹 파노라마</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>이익 대비 주가가 가장 크게 하락/상승하여 편차가 큰 기업의 랭킹입니다.</p>

            <div className="chart-container" style={{ padding: 0, background: 'transparent', boxShadow: 'none', border: 'none' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                {rankData.map((item) => (
                  <div key={item.ticker} className="rank-item" onClick={() => { setSelectedTicker(item.ticker); setActiveTab('dashboard'); }}>
                    <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                      <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-secondary)', width: '30px', textAlign: 'center' }}>{item.rank}</div>
                      <div className="rank-info">
                        <span className="rank-ticker">{item.ticker}</span>
                        <span className="rank-name">{item.name} • {item.sector}</span>
                      </div>
                    </div>
                    <div>
                      <span className="rank-score">{item.divergence.toFixed(1)}%</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: '6px' }}>Diff</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <nav className="bottom-nav">
        <button className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
          <BarChart2 size={24} />
          <span>상세분석</span>
        </button>
        <button className={`nav-item ${activeTab === 'ranking' ? 'active' : ''}`} onClick={() => setActiveTab('ranking')}>
          <Search size={24} />
          <span>랭킹</span>
        </button>
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
