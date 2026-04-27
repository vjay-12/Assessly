import './globals.css';

export const metadata = {
  title: 'Assessly — Candidate Portal',
  description: 'Secure distributed assessment platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
