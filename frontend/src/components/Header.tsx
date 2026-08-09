import { Terminal } from 'lucide-react';

interface HeaderProps {
  wellCount: number;
}

export function Header({ wellCount }: HeaderProps) {
  return (
    <header className="bg-slate-800 text-white px-4 sm:px-6 py-4 shadow-md flex items-center justify-between">
      <h1 className="text-lg sm:text-xl font-bold flex items-center gap-2">
        <Terminal className="w-6 h-6 shrink-0" />
        <span>MT Oil Analytics</span>
      </h1>
      <div className="text-sm text-gray-400 shrink-0 overflow-hidden text-ellipsis whitespace-nowrap max-w-[50%]">
        {wellCount.toLocaleString()} wells loaded
      </div>
    </header>
  );
}
