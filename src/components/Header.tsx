import { ShoppingBag, Search, Menu, Sparkles } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface HeaderProps {
  cartCount?: number;
}

const Header = ({ cartCount = 0 }: HeaderProps) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full glass border-b border-border/50">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center shadow-glow">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-lg font-bold text-foreground">VoiceShop</h1>
            <p className="text-xs text-muted-foreground -mt-1">AI Assistant</p>
          </div>
        </div>

        {/* Search bar - Desktop */}
        <div className={cn(
          "hidden md:flex items-center gap-2 flex-1 max-w-md mx-8",
          "bg-secondary/50 rounded-xl px-4 py-2 border border-border/50",
          "focus-within:border-primary/50 focus-within:shadow-glow transition-all"
        )}>
          <Search className="w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search products..."
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          {/* Mobile search toggle */}
          <button
            onClick={() => setIsSearchOpen(!isSearchOpen)}
            className="md:hidden w-10 h-10 rounded-xl bg-secondary/50 flex items-center justify-center hover:bg-secondary transition-colors"
          >
            <Search className="w-5 h-5 text-foreground" />
          </button>

          {/* Cart */}
          <button className="relative w-10 h-10 rounded-xl bg-secondary/50 flex items-center justify-center hover:bg-secondary transition-colors">
            <ShoppingBag className="w-5 h-5 text-foreground" />
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full gradient-primary text-xs font-bold text-primary-foreground flex items-center justify-center">
                {cartCount > 9 ? "9+" : cartCount}
              </span>
            )}
          </button>

          {/* Menu */}
          <button className="w-10 h-10 rounded-xl bg-secondary/50 flex items-center justify-center hover:bg-secondary transition-colors">
            <Menu className="w-5 h-5 text-foreground" />
          </button>
        </div>
      </div>

      {/* Mobile search bar */}
      <div
        className={cn(
          "md:hidden overflow-hidden transition-all duration-300",
          isSearchOpen ? "h-14 border-t border-border/50" : "h-0"
        )}
      >
        <div className="container mx-auto px-4 py-2">
          <div className="flex items-center gap-2 bg-secondary/50 rounded-xl px-4 py-2 border border-border/50">
            <Search className="w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search products..."
              className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            />
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
