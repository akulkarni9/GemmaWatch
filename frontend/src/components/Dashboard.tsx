import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Activity, AlertTriangle, CheckCircle, Search, RefreshCw, Eye,
  Image as ImageIcon, Plus, Trash2, Globe, X, BarChart3, Wifi,
  Lock, ChevronLeft, ChevronRight, ShieldAlert
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import MetricsChart from './MetricsChart';
import UptimeDisplay from './UptimeDisplay';
import ErrorDistribution from './ErrorDistribution';
import SiteDetails from './SiteDetails';
import RepairPipeline from './RepairPipeline';

interface MonitoringResult {
  site_id: string;
  check_id: string;
  name: string;
  url: string;
  status: 'SUCCESS' | 'FAILED';
  status_code?: number;
  timestamp: string;
  screenshot?: string;
  is_visual_change?: boolean;
  console_log_count?: number;
  network_error_count?: number;
  console_logs?: Array<{ level: string; message: string; timestamp?: string }>;
  network_errors?: Array<{ message: string; status?: number; url?: string }>;
  rca?: {
    probable_cause?: string;
    confidence: number;
    repair_action: string;
    category: string;
  };
  visual_analysis?: {
    is_regression: boolean;
    severity: string;
    change_summary: string;
    impact: string;
  };
  fingerprints?: Array<{
    id: string;
    fingerprint_hash: string;
    title: string;
    description: string;
    severity: string;
    error_type: string;
  }>;
}

interface Site {
  id: string;
  name: string;
  url: string;
  check_type?: string;
  frequency?: number;
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8002';
const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8002';

const Dashboard: React.FC = () => {
  const { isAdmin } = useAuth();
  const [results, setResults] = useState<MonitoringResult[]>([]);
  const [messages, setMessages] = useState<string[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sites, setSites] = useState<Site[]>([]);
  const [showAddSite, setShowAddSite] = useState(false);
  const [newSiteName, setNewSiteName] = useState('');
  const [newSiteUrl, setNewSiteUrl] = useState('');
  const [newSiteCheckType, setNewSiteCheckType] = useState<string>('http');
  const [screenshotModal, setScreenshotModal] = useState<string | null>(null);
  const [consoleLogsModal, setConsoleLogsModal] = useState<Array<{ level: string; message: string; timestamp?: string }> | null>(null);
  const [networkErrorsModal, setNetworkErrorsModal] = useState<Array<{ message: string; status?: number; url?: string }> | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [metricsData, setMetricsData] = useState<any[]>([]);
  const [uptimeData, setUptimeData] = useState<{ uptime_percentage: number; days: number } | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCheckType, setFilterCheckType] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 10;
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<any>(null);
  const fingerprintPollRef = useRef<any>(null);

  // Filter sites based on search query and check type
  const filteredSites = sites.filter((site) => {
    const matchesSearch = !searchQuery || 
      site.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      site.url.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesFilter = !filterCheckType || (site.check_type || 'http') === filterCheckType;
    
    return matchesSearch && matchesFilter;
  });

  // Reset pagination when filter or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterCheckType]);

  const totalPages = Math.ceil(filteredSites.length / PAGE_SIZE);
  const paginatedSites = filteredSites.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  // Filter results based on search query
  const filteredResults = results.filter((result) => {
    const matchesSearch = !searchResults ||
      result.name.toLowerCase().includes(searchResults.toLowerCase()) ||
      result.url.toLowerCase().includes(searchResults.toLowerCase());
    return matchesSearch;
  });

  // True when the selected site has fingerprints still awaiting Gemma's analysis
  const hasPendingFingerprints = results.some(r =>
    r.site_id === selectedSiteId &&
    Array.isArray(r.fingerprints) &&
    r.fingerprints.some(
      (fp: any) => !fp.title || fp.title === 'Unnamed Pattern' || fp.title === ''
    )
  );


  // WebSocket connection with reconnection logic
  useEffect(() => {
    let isMounted = true;
    
    const connect = () => {
      // Avoid connecting if the component has unmounted or if already connecting/open
      if (!isMounted || (wsRef.current && wsRef.current.readyState < 2)) return;
      
      console.log(`Connecting to WebSocket at ${WS_BASE}/ws/status...`);
      const ws = new WebSocket(`${WS_BASE}/ws/status`);
      wsRef.current = ws;
      
      ws.onopen = () => {
        if (!isMounted) return;
        console.log('✅ WebSocket CONNECTED!');
      };
      
      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message received:', JSON.stringify(data, null, 2));
          if (data.type === 'status') {
            setMessages(prev => [data.msg, ...prev.slice(0, 9)]);
          } else if (data.type === 'result') {
            console.log('✅ RESULT MESSAGE RECEIVED:', { site_id: data.site_id, check_id: data.check_id, status: data.status });
            setResults(prev => {
              if (prev.some(r => r.check_id === data.check_id)) {
                console.log('📝 Updating existing result');
                return prev.map(r => r.check_id === data.check_id ? data : r);
              }
              console.log('📝 Adding new result, total now:', prev.length + 1);
              return [data, ...prev];
            });
          }
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      ws.onclose = () => {
        if (!isMounted) return;
        console.log('❌ WebSocket closed. Retrying in 2s...');
        wsRef.current = null;
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(connect, 2000);
      };

      ws.onerror = (err) => {
        if (!isMounted) return;
        console.error('⚠️ WebSocket error:', err);
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, []);

  // Load registered sites
  const fetchSites = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/sites`);
      if (!res.ok) throw new Error('Failed to fetch sites');
      const data = await res.json();
      setSites(data.sites || []);
    } catch (e) { 
      console.error('Fetch sites error:', e); 
    }
  }, []);

  // Auto-select first site when sites load
  useEffect(() => {
    if (sites.length > 0 && !selectedSiteId) {
      setSelectedSiteId(sites[0].id);
    }
  }, [sites, selectedSiteId]);

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  // Add site & trigger first check
  const addSite = async () => {
    if (!newSiteName || !newSiteUrl) return;
    try {
      await fetch(`${API_BASE}/monitor?url=${encodeURIComponent(newSiteUrl)}&name=${encodeURIComponent(newSiteName)}&check_type=${encodeURIComponent(newSiteCheckType)}`, { method: 'POST' });
      setNewSiteName('');
      setNewSiteUrl('');
      setNewSiteCheckType('http');
      setShowAddSite(false);
      setTimeout(fetchSites, 1000);
    } catch (e) { console.error(e); }
  };

  // Delete site
  const deleteSite = async (siteId: string) => {
    try {
      await fetch(`${API_BASE}/sites/${siteId}`, { method: 'DELETE' });
      setSites(prev => prev.filter(s => s.id !== siteId));
    } catch (e) { console.error(e); }
  };

  // Trigger monitoring for a site
  const triggerMonitor = async (url: string, name: string, checkType: string = 'http') => {
    setIsRefreshing(true);
    try {
      await fetch(`${API_BASE}/monitor?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}&check_type=${encodeURIComponent(checkType)}`, { method: 'POST' });
    } catch (e) { console.error(e); }
    setTimeout(() => setIsRefreshing(false), 2000);
  };

  // Fetch metrics and uptime for selected site
  useEffect(() => {
    const fetchMetrics = async () => {
      if (!selectedSiteId) {
        setMetricsData([]);
        setUptimeData(null);
        return;
      }
      setMetricsLoading(true);
      try {
        const [metricsRes, uptimeRes] = await Promise.all([
          fetch(`${API_BASE}/sites/${selectedSiteId}/metrics?limit=20`),
          fetch(`${API_BASE}/sites/${selectedSiteId}/uptime?days=7`)
        ]);
        
        if (metricsRes.ok) {
          const metricsJson = await metricsRes.json();
          setMetricsData(metricsJson.metrics || []);
        }
        if (uptimeRes.ok) {
          const uptimeJson = await uptimeRes.json();
          setUptimeData(uptimeJson);
        }
      } catch (e) {
        console.error('Failed to fetch metrics:', e);
      } finally {
        setMetricsLoading(false);
      }
    };

    fetchMetrics();
  }, [selectedSiteId]);

  // Load historical check results for selected site
  useEffect(() => {
    const fetchHistoricalResults = async () => {
      if (!selectedSiteId) return;
      // Clear stale results immediately so old site's data doesn't flash
      setResults([]);
      setHistoryLoading(true);
      try {
        console.log('📊 Loading historical results for site:', selectedSiteId);
        const res = await fetch(`${API_BASE}/sites/${selectedSiteId}/history?limit=50`);
        if (res.ok) {
          const data = await res.json();
          console.log('📊 Historical results loaded:', data.history?.length || 0, 'check(s)', data.history);
          if (data.history && Array.isArray(data.history)) {
            // Get the site name and URL
            const selectedSite = sites.find(s => s.id === selectedSiteId);
            
            // Convert check history to result format
            const historicalResults = data.history.map((check: any) => ({
              site_id: selectedSiteId,
              check_id: check.id,
              name: selectedSite?.name || 'Unknown',
              url: selectedSite?.url || '',
              status: check.status,
              status_code: check.status_code,
              timestamp: check.timestamp,
              screenshot: check.screenshot || '',
              console_log_count: check.console_log_count || 0,
              network_error_count: check.network_error_count || 0,
              console_logs: check.console_logs || [],
              network_errors: check.network_errors || [],
              rca: check.rca || null,
              fingerprints: check.fingerprints || [],  // ← was missing, dropped fingerprint data
            }));
            
            // Merge with existing results, preferring WebSocket updates
            setResults(prev => {
              const wsResultIds = new Set(prev.map(r => r.check_id));
              const newHistoricalResults = historicalResults.filter(
                (h: MonitoringResult) => !wsResultIds.has(h.check_id)
              );
              console.log('📊 Adding', newHistoricalResults.length, 'new historical results');
              return [...prev, ...newHistoricalResults];
            });
          }
        }
      } catch (e) {
        console.error('Failed to load historical results:', e);
      } finally {
        setHistoryLoading(false);
      }
    };

    fetchHistoricalResults();
  }, [selectedSiteId, sites]);

  // Auto-poll fingerprint metadata until all patterns are named
  useEffect(() => {
    // Clear any existing poll when site or pending state changes
    if (fingerprintPollRef.current) {
      clearInterval(fingerprintPollRef.current);
      fingerprintPollRef.current = null;
    }

    if (!selectedSiteId || !hasPendingFingerprints) return;

    fingerprintPollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/sites/${selectedSiteId}/history?limit=50`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.history || !Array.isArray(data.history)) return;

        // Only patch the fingerprints field on existing results — don't reset the list
        setResults(prev =>
          prev.map(r => {
            const updated = data.history.find((h: any) => h.id === r.check_id);
            if (!updated || !updated.fingerprints) return r;
            return { ...r, fingerprints: updated.fingerprints };
          })
        );
      } catch (e) {
        console.error('Fingerprint poll error:', e);
      }
    }, 10_000);

    return () => {
      if (fingerprintPollRef.current) {
        clearInterval(fingerprintPollRef.current);
        fingerprintPollRef.current = null;
      }
    };
  }, [selectedSiteId, hasPendingFingerprints]);

  // Stats
  const totalChecks = results.length;
  const passCount = results.filter(r => r.status === 'SUCCESS').length;
  const passRate = totalChecks > 0 ? Math.round((passCount / totalChecks) * 100) : 0;

  return (
    <div className="p-6 lg:p-10 font-outfit">
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Checks', value: totalChecks, icon: BarChart3, color: 'text-blue-400' },
          { label: 'Pass Rate', value: `${passRate}%`, icon: CheckCircle, color: 'text-green-400' },
          { label: 'Registered Sites', value: sites.length, icon: Globe, color: 'text-indigo-400' },
          { label: 'Live Connections', value: '●', icon: Wifi, color: 'text-emerald-400' },
        ].map((stat) => (
          <div key={stat.label} className="bg-white/5 backdrop-blur rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 mb-1">
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
              <span className="text-xs text-gray-500 uppercase tracking-wider">{stat.label}</span>
            </div>
            <p className="text-2xl font-bold">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left Column */}
        <div className="lg:col-span-1 space-y-6">
          {/* Registered Sites */}
          <section className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 shadow-xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold flex items-center gap-2 text-white">
                <Globe className="w-5 h-5 text-indigo-400" />
                Registered Sites
              </h2>
              {isAdmin ? (
                <button
                  onClick={() => setShowAddSite(true)}
                  className="p-2 rounded-lg bg-blue-600/10 text-blue-400 hover:bg-blue-600 hover:text-white transition-all"
                  title="Add New Site"
                >
                  <Plus className="w-4 h-4" />
                </button>
              ) : (
                <div className="p-2 text-slate-600" title="Admin only">
                  <Lock className="w-4 h-4" />
                </div>
              )}
            </div>

            {/* Search & Filter */}
            <div className="space-y-3 mb-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search sites..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Filter by check type */}
              <select
                value={filterCheckType || ''}
                onChange={(e) => setFilterCheckType(e.target.value || null)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition"
              >
                <option value="">All Types</option>
                <option value="http">HTTP</option>
                <option value="api">API</option>
                <option value="dns">DNS</option>
                <option value="tcp">TCP</option>
              </select>
            </div>

            {/* Sites list */}
            <div className="space-y-2">
              {sites.length === 0 && (
                <p className="text-gray-500 text-sm">No sites registered yet.</p>
              )}
              {filteredSites.length === 0 && sites.length > 0 && (
                <p className="text-gray-500 text-sm">No sites match your search.</p>
              )}
              {paginatedSites.map((site) => (
                <div 
                  key={site.id} 
                  onClick={() => setSelectedSiteId(site.id)}
                  className={`p-3 rounded-lg flex justify-between items-center group cursor-pointer transition-all ${
                    selectedSiteId === site.id 
                      ? 'bg-blue-500/20 border border-blue-500/50' 
                      : 'bg-white/5 border border-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{site.name}</p>
                    <p className="text-xs text-gray-500 truncate">{site.url}</p>
                    {site.check_type && <p className="text-xs text-gray-600 mt-0.5">{site.check_type.toUpperCase()}</p>}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        triggerMonitor(site.url, site.name, site.check_type || 'http');
                      }}
                      className="p-1.5 rounded-lg hover:bg-blue-500/20 text-blue-400 transition"
                      title="Run check"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                    </button>
                    {isAdmin && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSite(site.id);
                          if (selectedSiteId === site.id) setSelectedSiteId(null);
                        }}
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-400 opacity-0 group-hover:opacity-100 transition"
                        title="Delete site"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentPage(prev => Math.max(1, prev - 1));
                  }}
                  disabled={currentPage === 1}
                  className={`flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-lg transition-all ${
                    currentPage === 1 
                      ? 'text-white/20 cursor-not-allowed' 
                      : 'text-indigo-400 hover:bg-indigo-500/10'
                  }`}
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  Prev
                </button>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    Page <span className="text-indigo-400">{currentPage}</span> of {totalPages}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentPage(prev => Math.min(totalPages, prev + 1));
                  }}
                  disabled={currentPage === totalPages}
                  className={`flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-lg transition-all ${
                    currentPage === totalPages 
                      ? 'text-white/20 cursor-not-allowed' 
                      : 'text-indigo-400 hover:bg-indigo-500/10'
                  }`}
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </section>

          {/* Live Activity Feed */}
          <section className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 shadow-xl">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Search className="w-5 h-5 text-blue-400" />
              Live Activity
            </h2>
            <div className="space-y-2">
              {messages.length === 0 && (
                <p className="text-gray-500 text-sm">Waiting for agent activity...</p>
              )}
              {messages.map((msg, idx) => (
                <div key={idx} className="p-3 bg-white/5 rounded-lg text-sm border-l-2 border-blue-500">
                  {msg}
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right Column: Results */}
        <div className="lg:col-span-3 space-y-6">
          {/* Metrics Visualization */}
          {selectedSiteId && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <UptimeDisplay 
                  uptime={uptimeData?.uptime_percentage || 0}
                  days={uptimeData?.days || 7}
                  loading={metricsLoading}
                />
                <ErrorDistribution 
                  metrics={metricsData}
                  loading={metricsLoading}
                />
              </div>
              <MetricsChart 
                metrics={metricsData}
                loading={metricsLoading}
              />
              
              {/* Site Details Panel */}
              {(() => {
                const selectedResult = results.find(r => r.site_id === selectedSiteId);
                return <SiteDetails 
                  selectedResult={selectedResult || null}
                  isLoading={historyLoading}
                  onViewScreenshot={(url) => setScreenshotModal(url)}
                  onViewConsoleLogs={(logs) => setConsoleLogsModal(logs)}
                  onViewNetworkErrors={(errors) => setNetworkErrorsModal(errors)}
                />;
              })()}
            </div>
          )}

          {results.length === 0 && (
            <div className="bg-white/5 backdrop-blur-md rounded-2xl p-12 border border-white/10 text-center">
              {historyLoading ? (
                <>
                  <div className="relative w-10 h-10 mx-auto mb-4">
                    <div className="absolute inset-0 rounded-full border-2 border-indigo-500/20" />
                    <div className="absolute inset-0 rounded-full border-2 border-t-indigo-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                  </div>
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-bold animate-pulse">Loading results...</p>
                </>
              ) : (
                <>
                  <div className="w-12 h-12 bg-blue-600/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <Activity className="w-6 h-6 text-blue-400" />
                  </div>
                  <p className="text-gray-500">No check results yet. Add a site and trigger the agent!</p>
                </>
              )}
            </div>
          )}

          {results.length > 0 && (
            <div className="mb-6">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search results by name or URL..."
                  value={searchResults}
                  onChange={(e) => setSearchResults(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
                />
                {searchResults && (
                  <button
                    onClick={() => setSearchResults('')}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
                  >
                    ✕
                  </button>
                )}
              </div>
              {selectedSiteId && (
                <p className="text-xs text-gray-500 mt-2">Showing results for selected site only</p>
              )}
            </div>
          )}

          {/* History Loading Spinner */}
          {historyLoading && (
            <div className="flex flex-col items-center justify-center gap-4 py-12">
              <div className="relative w-10 h-10">
                <div className="absolute inset-0 rounded-full border-2 border-indigo-500/20" />
                <div className="absolute inset-0 rounded-full border-2 border-t-indigo-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
              </div>
              <p className="text-xs text-gray-500 uppercase tracking-widest font-bold animate-pulse">Loading results...</p>
            </div>
          )}

          {!historyLoading && results.length > 0 && (() => {
            // Filter results by selected site and search query
            const siteFilteredResults = selectedSiteId 
              ? filteredResults.filter(r => r.site_id === selectedSiteId)
              : filteredResults;
            
            if (siteFilteredResults.length === 0) {
              return (
                <div className="bg-white/5 backdrop-blur-md rounded-2xl p-8 border border-white/10 text-center">
                  <p className="text-gray-500">{selectedSiteId ? 'No historical results for selected site.' : 'No results match your search.'}</p>
                </div>
              );
            }
            
            return siteFilteredResults.map((result) => (
            <div key={result.check_id} className={`bg-white/5 backdrop-blur-md rounded-2xl p-6 border transition-all ${result.status === 'SUCCESS' ? 'border-green-500/30' : 'border-red-500/30'}`}>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold">{result.name}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <p className="text-gray-500 text-xs">{new Date(result.timestamp).toLocaleString()}</p>
                    {result.fingerprints && result.fingerprints.length > 0 && (
                      <div className="flex gap-1.5 overflow-hidden max-w-[400px]">
                        {result.fingerprints.slice(0, 2).map((fp) => (
                          <span key={fp.id} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-tighter whitespace-nowrap">
                            <ShieldAlert className="w-3 h-3" />
                            {fp.title}
                          </span>
                        ))}
                        {result.fingerprints.length > 2 && (
                          <span className="text-[10px] text-slate-500 font-bold self-center">+{result.fingerprints.length - 2} more</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {result.status_code !== undefined && (
                    <span className="text-xs text-gray-500 font-mono">HTTP {result.status_code}</span>
                  )}
                  <div className={`px-3 py-1 rounded-full text-xs font-bold ${result.status === 'SUCCESS' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {result.status}
                  </div>
                </div>
              </div>

              {/* Visual Regression Alert */}
              {result.visual_analysis && (
                <div className="mb-4 p-4 bg-amber-500/10 rounded-xl border border-amber-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Eye className="w-4 h-4 text-amber-400" />
                    <span className="font-bold text-amber-400 uppercase tracking-wider text-xs">Visual Regression Detected</span>
                    <span className={`ml-auto px-2 py-0.5 rounded text-[10px] uppercase font-bold ${result.visual_analysis.severity === 'High' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>
                      {result.visual_analysis.severity}
                    </span>
                  </div>
                  <p className="text-sm text-gray-200 mb-1">{result.visual_analysis.change_summary}</p>
                  <p className="text-xs text-gray-400"><span className="font-bold">Impact:</span> {result.visual_analysis.impact}</p>
                </div>
              )}

              {/* RCA Alert */}
              {result.rca && (
                <div className="mb-4 p-6 bg-red-500/10 rounded-2xl border border-red-500/20">
                  <div className="flex items-center gap-2 mb-4">
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                    <span className="font-bold text-red-400 uppercase tracking-widest text-[10px]">Root Cause Analysis</span>
                    {result.rca.confidence !== undefined && (
                      <span className="ml-auto text-[10px] text-gray-500 font-bold">CONFIDENCE: {Math.round(result.rca.confidence * 100)}%</span>
                    )}
                  </div>
                  {result.rca.probable_cause && (
                    <div className="mb-6 p-4 bg-white/5 rounded-xl border border-white/5">
                       <p className="text-sm text-gray-200 italic">"{result.rca.probable_cause}"</p>
                    </div>
                  )}
                  <div className="space-y-4">
                    <RepairPipeline 
                      steps={(result.rca as any).repair_steps || []} 
                      fallbackAction={result.rca.repair_action}
                    />
                    {result.rca.category && (
                      <div className="pt-2">
                        <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider border border-blue-500/20">{result.rca.category}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Footer */}
              <div className="flex items-center gap-4 mt-4 pt-4 border-t border-white/5 text-xs">
                {result.screenshot && (
                  <button
                    onClick={() => setScreenshotModal(`${API_BASE}${result.screenshot}`)}
                    className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    <ImageIcon className="w-3.5 h-3.5" />
                    View Screenshot
                  </button>
                )}
                {(result.console_log_count ?? 0) > 0 && (
                  <button
                    onClick={() => setConsoleLogsModal(result.console_logs || [])}
                    className="flex items-center gap-1.5 text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
                  >
                    {result.console_log_count} console log(s)
                  </button>
                )}
                {(result.network_error_count ?? 0) > 0 && (
                  <button
                    onClick={() => setNetworkErrorsModal(result.network_errors || [])}
                    className="flex items-center gap-1.5 text-red-400 hover:text-red-300 transition-colors cursor-pointer"
                  >
                    {result.network_error_count} network error(s)
                  </button>
                )}
                {!result.rca && !result.visual_analysis && (
                  <div className="flex items-center gap-1.5 text-green-400">
                    <CheckCircle className="w-3.5 h-3.5" />
                    All checks passed
                  </div>
                )}
              </div>
            </div>
            ));
          })()}
        </div>
      </div>

      {/* Screenshot Modal */}
      {screenshotModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-8" onClick={() => setScreenshotModal(null)}>
          <div className="relative max-w-4xl max-h-[90vh] overflow-auto rounded-2xl border border-white/10" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setScreenshotModal(null)} className="absolute top-3 right-3 bg-black/50 p-1.5 rounded-full text-white hover:bg-black/80 z-10">
              <X className="w-5 h-5" />
            </button>
            <img src={screenshotModal} alt="Screenshot" className="rounded-2xl max-w-full" />
          </div>
        </div>
      )}

      {/* Console Logs Modal */}
      {consoleLogsModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-8" onClick={() => setConsoleLogsModal(null)}>
          <div className="bg-[#0a0a1a] rounded-2xl border border-white/10 w-full max-w-2xl max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-[#0a0a1a] p-6 border-b border-white/10 flex justify-between items-center">
              <h3 className="text-xl font-bold">Console Logs</h3>
              <button onClick={() => setConsoleLogsModal(null)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-3">
              {consoleLogsModal.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-400 mb-3">Detailed console logs not available for this check</p>
                  <p className="text-sm text-gray-500">
                    Run a new check to capture detailed logs and errors from the browser console
                  </p>
                </div>
              ) : (
                consoleLogsModal.map((log, idx) => (
                  <div key={idx} className="p-3 bg-white/5 rounded-lg border border-white/10 font-mono text-sm">
                    <div className="flex items-start gap-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap ${
                        log.level === 'error' ? 'bg-red-500/20 text-red-400' :
                        log.level === 'warn' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {(log.level || 'log').toUpperCase()}
                      </span>
                      <div className="flex-1 break-words text-gray-300">
                        {log.message}
                      </div>
                    </div>
                    {log.timestamp && (
                      <p className="text-xs text-gray-500 mt-2">{new Date(log.timestamp).toLocaleTimeString()}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Network Errors Modal */}
      {networkErrorsModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-8" onClick={() => setNetworkErrorsModal(null)}>
          <div className="bg-[#0a0a1a] rounded-2xl border border-white/10 w-full max-w-2xl max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-[#0a0a1a] p-6 border-b border-white/10 flex justify-between items-center">
              <h3 className="text-xl font-bold">Network Errors</h3>
              <button onClick={() => setNetworkErrorsModal(null)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-3">
              {networkErrorsModal.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-400 mb-3">Detailed network errors not available for this check</p>
                  <p className="text-sm text-gray-500">
                    Run a new check to capture detailed network request failures and API errors
                  </p>
                </div>
              ) : (
                networkErrorsModal.map((error, idx) => (
                  <div key={idx} className="p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                    <div className="flex items-start gap-3 mb-2">
                      <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm text-red-300 break-words">{error.message}</p>
                      </div>
                    </div>
                    {error.status && (
                      <div className="text-xs text-gray-400 ml-7">
                        <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded">Status: {error.status}</span>
                      </div>
                    )}
                    {error.url && (
                      <p className="text-xs text-gray-500 ml-7 mt-2 font-mono break-all">{error.url}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Site Modal */}
      {showAddSite && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-8" onClick={() => setShowAddSite(false)}>
          <div className="bg-[#0a0a1a] rounded-2xl border border-white/10 p-8 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-xl font-bold mb-6">Add Monitored Site</h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Site Name</label>
                <input
                  type="text"
                  value={newSiteName}
                  onChange={(e) => setNewSiteName(e.target.value)}
                  placeholder="e.g. Google"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">URL</label>
                <input
                  type="url"
                  value={newSiteUrl}
                  onChange={(e) => setNewSiteUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Check Type</label>
                <select
                  value={newSiteCheckType}
                  onChange={(e) => setNewSiteCheckType(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                >
                  <option value="http">HTTP/Web Monitor</option>
                  <option value="api">API Endpoint</option>
                  <option value="dns">DNS Resolution</option>
                  <option value="tcp">TCP Connectivity</option>
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowAddSite(false)} className="flex-1 px-4 py-2.5 rounded-xl border border-white/10 text-sm hover:bg-white/5 transition">
                  Cancel
                </button>
                <button onClick={addSite} className="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-sm font-medium transition">
                  Add & Monitor
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
