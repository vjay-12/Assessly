import './globals.css';

export const metadata = {
  title: 'Assessly — Assessment Engine',
  description: 'Secure MCQ assessment environment',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
