import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const navigation = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/upload", label: "Upload" },
  { to: "/documents", label: "Documents" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex min-h-screen bg-slate-100">
      <aside className="flex w-60 flex-col bg-slate-900 text-slate-300">
        <div className="border-b border-slate-800 px-5 py-5">
          <h1 className="text-sm font-semibold tracking-wide text-white">Secure Manuscript</h1>
          <p className="mt-1 text-xs text-slate-500">Intelligence Platform</p>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800/60 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 px-5 py-4">
          <p className="truncate text-sm font-medium text-white">{user?.full_name ?? user?.email}</p>
          <p className="mt-0.5 text-xs uppercase tracking-wide text-slate-500">{user?.role}</p>
          <button
            onClick={handleLogout}
            className="mt-3 w-full rounded-md bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700 hover:text-white"
          >
            Se déconnecter
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}