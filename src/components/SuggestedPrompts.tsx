import { Zap, Gift, TrendingUp, Percent } from "lucide-react";

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

const prompts = [
  {
    icon: TrendingUp,
    label: "Trending",
    prompt: "What are the trending products right now?",
  },
  {
    icon: Percent,
    label: "Deals",
    prompt: "Show me the best deals today",
  },
  {
    icon: Gift,
    label: "Gift Ideas",
    prompt: "I need gift ideas under $50",
  },
  {
    icon: Zap,
    label: "Quick Picks",
    prompt: "Recommend something popular in electronics",
  },
];

const SuggestedPrompts = ({ onSelect }: SuggestedPromptsProps) => {
  return (
    <div className="flex flex-wrap gap-2 justify-center">
      {prompts.map((item) => (
        <button
          key={item.label}
          onClick={() => onSelect(item.prompt)}
          className="flex items-center gap-2 px-4 py-2 rounded-full glass hover:bg-secondary/80 transition-all duration-200 hover:scale-105 group"
        >
          <item.icon className="w-4 h-4 text-primary group-hover:scale-110 transition-transform" />
          <span className="text-sm font-medium text-foreground">
            {item.label}
          </span>
        </button>
      ))}
    </div>
  );
};

export default SuggestedPrompts;
