import React from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, ShieldCheck, Activity } from 'lucide-react';

export default function Landing() {
    const navigate = useNavigate();

    return (
        <div className="landing-container">
            <div className="landing-content">
                <div className="landing-icon-wrapper" style={{ animation: 'bounceIn 1s ease-out' }}>
                    <Activity size={48} color="var(--accent-color)" />
                </div>

                <h1 className="landing-title" style={{ animation: 'fadeUp 0.8s ease-out 0.2s both' }}>
                    차원이 다른<br />
                    <span className="text-gradient">다이내믹 밸류에이션</span>
                </h1>

                <p className="landing-subtitle" style={{ animation: 'fadeUp 0.8s ease-out 0.4s both' }}>
                    실시간 주가 시세와 EPS 변화율, PER 밴드를 한눈에 비교하고<br />
                    가장 과대/과소평가된 기업의 랭킹을 즉시 확인하세요.
                </p>

                <div className="landing-features" style={{ animation: 'fadeUp 0.8s ease-out 0.6s both' }}>
                    <div className="feature-item">
                        <TrendingUp size={20} color="var(--success-color)" />
                        <span>실시간 주가 모멘텀</span>
                    </div>
                    <div className="feature-item">
                        <ShieldCheck size={20} color="var(--warning-color)" />
                        <span>객관적 가치 지표</span>
                    </div>
                </div>

                <div className="landing-actions" style={{ animation: 'fadeUp 0.8s ease-out 0.8s both' }}>
                    <button className="primary-button large" onClick={() => navigate('/dashboard')}>
                        시작하기
                    </button>
                </div>
            </div>
        </div>
    );
}
