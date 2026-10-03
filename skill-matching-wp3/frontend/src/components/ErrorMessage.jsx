function ErrorMessage({ message, onReturn }) {
  const noProfile = message?.includes('Aucun profil')
  return (
    <div className="error-box" role="alert">
      <strong>{noProfile ? 'Profil introuvable en mémoire' : 'Une erreur est survenue'}</strong>
      <p>{noProfile ? 'Le serveur a redémarré et a perdu les profils temporaires. Téléversez de nouveau votre CV pour continuer.' : message}</p>
      {(noProfile || onReturn) && <button className="button button-secondary" onClick={onReturn || (() => { window.location.href = '/profil' })}>Retourner à mon profil</button>}
    </div>
  )
}

export default ErrorMessage