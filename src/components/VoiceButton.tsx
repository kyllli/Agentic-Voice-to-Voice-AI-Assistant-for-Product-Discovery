import { Mic, MicOff, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type VoiceStatus = "idle" | "listening" | "processing" | "speaking";

interface VoiceButtonProps {
  status: VoiceStatus;
  onClick: () => void;
  disabled?: boolean;
}

const VoiceButton = ({ status, onClick, disabled }: VoiceButtonProps) => {
  const isActive = status === "listening" || status === "speaking";
  const isProcessing = status === "processing";

  return (
    <div className="relative flex items-center justify-center">
      {/* Outer glow rings */}
      {isActive && (
        <>
          <div className="absolute w-40 h-40 rounded-full gradient-glow animate-pulse-ring" />
          <div className="absolute w-48 h-48 rounded-full gradient-glow animate-pulse-ring [animation-delay:0.5s]" />
          <div className="absolute w-56 h-56 rounded-full gradient-glow animate-pulse-ring [animation-delay:1s]" />
        </>
      )}

      {/* Voice waves when speaking */}
      {status === "speaking" && (
        <div className="absolute flex items-center gap-1">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="w-1 h-8 rounded-full bg-primary animate-voice-wave"
              style={{ animationDelay: `${i * 0.1}s` }}
            />
          ))}
        </div>
      )}

      {/* Main button */}
      <button
        onClick={onClick}
        disabled={disabled || isProcessing}
        className={cn(
          "relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300",
          "focus:outline-none focus:ring-4 focus:ring-primary/30",
          isActive
            ? "gradient-primary shadow-glow-intense scale-110"
            : "bg-secondary hover:bg-secondary/80 hover:scale-105",
          isProcessing && "bg-secondary cursor-wait",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        {isProcessing ? (
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
        ) : isActive ? (
          <Mic className="w-10 h-10 text-primary-foreground" />
        ) : (
          <MicOff className="w-10 h-10 text-muted-foreground" />
        )}
      </button>

      {/* Status text */}
      <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 whitespace-nowrap">
        <span
          className={cn(
            "text-sm font-medium transition-colors",
            isActive ? "text-primary" : "text-muted-foreground"
          )}
        >
          {status === "idle" && "Tap to speak"}
          {status === "listening" && "Listening..."}
          {status === "processing" && "Processing..."}
          {status === "speaking" && "Speaking..."}
        </span>
      </div>
    </div>
  );
};

export default VoiceButton;
