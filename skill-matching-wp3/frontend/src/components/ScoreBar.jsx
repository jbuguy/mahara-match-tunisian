function ScoreBar({ value, label, detail }) {
  const score = Math.max(0, Math.min(100, Number(value) || 0))
  return (
    <div className="score-line">
      <div className="score-line-head"><span>{label}</span><strong>{score.toFixed(1)}<small>/100</small></strong></div>
      <div className="progress-track" role="progressbar" aria-label={label} aria-valuenow={score} aria-valuemin="0" aria-valuemax="100">
        <span className="progress-fill" style={{ width: `${score}%` }} />
      </div>
      {detail && <small className="score-detail">{detail}</small>}
    </div>
  )
}

export default ScoreBar