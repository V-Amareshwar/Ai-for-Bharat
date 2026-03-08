import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, ArrowRight, BadgeCheck } from 'lucide-react';
import './LandingPage.css';

const SCHEMES = [
    "Atal Pension Yojana",
    "Ayushman Bharat",
    "Kisan Credit Card",
    "PM MUDRA Yojana",
    "PM SVANidhi",
    "PMFBY",
    "PM KISAN",
    "Pradhan Mantri Awas Yojana",
    "Stand-up India Scheme"
];

export const LandingPage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="landing-container">
            {/* Background Gradients */}
            <div className="bg-blob blob-1"></div>
            <div className="bg-blob blob-2"></div>

            <nav className="landing-nav">
                <div className="nav-brand">
                    <ShieldCheck size={28} className="brand-icon" />
                    <span>DidiGov</span>
                </div>
                <button className="nav-cta" onClick={() => navigate('/admin')}>
                    Officer Login
                </button>
            </nav>

            <main className="landing-main">
                <div className="hero-section">
                    <div className="hero-badge">A Government of India AI Initiative</div>
                    <h1 className="hero-title">
                        Your Voice. <br />
                        <span className="text-gradient">Your Entitlements.</span>
                    </h1>
                    <p className="hero-subtitle">
                        Experience the future of inclusive governance. Speak naturally in your native language to discover eligibility, ask questions, and seamlessly apply for vital government schemes entirely via voice.
                    </p>

                    <button className="hero-primary-cta" onClick={() => navigate('/portal')}>
                        Start Talking to Didi
                        <ArrowRight size={20} className="cta-icon" />
                    </button>
                </div>

                <div className="schemes-section">
                    <p className="schemes-label">Live knowledge base supporting national initiatives:</p>
                    <div className="schemes-grid">
                        {SCHEMES.map((scheme, idx) => (
                            <div key={idx} className="scheme-card">
                                <BadgeCheck size={18} className="scheme-icon" />
                                <span>{scheme}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </main>
        </div>
    );
};
