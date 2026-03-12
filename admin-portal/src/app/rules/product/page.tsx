import React from 'react';
import ProductTable from '@/components/dashboard/ProductTable';
import { ListChecks } from 'lucide-react';

export default function ProductOverridesPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="h-8 w-8 rounded bg-primary/10 flex items-center justify-center text-primary">
              <ListChecks className="h-5 w-5" />
            </div>
            <h2 className="text-2xl font-black text-gray-900 tracking-tight uppercase">Product Overrides</h2>
          </div>
          <p className="text-gray-500 font-medium max-w-xl">
            Apply surgical discounts to specific products. These rules have the highest priority and override both Category and Global discounts.
          </p>
        </div>
      </div>

      <ProductTable />
    </div>
  );
}
