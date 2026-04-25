export const metadata = {
  title: 'Zetheta — Assessment Engine',
  description: 'Secure MCQ assessment environment',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
