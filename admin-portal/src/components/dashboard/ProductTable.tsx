'use client';

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import { Product, Category } from '../../types';
import { Search, Filter, Edit2, Package, Tag, ArrowRight, X } from 'lucide-react';

export default function ProductTable() {
  const [products, setProducts] = useState<(Product & { category?: Category })[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      setLoading(true);
      
      const [prodRes, catRes] = await Promise.all([
        supabase.from('products').select('*, categories(*)'),
        supabase.from('categories').select('*').order('name')
      ]);

      if (prodRes.error) throw prodRes.error;
      if (catRes.error) throw catRes.error;

      setProducts(prodRes.data || []);
      setCategories(catRes.data || []);
    } catch (e: any) {
      console.error('Error fetching dashboard data:', e.message);
    } finally {
      setLoading(false);
    }
  }

  const filteredProducts = products.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || p.category_id === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  if (loading) return <div className="p-8 text-center text-gray-500 animate-pulse font-bold uppercase tracking-widest text-xs">Loading Products...</div>;

  return (
    <div className="space-y-6">
      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-white p-4 rounded-xl border border-border card-shadow">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search product by name..."
            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="h-4 w-4 text-gray-400 shrink-0" />
          <select 
            className="w-full sm:w-48 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 outline-none transition-all font-medium"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="all">All Categories</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Product Table */}
      <div className="bg-white rounded-2xl border border-border overflow-hidden card-shadow">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400">ID</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400">Product</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400">Category</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400 text-center">Active Overrides</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filteredProducts.slice(0, 50).map((prod) => (
              <tr key={prod.id} className="hover:bg-gray-50/50 transition-all group">
                <td className="px-6 py-4">
                  <span className="text-xs font-mono text-gray-400 font-bold">{prod.id}</span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded bg-gray-100 flex items-center justify-center text-gray-400 group-hover:text-primary transition-colors">
                      <Package className="h-4 w-4" />
                    </div>
                    <span className="text-sm font-bold text-gray-900 group-hover:text-primary transition-colors">{prod.name}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="text-xs font-bold text-gray-500 uppercase bg-gray-100 px-2 py-1 rounded">
                    {categories.find(c => c.id === prod.category_id)?.name || 'Unknown'}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                   <div className="flex items-center justify-center gap-1.5">
                      <div className="h-1.5 w-1.5 rounded-full bg-gray-300"></div>
                      <span className="text-[10px] font-black text-gray-400 uppercase tracking-tighter">No Override</span>
                   </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <button 
                    onClick={() => setEditingProduct(prod)}
                    className="flex items-center gap-1.5 ml-auto text-xs font-black uppercase tracking-widest text-gray-400 hover:text-primary translation-all group/btn"
                  >
                    Set Discount
                    <ArrowRight className="h-3 w-3 group-hover/btn:translate-x-1 transition-transform" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredProducts.length === 0 && (
          <div className="p-12 text-center">
            <Package className="h-12 w-12 text-gray-200 mx-auto mb-4" />
            <p className="text-gray-400 font-bold uppercase tracking-widest text-xs">No products matched your search</p>
          </div>
        )}
      </div>

      {/* Product Drawer */}
      {editingProduct && (
        <>
          <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[60]" onClick={() => setEditingProduct(null)}></div>
          <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white z-[70] shadow-2xl animate-in slide-in-from-right duration-300 border-l border-border flex flex-col">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-primary text-white">
               <div>
                  <h3 className="text-xl font-black uppercase tracking-tighter">Product Override</h3>
                  <p className="text-xs font-medium text-white/70 tracking-wide">{editingProduct.name}</p>
               </div>
               <button onClick={() => setEditingProduct(null)} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                  <X className="h-6 w-6" />
               </button>
            </div>
            
            <div className="flex-1 p-8 space-y-8 overflow-y-auto">
               <section className="space-y-4">
                  <div className="p-4 rounded-xl border-2 border-primary/10 bg-primary/5 space-y-4">
                     <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Override Discount %</label>
                        <div className="relative">
                           <input id="prod-discount-pc" type="number" className="w-full px-4 py-2 border border-gray-200 rounded-lg font-black text-lg focus:ring-2 focus:ring-primary/20 outline-none transition-all" defaultValue="0" />
                           <span className="absolute right-4 top-1/2 -translate-y-1/2 text-primary font-bold">%</span>
                        </div>
                        <p className="text-[10px] text-gray-400 italic mt-1">Note: Product overrides take absolute priority over global/category rules.</p>
                     </div>
                  </div>
               </section>

               <section className="space-y-4 pt-4 border-t border-gray-100">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Update Reason</label>
                  <textarea id="prod-reason" className="w-full h-24 p-4 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-primary/20 outline-none transition-all resize-none italic" placeholder="e.g., Tactical price adjustment for competitor matching"></textarea>
               </section>
            </div>

            <div className="p-6 border-t border-gray-100 bg-gray-50 flex items-center justify-end gap-3">
               <button onClick={() => setEditingProduct(null)} className="px-6 py-2 rounded-lg text-sm font-bold text-gray-500 hover:bg-gray-100 transition-all uppercase tracking-wide">Cancel</button>
               <button 
                  onClick={async () => {
                     const pc = parseInt((document.getElementById('prod-discount-pc') as HTMLInputElement).value);
                     const reason = (document.getElementById('prod-reason') as HTMLTextAreaElement).value;
                     try {
                        // 1. Check for existing product rule
                        const { data: existingRules } = await (supabase.from('discount_rules') as any)
                          .select('id')
                          .eq('scope', 'product')
                          .eq('target_product_id', editingProduct.id)
                          .limit(1);

                        const payload = {
                          rule_name: `Product Override: ${editingProduct.name}`,
                          scope: 'product',
                          target_product_id: editingProduct.id,
                          discount_percent: pc,
                          status: 'active',
                          reason: reason
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
                        alert('Product override applied!');
                        setEditingProduct(null);
                     } catch (e: any) { alert(e.message); }
                  }}
                  className="px-8 py-2 bg-primary text-white rounded-lg text-sm font-black shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all uppercase tracking-wider">Apply Override</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
