import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '{{ cookiecutter.project_name }}',
  description: '{{ cookiecutter.description }}',
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
