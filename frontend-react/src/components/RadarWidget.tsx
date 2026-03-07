import React, { useState, useEffect } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { Card } from './ui';
import { Loader2, Zap, Brain, AlertCircle } from 'lucide-react';

interface RadarData {
    subject: string;
    A: number;
    fullMark: number;
    articles: number;
    papers: number;
    relevance: number;
}

interface RadarWidgetProps {
    domain: 'quantum' | 'ai';
    compact?: boolean;
}

export const RadarWidget: React.FC<RadarWidgetProps> = ({ domain, compact = false }) => {
    const [data, setData] = useState<RadarData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                // Using native fetch against the vite proxy
                const response = await fetch(`/api/radar/metrics/${domain}`);

                if (!response.ok) {
                    throw new Error('Failed to fetch radar metrics');
                }

                const result = await response.json();
                if (result.status === 'success' && result.data) {
                    setData(result.data);
                } else {
                    throw new Error('Invalid response format');
                }
            } catch (err) {
                console.error('Error fetching radar data:', err);
                setError('Unable to load maturity metrics');
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [domain]);

    // Custom Tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="bg-charcoal-700 p-3 rounded-md border border-charcoal-600 shadow-xl max-w-xs">
                    <p className="text-white font-medium mb-1">{data.subject}</p>
                    <div className="flex items-center justify-between text-xs text-charcoal-300 mb-1">
                        <span>Signal Score:</span>
                        <span className="text-signal-teal font-mono">{data.A.toFixed(1)}/100</span>
                    </div>
                    <div className="flex items-center justify-between text-xs text-charcoal-400">
                        <span>Volume (30d):</span>
                        <span>{data.articles} News / {data.papers} ArXiv</span>
                    </div>
                    <div className="flex items-center justify-between text-xs text-charcoal-400 mt-1">
                        <span>Relevance Density:</span>
                        <span>{(data.relevance * 100).toFixed(0)}%</span>
                    </div>
                </div>
            );
        }
        return null;
    };

    const domainColor = domain === 'quantum' ? '#00f2fe' : '#f03a47'; // Teal for Q, Accent Red for AI

    return (
        <Card className="h-full flex flex-col bg-charcoal-800/50 backdrop-blur-sm border-charcoal-700 relative overflow-hidden group">
            {/* Decorative gradient orb */}
            <div
                className="absolute -top-24 -right-24 w-48 h-48 rounded-full blur-3xl opacity-10 transition-opacity duration-700 group-hover:opacity-20 pointer-events-none"
                style={{ backgroundColor: domainColor }}
            />

            <div className={`flex items-center justify-between ${compact ? 'px-3 py-2' : 'p-4'} border-b border-charcoal-700/50`}>
                <div className={`flex items-center gap-2 text-white ${compact ? 'text-xs font-medium' : 'font-medium'}`}>
                    {domain === 'quantum' ? <Zap size={compact ? 12 : 16} className="text-signal-teal" /> : <Brain size={compact ? 12 : 16} className="text-accent-red" />}
                    30-Day Maturity Radar
                </div>
            </div>

            <div className={`${compact ? 'p-2' : 'p-4'} flex-1 flex flex-col items-center justify-center ${compact ? 'min-h-[180px]' : 'min-h-[300px]'} relative z-10`}>
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center text-charcoal-400 gap-3">
                        <Loader2 className="animate-spin w-8 h-8" />
                        <span className="text-sm">Calculating trajectory signals...</span>
                    </div>
                ) : error ? (
                    <div className="flex flex-col items-center justify-center text-red-400 gap-2">
                        <AlertCircle size={24} />
                        <span className="text-sm">{error}</span>
                    </div>
                ) : data.length === 0 ? (
                    <div className="text-charcoal-400 text-sm">No signals detected in the last 30 days.</div>
                ) : (
                    <div className={`w-full ${compact ? 'h-[180px]' : 'h-[280px]'}`}>
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
                                <PolarGrid stroke="#374151" strokeDasharray="3 3" />
                                <PolarAngleAxis
                                    dataKey="subject"
                                    tick={{ fill: '#9CA3AF', fontSize: 11 }}
                                />
                                <PolarRadiusAxis
                                    angle={30}
                                    domain={[0, 100]}
                                    tick={false}
                                    axisLine={false}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Radar
                                    name="Signal Score"
                                    dataKey="A"
                                    stroke={domainColor}
                                    fill={domainColor}
                                    fillOpacity={0.3}
                                    animationBegin={200}
                                    animationDuration={1500}
                                    animationEasing="ease-out"
                                />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </div>

            {/* Footer Insight */}
            {!compact && !isLoading && !error && data.length > 0 && (
                <div className="px-4 py-3 bg-charcoal-900/30 border-t border-charcoal-700/50 text-xs text-charcoal-400 flex items-center justify-between">
                    <span>Leading Trend: <strong className="text-white">{data[0]?.subject}</strong></span>
                    <span className="text-[10px] uppercase tracking-wider font-mono opacity-50">Volume + Relevance</span>
                </div>
            )}
        </Card>
    );
};
