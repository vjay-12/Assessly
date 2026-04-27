import './globals.css';

export const metadata = {
  title: 'Assessly — Admin Dashboard',
  description: 'Real-time talent insights and audit trails',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-slate-50">{children}</body>
    </html>
  );
}
