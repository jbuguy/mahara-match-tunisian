function ScoreBadge({ score }) {
  const tone = score >= 80 ? 'good' : score >= 50 ? 'medium' : 'low'
  return <span className={`score-badge ${tone}`}>{Number(score).toFixed(1)}<small>/100</small></span>
}

export default ScoreBadge