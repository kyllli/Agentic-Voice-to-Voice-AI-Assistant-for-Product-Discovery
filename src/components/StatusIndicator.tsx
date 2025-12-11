import { Wifi, WifiOff, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusIndicatorProps {
  isConnected: boolean;
  isMuted: boolean;
  onToggleMute: () => void;
}

const StatusIndicator = ({
  isConnected,
  isMuted,
  onToggleMute,
}: StatusIndicatorProps) => {
  return (
    <div className="flex items-center gap-2">
      {/* Connection status */}
      <div
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium",
          isConnected
            ? "bg-primary/10 text-primary"
            : "bg-destructive/10 text-destructive"
        )}
      >
        {isConnected ? (
          <Wifi className="w-3 h-3" />
        ) : (
          <WifiOff className="w-3 h-3" />
        )}
        <span>{isConnected ? "Connected" : "Offline"}</span>
      </div>

      {/* Mute toggle */}
      <button
        onClick={onToggleMute}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
          isMuted
            ? "bg-muted text-muted-foreground"
            : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
        )}
      >
        {isMuted ? (
          <VolumeX className="w-3 h-3" />
        ) : (
          <Volume2 className="w-3 h-3" />
        )}
        <span>{isMuted ? "Muted" : "Sound On"}</span>
      </button>
    </div>
  );
};

export default StatusIndicator;
