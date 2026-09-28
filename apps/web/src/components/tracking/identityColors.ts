export const EMBEDDING_PALETTE = [
  '#f59e0b',
  '#22d3ee',
  '#a78bfa',
  '#34d399',
  '#fb7185',
  '#60a5fa',
  '#facc15',
  '#f472b6',
  '#4ade80',
  '#fb923c',
]

export function colorForIdentity(identityId: number): string {
  return EMBEDDING_PALETTE[identityId % EMBEDDING_PALETTE.length]
}
