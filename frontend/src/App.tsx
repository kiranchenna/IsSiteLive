import { useEffect } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { AlarmToggle } from "./components/AlarmToggle";
import { AlertBanner } from "./components/AlertBanner";
import { NotificationToggle } from "./components/NotificationToggle";
import { useFailureNotifications } from "./hooks/useFailureNotifications";
import { armAudioUnlock } from "./lib/notifications";
import { Dashboard } from "./pages/Dashboard";
import { SiteDetail } from "./pages/SiteDetail";
import { Recorder } from "./pages/Recorder";
import { SitesPage } from "./pages/admin/Sites";
import { AlertChannelsPage } from "./pages/admin/AlertChannels";

export default function App() {
  useFailureNotifications();
  useEffect(() => {
    armAudioUnlock();
  }, []);

  return (
    <div className="app-shell">
      <AlertBanner />
      <header className="app-header">
        <NavLink to="/" className="brand">
          <span className="brand-dot" />
          IsSiteLive
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/sites" className={({ isActive }) => (isActive ? "active" : "")}>
            Sites
          </NavLink>
          <NavLink to="/alert-channels" className={({ isActive }) => (isActive ? "active" : "")}>
            Alert channels
          </NavLink>
        </nav>
        <div style={{ marginLeft: "auto" }} className="flex items-center gap-2">
          <AlarmToggle />
          <NotificationToggle />
        </div>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sites" element={<SitesPage />} />
          <Route path="/sites/:id" element={<SiteDetail />} />
          <Route path="/sites/:id/record" element={<Recorder />} />
          <Route path="/alert-channels" element={<AlertChannelsPage />} />
        </Routes>
      </main>
    </div>
  );
}
