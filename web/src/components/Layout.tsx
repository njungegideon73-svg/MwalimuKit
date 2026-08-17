import { NavLink, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/lib/auth-store';
import {
  LayoutDashboard,
  ClipboardList,
  Users,
  Settings,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/assessments', icon: ClipboardList, label: 'Assessments' },
  { to: '/classes', icon: Users, label: 'Classes' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 bg-white border-r border-gray-200">
        <div className="flex h-16 items-center gap-2 px-6 border-b border-gray-200">
          <div className="h-8 w-8 rounded-lg bg-primary-500 flex items-center justify-center">
            <span className="text-white font-bold text-sm">MK</span>
          </div>
          <span className="text-lg font-bold text-gray-900">MwalimuKit</span>
        </div>
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-200 p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-9 w-9 rounded-full bg-primary-100 flex items-center justify-center">
              <span className="text-primary-700 font-medium text-sm">
                {user?.full_name?.charAt(0) ?? '?'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 inset-x-0 z-50 flex h-14 items-center gap-4 bg-white border-b border-gray-200 px-4">
        <button onClick={() => setSidebarOpen(true)} className="p-1 text-gray-600">
          <Menu className="h-6 w-6" />
        </button>
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-primary-500 flex items-center justify-center">
            <span className="text-white font-bold text-xs">MK</span>
          </div>
          <span className="font-bold text-gray-900">MwalimuKit</span>
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSidebarOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white shadow-xl flex flex-col">
            <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200">
              <span className="font-bold text-gray-900">MwalimuKit</span>
              <button onClick={() => setSidebarOpen(false)} className="p-1 text-gray-500">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 px-3 py-4 space-y-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`
                  }
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="border-t border-gray-200 p-3">
              <button
                onClick={() => { logout(); setSidebarOpen(false); }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 lg:pl-64">
        <div className="pt-14 lg:pt-0 min-h-screen">
          <div className="p-4 sm:p-6 lg:p-8">{children}</div>
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-200 px-2 pb-safe">
        <div className="flex justify-around py-2">
          {navItems.map((item) => {
            const isActive =
              item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex flex-col items-center gap-1 px-3 py-1.5 text-xs ${
                  isActive ? 'text-primary-600' : 'text-gray-500'
                }`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
