'use client';

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Package, 
  Users, 
  Clock, 
  AlertCircle,
  Percent,
  Tag as TagIcon
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { Product, PricingPreview } from '../types';

export default function Dashboard() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | ''>('');
  const [duration, setDuration] = useState<number>(6);
  const [preview, setPreview] = useState<PricingPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [globalDiscount, setGlobalDiscount] = useState({ percent: 10, status: 'active' });

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (selectedProductId) {
      updatePreview();
    }
  }, [selectedProductId, duration]);

  async function fetchInitialData() {
    const { data } = await supabase.from('products').select('*').order('name');
    if (data) {
      const typedData = data as Product[];
      setProducts(typedData);
      if (typedData.length > 0) setSelectedProductId(typedData[0].id);
    }
    
    // Fetch current global discount
    const { data: rules } = await supabase
      .from('discount_rules')
      .select('*')
      .eq('scope', 'global')
      .eq('status', 'active')
      .limit(1);
    
    if (rules && rules.length > 0) {
      const rule = rules[0] as any;
      setGlobalDiscount({ percent: rule.discount_percent, status: rule.status });
    }
  }

  async function updatePreview() {
    if (!selectedProductId) return;
    setLoadingPreview(true);
    try {
      const { data, error } = await (supabase.rpc as any)('calculate_effective_price', {
        p_product_id: Number(selectedProductId),
        p_duration: duration
      });
      if (data) setPreview(data as PricingPreview);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingPreview(false);
    }
  }

  async function applyGlobalDiscount() {
    const reason = (document.getElementById('global-reason') as HTMLTextAreaElement)?.value;
    try {
      // 1. Check if an existing global rule exists
      const { data: existingRules } = await (supabase.from('discount_rules') as any)
        .select('id')
        .eq('scope', 'global')
        .limit(1);

      const payload = {
        rule_name: 'Global Market Override',
        scope: 'global',
        discount_percent: globalDiscount.percent,
        status: globalDiscount.status,
        reason: reason || 'Updated via Admin Portal'
      };

      let error;
      if (existingRules && existingRules.length > 0) {
        // 2. Update existing rule
        const { error: updateError } = await (supabase.from('discount_rules') as any)
          .update(payload)
          .eq('id', existingRules[0].id);
        error = updateError;
      } else {
        // 3. Insert new rule
        const { error: insertError } = await (supabase.from('discount_rules') as any)
          .insert(payload);
        error = insertError;
      }

      if (error) throw error;
      alert('Global Discount Applied Successfully!');
      updatePreview();
    } catch (e: any) {
      alert('Error: ' + e.message);
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header section with contextual info */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight">Pricing Dashboard</h2>
          <p className="text-gray-500 mt-1 max-w-2xl font-medium">
            Manage your rental discounts across all product categories. Changes here affect the real-time pricing shown to customers on WhatsApp.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-lg border border-border card-shadow shrink-0">
          <div className="h-2 w-2 rounded-full bg-active-green"></div>
          <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">Sync Status: Real-time</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Left Column: Rules & Controls */}
        <div className="xl:col-span-2 space-y-8">
          <section className="bg-white rounded-2xl border-2 border-primary/10 card-shadow overflow-hidden relative">
            <div className="absolute top-0 right-0 p-3 italic text-[10px] uppercase font-black tracking-widest text-primary/20 rotate-12 pointer-events-none">Highest Hierarchal Control</div>
            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-primary/5">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center text-white shadow-lg shadow-primary/20">
                  <Percent className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Global Discount Master</h3>
                  <p className="text-xs text-gray-500 font-medium">Affects all non-restricted categories</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" checked={globalDiscount.status === 'active'} onChange={(e) => setGlobalDiscount({...globalDiscount, status: e.target.checked ? 'active' : 'disabled'})} />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wider">Discount Percentage</label>
                <div className="relative">
                  <input type="number" className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-bold text-lg" value={globalDiscount.percent} onChange={(e) => setGlobalDiscount({...globalDiscount, percent: parseInt(e.target.value) || 0})} />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold">%</span>
                </div>
              </div>
              <div className="md:col-span-2 space-y-2">
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wider">Campaign Schedule (Optional)</label>
                <div className="flex items-center gap-2">
                  <input type="datetime-local" className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 transition-all" />
                  <span className="text-gray-400 font-black">→</span>
                  <input type="datetime-local" className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 transition-all" />
                </div>
              </div>
              <div className="md:col-span-3 space-y-2">
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wider">Reason for Update</label>
                <textarea id="global-reason" className="w-full px-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 transition-all h-20 resize-none" placeholder="e.g., Summer Sale 2024 Campaign Override"></textarea>
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
              <p className="text-xs text-gray-400 italic">Connected to live Supabase Instance</p>
              <button 
                onClick={applyGlobalDiscount}
                className="px-6 py-2 bg-primary hover:bg-primary/90 text-white font-bold rounded-lg transition-all shadow-lg shadow-primary/20 hover:scale-105 active:scale-95">
                Apply Global Changes
              </button>
            </div>
          </section>

          <section className="bg-white rounded-2xl border border-border card-shadow overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-bold text-gray-900 tracking-tight flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-gray-400" />
                Quick Status Overview
              </h3>
            </div>
            <div className="p-12 text-center">
               <p className="text-sm text-gray-400 italic">Select individual categories or products from the sidebar for granular control.</p>
            </div>
          </section>
        </div>

        {/* Right Column: Pricing Preview */}
        <div className="space-y-8">
          <section className="bg-white rounded-2xl border border-border card-shadow h-fit sticky top-24 overflow-hidden">
            <div className="p-6 border-b border-gray-100 bg-gray-900 text-white flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm tracking-tight uppercase">Live Pricing Preview</h3>
                <p className="text-[10px] text-gray-400 font-medium">customer view simulation</p>
              </div>
              <div className="p-2 bg-white/10 rounded-lg">
                <AlertCircle className="h-4 w-4 text-primary" />
              </div>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Select Product</label>
                <select 
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-1 focus:ring-primary focus:border-primary outline-none font-medium"
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(parseInt(e.target.value))}
                >
                  {products.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest text-center block w-full">Tenure Choice</label>
                <div className="grid grid-cols-4 gap-2">
                  {[3, 6, 9, 12].map(m => (
                    <button 
                      key={m} 
                      onClick={() => setDuration(m)}
                      className={`py-2 text-xs font-bold rounded-lg border transition-all ${duration === m ? 'bg-primary border-primary text-white shadow-md shadow-primary/20 scale-105' : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'}`}>
                      {m}m
                    </button>
                  ))}
                </div>
              </div>

              <div className={`bg-gray-50 rounded-2xl p-6 border border-gray-100 space-y-4 relative ${loadingPreview ? 'opacity-50' : ''}`}>
                {loadingPreview && <div className="absolute inset-0 flex items-center justify-center bg-white/20 backdrop-blur-[1px] z-10 rounded-2xl">
                   <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                </div>}
                
                <div className="flex justify-between items-start">
                  <h4 className="text-xs font-black text-gray-400 uppercase tracking-widest">Summary</h4>
                  {preview && preview.discount_percent > 0 && (
                    <span className="text-[10px] bg-active-green text-white px-2 py-0.5 rounded font-black italic">-{preview.discount_percent}% OFF</span>
                  )}
                </div>
                
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 font-medium tracking-tight">Base Rent</span>
                    <span className="text-gray-900 font-bold">₹{preview?.base_price || '0'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 font-medium tracking-tight">Applied Rule</span>
                    <span className={`font-bold uppercase text-[10px] ${preview?.discount_source !== 'none' ? 'text-primary' : 'text-gray-400'}`}>
                       {preview?.discount_source || 'Base Price'}
                    </span>
                  </div>
                  <div className="pt-3 border-t border-gray-200 flex justify-between items-baseline">
                    <span className="text-xs font-bold text-gray-900 uppercase tracking-wider">Final Rent</span>
                    <span className="text-2xl font-black text-gray-900">₹{preview?.final_price || '0'}<span className="text-[10px] text-gray-400 font-medium lowercase ml-1">/month</span></span>
                  </div>
                </div>

                <div className="mt-6 pt-6 border-t border-dashed border-gray-300 text-center">
                   <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-3">WhatsApp Preview</p>
                   <div className="bg-[#DCF8C6] rounded-xl p-4 shadow-sm border border-[#C5E1A5] text-left">
                      <p className="text-sm text-gray-800 leading-snug">
                         {preview?.display_text || 'Loading...'}
                      </p>
                      <span className="block text-right text-[9px] text-gray-500 mt-1 uppercase">JUST NOW ✓</span>
                   </div>
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-yellow-50 border-t border-yellow-100 italic">
               <p className="text-[9px] text-yellow-800 leading-normal font-medium">
                  *Live calculation via Supabase RPC.
               </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
