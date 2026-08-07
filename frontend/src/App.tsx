import { NavLink, Route, Routes } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { SiteDetail } from "./pages/SiteDetail";
import { SitesPage } from "./pages/admin/Sites";
import { AlertChannelsPage } from "./pages/admin/AlertChannels";

export default function App() {
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
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sites" element={<SitesPage />} />
          <Route path="/sites/:id" element={<SiteDetail />} />
          <Route path="/alert-channels" element={<AlertChannelsPage />} />
        </Routes>
      </main>
    </div>
  );
}
