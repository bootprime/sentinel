import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Filter, RefreshCw, AlertCircle, Info, Shield, Bug, Search } from 'lucide-react';
import { getLogs } from '../api';

const LogViewer = ({ isOpen, onClose }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [filterLevel, setFilterLevel] = useState('ALL'); // ALL, USER, SYSTEM, AUDIT, DEBUG
    const [search, setSearch] = useState('');

    const bottomRef = useRef(null);

    const fetchLogs = async () => {
        setLoading(true);
        // Fetch generic amount, filtering mostly handled on client for search, 
        // but level can be server-side if optimized. 
        // For now, let's fetch 'ALL' from server (up to 100 lines) and filter locally for search,
        // passing 'level' to server if it's not ALL/SEARCH.

        // Server expects level as string or null.
        const serverLevel = filterLevel === 'ALL' ? null : filterLevel;

        const data = await getLogs(100, serverLevel);
        if (Array.isArray(data)) {
            setLogs(data);
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchLogs();
        const interval = setInterval(() => {
            if (autoRefresh) fetchLogs();
        }, 3000);
        return () => clearInterval(interval);
    }, [autoRefresh, filterLevel]);

    // Scroll to bottom on new logs if near bottom? 
    // For now simple scroll.
    useEffect(() => {
        if (bottomRef.current && autoRefresh) {
            bottomRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs, autoRefresh]);

    const getLevelColor = (level) => {
        switch (level?.toUpperCase()) {
            case 'USER': return 'text-green-400 border-green-500/30 bg-green-500/10';
            case 'SYSTEM': return 'text-blue-400 border-blue-500/30 bg-blue-500/10';
            case 'AUDIT': return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
            case 'CRITICAL':
            case 'ERROR': return 'text-red-400 border-red-500/30 bg-red-500/10';
            case 'DEBUG': return 'text-gray-500 border-gray-500/30 bg-gray-500/10';
            default: return 'text-gray-400 border-gray-500/30';
        }
    };

    const getIcon = (level) => {
        switch (level?.toUpperCase()) {
            case 'USER': return <Info size={14} />;
            case 'SYSTEM': return <Terminal size={14} />;
            case 'AUDIT': return <Shield size={14} />;
            case 'ERROR': return <AlertCircle size={14} />;
            case 'DEBUG': return <Bug size={14} />;
            default: return <Info size={14} />;
        }
    };

    const filteredLogs = logs.filter(l =>
        l.message?.toLowerCase().includes(search.toLowerCase()) ||
        l.module?.toLowerCase().includes(search.toLowerCase())
    );

    if (!isOpen) return null;

    return (
        <div className="fixed inset-x-0 bottom-0 h-96 bg-[#0f172a]/95 backdrop-blur-xl border-t border-gray-800 shadow-2xl z-50 flex flex-col transition-all duration-300">

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-[#0f172a]">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 text-blue-400 font-bold tracking-wider text-xs uppercase">
                        <Terminal size={16} /> Sentinel System Logs
                    </div>
                    <div className="flex items-center gap-1 bg-gray-800/50 rounded p-1">
                        {['ALL', 'USER', 'SYSTEM'].map(lvl => (
                            <button
                                key={lvl}
                                onClick={() => setFilterLevel(lvl)}
                                className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${filterLevel === lvl ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}
                            >
                                {lvl}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative group">
                        <Search size={14} className="absolute left-2 top-1.5 text-gray-500 group-focus-within:text-blue-400" />
                        <input
                            type="text"
                            placeholder="Search logs..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="bg-gray-900 border border-gray-700 rounded-md py-1 pl-8 pr-2 text-xs text-gray-300 focus:outline-none focus:border-blue-500 w-48 transition-all"
                        />
                    </div>

                    <button
                        onClick={() => setAutoRefresh(!autoRefresh)}
                        className={`p-1.5 rounded-md border ${autoRefresh ? 'border-green-500/30 text-green-400 bg-green-500/10' : 'border-gray-700 text-gray-500'} transition-all`}
                        title="Auto-scroll"
                    >
                        <RefreshCw size={14} className={autoRefresh ? "animate-spin-slow" : ""} />
                    </button>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-red-500/20 hover:text-red-400 rounded transition-colors text-gray-500"
                    >
                        ✕
                    </button>
                </div>
            </div>

            {/* Log Body */}
            <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                {filteredLogs.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-600 gap-2">
                        <Terminal size={32} opacity={0.2} />
                        <p>No logs found for current filter.</p>
                    </div>
                ) : (
                    filteredLogs.map((log, i) => (
                        <div key={i} className="flex items-start gap-3 hover:bg-white/5 p-1 px-2 rounded -mx-2 transition-colors group">
                            <span className="text-gray-600 shrink-0 select-none w-24">{log.timestamp?.split('T')[1]?.split('.')[0] || '00:00:00'}</span>

                            <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 w-20 justify-center ${getLevelColor(log.level)}`}>
                                {getIcon(log.level)} {log.level}
                            </span>

                            <span className="text-gray-500 shrink-0 w-24 text-[10px] uppercase tracking-wide text-right truncate">
                                {log.module || log.category}
                            </span>

                            <span className="text-gray-300 break-all">
                                {log.message}
                                {log.traceback && (
                                    <details className="mt-1 text-gray-500 cursor-pointer">
                                        <summary className="hover:text-red-400">View Traceback</summary>
                                        <pre className="p-2 bg-black/50 rounded mt-1 text-[10px] overflow-x-auto text-red-300/80">
                                            {log.traceback}
                                        </pre>
                                    </details>
                                )}
                            </span>
                        </div>
                    ))
                )}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};

export default LogViewer;
