'use client';

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import { Category } from '../../types';
import { ShieldCheck, ShieldAlert, Edit2, CheckCircle2, X } from 'lucide-react';

export default function CategoryTable() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);

  useEffect(() => {
    fetchCategories();
  }, []);

  async function fetchCategories() {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('categories')
        .select('*')
        .order('name', { ascending: true });

      if (error) throw error;
      setCategories(data || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function toggleEligibility(category: Category) {
    try {
      const { error } = await (supabase.from('categories') as any)
        .update({ is_discount_eligible: !category.is_discount_eligible })
        .eq('id', category.id);

      if (error) throw error;
      
      setCategories(categories.map(c => 
        c.id === category.id ? { ...c, is_discount_eligible: !c.is_discount_eligible } : c
      ));
    } catch (e: any) {
      alert('Error updating eligibility: ' + e.message);
    }
  }

  async function updateDiscountRule(categoryId: string, percent: number, reason: string) {
    try {
      // 1. Check if an existing rule exists for this category
      const { data: existingRules } = await (supabase.from('discount_rules') as any)
        .select('id')
        .eq('scope', 'category')
        .eq('target_category_id', categoryId)
        .limit(1);

      const payload = {
        rule_name: `Category Discount: ${editingCategory?.name}`,
        scope: 'category',
        target_category_id: categoryId,
        discount_percent: percent,
        status: 'active',
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
      alert('Category rule updated!');
      setEditingCategory(null);
      // Refresh local list if needed
    } catch (e: any) {
      alert('Error: ' + e.message);
    }
  }

  if (loading) return <div className="p-8 text-center text-gray-500 animate-pulse font-bold uppercase tracking-widest text-xs">Loading Categories...</div>;
  if (error) return <div className="p-8 text-red-500 font-bold bg-red-50 rounded-xl border border-red-100 italic">Error: {error}</div>;

  return (
    <div className="relative">
      <div className="bg-white rounded-2xl border border-border overflow-hidden card-shadow">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400">Eligibility</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400">Category Name</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400">Slug</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-gray-400 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {categories.map((cat) => (
              <tr key={cat.id} className="hover:bg-gray-50/50 transition-all group">
                <td className="px-6 py-4">
                  <button 
                    onClick={() => toggleEligibility(cat)}
                    className={`flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest transition-all ${
                      cat.is_discount_eligible 
                        ? 'bg-active-green/10 text-active-green hover:bg-active-green hover:text-white' 
                        : 'bg-red-50 text-red-500 hover:bg-red-500 hover:text-white'
                    }`}
                  >
                    {cat.is_discount_eligible ? (
                      <><ShieldCheck className="h-3.3 w-3.3" /> Eligible</>
                    ) : (
                      <><ShieldAlert className="h-3.3 w-3.3" /> Restricted</>
                    )}
                  </button>
                </td>
                <td className="px-6 py-4">
                  <span className="text-sm font-bold text-gray-900 group-hover:text-primary transition-colors">{cat.name}</span>
                </td>
                <td className="px-6 py-4">
                  <code className="text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-500 font-mono">{cat.slug}</code>
                </td>
                <td className="px-6 py-4 text-right">
                  <button 
                    onClick={() => setEditingCategory(cat)}
                    className="p-2 text-gray-400 hover:text-primary hover:bg-primary/5 rounded-lg transition-all"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Editing Side Drawer Animation Mockup */}
      {editingCategory && (
        <>
          <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[60]" onClick={() => setEditingCategory(null)}></div>
          <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white z-[70] shadow-2xl animate-in slide-in-from-right duration-300 border-l border-border flex flex-col">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-primary text-white">
               <div>
                  <h3 className="text-xl font-black uppercase tracking-tighter">Configure Category</h3>
                  <p className="text-xs font-medium text-white/70 tracking-wide">{editingCategory.name}</p>
               </div>
               <button onClick={() => setEditingCategory(null)} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                  <X className="h-6 w-6" />
               </button>
            </div>
            
            <div className="flex-1 p-8 space-y-8 overflow-y-auto">
               <section className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-xl border border-border bg-gray-50/50">
                     <div>
                        <p className="text-sm font-bold text-gray-900">Eligibility Toggle</p>
                        <p className="text-xs text-gray-500 italic">Enable or disable all discounts for this category</p>
                     </div>
                     <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" checked={editingCategory.is_discount_eligible} onChange={() => toggleEligibility(editingCategory)} />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-active-green"></div>
                     </label>
                  </div>
               </section>

               <section className="space-y-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center gap-2 mb-2">
                     <Edit2 className="h-4 w-4 text-primary" />
                     <h4 className="text-xs font-black uppercase tracking-widest text-gray-400">Active Rule Configuration</h4>
                  </div>
                  <div className="p-4 rounded-xl border-2 border-primary/10 bg-primary/5 space-y-4">
                     <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Current Discount %</label>
                        <div className="relative">
                           <input id="cat-discount-pc" type="number" className="w-full px-4 py-2 border border-gray-200 rounded-lg font-black text-lg focus:ring-2 focus:ring-primary/20 outline-none transition-all" defaultValue="0" />
                           <span className="absolute right-4 top-1/2 -translate-y-1/2 text-primary font-bold">%</span>
                        </div>
                     </div>
                  </div>
               </section>

               <section className="space-y-4 pt-4 border-t border-gray-100">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Update Reason</label>
                  <textarea id="cat-reason" className="w-full h-24 p-4 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-primary/20 outline-none transition-all resize-none italic" placeholder="Describe why this change is being made..."></textarea>
               </section>
            </div>

            <div className="p-6 border-t border-gray-100 bg-gray-50 flex items-center justify-end gap-3">
               <button onClick={() => setEditingCategory(null)} className="px-6 py-2 rounded-lg text-sm font-bold text-gray-500 hover:bg-gray-100 transition-all uppercase tracking-wide">Cancel</button>
               <button 
                  onClick={() => {
                     const pc = parseInt((document.getElementById('cat-discount-pc') as HTMLInputElement).value);
                     const reason = (document.getElementById('cat-reason') as HTMLTextAreaElement).value;
                     updateDiscountRule(editingCategory.id, pc, reason);
                  }}
                  className="px-8 py-2 bg-primary text-white rounded-lg text-sm font-black shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all uppercase tracking-wider">Save Changes</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
