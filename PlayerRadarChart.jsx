import React from 'react';
import {
    Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

/**
 * PlayerProfileRadar Component
 * 
 * Bu bileşen oyuncunun yetenek grafiğini (Spider/Radar Chart) çıkarır.
 * Hem oyuncuyu hem de baz alınan veriyi (örneğin lig ortalaması) üst üste gösterir.
 * 
 * @param {Object} props
 * @param {Object} props.playerData - İncelenen oyuncunun verisi (0-100 arası normalize edilmiş değerler önerilir)
 * @param {Object} props.baselineData - Kıyaslanacak baz veri (Lig ortalaması veya 2. bir oyuncu)
 * @param {string} props.playerName - Oyuncu Adı
 * @param {string} props.baselineName - Baz verinin adı (Örn: "Lig Ortalaması")
 */
const PlayerProfileRadar = ({
    playerData,
    baselineData,
    playerName = "Hedef Oyuncu",
    baselineName = "Lig Ortalaması"
}) => {

    // Grafiğin eksenlerini props üzerinden gelen verilerle eşleştiriyoruz.
    // Her eksenin maksimum skorunu (fullMark) 100 olarak varsayıyoruz ki orantılı dursun.
    const data = [
        {
            subject: 'Hücum Katkısı (G+A)',
            A: playerData.offensiveContribution || 0,
            B: baselineData.offensiveContribution || 0,
            fullMark: 100,
        },
        {
            subject: 'Pas Dağıtımı',
            A: playerData.passDistribution || 0,
            B: baselineData.passDistribution || 0,
            fullMark: 100,
        },
        {
            subject: 'Defansif Direnç',
            A: playerData.defensiveResistance || 0,
            B: baselineData.defensiveResistance || 0,
            fullMark: 100,
        },
        {
            subject: 'Bireysel Reyting',
            A: playerData.ratingClass || 0,
            B: baselineData.ratingClass || 0,
            fullMark: 100,
        },
        {
            subject: 'Takım Zekası (MVP Etkisi)',
            A: playerData.teamIQ || 0,
            B: baselineData.teamIQ || 0,
            fullMark: 100,
        }
    ];

    // Özelleştirilmiş profesyonel görünümlü modern tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div style={{
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    padding: '16px',
                    borderRadius: '10px',
                    border: '1px solid #334155',
                    color: '#f8fafc',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
                }}>
                    <p style={{ margin: '0 0 10px 0', fontWeight: 600, color: '#38bdf8', fontSize: '14px', borderBottom: '1px solid #334155', paddingBottom: '6px' }}>
                        {payload[0].payload.subject}
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '15px' }}>
                            <span style={{ color: payload[0].color, fontWeight: 'bold' }}>{playerName}</span>
                            <span>{payload[0].value}%</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '15px' }}>
                            <span style={{ color: payload[1].color, fontWeight: 'bold' }}>{baselineName}</span>
                            <span>{payload[1].value}%</span>
                        </div>
                    </div>
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{
            width: '100%',
            height: '450px',
            backgroundColor: '#020617', // Profesyonel veri analiz koyu teması
            borderRadius: '16px',
            padding: '20px',
            border: '1px solid #1e293b'
        }}>
            <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
                    {/* Arka plan grid ağları */}
                    <PolarGrid stroke="#334155" strokeDasharray="3 3" />

                    {/* Eksen İsimleri */}
                    <PolarAngleAxis
                        dataKey="subject"
                        tick={{ fill: '#cbd5e1', fontSize: 13, fontWeight: 500 }}
                    />

                    {/* İç Çember Sayıları (0, 25, 50, 75, 100) */}
                    <PolarRadiusAxis
                        angle={30}
                        domain={[0, 100]}
                        tick={{ fill: '#475569', fontSize: 11 }}
                        axisLine={false}
                    />

                    <Tooltip content={<CustomTooltip />} />

                    {/* Lejant (Kimin Hangi Renk Olduğunu Gösteren Kısım) */}
                    <Legend
                        wrapperStyle={{ paddingTop: "20px", fontSize: "14px", color: "#e2e8f0" }}
                        iconType="circle"
                    />

                    {/* Baz Veri (Lig Ortalaması - Yarı Saydam Gri/Soğuk Mavi) */}
                    <Radar
                        name={baselineName}
                        dataKey="B"
                        stroke="#64748b"
                        strokeWidth={2}
                        fill="#64748b"
                        fillOpacity={0.3}
                    />

                    {/* İncelenen Oyuncu (Dikkat Çekici Neon Mavi) */}
                    <Radar
                        name={playerName}
                        dataKey="A"
                        stroke="#0ea5e9"
                        strokeWidth={3}
                        fill="#0ea5e9"
                        fillOpacity={0.55}
                    />
                </RadarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default PlayerProfileRadar;
