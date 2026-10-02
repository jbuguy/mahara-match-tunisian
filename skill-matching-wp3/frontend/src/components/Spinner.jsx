function Spinner({ label = 'Chargement en cours…' }) {
  return <div className="loading-state" role="status"><span className="spinner" />{label}</div>
}

export default Spinner