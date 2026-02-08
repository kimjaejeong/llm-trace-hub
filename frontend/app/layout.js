import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "LLM Trace Hub",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <div className="nav">
            <Link href="/projects">Projects</Link>
            <Link href="/">Trace Dashboard</Link>
            <Link href="/cases">Cases</Link>
          </div>
          {children}
        </div>
      </body>
    </html>
  );
}
