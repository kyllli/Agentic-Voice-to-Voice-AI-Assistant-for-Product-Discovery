import { User, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ConversationPanelProps {
  messages: Message[];
  isLoading?: boolean;
}

const ConversationPanel = ({ messages, isLoading }: ConversationPanelProps) => {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4">
        <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-4 shadow-glow">
          <Bot className="w-8 h-8 text-primary-foreground" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          Start a conversation
        </h3>
        <p className="text-muted-foreground text-sm max-w-xs">
          Tap the microphone and ask me about products, deals, or help finding
          what you need.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4 overflow-y-auto">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300",
            message.role === "user" ? "flex-row-reverse" : ""
          )}
        >
          {/* Avatar */}
          <div
            className={cn(
              "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
              message.role === "user"
                ? "bg-secondary"
                : "gradient-primary shadow-glow"
            )}
          >
            {message.role === "user" ? (
              <User className="w-4 h-4 text-foreground" />
            ) : (
              <Bot className="w-4 h-4 text-primary-foreground" />
            )}
          </div>

          {/* Message bubble */}
          <div
            className={cn(
              "max-w-[80%] rounded-2xl px-4 py-3",
              message.role === "user"
                ? "bg-primary text-primary-foreground rounded-tr-md"
                : "glass rounded-tl-md"
            )}
          >
            <p className="text-sm leading-relaxed">{message.content}</p>
            <span className="text-xs opacity-60 mt-1 block">
              {message.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
      ))}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex gap-3 animate-in fade-in duration-300">
          <div className="w-8 h-8 rounded-full gradient-primary flex items-center justify-center shadow-glow">
            <Bot className="w-4 h-4 text-primary-foreground" />
          </div>
          <div className="glass rounded-2xl rounded-tl-md px-4 py-3">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversationPanel;
