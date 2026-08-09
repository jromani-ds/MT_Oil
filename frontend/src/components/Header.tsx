interface HeaderProps {
  wellCount: number;
}

export function Header({ wellCount }: HeaderProps) {
  return (
    <header className="bg-slate-800 text-white w-full flex justify-between items-center px-6 py-3 box-border shadow-md">
      <h1 className="text-lg sm:text-xl font-bold">MT Oil Analytics</h1>
      <div className="text-sm text-gray-400 shrink-0 overflow-hidden text-ellipsis whitespace-nowrap max-w-[50%] pr-6">
        {wellCount.toLocaleString()} wells loaded
      </div>
    </header>
  );
}
