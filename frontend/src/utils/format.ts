export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatMultiplier(value: number): string {
  return `${value.toFixed(2)}x`;
}

export function formatDuration(months: number): string {
  if (months <= 0) return 'N/A';
  return `${months} months`;
}

export function formatVolume(bbl: number): string {
  return `${(bbl / 1000).toFixed(1)}k bbl`;
}

export function formatCoordinate(value: number): string {
  return value.toFixed(4);
}

export function formatAPI(api: string): string {
  return `API: ${api}`;
}

export function formatCompactNumber(value: number): string {
  return value.toLocaleString();
}

export function formatYear(dateVal: number): string {
  return new Date(dateVal).getFullYear().toString();
}

export function formatChartDate(dateVal: number): string {
  return new Date(dateVal).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
  });
}
