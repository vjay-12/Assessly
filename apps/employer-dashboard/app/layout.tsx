export const metadata = {
  title: 'Zetheta — Employer Dashboard',
  description: 'Real-time talent insights',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
