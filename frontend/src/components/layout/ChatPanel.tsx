import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Send,
  User,
  Loader2,
  Sparkles,
  CheckCircle2,
  XCircle,
  BarChart3,
  Calendar,
  X,
  Download,
  Eye,
  Wrench,
  FileDown,
  Check,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/** Render lightweight markdown (bold, italic) into React elements */
function formatMarkdown(text: string) {
  // Split by **bold** and *italic* markers, return mixed string/JSX array
  const parts: React.ReactNode[] = [];
  // Process line by line to preserve whitespace
  const regex = /\*\*(.+?)\*\*|\*(.+?)\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[1] !== undefined) {
      parts.push(<strong key={key++}>{match[1]}</strong>);
    } else if (match[2] !== undefined) {
      parts.push(<em key={key++}>{match[2]}</em>);
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

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
  "Generate timetable for semester 3",
  "Export PDF",
  "Show faculty load distribution",
  "Which rooms are free Monday Period 2?",
];

function GenerationCard({ data, onAction }: { data: Record<string, unknown>; onAction: (msg: string) => void }) {
  const score = data.score as number;
  const entryCount = data.entry_count as number;
  const wallTime = data.wall_time as number;
  const status = data.status as string;
  const timetableId = data.timetable_id as string;
  const published = data.published as boolean;
  const autoFixes = data.auto_fixes as string[] | undefined;
  const [showFixes, setShowFixes] = useState(false);

  const isGood = status === "OPTIMAL" || status === "FEASIBLE";

  return (
    <div className="mt-2 p-2.5 rounded-xl bg-background border space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Status header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold">
          {isGood ? (
            <div className="h-5 w-5 rounded-md bg-green-100 dark:bg-green-900 flex items-center justify-center">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
            </div>
          ) : (
            <div className="h-5 w-5 rounded-md bg-red-100 dark:bg-red-900 flex items-center justify-center">
              <XCircle className="w-3.5 h-3.5 text-red-500" />
            </div>
          )}
          <span>{status}{published ? " & Published" : ""}</span>
        </div>
        {isGood && score != null && (
          <span className={cn(
            "text-[10px] font-bold px-1.5 py-0.5 rounded-md",
            score >= 90 ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-400"
              : score >= 70 ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-400"
              : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-400",
          )}>
            {score}%
          </span>
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1">
          <BarChart3 className="w-3 h-3" />
          {entryCount ?? 0} entries
        </div>
        <div className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {wallTime ?? 0}s
        </div>
      </div>

      {/* Auto-fixes */}
      {autoFixes && autoFixes.length > 0 && (
        <div className="animate-in fade-in duration-500 delay-200">
          <button
            onClick={() => setShowFixes((v) => !v)}
            className="flex items-center gap-1 text-[10px] font-medium text-amber-600 dark:text-amber-400 hover:text-amber-700 transition-colors w-full"
          >
            <Wrench className="w-3 h-3" />
            Auto-fixed {autoFixes.length} issue{autoFixes.length > 1 ? "s" : ""}
            <span className={cn(
              "ml-auto text-[9px] transition-transform duration-200",
              showFixes && "rotate-180",
            )}>▼</span>
          </button>
          {showFixes && (
            <ul className="mt-1 space-y-0.5 text-[9px] text-muted-foreground animate-in fade-in slide-in-from-top-1 duration-200">
              {autoFixes.map((fix, i) => (
                <li key={i} className="flex items-start gap-1">
                  <span className="text-amber-500 mt-px">•</span>
                  {fix}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Action buttons */}
      {timetableId && (
        <div className="flex gap-1.5 pt-1 animate-in fade-in duration-500 delay-300">
          <a
            href={`/timetable/view/${timetableId}`}
            className={cn(
              "inline-flex items-center gap-1.5 text-[10px] font-medium px-2.5 py-1.5 rounded-lg",
              "bg-primary/10 text-primary hover:bg-primary/20",
              "transition-all duration-200 active:scale-95",
            )}
          >
            <Eye className="w-3 h-3" /> View
          </a>
          <button
            onClick={() => onAction("Export PDF")}
            className={cn(
              "inline-flex items-center gap-1.5 text-[10px] font-medium px-2.5 py-1.5 rounded-lg",
              "bg-primary text-primary-foreground hover:bg-primary/90",
              "transition-all duration-200 active:scale-95 shadow-sm",
            )}
          >
            <Download className="w-3 h-3" /> Export PDF
          </button>
        </div>
      )}
    </div>
  );
}

function ExportCard({ data }: { data: Record<string, unknown> }) {
  const timetableId = data.timetable_id as string;
  const exportType = (data.export_type as string) || "department";
  const [downloading, setDownloading] = useState<string | null>(null);
  const [done, setDone] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const handleDownload = useCallback(async (type: string) => {
    if (downloading) return;
    setDownloading(type);
    setError(null);
    try {
      const res = await apiClient.get(`/export/${type}/${timetableId}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = `timetable_${type}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setDone((prev) => new Set(prev).add(type));
    } catch {
      setError(`Failed to download ${type} PDF`);
    } finally {
      setDownloading(null);
    }
  }, [downloading, timetableId]);

  const types = ["department", "faculty", "room"] as const;

  return (
    <div className="mt-2 p-2.5 rounded-xl bg-background border space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex items-center gap-2 text-xs font-semibold">
        <div className="h-5 w-5 rounded-md bg-primary/10 flex items-center justify-center">
          <FileDown className="w-3 h-3 text-primary" />
        </div>
        Download PDF
      </div>
      <div className="flex flex-col gap-1.5">
        {types.map((type) => {
          const isActive = downloading === type;
          const isDone = done.has(type);
          const isHighlight = type === exportType;
          return (
            <button
              key={type}
              onClick={() => handleDownload(type)}
              disabled={!!downloading}
              className={cn(
                "group relative flex items-center gap-2 text-[11px] px-3 py-2 rounded-lg transition-all duration-200",
                "border hover:shadow-sm active:scale-[0.98]",
                isActive && "border-primary/40 bg-primary/5",
                isDone && "border-green-300 bg-green-50 dark:border-green-800 dark:bg-green-950",
                !isActive && !isDone && isHighlight && "border-primary/30 bg-primary/5 hover:bg-primary/10",
                !isActive && !isDone && !isHighlight && "border-border hover:bg-accent",
                downloading && !isActive && "opacity-50 cursor-not-allowed",
              )}
            >
              <div className={cn(
                "h-6 w-6 rounded-md flex items-center justify-center shrink-0 transition-all duration-300",
                isDone ? "bg-green-100 dark:bg-green-900" : "bg-muted",
              )}>
                {isActive ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                ) : isDone ? (
                  <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                ) : (
                  <Download className={cn(
                    "w-3.5 h-3.5 transition-transform duration-200",
                    "group-hover:translate-y-0.5",
                    isHighlight ? "text-primary" : "text-muted-foreground"
                  )} />
                )}
              </div>
              <span className={cn(
                "flex-1 text-left font-medium",
                isDone ? "text-green-700 dark:text-green-400" : "",
              )}>
                {type.charAt(0).toUpperCase() + type.slice(1)} Timetable
              </span>
              {isDone && (
                <span className="text-[9px] text-green-600 dark:text-green-400 animate-in fade-in duration-200">
                  Downloaded
                </span>
              )}
              {isActive && (
                <span className="text-[9px] text-primary animate-pulse">
                  Preparing...
                </span>
              )}
            </button>
          );
        })}
      </div>
      {error && (
        <p className="text-[10px] text-red-500 animate-in fade-in duration-200 flex items-center gap-1">
          <XCircle className="w-3 h-3" /> {error}
        </p>
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
          "fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-xl flex items-center justify-center overflow-hidden",
          "transition-all duration-300 ease-out hover:shadow-2xl",
          open
            ? "bg-muted text-muted-foreground hover:bg-accent rotate-0"
            : "bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-110",
        )}
        title={open ? "Close assistant" : "Open AI assistant"}
      >
        <div className="relative h-6 w-6">
          <img src="/logo.png" alt="AI" className={cn(
            "absolute inset-0 h-full w-full object-contain scale-[2.4] transition-all duration-300",
            open ? "opacity-0 rotate-90 scale-0" : "opacity-100 rotate-0 scale-[2.4]",
          )} />
          <X className={cn(
            "h-6 w-6 transition-all duration-300",
            open ? "opacity-100 rotate-0 scale-100" : "opacity-0 -rotate-90 scale-0",
          )} />
        </div>
        {/* Pulse ring when closed */}
        {!open && (
          <span className="absolute inset-0 rounded-full bg-primary/30 animate-ping opacity-20" />
        )}
      </button>

      {/* Panel */}
      <div
        className={cn(
          "fixed bottom-[5.5rem] right-6 z-50 w-[380px] rounded-2xl border bg-card shadow-2xl flex flex-col origin-bottom-right",
          "transition-all duration-300 ease-out",
          open
            ? "opacity-100 scale-100 translate-y-0 pointer-events-auto"
            : "opacity-0 scale-90 translate-y-4 pointer-events-none",
        )}
        style={{ height: "min(600px, calc(100vh - 120px))" }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b shrink-0">
          <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
            <img src="/logo.png" alt="AI" className="w-6 h-6 object-contain" />
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
                  "flex gap-2 animate-in fade-in slide-in-from-bottom-2 duration-300",
                  msg.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {msg.role === "assistant" && (
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5 overflow-hidden">
                    <img src="/logo.png" alt="AI" className="w-5 h-5 object-contain" />
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
                  <p className="whitespace-pre-wrap">{formatMarkdown(msg.text)}</p>
                  {msg.data && msg.data.timetable_id && msg.data.export_ready && (
                    <ExportCard data={msg.data} />
                  )}
                  {msg.data && msg.data.timetable_id && !msg.data.export_ready && (
                    <GenerationCard data={msg.data} onAction={sendMessage} />
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
              <div className="flex gap-2 justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
                  <img src="/logo.png" alt="AI" className="w-5 h-5 object-contain" />
                </div>
                <div className="bg-muted rounded-2xl px-4 py-2.5 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Quick actions */}
        {messages.length <= 1 && (
          <div className="px-3 pb-2 shrink-0 animate-in fade-in slide-in-from-bottom-3 duration-500 delay-300">
            <div className="flex items-center gap-1.5 mb-1.5 text-[10px] text-muted-foreground">
              <Sparkles className="w-3 h-3" />
              Quick actions
            </div>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_ACTIONS.map((action, i) => (
                <Button
                  key={action}
                  variant="outline"
                  size="sm"
                  className={cn(
                    "text-[10px] h-7 px-2.5 transition-all duration-200",
                    "hover:bg-primary/10 hover:text-primary hover:border-primary/30",
                    "active:scale-95",
                    "animate-in fade-in duration-300",
                  )}
                  style={{ animationDelay: `${i * 75}ms` }}
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
              className="h-8 w-8 transition-all duration-200 active:scale-90 hover:shadow-md"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>
        </div>
      </div>
    </>
  );
}
