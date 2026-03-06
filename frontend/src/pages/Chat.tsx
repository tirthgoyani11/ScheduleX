import { useState, useRef, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PageHeader } from "@/components/common/PageHeader";
import { Bot, Send, User, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api-client";

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  intent?: string;
  confidence?: number;
  timestamp: Date;
}

interface ChatApiResponse {
  reply: string;
  intent: string;
  confidence: number;
  data?: Record<string, unknown> | null;
}

const QUICK_ACTIONS = [
  "Which rooms are free Monday Period 2?",
  "Show faculty load distribution",
  "Prof. Patel is absent Period 3, who can substitute?",
  "Why was this timetable generated this way?",
  "Any clashes in the current schedule?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 0,
      role: "assistant",
      text: "Hi! I'm TimetableAI 🎓 I can help you with room availability, faculty workload, substitutions, and scheduling questions. Try asking something or use a quick action below!",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now(),
      role: "user",
      text: text.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post<ChatApiResponse>("/chat/message", {
        message: text.trim(),
      });
      const botMsg: ChatMessage = {
        id: Date.now() + 1,
        role: "assistant",
        text: res.reply,
        intent: res.intent,
        confidence: res.confidence,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: "Sorry, I encountered an error. Please check if the AI service is configured (NVIDIA API key in .env) and try again.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <PageHeader
        title="AI Chat Assistant"
        description="Ask questions about timetables, rooms, faculty, and scheduling"
      />

      <Card className="flex-1 flex flex-col min-h-0 mt-4">
        {/* Messages */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {msg.intent && (
                    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/30">
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                        {msg.intent}
                      </Badge>
                      {msg.confidence !== undefined && msg.confidence > 0 && (
                        <span className="text-[10px] text-muted-foreground">
                          {Math.round(msg.confidence * 100)}% conf
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <User className="w-4 h-4 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
                <div className="bg-muted rounded-2xl px-4 py-3">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Quick actions */}
        {messages.length <= 1 && (
          <div className="px-4 pb-2">
            <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
              <Sparkles className="w-3 h-3" />
              Quick actions
            </div>
            <div className="flex flex-wrap gap-2 max-w-3xl mx-auto">
              {QUICK_ACTIONS.map((action) => (
                <Button
                  key={action}
                  variant="outline"
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => sendMessage(action)}
                  disabled={loading}
                >
                  {action}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="border-t p-4">
          <form
            onSubmit={handleSubmit}
            className="flex gap-2 max-w-3xl mx-auto"
          >
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about rooms, faculty, scheduling..."
              disabled={loading}
              className="flex-1"
              autoFocus
            />
            <Button type="submit" disabled={loading || !input.trim()} size="icon">
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
