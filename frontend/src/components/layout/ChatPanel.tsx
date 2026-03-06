import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Bot,
  Send,
  User,
  Loader2,
  Sparkles,
  CheckCircle2,
  XCircle,
  BarChart3,
  Calendar,
  X,
  MessageSquare,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  intent?: string;
  confidence?: number;
  timestamp: Date;
  data?: Record<string, unknown> | null;
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
  "Generate timetable for semester 3",
  "Publish the timetable",
];

function GenerationCard({ data }: { data: Record<string, unknown> }) {
  const score = data.score as number;
  const entryCount = data.entry_count as number;
  const wallTime = data.wall_time as number;
  const status = data.status as string;
  const timetableId = data.timetable_id as string;

  return (
    <div className="mt-2 p-2 rounded-lg bg-background border space-y-1.5">
      <div className="flex items-center gap-2 text-xs font-medium">
        {status === "OPTIMAL" || status === "FEASIBLE" ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-red-500" />
        )}
        Timetable {status}
      </div>
      <div className="grid grid-cols-3 gap-1 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1">
          <BarChart3 className="w-3 h-3" />
          {score ?? 0}%
        </div>
        <div className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {entryCount ?? 0}
        </div>
        <div>{wallTime ?? 0}s</div>
      </div>
      {timetableId && (
        <a
          href="/timetable"
          className="text-[10px] text-primary underline hover:no-underline"
        >
          View Timetable →
        </a>
      )}
    </div>
  );
}

export function ChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 0,
      role: "assistant",
      text: "Hi! I'm TimetableAI 🎓 Ask me about rooms, faculty, scheduling, or generate timetables!",
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

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

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
        data: res.data,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: "Sorry, I encountered an error. Please try again.",
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
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed bottom-6 right-6 z-50 h-12 w-12 rounded-full shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-105",
          open
            ? "bg-muted text-muted-foreground hover:bg-accent"
            : "bg-primary text-primary-foreground hover:bg-primary/90"
        )}
        title={open ? "Close assistant" : "Open AI assistant"}
      >
        {open ? <X className="h-5 w-5" /> : <MessageSquare className="h-5 w-5" />}
      </button>

      {/* Panel */}
      <div
        className={cn(
          "fixed bottom-20 right-6 z-50 w-[380px] rounded-2xl border bg-card shadow-2xl flex flex-col transition-all duration-200 origin-bottom-right",
          open
            ? "opacity-100 scale-100 pointer-events-auto"
            : "opacity-0 scale-95 pointer-events-none"
        )}
        style={{ height: "min(600px, calc(100vh - 120px))" }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b shrink-0">
          <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center">
            <Bot className="w-4 h-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold leading-tight">TimetableAI</p>
            <p className="text-[10px] text-muted-foreground">Scheduling assistant</p>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded-lg hover:bg-accent transition-colors"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="p-3 space-y-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "flex gap-2",
                  msg.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {msg.role === "assistant" && (
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
                    <Bot className="w-3 h-3 text-primary" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[80%] rounded-2xl px-3 py-2 text-xs leading-relaxed",
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  )}
                >
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {msg.data && msg.data.timetable_id && (
                    <GenerationCard data={msg.data} />
                  )}
                  {msg.intent && (
                    <div className="flex items-center gap-1.5 mt-1.5 pt-1.5 border-t border-border/30">
                      <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
                        {msg.intent}
                      </Badge>
                      {msg.confidence !== undefined && msg.confidence > 0 && (
                        <span className="text-[9px] text-muted-foreground">
                          {Math.round(msg.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary flex items-center justify-center mt-0.5">
                    <User className="w-3 h-3 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-2 justify-start">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="w-3 h-3 text-primary" />
                </div>
                <div className="bg-muted rounded-2xl px-3 py-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Quick actions */}
        {messages.length <= 1 && (
          <div className="px-3 pb-2 shrink-0">
            <div className="flex items-center gap-1.5 mb-1.5 text-[10px] text-muted-foreground">
              <Sparkles className="w-3 h-3" />
              Quick actions
            </div>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_ACTIONS.map((action) => (
                <Button
                  key={action}
                  variant="outline"
                  size="sm"
                  className="text-[10px] h-6 px-2"
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
        <div className="border-t p-3 shrink-0">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything..."
              disabled={loading}
              className="flex-1 h-8 text-xs"
            />
            <Button
              type="submit"
              disabled={loading || !input.trim()}
              size="icon"
              className="h-8 w-8"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>
        </div>
      </div>
    </>
  );
}
