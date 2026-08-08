import { NavLink, Route, Routes } from "react-router-dom";
import { NotificationToggle } from "./components/NotificationToggle";
import { useFailureNotifications } from "./hooks/useFailureNotifications";
import { Dashboard } from "./pages/Dashboard";
import { SiteDetail } from "./pages/SiteDetail";
import { Recorder } from "./pages/Recorder";
import { SitesPage } from "./pages/admin/Sites";
import { AlertChannelsPage } from "./pages/admin/AlertChannels";

export default function App() {
  useFailureNotifications();

  return (
    <div className="app-shell">
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
        <div style={{ marginLeft: "auto" }}>
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
