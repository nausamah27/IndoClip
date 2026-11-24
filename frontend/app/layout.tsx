import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'IndoClip Pro - OpusClip Clone Khusus Kreator Indonesia',
  description: 'AI Video Clipper otomatis 100% lokal hemat resource untuk Podcast, Gaming, Reaction, & Storytelling YouTube ke TikTok/Shorts.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className="dark">
      <body className="bg-dark-bg text-gray-100 antialiased selection:bg-salmon selection:text-white">
        {children}
      </body>
    </html>
  );
}
