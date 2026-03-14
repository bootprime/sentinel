import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Settings, Activity, Shield, Power, Terminal, Wifi, HelpCircle, Info, RefreshCw, Volume2, VolumeX, AlertTriangle, ShieldAlert, Lock, Unlock, User, CreditCard, LogOut, ChevronRight, FileText, Cpu, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { checkSystemStatus, getConfig, updateConfig, getSignals, getLogs, getAuthStatus, updateToken, triggerKillSwitch, triggerManualPause } from './api';
import LogViewer from './components/LogViewer';
import TokenExpiryModal from './components/TokenExpiryModal';
import SentinelWebSocket from './websocket';

// Static Assets Initialization (Outside Component)
const getAudio = (path) => typeof Audio !== 'undefined' ? new Audio(path) : null;
const audioAssets = {
  signal: getAudio('/sounds/signal.mp3'),
  filled: getAudio('/sounds/filled.mp3'),
  critical: getAudio('/sounds/critical.mp3')
};

// Components
const SourceBadge = ({ lastHeartbeat }) => {
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    if (!lastHeartbeat) {
      setIsLive(false);
      return;
    }
    const check = () => {
      const diff = Date.now() - new Date(lastHeartbeat).getTime();
      setIsLive(diff < 15000); // Snappy 15s threshold
    };
    check();
    const interval = setInterval(check, 2000);
    return () => clearInterval(interval);
  }, [lastHeartbeat]);

  return (
    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black border transition-all ${isLive ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' : 'bg-gray-500/10 text-gray-500 border-gray-500/20'}`}>
      <Cpu size={10} className={isLive ? 'animate-pulse' : ''} />
      {isLive ? 'SOURCE LIVE' : 'SOURCE OFFLINE'}
    </div>
  );
};

const BrokerBadge = ({ broker }) => {
  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black border bg-blue-500/10 text-blue-400 border-blue-500/20 transition-all">
      <Zap size={10} />
      {broker || 'NULL'}
    </div>
  );
};

const SystemBadge = ({ status }) => {
  if (!status.online) {
    return (
      <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-red-500/10 text-red-500 border border-red-500/20">
        <div className="w-2 h-2 rounded-full bg-red-500" />
        OFFLINE
      </div>
    );
  }

  const getStyle = (s) => {
    switch (s) {
      case 'READY': return 'bg-green-500/10 text-green-400 border-green-500/20 shadow-[0_0_10px_rgba(34,197,94,0.2)]';
      case 'KILL_SWITCH': return 'bg-red-500/10 text-red-500 border-red-500/20 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.4)]';
      case 'DAILY_LOCK': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default: return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  };

  return (
    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold border transition-all ${getStyle(status.system_state)}`}>
      <Activity size={12} className={status.system_state === 'KILL_SWITCH' ? 'animate-bounce' : ''} />
      {status.system_state || 'SYSTEM UP'}
    </div>
  );
};

const LabelWithTooltip = ({ label, tooltip, align = 'left' }) => {
  const [show, setShow] = useState(false);
  return (
    <div className="flex items-center gap-1.5 mb-1 relative">
      <label className="block text-xs text-muted-foreground">{label}</label>
      <div
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="text-gray-500 hover:text-blue-400 cursor-help transition-all duration-200"
      >
        <HelpCircle size={12} />
      </div>
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className={`absolute z-[100] bottom-full mb-3 w-64 p-3 bg-[#0f172a] border border-blue-500/30 rounded-xl shadow-[0_10px_40px_rgba(0,0,0,0.7)] text-[11px] text-gray-300 leading-relaxed pointer-events-none backdrop-blur-md ${align === 'right' ? 'right-0 origin-bottom-right' : 'left-0 origin-bottom-left'}`}
          >
            <div className="flex items-center gap-2 font-bold text-blue-400 mb-1.5 border-b border-gray-800 pb-1.5 uppercase tracking-wider text-[10px]">
              <Info size={12} /> System Intelligence
            </div>
            {tooltip}
            <div className={`absolute top-full border-[6px] border-transparent border-t-[#0f172a] ${align === 'right' ? 'right-4' : 'left-4'}`}></div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const ConfigPanel = ({ config, onSave, soundEnabled, setSoundEnabled, online }) => {
  const [localConfig, setLocalConfig] = useState(config);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (!isEditing) {
      setLocalConfig(config);
    }
  }, [config, isEditing]);

  const handleChange = (section, key, val) => {
    setLocalConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: val
      }
    }));
  };

  const handleSave = () => {
    const sterilize = (val, type) => {
      if (val === "" || val === null || isNaN(val)) return 0;
      const parsed = type === 'int' ? parseInt(val) : parseFloat(val);
      return isNaN(parsed) ? 0 : parsed;
    };

    let step = sterilize(localConfig.option.strike_step, 'int');
    if (step <= 0) step = 50;
    if (step % 50 !== 0) {
      step = Math.round(step / 50) * 50;
      if (step === 0) step = 50;
    }

    const finalConfig = {
      ...config,
      option: {
        ...localConfig.option,
        strike_step: step,
        strike_offset: sterilize(localConfig.option.strike_offset, 'int'),
      },
      risk: {
        ...localConfig.risk,
        sl_percentage: sterilize(localConfig.risk.sl_percentage, 'float'),
        tp_percentage: sterilize(localConfig.risk.tp_percentage, 'float'),
        sl_points: sterilize(localConfig.risk.sl_points, 'float'),
        tp_points: sterilize(localConfig.risk.tp_points, 'float'),
      }
    };
    onSave(finalConfig);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setLocalConfig(config);
    setIsEditing(false);
  };

  if (!localConfig) return (
    <div className="glass-panel h-full flex flex-col items-center justify-center text-center p-8">
      <div className="bg-red-500/10 p-4 rounded-full mb-4">
        <Wifi size={32} className="text-red-500 animate-pulse" />
      </div>
      <h3 className="text-lg font-bold mb-2">Offline Connection</h3>
      <p className="text-xs text-muted-foreground mb-6">Unable to establish secure link with backend authority.</p>
      <button
        onClick={() => window.location.reload()}
        className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg text-sm font-bold transition-all"
      >
        Retry Handshake
      </button>
    </div>
  );

  return (
    <div className="glass-panel h-full flex flex-col overflow-visible relative">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-semibold flex items-center gap-2 text-primary">
          <Settings size={20} /> Option Setup
        </h2>
        {!isEditing ? (
          <button onClick={() => setIsEditing(true)} className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-1.5 rounded-lg text-sm font-medium border border-gray-700 transition-all active:scale-95">
            Edit
          </button>
        ) : (
          <div className="flex gap-2">
            <button onClick={handleCancel} className="text-gray-500 hover:text-gray-400 px-3 py-1.5 text-sm font-medium transition-all">
              Cancel
            </button>
            <button onClick={handleSave} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-all shadow-lg shadow-blue-500/20 active:scale-95">
              Apply
            </button>
          </div>
        )}
      </div>
      <div className="flex items-center gap-6 mb-6">
        <button
          onClick={() => setSoundEnabled(!soundEnabled)}
          className={`p-2 rounded-lg transition-colors ${soundEnabled ? 'text-blue-400 bg-blue-500/10 hover:bg-blue-500/20' : 'text-gray-500 bg-gray-500/10 hover:bg-gray-500/20'}`}
          title={soundEnabled ? 'Mute Sounds' : 'Unmute Sounds'}
        >
          {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
        </button>

        <div className="flex items-center gap-3 px-4 py-2 bg-black/20 rounded-xl border border-white/5">
          <div className={`w-2 h-2 rounded-full animate-pulse ${online ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
          <span className={`text-xs font-bold tracking-widest ${online ? 'text-green-400' : 'text-red-400'}`}>
            {online ? 'CONNECTED' : 'DISCONNECTED'}
          </span>
        </div>
      </div>

      <div className="space-y-6 flex-1">
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Strike Selection</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <LabelWithTooltip label="Mode" tooltip="Determines the option contract relative to the index price." />
              <select
                value={localConfig.option.option_mode}
                onChange={(e) => handleChange('option', 'option_mode', e.target.value)}
                className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                disabled={!isEditing}
              >
                <option value="ATM">ATM (At The Money)</option>
                <option value="ITM">ITM (In The Money)</option>
                <option value="OTM">OTM (Out The Money)</option>
              </select>
            </div>

            <div>
              <LabelWithTooltip label="Strike Step" tooltip="The interval between strike prices." align="right" />
              <input
                type="text"
                inputMode="numeric"
                value={localConfig.option.strike_step}
                readOnly={!isEditing}
                onChange={(e) => handleChange('option', 'strike_step', e.target.value)}
                className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-pointer' : ''}`}
                onClick={() => !isEditing && setIsEditing(true)}
              />
            </div>

            <div>
              <LabelWithTooltip label="Offset (Steps)" tooltip="Number of steps away from the baseline strike." />
              <input
                type="text"
                inputMode="numeric"
                value={localConfig.option.strike_offset}
                readOnly={!isEditing}
                onChange={(e) => handleChange('option', 'strike_offset', e.target.value)}
                className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-pointer' : ''}`}
                onClick={() => !isEditing && setIsEditing(true)}
              />
            </div>

            <div>
              <LabelWithTooltip label="Expiry" tooltip="Choose between current week or current month contracts." align="right" />
              <select
                value={localConfig.option.expiry_type || 'WEEKLY'}
                onChange={(e) => handleChange('option', 'expiry_type', e.target.value)}
                className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                disabled={!isEditing}
              >
                <option value="WEEKLY">Weekly</option>
                <option value="MONTHLY">Monthly</option>
              </select>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-800 my-4"></div>

        <div className="space-y-4">
          <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Risk Translation</h3>
          <div>
            <LabelWithTooltip label="Method" tooltip="Algorithm used to calculate SL and Target prices." />
            <select
              value={localConfig.risk.mode}
              onChange={(e) => handleChange('risk', 'mode', e.target.value)}
              className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
              disabled={!isEditing}
            >
              <option value="PERCENTAGE">Percentage of Premium</option>
              <option value="FIXED_PREMIUM">Fixed Points</option>
              <option value="DELTA_APPROX">Delta Approximation (Beta)</option>
            </select>
          </div>

          {localConfig.risk.mode === 'PERCENTAGE' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <LabelWithTooltip label="SL %" tooltip="Stop Loss percentage." />
                <input
                  type="text"
                  inputMode="decimal"
                  value={localConfig.risk.sl_percentage}
                  onChange={(e) => handleChange('risk', 'sl_percentage', e.target.value)}
                  className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={!isEditing}
                />
              </div>
              <div>
                <LabelWithTooltip label="TP %" tooltip="Take Profit percentage." align="right" />
                <input
                  type="text"
                  inputMode="decimal"
                  value={localConfig.risk.tp_percentage}
                  onChange={(e) => handleChange('risk', 'tp_percentage', e.target.value)}
                  className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={!isEditing}
                />
              </div>
            </div>
          )}

          {localConfig.risk.mode === 'FIXED_PREMIUM' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <LabelWithTooltip label="SL Points" tooltip="Fixed points Stop Loss." />
                <input
                  type="text"
                  inputMode="decimal"
                  value={localConfig.risk.sl_points}
                  onChange={(e) => handleChange('risk', 'sl_points', e.target.value)}
                  className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={!isEditing}
                />
              </div>
              <div>
                <LabelWithTooltip label="TP Points" tooltip="Fixed points Take Profit." align="right" />
                <input
                  type="text"
                  inputMode="decimal"
                  value={localConfig.risk.tp_points}
                  onChange={(e) => handleChange('risk', 'tp_points', e.target.value)}
                  className={`w-full bg-gray-900/50 border border-gray-800 rounded p-2 text-sm focus:border-blue-500 outline-none transition-opacity ${!isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={!isEditing}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const DisciplinePanel = ({ config, onSave }) => {
  const [localConfig, setLocalConfig] = useState(config);
  const [frictionStep, setFrictionStep] = useState('LOCKED');
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    console.info(`[Auth] Step changed: ${frictionStep}`);
  }, [frictionStep]);

  useEffect(() => {
    // Only reset local state from prop if we aren't currently breaking the seal
    // This allows background updates to sync when locked, but prevents overwriting user typing
    if (frictionStep === 'LOCKED' && config) {
      setLocalConfig(config);
    }
  }, [config, frictionStep]);

  const handleChange = (key, val) => {
    // Keep as string during typing for fluid UI
    setLocalConfig(prev => ({
      ...prev,
      discipline: {
        ...prev.discipline,
        [key]: val
      }
    }));
  };

  const handleSave = async () => {
    // Audit before Save: Final sterilization
    const sterilize = (val, type) => {
      if (val === "" || val === null || isNaN(val)) return 0;
      const parsed = type === 'int' ? parseInt(val) : parseFloat(val);
      return isNaN(parsed) ? 0 : parsed;
    };

    const final = {
      ...config, // Master Sync - pull absolute latest option/risk data
      discipline: {
        ...localConfig.discipline,
        max_trades_per_day: sterilize(localConfig.discipline.max_trades_per_day, 'int'),
        trade_qty: sterilize(localConfig.discipline.trade_qty, 'int'),
        max_daily_loss: -Math.abs(sterilize(localConfig.discipline.max_daily_loss, 'float')),
        max_daily_profit: sterilize(localConfig.discipline.max_daily_profit, 'float'),
        min_rr_ratio: sterilize(localConfig.discipline.min_rr_ratio, 'float'),
      }
    };

    setIsProcessing(true);
    try {
      console.info("[Auth] Initializing Discipline Overwrite...");
      await onSave(final);
      setFrictionStep('LOCKED');
    } finally {
      setIsProcessing(false);
    }
  };

  if (!localConfig || !localConfig.discipline) return (
    <div className="glass-panel h-24 flex items-center justify-center text-xs text-gray-500 italic opacity-50">
      Initializing Discipline Module...
    </div>
  );

  return (
    <div className={`glass-panel flex flex-col transition-all duration-500 border-2 relative ${frictionStep !== 'LOCKED' ? 'border-amber-500/40 shadow-[0_0_20px_rgba(245,158,11,0.1)]' : 'border-white/5'}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className={`text-xl font-semibold flex items-center gap-2 ${frictionStep !== 'LOCKED' ? 'text-amber-400' : 'text-primary'}`}>
          <ShieldAlert size={20} /> Discipline Protocol
        </h2>

        {frictionStep === 'LOCKED' && (
          <button
            onClick={() => setFrictionStep('CONFIRM_1')}
            className="flex items-center gap-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest border border-amber-500/20 transition-all border-dashed"
          >
            <Lock size={12} /> Break Rule Seal
          </button>
        )}

        {frictionStep === 'CONFIRM_1' && (
          <button
            onClick={() => setFrictionStep('CONFIRM_2')}
            className="bg-red-500 text-white px-4 py-1.5 rounded-lg text-[10px] font-black animate-pulse uppercase tracking-tighter"
          >
            I AM ACTING IMPULSIVELY? (STEP 1/2)
          </button>
        )}

        {frictionStep === 'CONFIRM_2' && (
          <button
            onClick={() => setFrictionStep('EDITING')}
            className="bg-red-600 text-white px-4 py-1.5 rounded-lg text-[11px] font-black uppercase shadow-2xl shadow-red-500/50"
          >
            CONFIRM: I WILL ADHERE TO NEW RULES (FINAL)
          </button>
        )}

        {frictionStep === 'EDITING' && (
          <div className="flex gap-2">
            <button onClick={() => setFrictionStep('LOCKED')} disabled={isProcessing} className="text-gray-500 hover:text-gray-400 px-3 py-1.5 text-sm font-medium transition-all disabled:opacity-30">
              Abort
            </button>
            <button
              onClick={handleSave}
              disabled={isProcessing}
              className="bg-amber-600 hover:bg-amber-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-all shadow-lg shadow-amber-500/20 active:scale-95 disabled:grayscale disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? 'Authorizing...' : 'Overwrite Rules'}
            </button>
          </div>
        )}
      </div>

      <div className={`space-y-5 transition-opacity duration-300 ${frictionStep !== 'EDITING' ? 'opacity-40 grayscale' : 'opacity-100'}`}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <LabelWithTooltip label="Max Day Trades" tooltip="Hard limit on number of authorized entry signals per calendar day." />
            <input
              type="text"
              inputMode="numeric"
              value={localConfig.discipline.max_trades_per_day}
              readOnly={frictionStep !== 'EDITING'}
              onChange={(e) => handleChange('max_trades_per_day', e.target.value)}
              className={`w-full bg-black/40 border border-amber-500/20 rounded p-2 text-sm focus:border-amber-500 outline-none text-amber-100 ${frictionStep !== 'EDITING' ? 'cursor-default opacity-50' : 'cursor-text'}`}
            />
          </div>
          <div>
            <LabelWithTooltip label="Daily Profit Stop" tooltip="Target ₹ profit at which system locks to safeguard gains." align="right" />
            <input
              type="text"
              inputMode="decimal"
              value={localConfig.discipline.max_daily_profit}
              readOnly={frictionStep !== 'EDITING'}
              onChange={(e) => handleChange('max_daily_profit', e.target.value)}
              className={`w-full bg-black/40 border border-amber-500/20 rounded p-2 text-sm focus:border-amber-500 outline-none text-amber-100 ${frictionStep !== 'EDITING' ? 'cursor-default opacity-50' : 'cursor-text'}`}
            />
          </div>
          <div>
            <LabelWithTooltip label="Daily Drawdown" tooltip="Max ₹ loss allowed before permanent intraday lockout (Enter negative)." />
            <input
              type="text"
              inputMode="decimal"
              value={localConfig.discipline.max_daily_loss}
              readOnly={frictionStep !== 'EDITING'}
              onChange={(e) => handleChange('max_daily_loss', e.target.value)}
              className={`w-full bg-black/40 border border-amber-500/20 rounded p-2 text-sm focus:border-amber-500 outline-none text-red-400 ${frictionStep !== 'EDITING' ? 'cursor-default opacity-50' : 'cursor-text'}`}
            />
          </div>
          <div>
            <LabelWithTooltip label="Min R:R Ratio" tooltip="Minimum Risk-to-Reward ratio required for signal authorization." align="right" />
            <input
              type="text"
              inputMode="decimal"
              value={localConfig.discipline.min_rr_ratio}
              readOnly={frictionStep !== 'EDITING'}
              onChange={(e) => handleChange('min_rr_ratio', e.target.value)}
              className={`w-full bg-black/40 border border-amber-500/20 rounded p-2 text-sm focus:border-amber-500 outline-none text-green-400 ${frictionStep !== 'EDITING' ? 'cursor-default opacity-50' : 'cursor-text'}`}
            />
          </div>
          <div>
            <LabelWithTooltip label="Trade Quantity" tooltip="Authorative execution size per authorized signal." />
            <input
              type="text"
              inputMode="numeric"
              value={localConfig.discipline.trade_qty}
              readOnly={frictionStep !== 'EDITING'}
              onChange={(e) => handleChange('trade_qty', e.target.value)}
              className={`w-full bg-black/40 border border-amber-500/20 rounded p-2 text-sm focus:border-amber-500 outline-none text-blue-400 font-bold ${frictionStep !== 'EDITING' ? 'cursor-default' : 'cursor-text'}`}
            />
          </div>
        </div>

        <div className="pt-2 border-t border-white/5">
          <h3 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3">Operational Session</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <span className="text-[9px] text-gray-500 block mb-1">Start Time</span>
              <input
                type="text" value={localConfig.discipline.session_start}
                readOnly={frictionStep !== 'EDITING'}
                onChange={(e) => handleChange('session_start', e.target.value)}
                className={`w-full bg-black/20 border border-white/5 rounded p-1.5 text-xs font-mono ${frictionStep !== 'EDITING' ? 'cursor-default opacity-50' : 'cursor-text'}`}
              />
            </div>
            <div>
              <span className="text-[9px] text-gray-500 block mb-1">End Time</span>
              <input
                type="text" value={localConfig.discipline.session_end}
                readOnly={frictionStep !== 'EDITING'}
                onChange={(e) => handleChange('session_end', e.target.value)}
                className={`w-full bg-black/20 border border-white/5 rounded p-1.5 text-xs font-mono ${frictionStep !== 'EDITING' ? 'cursor-default opacity-50' : 'cursor-text'}`}
              />
            </div>
            <div>
              <span className="text-[9px] text-gray-500 block mb-1">Last Entry</span>
              <input
                type="text" value={localConfig.discipline.last_entry}
                readOnly={frictionStep !== 'EDITING'}
                onChange={(e) => handleChange('last_entry', e.target.value)}
                className={`w-full bg-black/20 border border-white/5 rounded p-1.5 text-xs font-mono mb-6 ${frictionStep !== 'EDITING' ? 'cursor-default opacity-50' : 'cursor-text'}`}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const SignalFeed = ({ signals = [] }) => {
  return (
    <div className="glass-panel h-full flex flex-col">
      <h2 className="text-xl font-semibold flex items-center gap-2 text-primary mb-6">
        <Activity size={20} /> Signal Feed
      </h2>
      <div className="flex-1 overflow-y-auto space-y-3 pr-2">
        {signals.length === 0 ? (
          <div className="text-center text-muted-foreground py-10 text-sm">Waiting for signals...</div>
        ) : (
          signals.map((entry, i) => {
            if (!entry || !entry.signal) return null;
            const sig = entry.signal;
            const opt = entry.option || {};
            const isProtected = entry.status === "FULLY_PROTECTED";
            const isPartial = entry.fill && entry.fill.qty < 50; // Mock lot size 50
            const isFlattened = entry.status === "FLATTENED";

            return (
              <div key={i} className={`bg-gray-800/50 p-4 rounded-xl border transition-all group ${isFlattened ? 'border-red-500/50 bg-red-500/5' : isProtected ? 'border-green-500/20 hover:border-green-500/40' : 'border-blue-500/20 animate-pulse'}`}>
                <div className="flex justify-between items-start mb-2">
                  <div className="flex flex-col">
                    <span className={`font-bold text-base ${sig.direction === 'CALL' ? 'text-green-400' : 'text-red-400'}`}>
                      {sig.symbol} {sig.direction}
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">{sig.signal_id}</span>
                  </div>
                  <div className={`text-[10px] px-2 py-0.5 rounded border font-bold ${isFlattened ? 'bg-red-600/10 text-red-400 border-red-600/20' : isProtected ? 'bg-green-600/10 text-green-400 border-green-600/20' : 'bg-blue-600/10 text-blue-400 border-blue-600/20'}`}>
                    {opt.strike}
                  </div>
                </div>

                {/* Index Reference */}
                <div className="grid grid-cols-3 gap-3 text-[11px] text-gray-400 mb-4 bg-black/20 p-2 rounded-lg border border-white/5">
                  <div className="flex flex-col">
                    <span className="text-[9px] uppercase tracking-wider text-gray-600 mb-0.5">Index Entry</span>
                    <span className="text-gray-200 font-mono">{sig.index_entry}</span>
                  </div>
                  <div className="flex flex-col border-l border-white/5 pl-3">
                    <span className="text-[9px] uppercase tracking-wider text-gray-600 mb-0.5">SL</span>
                    <span className="text-red-400/80 font-mono italic">{sig.index_sl}</span>
                  </div>
                  <div className="flex flex-col border-l border-white/5 pl-3">
                    <span className="text-[9px] uppercase tracking-wider text-gray-600 mb-0.5">TP</span>
                    <span className="text-green-400/80 font-mono italic">{sig.index_tp}</span>
                  </div>
                </div>

                {/* Execution Enforcement */}
                <div className="mb-2">
                  <h4 className={`text-[9px] font-bold uppercase tracking-widest mb-2 flex items-center gap-1.5 ${isFlattened ? 'text-red-500' : isProtected ? 'text-green-500' : 'text-blue-400'}`}>
                    {isFlattened ? <AlertTriangle size={10} /> : isProtected ? <Shield size={10} /> : <Activity size={10} />}
                    {isFlattened ? 'EMERGENCY FLATTENED' : isProtected ? (isPartial ? 'Partial Protection' : 'Protected Execution') : 'Gateway Authorization'}
                  </h4>

                  {(isProtected || isFlattened) ? (
                    <>
                      <div className={`grid grid-cols-2 gap-2 p-2 rounded border ${isFlattened ? 'bg-red-500/5 border-red-500/10' : 'bg-green-500/5 border-green-500/10'}`}>
                        <div className="flex justify-between items-center text-[10px]">
                          <span className="text-gray-500">Premium SL</span>
                          <span className="text-red-400 font-bold font-mono">₹{entry.risk?.sl_price?.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center text-[10px] border-l border-white/5 pl-2">
                          <span className="text-gray-500">Premium TP</span>
                          <span className="text-green-400 font-bold font-mono">₹{entry.risk?.tp_price?.toFixed(2)}</span>
                        </div>
                      </div>
                      <p className="text-[9px] text-gray-600 mt-2 italic px-1 flex justify-between">
                        <span>Filled @ ₹{entry.risk?.estimated_premium}</span>
                        {entry.fill && <span className={isPartial ? 'text-amber-500 font-bold' : ''}>Qty: {entry.fill.qty}</span>}
                      </p>
                    </>
                  ) : (
                    <div className="p-3 text-center border border-dashed border-blue-500/20 rounded-lg text-[10px] text-blue-400/60 font-medium italic">
                      Verifying Broker Fill...
                    </div>
                  )}
                </div>

                <div className="pt-2 border-t border-gray-800/50 flex items-center justify-between text-[10px]">
                  <span className="text-gray-500">{sig.bar_time}</span>
                  <span className={`transition-colors font-bold ${isFlattened ? 'text-red-500' : isProtected ? 'text-green-500' : 'text-blue-500'}`}>
                    {isFlattened ? 'HALTED' : isProtected ? 'ENFORCED' : 'MATCHED'}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

const ProfileDrawer = ({ isOpen, onClose, config, onSave, onLogout, onKillSwitch, onPause, systemState }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200]"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full max-w-[400px] bg-[#0f172a] border-l border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)] z-[201] flex flex-col"
          >
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <User className="text-blue-500" size={20} /> User Authority
              </h3>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors text-gray-500">
                <ChevronRight size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8">
              {/* User Profile Info */}
              <section className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-white/5 rounded-2xl border border-white/5">
                  <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center font-bold text-xl text-white">
                    R
                  </div>
                  <div>
                    <h4 className="font-bold">Raj Sentinel</h4>
                    <p className="text-xs text-gray-500">Authority Level: Admin</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 block mb-1 uppercase tracking-widest font-bold">Broker Link</span>
                    <span className="text-xs font-mono text-green-400">ZERODHA (Active)</span>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                    <span className="text-[10px] text-gray-500 block mb-1 uppercase tracking-widest font-bold">Session IP</span>
                    <span className="text-xs font-mono text-gray-400">127.0.0.1</span>
                  </div>
                </div>
              </section>

              {/* Subscription Details */}
              <section className="space-y-3">
                <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2">
                  <CreditCard size={12} /> Plan Details
                </h4>
                <div className="bg-blue-600/10 border border-blue-500/20 p-4 rounded-xl relative overflow-hidden group">
                  <div className="relative z-10">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-bold text-blue-400">Sentinel PRO</span>
                      <span className="text-[10px] bg-blue-500 text-white px-2 py-0.5 rounded font-black">LIFETIME</span>
                    </div>
                    <p className="text-[11px] text-blue-300/80 leading-relaxed">
                      Advanced High-Authority Execution inclusive of Post-Fill Protection & Sound Engines.
                    </p>
                  </div>
                  <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full -mr-12 -mt-12 group-hover:scale-150 transition-transform duration-700"></div>
                </div>
              </section>

              {/* Discipline Panel Integration */}
              <section>
                <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
                  <ShieldAlert size={12} className="text-amber-500" /> Institutional Safety
                </h4>
                <DisciplinePanel config={config} onSave={onSave} />
              </section>
              {/* Governance Control Block */}
              <section className="space-y-3">
                <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2">
                  <Shield size={12} className="text-red-500" /> Administrative Override
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={onPause}
                    disabled={systemState === 'MANUAL_PAUSE' || systemState === 'KILL_SWITCH'}
                    className={`flex items-center justify-center gap-2 py-3 rounded-xl text-[11px] font-black transition-all border ${systemState === 'MANUAL_PAUSE' ? 'bg-amber-500 text-black border-amber-600' : 'bg-gray-800 text-gray-400 border-white/5 hover:text-amber-400 hover:border-amber-500/30'}`}
                  >
                    <Power size={14} /> {systemState === 'MANUAL_PAUSE' ? 'PAUSED' : 'PAUSE'}
                  </button>
                  <button
                    onClick={onKillSwitch}
                    className="flex items-center justify-center gap-2 py-3 rounded-xl bg-red-600 hover:bg-red-500 text-white text-[11px] font-black shadow-[0_0_15px_rgba(220,38,38,0.3)] hover:shadow-[0_0_20px_rgba(220,38,38,0.5)] transition-all border border-red-500/20"
                  >
                    <AlertTriangle size={14} /> KILL SWITCH
                  </button>
                </div>
              </section>
            </div>

            <div className="p-6 border-t border-white/5 bg-black/20 text-center">
              <button
                onClick={onLogout}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-500 text-xs font-bold transition-all border border-red-500/10"
              >
                <LogOut size={14} /> Revoke UI Authority (Logout)
              </button>
              <p className="text-[9px] text-gray-400 mt-2 uppercase tracking-tighter">⚠️ Engine will continue to run in background</p>
              <p className="text-[9px] text-gray-600 mt-4">Sentinel Prime v1.2.0 • Build 250126</p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

function App() {
  const [status, setStatus] = useState({ online: false });
  const [isInitializing, setIsInitializing] = useState(true);
  const [config, setConfig] = useState(null);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isLogViewerOpen, setIsLogViewerOpen] = useState(false);
  const [uiMessage, setUiMessage] = useState(null);
  const [signals, setSignals] = useState([]);
  const [logs, setLogs] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [tokenExpiry, setTokenExpiry] = useState({ isExpired: false, broker: null });
  const [wsConnected, setWsConnected] = useState(false);
  const [livePrices, setLivePrices] = useState({}); // {symbol: {price, timestamp, volume, change_24h}}
  const wsRef = useRef(null);

  const playSound = (type) => {
    if (!soundEnabled) return;
    const sound = audioAssets[type];
    if (sound) {
      sound.currentTime = 0;
      sound.play().catch(e => console.warn("Audio blocked", e));
    }
  };

  // Sound Alert Monitor
  useEffect(() => {
    if (signals.length === 0) return;

    const latest = signals[0];
    if (latest.status === "FULLY_PROTECTED") {
      playSound('filled');
    } else if (latest.status === "FLATTENED") {
      playSound('critical');
    } else {
      playSound('signal');
    }
  }, [signals.length, signals[0]?.status]);

  // Initialize WebSocket connection
  useEffect(() => {
    // Create WebSocket instance
    const ws = new SentinelWebSocket('ws://127.0.0.1:8001/ws');
    wsRef.current = ws;

    // Connection handlers
    ws.onConnect(() => {
      console.log('[App] WebSocket connected');
      setWsConnected(true);
      setStatus(prev => ({ ...prev, online: true })); // Force immediate Green
      // Initial data fetch on connection
      refreshStatus();
      refreshConfig();
      refreshSignals();
      refreshLogs();
      refreshAuthStatus();
    });

    ws.onDisconnect(() => {
      console.log('[App] WebSocket disconnected');
      setWsConnected(false);
      setStatus(prev => ({ ...prev, online: false })); // Force immediate Red
    });

    // Message handlers for real-time updates
    ws.on('state_change', (data) => {
      console.log('[App] State change received:', data);
      setStatus(prev => ({
        ...prev,
        online: true,
        system_state: data.state,
        trades_today: data.trades_today,
        daily_pnl: data.daily_pnl,
        weekly_pnl: data.weekly_pnl
      }));
    });

    ws.on('signal', (data) => {
      console.log('[App] New signal received:', data);
      refreshSignals(); // Refresh signal list
      playSound('signal');
    });

    ws.on('fill', (data) => {
      console.log('[App] Fill event received:', data);
      refreshSignals(); // Refresh to show updated status
      playSound('filled');
    });

    ws.on('log', (data) => {
      console.log('[App] Log entry received:', data);
      setLogs(prev => [data, ...prev].slice(0, 100)); // Keep last 100 logs
    });

    // Add state override listener
    ws.on('state_change', (data) => {
      // If we were just flattened or killed, play the critical sound
      if (data.state === 'KILL_SWITCH') {
        playSound('critical');
      }
    });

    ws.on('token_expiry', (data) => {
      console.log('[App] Token expiry warning:', data);
      setTokenExpiry({
        isExpired: true,
        broker: data.broker,
        hoursRemaining: data.hours_remaining
      });
    });

    // Connect
    ws.connect();

    // Immediate initial check (don't wait for WS if backend is down)
    refreshStatus();

    // Fallback polling (every 5s)
    const fallbackInterval = setInterval(() => {
      if (!ws || !ws.isConnected()) {
        console.log('[App] WebSocket disconnected, using fallback polling');
        refreshStatus();
        refreshSignals();
      }
    }, 5000);

    // Cleanup on unmount
    return () => {
      clearInterval(fallbackInterval);
      ws.disconnect();
    };
  }, []);

  const refreshStatus = async () => {
    try {
      const s = await checkSystemStatus();
      setStatus({
        online: s.status === 'alive',
        system_state: s.system_state || 'UNKNOWN',
        mode: s.mode || 'UNKNOWN',
        last_source_heartbeat: s.last_source_heartbeat || null,
        execution_broker: s.execution_broker || 'NULL'
      });
      if (s.status === 'alive') {
        setIsInitializing(false);
      } else {
        setIsInitializing(false); // Force UI load even if offline
      }
    } catch (e) {
      setStatus(prev => ({ ...prev, online: false }));
      setIsInitializing(false); // Allow UI to load even if backend is offline
    }
  };

  const refreshConfig = async () => {
    try {
      const c = await getConfig();
      setConfig(c);
    } catch (e) { }
  };

  const refreshSignals = async () => {
    try {
      const sList = await getSignals();
      setSignals(sList);
    } catch (e) { }
  };

  const refreshLogs = async () => {
    try {
      const lList = await getLogs(50, 'SYSTEM');
      setLogs(lList);
    } catch (e) { }
  };

  const refreshAuthStatus = async () => {
    try {
      const authStatus = await getAuthStatus();
      if (authStatus && authStatus.token_status && !authStatus.token_status.valid) {
        // Only show modal if broker is not NULL (i.e., user has configured a real broker)
        if (authStatus.broker && authStatus.broker !== 'NULL') {
          setTokenExpiry({ isExpired: true, broker: authStatus.broker });
        }
      } else {
        setTokenExpiry({ isExpired: false, broker: null });
      }
    } catch (e) {
      console.error('Auth status check failed:', e);
    }
  };

  const handleTokenUpdate = async ({ broker, access_token, client_id }) => {
    try {
      await updateToken(broker, access_token, client_id);
      setTokenExpiry({ isExpired: false, broker: null });
      // Refresh status to get updated broker info
      await refreshStatus();
    } catch (error) {
      throw error;
    }
  };

  const logEndRef = useRef(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleConfigSave = async (newConf) => {
    try {
      setUiMessage({ text: "Authorizing Update...", type: "info" });
      await updateConfig(newConf);
      await refreshConfig();
      setUiMessage({ text: "Authority Overwritten Successfully!", type: "success" });
      setTimeout(() => setUiMessage(null), 3000);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setUiMessage({ text: `AUTHORITY FAILURE: ${msg}`, type: "error" });
      setTimeout(() => setUiMessage(null), 5000);
      console.error(`SYSTEM: Authority update failed - ${msg}`);
    }
  };

  const handleKillSwitch = async () => {
    if (!window.confirm("🚨 EMERGENCY KILL SWITCH 🚨\n\nThis will FLATTEN all active positions and LOCK the system. Are you absolutely certain?")) return;

    try {
      setUiMessage({ text: "Activating Kill Switch...", type: "info" });
      await triggerKillSwitch();
      await refreshStatus();
      setUiMessage({ text: "System Locked. All positions flattened.", type: "error" });
      setTimeout(() => setUiMessage(null), 5000);
    } catch (err) {
      setUiMessage({ text: "Kill Switch Failed!", type: "error" });
    }
  };

  const handlePause = async () => {
    try {
      await triggerManualPause();
      await refreshStatus();
      setUiMessage({ text: "System Manually Paused", type: "info" });
      setTimeout(() => setUiMessage(null), 3000);
    } catch (err) {
      setUiMessage({ text: "Pause Failed", type: "error" });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('sentinel_token');
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6 font-sans selection:bg-blue-500/30 overflow-hidden h-screen flex flex-col">
      {/* Initialization Overlay */}
      <AnimatePresence>
        {isInitializing && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[500] bg-[#020617] flex flex-col items-center justify-center"
          >
            <motion.div
              animate={{
                scale: [1, 1.1, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{ repeat: Infinity, duration: 2 }}
              className="mb-8"
            >
              <Shield className="text-blue-500" size={80} />
            </motion.div>
            <h2 className="text-xl font-bold tracking-widest text-white mb-2 font-mono uppercase">Initializing Sentinel Prime</h2>
            <div className="text-[10px] text-blue-400 font-mono tracking-widest animate-pulse">CONNECTING TO EXECUTION AUTHORITY...</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Authority Notification Overlay */}
      <AnimatePresence>
        {uiMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-24 left-1/2 -translate-x-1/2 z-[300]"
          >
            <div className={`px-6 py-3 rounded-2xl border shadow-2xl backdrop-blur-xl flex items-center gap-3 font-bold text-sm tracking-wide ${uiMessage.type === 'success' ? 'bg-green-500/20 border-green-500/30 text-green-400' :
              uiMessage.type === 'error' ? 'bg-red-500/20 border-red-500/30 text-red-400' :
                'bg-blue-500/20 border-blue-500/30 text-blue-400'
              }`}>
              {uiMessage.type === 'success' ? <Shield size={18} /> : uiMessage.type === 'error' ? <AlertTriangle size={18} /> : <Activity size={18} />}
              {uiMessage.text}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <header className="flex items-center justify-between mb-8 shrink-0">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Shield className="text-white" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Sentinel <span className="text-blue-500">Prime</span></h1>
            <p className="text-xs text-muted-foreground tracking-widest uppercase">Execution Authority</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <BrokerBadge broker={status.execution_broker} />
          <SourceBadge lastHeartbeat={status.last_source_heartbeat} />
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-2 rounded-lg transition-colors ${soundEnabled ? 'text-blue-400 bg-blue-500/10 hover:bg-blue-500/20' : 'text-gray-500 bg-gray-500/10 hover:bg-gray-500/20'}`}
            title={soundEnabled ? 'Mute Sounds' : 'Unmute Sounds'}
          >
            {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
          </button>



          <button
            onClick={() => {
              refreshStatus();
              refreshConfig();
              refreshSignals();
              refreshLogs();
            }}
            className="p-2 text-gray-500 hover:text-blue-400 transition-colors"
            title="Force System Refresh"
          >
            <RefreshCw size={18} />
          </button>
          <button
            onClick={() => setIsLogViewerOpen(!isLogViewerOpen)}
            className={`p-2 transition-colors ${isLogViewerOpen ? 'text-blue-400 bg-blue-500/10' : 'text-gray-500 hover:text-blue-400'}`}
            title="Toggle System Logs"
          >
            <FileText size={18} />
          </button>
          <SystemBadge status={status} />

          <button
            onClick={() => setIsProfileOpen(true)}
            className="flex items-center gap-2 p-1.5 pr-4 bg-white/5 hover:bg-white/10 rounded-full border border-white/5 transition-all group"
          >
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center font-bold text-sm text-white shadow-lg">
              R
            </div>
            <div className="text-left hidden md:block">
              <div className="text-[10px] font-bold leading-none mb-0.5">Admin</div>
              <div className="text-[8px] text-blue-400 font-mono leading-none tracking-widest">PRO PLAN</div>
            </div>
          </button>

          <div className="text-xs text-gray-500 font-mono">v1.2.0</div>
        </div>
      </header>

      {/* Profile Authority Overlay */}
      <ProfileDrawer
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        config={config}
        onSave={handleConfigSave}
        onLogout={handleLogout}
        onKillSwitch={handleKillSwitch}
        onPause={handlePause}
        systemState={status.system_state}
      />

      {/* Main Grid */}
      <main className="grid grid-cols-12 gap-6 flex-1 min-h-0 overflow-hidden">

        {/* Left Col: Option Setup */}
        <div className="col-span-12 md:col-span-4 lg:col-span-3">
          <ConfigPanel
            config={config}
            onSave={handleConfigSave}
            soundEnabled={soundEnabled}
            setSoundEnabled={setSoundEnabled}
            online={status.online || wsConnected}
          />
        </div>

        {/* Middle Col: Signal Feed */}
        <div className="col-span-12 md:col-span-4 lg:col-span-5 flex flex-col min-h-0">
          <SignalFeed signals={signals} />
        </div>

        {/* Right Col: Logs & Status */}
        <div className="col-span-12 md:col-span-4 lg:col-span-4 flex flex-col gap-6 min-h-0 overflow-hidden">
          <div className="glass-panel flex-1 flex flex-col min-h-0">
            <h2 className="text-xl font-semibold flex items-center gap-2 text-primary mb-4 shrink-0">
              <Terminal size={20} /> System Logs
            </h2>
            <div className="font-mono text-[10px] text-gray-400 space-y-1 overflow-y-auto flex-1 pr-2 custom-scrollbar overflow-x-hidden">
              {logs.length === 0 ? (
                <div className="text-gray-600 italic">No system logs available...</div>
              ) : (
                (() => {
                  // Filter logs to show only the current session (from last startup)
                  // Filter logs to show only the current session (from last startup)
                  let displayLogs = logs;
                  // Since logs are newest-first [newest, ..., oldest], 
                  // the FIRST "Starting Up" message we encounter is the LATEST session start.
                  for (let i = 0; i < logs.length; i++) {
                    const msg = typeof logs[i] === 'string' ? logs[i] : logs[i].message || '';
                    if (msg.includes("Sentinel System Starting Up")) {
                      displayLogs = logs.slice(0, i + 1);
                      break;
                    }
                  }

                  return displayLogs.map((log, i) => {
                    let entry = log;
                    if (typeof log === 'string') {
                      try { entry = JSON.parse(log); } catch { return null; }
                    }
                    if (typeof entry !== 'object') return null;
                    if (entry.user_visible === false) return null;
                    if (entry.message?.includes("Institutional Signal Pulse")) return null; // Fallback for old logs

                    // --- Client-Side "Friendly" Filter ---
                    let cleanMessage = entry.message;
                    let isTechnical = false;

                    if (cleanMessage.includes("Can't instantiate abstract class")) {
                      cleanMessage = "Broker: Paper Trading Mode (Fallback)";
                      isTechnical = true;
                    } else if (cleanMessage.includes("Strategies:")) {
                      cleanMessage = "Strategies Initialized";
                      isTechnical = true;
                    } else if (cleanMessage.includes("Shutting Down")) {
                      cleanMessage = "System Shutdown Initiated";
                    }

                    // Hide other specific technical noise if needed
                    // if (entry.level === 'DEBUG') return null; 

                    return (
                      <div key={i} className="flex gap-2 border-b border-white/5 pb-1">
                        <span className="text-blue-500/50 shrink-0 text-[9px] w-12 pt-0.5 opacity-50">
                          {entry.timestamp?.split('T')[1]?.split('.')[0] || ''}
                        </span>
                        <span className={`break-words leading-tight ${entry.level === 'ERROR' ? 'text-red-400' :
                          entry.level === 'USER' ? 'text-white font-medium' :
                            isTechnical ? 'text-gray-500 italic' : 'text-gray-400'
                          }`}>
                          {cleanMessage}
                        </span>
                      </div>
                    );
                  })
                })()
              )}
              <div ref={logEndRef} />
            </div>
          </div>

          <div className="glass-panel h-[160px] flex flex-col justify-center items-center text-center shrink-0">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-2">Daily P&L</h3>
            <div className="text-4xl font-bold text-gray-500">₹0.00</div>
            <div className="text-xs text-green-500 mt-2">No active trades</div>
          </div>
        </div>
      </main>

      <LogViewer isOpen={isLogViewerOpen} onClose={() => setIsLogViewerOpen(false)} />

      <TokenExpiryModal
        isOpen={tokenExpiry.isExpired}
        onClose={() => setTokenExpiry({ isExpired: false, broker: null })}
        broker={tokenExpiry.broker}
        onTokenSubmit={handleTokenUpdate}
      />
    </div>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-black text-red-500 p-10 font-mono">
          <h1 className="text-3xl font-bold mb-4">Something went wrong.</h1>
          <div className="bg-gray-900 p-4 rounded border border-red-900 overflow-auto">
            <h2 className="text-xl mb-2">{this.state.error && this.state.error.toString()}</h2>
            <pre className="text-xs text-gray-400 whitespace-pre-wrap">
              {this.state.errorInfo && this.state.errorInfo.componentStack}
            </pre>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500"
          >
            Reload Application
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

const AppWithBoundary = () => (
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
);

export default AppWithBoundary;


