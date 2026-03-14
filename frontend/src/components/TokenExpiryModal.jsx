import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, ExternalLink, Key, X } from 'lucide-react';

const TokenExpiryModal = ({ isOpen, onClose, broker, onTokenSubmit }) => {
    const [newToken, setNewToken] = useState('');
    const [clientId, setClientId] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async () => {
        if (!newToken.trim()) {
            alert('Please enter a valid access token');
            return;
        }

        setIsSubmitting(true);
        try {
            await onTokenSubmit({ broker, access_token: newToken, client_id: clientId });
            setNewToken('');
            setClientId('');
            onClose();
        } catch (error) {
            alert(`Failed to update token: ${error.message}`);
        } finally {
            setIsSubmitting(false);
        }
    };

    const getBrokerInstructions = () => {
        switch (broker) {
            case 'DHAN':
                return {
                    portal: 'https://web.dhan.co',
                    steps: [
                        'Login to web.dhan.co',
                        'Go to Profile → Access DhanHQ APIs',
                        'Click "Generate Access Token"',
                        'Copy both Client ID and Access Token'
                    ]
                };
            case 'ZERODHA':
            case 'KITE':
                return {
                    portal: 'https://kite.zerodha.com',
                    steps: [
                        'Login to kite.zerodha.com',
                        'Go to your Kite Connect app',
                        'Complete the login flow',
                        'Copy the access token from the redirect URL'
                    ]
                };
            default:
                return {
                    portal: '#',
                    steps: ['Contact your broker for token generation instructions']
                };
        }
    };

    const instructions = getBrokerInstructions();

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    onClick={onClose}
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.9, opacity: 0 }}
                        onClick={(e) => e.stopPropagation()}
                        className="bg-gradient-to-br from-gray-900 to-gray-800 border border-red-500/30 rounded-xl p-6 max-w-md w-full shadow-2xl"
                    >
                        {/* Header */}
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-red-500/20 rounded-lg">
                                    <AlertTriangle className="text-red-400" size={24} />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold text-white">Token Expired</h2>
                                    <p className="text-sm text-gray-400">{broker} Authentication Required</p>
                                </div>
                            </div>
                            <button
                                onClick={onClose}
                                className="text-gray-500 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* Warning Message */}
                        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-4">
                            <p className="text-sm text-red-300">
                                Your broker access token has expired. Execution is currently <strong>disabled</strong> to prevent unauthorized trades.
                            </p>
                        </div>

                        {/* Instructions */}
                        <div className="mb-4">
                            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                                <Key size={14} />
                                How to get a new token:
                            </h3>
                            <ol className="text-xs text-gray-300 space-y-1 ml-5 list-decimal">
                                {instructions.steps.map((step, idx) => (
                                    <li key={idx}>{step}</li>
                                ))}
                            </ol>
                            <a
                                href={instructions.portal}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2"
                            >
                                Open {broker} Portal
                                <ExternalLink size={12} />
                            </a>
                        </div>

                        {/* Input Fields */}
                        <div className="space-y-3 mb-4">
                            {broker === 'DHAN' && (
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 mb-1">
                                        Client ID
                                    </label>
                                    <input
                                        type="text"
                                        value={clientId}
                                        onChange={(e) => setClientId(e.target.value)}
                                        placeholder="Enter your Dhan Client ID"
                                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                                    />
                                </div>
                            )}
                            <div>
                                <label className="block text-xs font-medium text-gray-400 mb-1">
                                    Access Token
                                </label>
                                <input
                                    type="password"
                                    value={newToken}
                                    onChange={(e) => setNewToken(e.target.value)}
                                    placeholder="Paste your new access token here"
                                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                                />
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="flex gap-3">
                            <button
                                onClick={onClose}
                                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={isSubmitting}
                                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isSubmitting ? 'Updating...' : 'Update Token'}
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default TokenExpiryModal;
