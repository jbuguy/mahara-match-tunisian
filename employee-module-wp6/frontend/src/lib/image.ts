/** Largest file we try to open; phone photos are usually 2-8 MB. */
export const MAX_SOURCE_BYTES = 20 * 1024 * 1024

/**
 * Crops a picture to a centred square and shrinks it to a JPEG of size x size (about 20-40 KB),
 * so the upload is quick and the backend stores something small. Rejects if the browser can't read it.
 */
export async function squareJpeg(file: Blob, size = 256): Promise<Blob> {
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await image.decode()
    const side = Math.min(image.naturalWidth, image.naturalHeight)
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const context = canvas.getContext('2d')
    if (!context || side === 0) throw new Error('cannot draw image')
    context.fillStyle = '#FFFFFF' // transparent PNGs get a white background, not black
    context.fillRect(0, 0, size, size)
    context.drawImage(
      image,
      (image.naturalWidth - side) / 2,
      (image.naturalHeight - side) / 2,
      side,
      side,
      0,
      0,
      size,
      size,
    )
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('cannot encode JPEG'))), 'image/jpeg', 0.85),
    )
  } finally {
    URL.revokeObjectURL(url)
  }
}
