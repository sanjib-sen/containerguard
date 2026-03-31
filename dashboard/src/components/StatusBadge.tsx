interface Props {
  status: string;
}

const colors: Record<string, string> = {
  online: 'bg-green-100 text-green-800',
  unreachable: 'bg-yellow-100 text-yellow-800',
  offline: 'bg-red-100 text-red-800',
};

export function StatusBadge({ status }: Props) {
  const cls = colors[status] || 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}
