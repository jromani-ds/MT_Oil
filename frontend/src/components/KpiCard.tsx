interface KpiCardProps {
  label: string;
  value: string;
  colorScheme: 'green' | 'blue' | 'purple' | 'orange';
  negative?: boolean;
}

const colorClasses: Record<string, { bg: string; label: string; value: string }> = {
  green: {
    bg: 'bg-gradient-to-br from-green-50 to-green-100',
    label: 'text-green-800',
    value: 'text-green-700',
  },
  blue: {
    bg: 'bg-gradient-to-br from-blue-50 to-blue-100',
    label: 'text-blue-800',
    value: 'text-blue-700',
  },
  purple: {
    bg: 'bg-gradient-to-br from-purple-50 to-purple-100',
    label: 'text-purple-800',
    value: 'text-purple-700',
  },
  orange: {
    bg: 'bg-gradient-to-br from-orange-50 to-orange-100',
    label: 'text-orange-800',
    value: 'text-orange-700',
  },
};

export function KpiCard({ label, value, colorScheme, negative }: KpiCardProps) {
  const colors = colorClasses[colorScheme];
  return (
    <div className={`${colors.bg} p-6 rounded-lg border border-gray-200/60`}>
      <p className={`text-gray-600 text-sm uppercase tracking-wider font-semibold mb-2`}>{label}</p>
      <p
        className={`text-3xl sm:text-4xl font-mono font-bold ${
          negative !== undefined
            ? negative
              ? 'text-red-700'
              : 'text-green-700'
            : colors.value
        }`}
      >
        {value}
      </p>
    </div>
  );
}
