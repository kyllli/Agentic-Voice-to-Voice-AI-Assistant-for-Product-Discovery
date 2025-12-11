import { useState, useCallback } from "react";
import { useAudioRecorder } from "./useAudioRecorder";

interface BackendProduct {
  id: string;
  title: string;
  price: number;
  rating: number;
  brand: string;
  product_url: string;
  image_url: string;
}

export interface VoiceResponse {
  transcript: string;
  answer: string;
  products: BackendProduct[];
}

interface UseVoiceAssistantReturn {
  isRecording: boolean;
  isProcessing: boolean;
  isPlaying: boolean;
  error: string | null;
  lastResponse: VoiceResponse | null;
  startRecording: () => Promise<void>;
  stopAndPlay: () => Promise<VoiceResponse | null>;
}

export const useVoiceAssistant = (): UseVoiceAssistantReturn => {
  const { isRecording, startRecording, stopRecording, error: recorderError } = useAudioRecorder();
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<VoiceResponse | null>(null);

  const stopAndPlay = useCallback(async (): Promise<VoiceResponse | null> => {
    setError(null);
    
    const audioBlob = await stopRecording();
    
    if (!audioBlob) {
      setError("No audio recorded");
      return null;
    }

    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");

      const response = await fetch("/api/voice", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Voice request failed: ${response.status}`);
      }

      const data = await response.json();
      const { transcript, answer, audio_base64, products = [] } = data;

      // Store the response
      const voiceResponse: VoiceResponse = { transcript, answer, products };
      setLastResponse(voiceResponse);

      // Convert base64 to audio and play
      const binaryString = atob(audio_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const mp3Blob = new Blob([bytes], { type: "audio/mpeg" });
      const audioUrl = URL.createObjectURL(mp3Blob);
      const audio = new Audio(audioUrl);
      
      setIsProcessing(false);
      setIsPlaying(true);
      
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.onerror = () => {
        setIsPlaying(false);
        setError("Failed to play audio");
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
      return voiceResponse;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Voice request failed";
      setError(errorMessage);
      console.error("Voice error:", err);
      setIsProcessing(false);
      return null;
    }
  }, [stopRecording]);

  return {
    isRecording,
    isProcessing,
    isPlaying,
    error: error || recorderError,
    lastResponse,
    startRecording,
    stopAndPlay,
  };
};
