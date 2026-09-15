import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '{{ cookiecutter.project_name }}',
  description: '{{ cookiecutter.description }}',
  // Social preview — generated from public/og.html. Set metadataBase once the domain is known.
  openGraph: { images: ['/og.png'] },
  twitter: { card: 'summary_large_image', images: ['/og.png'] },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {/* TRACKING_PLACEHOLDER */}
        {children}
      </body>
    </html>
  )
}
