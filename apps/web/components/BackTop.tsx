import Link from 'next/link';

export default function BackTop({ href, children }: { href: string; children: React.ReactNode }) {
  return <nav className="topBack"><Link className="backLink" href={href}>{children}</Link></nav>;
}
