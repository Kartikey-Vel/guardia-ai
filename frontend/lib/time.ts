const ISO_WITHOUT_TZ = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;

export function parseBackendTimestamp(timestamp: string): Date {
  const normalised = ISO_WITHOUT_TZ.test(timestamp) ? `${timestamp}Z` : timestamp;
  return new Date(normalised);
}

export function formatRelativeTime(timestamp: string): string {
  const date = parseBackendTimestamp(timestamp);

  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  const deltaSeconds = Math.floor((Date.now() - date.getTime()) / 1000);

  if (deltaSeconds < 5) return "just now";
  if (deltaSeconds < 60) return `${deltaSeconds}s ago`;

  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) return `${deltaMinutes}m ago`;

  const deltaHours = Math.floor(deltaMinutes / 60);
  if (deltaHours < 24) return `${deltaHours}h ago`;

  const deltaDays = Math.floor(deltaHours / 24);
  return `${deltaDays}d ago`;
}
