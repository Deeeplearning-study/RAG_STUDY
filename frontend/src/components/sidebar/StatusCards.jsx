function StatusCards({ health, documents }) {
  const stats = [
    { label: 'Indexed files', value: health?.indexed_files ?? documents.length ?? 0 },
    { label: 'Vector DB', value: health?.collection ?? 'Chroma' },
    { label: 'Embedding', value: health?.embedding_model ? 'Ready' : 'Loading' },
  ]

  return (
    <div className="stats">
      {stats.map((item) => (
        <div key={item.label} className="stat">
          <span>{item.label}</span>
          <strong>{String(item.value)}</strong>
        </div>
      ))}
    </div>
  )
}

export default StatusCards
