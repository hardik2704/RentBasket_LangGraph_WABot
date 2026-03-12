import React from 'react';
import { Search, Bell, UserCircle, RefreshCcw, Download } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full glass border-b border-border bg-white/80 backdrop-blur-md">
      <div className="px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-900 leading-none">
              <span className="text-primary font-black uppercase tracking-tighter mr-1">RentBasket</span>
              <span className="font-light tracking-wide text-gray-500 uppercase text-xs border-l border-gray-300 pl-3">Discount Portal</span>
            </h1>
            
            <div className="hidden lg:flex items-center ml-10 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-gray-400" />
              </div>
              <input
                type="text"
                className="block w-64 pl-10 pr-3 py-1.5 border border-gray-200 rounded-md text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary bg-gray-50/50"
                placeholder="Search products or rules..."
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors relative">
              <RefreshCcw className="h-5 w-5" />
            </button>
            <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors relative">
              <Download className="h-5 w-5" />
            </button>
            <div className="h-6 w-px bg-gray-200 mx-1"></div>
            <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors relative">
              <Bell className="h-5 w-5" />
              <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-primary border border-white"></span>
            </button>
            <div className="flex items-center gap-2 pl-2 cursor-pointer hover:bg-gray-100 p-1.5 rounded-lg transition-all">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-semibold text-gray-900 leading-tight">Admin User</p>
                <p className="text-xs text-gray-500 leading-tight uppercase font-medium tracking-wide">Super Admin</p>
              </div>
              <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-white font-bold text-xs ring-2 ring-primary/10">
                AU
              </div>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
