import { useState, useCallback, useEffect } from "react";
import Header from "@/components/Header";
import VoiceButton, { VoiceStatus } from "@/components/VoiceButton";
import ConversationPanel, { Message } from "@/components/ConversationPanel";
import ProductComparisonTable, { ComparisonProduct } from "@/components/ProductComparisonTable";
import StatusIndicator from "@/components/StatusIndicator";
import SuggestedPrompts from "@/components/SuggestedPrompts";
import { useToast } from "@/hooks/use-toast";
import { useVoiceAssistant } from "@/hooks/useSpeechToText";

const Index = () => {
  const { toast } = useToast();
  const { isRecording, isProcessing, isPlaying, startRecording, stopAndPlay, error } = useVoiceAssistant();
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");
  const [isConnected] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [products, setProducts] = useState<ComparisonProduct[]>([]);
  const [cartCount, setCartCount] = useState(0);

  // Sync voice status with recording/processing/playing state
  useEffect(() => {
    if (isRecording) {
      setVoiceStatus("listening");
    } else if (isProcessing) {
      setVoiceStatus("processing");
    } else if (isPlaying) {
      setVoiceStatus("speaking");
    } else {
      setVoiceStatus("idle");
    }
  }, [isRecording, isProcessing, isPlaying]);

  // Show error toast
  useEffect(() => {
    if (error) {
      toast({
        title: "Error",
        description: error,
        variant: "destructive",
      });
    }
  }, [error, toast]);

  const handleVoiceClick = useCallback(async () => {
    if (voiceStatus === "idle") {
      // Start recording
      await startRecording();
    } else if (voiceStatus === "listening") {
      // Stop recording and send to backend, play response
      const response = await stopAndPlay();
      
      if (response) {
        // Add user message with transcript
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: "user",
            content: response.transcript,
            timestamp: new Date(),
          },
        ]);

        // Add assistant message with answer
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: response.answer,
            timestamp: new Date(),
          },
        ]);

        // Map backend products to ComparisonProduct format
        if (response.products && response.products.length > 0) {
          const mappedProducts: ComparisonProduct[] = response.products.map((p, index) => ({
            id: p.id,
            name: p.title,
            brand: p.brand || "Unknown",
            price: p.price,
            rating: p.rating >= 0 ? p.rating : 0,
            reviews: 0,
            ingredients: "",
            sourceType: "link" as const,
            sourceLabel: "View Product",
            sourceUrl: p.product_url,
            isTopPick: index === 0,
            imageUrl: p.image_url,
          }));
          setProducts(mappedProducts);
        }
      }
    } else {
      // Cancel/stop any ongoing process
      setVoiceStatus("idle");
    }
  }, [voiceStatus, startRecording, stopAndPlay]);

  const handlePromptSelect = (prompt: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: "user",
        content: prompt,
        timestamp: new Date(),
      },
    ]);
    setVoiceStatus("processing");

    setTimeout(() => {
      setVoiceStatus("speaking");
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: `Great choice! I'm searching for "${prompt.toLowerCase()}". Here are some recommendations I think you'll love.`,
          timestamp: new Date(),
        },
      ]);
      // Products already showing
    }, 1500);

    setTimeout(() => {
      setVoiceStatus("idle");
    }, 3000);
  };

  const handleSelectProduct = (product: ComparisonProduct) => {
    setCartCount((prev) => prev + 1);
    toast({
      title: "Added to cart",
      description: `${product.name} by ${product.brand} has been added to your cart.`,
    });
  };

  return (
    <div className="min-h-screen gradient-surface">
      <Header cartCount={cartCount} />

      <main className="container mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-2 gap-8 min-h-[calc(100vh-8rem)]">
          {/* Left Panel - Voice Interface */}
          <div className="flex flex-col">
            {/* Status bar */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-foreground">
                AI Assistant
              </h2>
              <StatusIndicator
                isConnected={isConnected}
                isMuted={isMuted}
                onToggleMute={() => setIsMuted(!isMuted)}
              />
            </div>

            {/* Conversation area */}
            <div className="flex-1 glass rounded-2xl mb-6 min-h-[300px] max-h-[400px] overflow-y-auto">
              <ConversationPanel
                messages={messages}
                isLoading={voiceStatus === "processing"}
              />
            </div>

            {/* Voice button section */}
            <div className="flex flex-col items-center gap-8 py-8">
              <VoiceButton status={voiceStatus} onClick={handleVoiceClick} />
              
              {/* Suggested prompts */}
              {messages.length === 0 && (
                <div className="mt-8 w-full">
                  <p className="text-center text-sm text-muted-foreground mb-4">
                    Or try one of these:
                  </p>
                  <SuggestedPrompts onSelect={handlePromptSelect} />
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Product Comparison */}
          <div className="flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-foreground">
                Top Products Recommendation
              </h2>
            </div>

            {/* Comparison Table */}
            {products.length > 0 && (
              <div className="animate-in fade-in slide-in-from-bottom-4">
                <ProductComparisonTable
                  products={products}
                  onSelectProduct={handleSelectProduct}
                />
              </div>
            )}


            {/* Feature highlights */}
            <div className="mt-8 grid grid-cols-3 gap-4">
              {[
                { label: "Free Shipping", value: "Orders $50+" },
                { label: "Easy Returns", value: "30 Days" },
                { label: "Secure Pay", value: "Encrypted" },
              ].map((feature) => (
                <div
                  key={feature.label}
                  className="glass rounded-xl p-4 text-center"
                >
                  <p className="text-primary font-semibold text-sm">
                    {feature.label}
                  </p>
                  <p className="text-muted-foreground text-xs mt-1">
                    {feature.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
