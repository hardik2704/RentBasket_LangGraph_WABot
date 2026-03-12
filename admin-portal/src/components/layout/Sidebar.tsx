import React from 'react';
import { 
  BarChart3, 
  Tag, 
  Layers, 
  ListChecks, 
  History, 
  Settings, 
  HelpCircle,
  LayoutDashboard
} from 'lucide-react';
import Link from 'next/link';

const menuItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/', active: true },
  { icon: Tag, label: 'Global Rules', href: '/rules/global' },
  { icon: Layers, label: 'Category Rules', href: '/rules/category' },
  { icon: ListChecks, label: 'Product Overrides', href: '/rules/product' },
  { icon: History, label: 'Audit Trail', href: '/audit' },
];

const secondaryItems = [
  { icon: Settings, label: 'Settings', href: '/settings' },
  { icon: HelpCircle, label: 'Support', href: '/support' },
];

export default function Sidebar() {
  return (
    <aside className="w-64 h-[calc(100vh-3.5rem)] fixed left-0 top-14 bg-white border-r border-border overflow-y-auto hidden md:block">
      <div className="flex flex-col h-full py-6">
        <div className="px-4 space-y-1">
          {menuItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md transition-all group ${
                item.active 
                  ? 'bg-primary/5 text-primary' 
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <item.icon className={`h-5 w-5 ${item.active ? 'text-primary' : 'text-gray-400 group-hover:text-gray-600'}`} />
              <span className="text-sm font-medium">{item.label}</span>
              {item.active && <div className="ml-auto w-1 h-1 rounded-full bg-primary" />}
            </Link>
          ))}
        </div>

        <div className="mt-auto px-4 pt-6 border-t border-gray-100">
          <p className="px-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Internal Tools</p>
          <div className="space-y-1">
            {secondaryItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="flex items-center gap-3 px-3 py-2 rounded-md text-gray-500 hover:bg-gray-50 hover:text-gray-900 transition-all"
              >
                <item.icon className="h-5 w-5 text-gray-400" />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            ))}
          </div>
        </div>
        
        <div className="mx-4 mt-6 p-4 rounded-xl bg-gray-900 text-white relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-20 h-20 bg-primary/20 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-primary/40 transition-all duration-500"></div>
          <p className="text-xs font-medium text-gray-400 mb-1">Live Environment</p>
          <div className="flex items-center gap-2 mb-3">
            <div className="h-2 w-2 rounded-full bg-active-green animate-pulse"></div>
            <p className="text-sm font-bold tracking-tight">Production v1.0</p>
          </div>
          <button className="w-full py-2 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-bold transition-all border border-white/5">
            System Status
          </button>
        </div>
      </div>
    </aside>
  );
}
