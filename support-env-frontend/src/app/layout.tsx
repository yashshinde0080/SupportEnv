import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { Header } from "@/components/layout/header";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SupportEnv - Customer Support RL Environment",
  description: "Interactive environment for training AI agents on customer support workflows",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <div className="min-h-screen bg-background">
          <Header />
          <main className="container mx-auto py-6 px-4">
            {children}
          </main>
        </div>
        <Toaster />
      </body>
    </html>
  );
}