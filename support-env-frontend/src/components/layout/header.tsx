"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Headphones,
  PlayCircle,
  BarChart3,
  ListChecks,
  GitBranch,
  ExternalLink,
} from "lucide-react";

const navItems = [
  {
    href: "/",
    label: "Home",
    icon: Headphones,
  },
  {
    href: "/playground",
    label: "Playground",
    icon: PlayCircle,
  },
  {
    href: "/baseline",
    label: "Baseline",
    icon: BarChart3,
  },
  {
    href: "/tasks",
    label: "Tasks",
    icon: ListChecks,
  },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        {/* Logo */}
        <Link href="/" className="flex items-center space-x-2 mr-8">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Headphones className="h-5 w-5" />
          </div>
          <span className="font-bold text-xl">SupportEnv</span>
        </Link>

        {/* Navigation */}
        <nav className="flex items-center space-x-1 flex-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={isActive ? "secondary" : "ghost"}
                  size="sm"
                  className={cn(
                    "gap-2",
                    isActive && "bg-secondary"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </nav>

        {/* External Links */}
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" asChild>
            <a
              href="https://github.com/username/support-env"
              target="_blank"
              rel="noopener noreferrer"
              className="gap-2"
            >
              <GitBranch className="h-4 w-4" />
              GitHub
            </a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a
              href="https://huggingface.co/spaces/username/support-env"
              target="_blank"
              rel="noopener noreferrer"
              className="gap-2"
            >
              <ExternalLink className="h-4 w-4" />
              HF Space
            </a>
          </Button>
        </div>
      </div>
    </header>
  );
}