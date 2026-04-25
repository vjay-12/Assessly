export const metadata = {
  title: 'Zetheta — Admin Dashboard',
  description: 'Real-time talent insights and audit trails',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50">{children}</body>
    </html>
  );
}
