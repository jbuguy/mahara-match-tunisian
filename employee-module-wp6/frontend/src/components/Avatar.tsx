import { useState } from 'react'

import { initials } from '@/lib/auth-context'
import { useUserPhoto } from '@/lib/photo'
import { cn } from '@/lib/utils'

/**
 * A round photo, or the person's initials when there is none or it fails to load.
 * Decorative (aria-hidden): the name is always written next to it.
 */
export function Avatar({
  name,
  src,
  inverted = false,
  className,
}: {
  name: string
  src: string | null
  inverted?: boolean
  className?: string
}) {
  const [failed, setFailed] = useState<string | null>(null)

  if (src && failed !== src) {
    return (
      <img
        src={src}
        alt=""
        aria-hidden
        // Google photos are refused when the request carries our page as referrer.
        referrerPolicy="no-referrer"
        onError={() => setFailed(src)}
        className={cn('shrink-0 rounded-full bg-secondary object-cover', className)}
      />
    )
  }
  return (
    <span
      aria-hidden
      className={cn(
        'grid shrink-0 place-items-center rounded-full font-heading font-semibold',
        inverted ? 'bg-white text-teal' : 'bg-teal text-white',
        className,
      )}
    >
      {initials(name)}
    </span>
  )
}

/** The signed-in user's avatar: uploaded photo, else Google photo, else initials. */
export function UserAvatar(props: { name: string; inverted?: boolean; className?: string }) {
  const { src } = useUserPhoto()
  return <Avatar {...props} src={src} />
}
