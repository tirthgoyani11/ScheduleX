import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";

export default function RegisterPage() {
  const { register, isLoading } = useAuthStore();
  const navigate = useNavigate();
  const [role, setRole] = useState<"super_admin" | "dept_admin">("super_admin");
  const [collegeName, setCollegeName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    try {
      await register({
        email,
        password,
        full_name: fullName,
        role,
        college_name: collegeName,
      });
      toast.success("Account created successfully");
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Registration failed";
      toast.error(msg);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary relative overflow-hidden flex-col justify-center px-16">
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="h-12 w-12 rounded-lg bg-primary-foreground/10 border border-primary-foreground/20 flex items-center justify-center">
              <span className="text-primary-foreground font-display font-bold text-xl">X</span>
            </div>
            <span className="text-primary-foreground font-display font-bold text-3xl">ScheduleX</span>
          </div>
          <p className="text-primary-foreground/70 text-xl font-body">Academic scheduling, reimagined.</p>
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-sm page-enter">
          <h1 className="text-2xl font-semibold font-display mb-1">Create account</h1>
          <p className="text-muted-foreground mb-8">Get started with ScheduleX</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>College Name</Label>
              <Input className="rounded-xl" value={collegeName} onChange={(e) => setCollegeName(e.target.value)} placeholder="CVM University" />
            </div>
            <div className="space-y-2">
              <Label>Your Name</Label>
              <Input className="rounded-xl" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Dr. John Doe" />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" className="rounded-xl" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@college.edu" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Password</Label>
                <Input type="password" className="rounded-xl" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
              </div>
              <div className="space-y-2">
                <Label>Confirm</Label>
                <Input type="password" className="rounded-xl" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="••••••••" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <div className="grid grid-cols-2 gap-3">
                {([["super_admin", "🔑 Super Admin"], ["dept_admin", "📋 Dept Admin"]] as const).map(([r, lbl]) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`p-3 rounded-xl border-2 text-sm font-medium transition-all ${
                      role === r ? "border-primary bg-accent" : "border-border hover:border-border-strong"
                    }`}
                  >
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="terms" />
              <Label htmlFor="terms" className="text-sm font-normal">I agree to the terms of service</Label>
            </div>
            <Button type="submit" className="w-full rounded-xl btn-press" disabled={isLoading}>
              {isLoading ? "Creating account..." : "Create account"}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            Already have an account?{" "}
            <Link to="/login" className="text-foreground font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
