import { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { VoiceRecorder } from './components/VoiceRecorder';
import { MobileLogin } from './components/MobileLogin';
import { AdminDashboard } from './pages/AdminDashboard';
import { LandingPage } from './pages/LandingPage';
import { t } from './i18n';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userLang, setUserLang] = useState<string>('en');

  const handleLoginSuccess = (id: string, lang: string) => {
    setSessionId(id);
    if (lang) setUserLang(lang);
  };

  const handleLanguageChange = (lang: string) => {
    setUserLang(lang);
  };

  return (
    <Routes>
      {/* Officer Dashboard specific route */}
      <Route path="/admin" element={<AdminDashboard />} />

      {/* New Aesthetic Landing Page */}
      <Route path="/" element={<LandingPage />} />

      {/* Main App Container */}
      <Route path="/portal" element={
        <div className="app-container">
          <header className="app-header">
            <div className="app-logo">{t('app_title', userLang)}</div>
            <p className="app-tagline">{t('app_tagline', userLang)}</p>
          </header>

          <main>
            {sessionId ? (
              <VoiceRecorder
                sessionId={sessionId}
                initialLang={userLang}
                onLanguageChange={handleLanguageChange}
              />
            ) : (
              <MobileLogin
                onLoginSuccess={handleLoginSuccess}
                currentLang={userLang}
                onLanguageChange={handleLanguageChange}
              />
            )}
          </main>

          <footer className="app-footer">
            <p>{t('footer', userLang)}</p>
          </footer>
        </div>
      } />
    </Routes>
  );
}

export default App;

