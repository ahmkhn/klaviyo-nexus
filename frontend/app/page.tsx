'use client';

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  RocketIcon, 
  Bot, 
  ShieldCheck, 
  Terminal, 
  Sparkles, 
  Users, 
  Zap, 
  ArrowRight, 
  CheckCircle2,
  Code2,
  Cpu
} from "lucide-react";

export default function Home() {
  const scrollToFeatures = () => {
    document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-slate-50 selection:bg-black selection:text-white">
      
      {/* Navigation */}
      <nav className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur-md">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-black p-1.5 rounded-lg">
              <RocketIcon className="h-5 w-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight">Klaviyo Nexus</span>
          </div>
          <div className="hidden md:flex items-center gap-6">
            <button onClick={scrollToFeatures} className="text-sm font-medium text-slate-600 hover:text-black transition-colors">
              Capabilities
            </button>
            <Link href="https://github.com/ahmkhn/klaviyo-nexus" target="_blank" className="text-sm font-medium text-slate-600 hover:text-black transition-colors">
              GitHub
            </Link>
          </div>
          <Link href="http://localhost:8000/auth/login">
            <Button className="bg-[#231F20] hover:bg-[#3F3F3F] text-white font-medium">
              Connect Klaviyo
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-20 pb-32 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <div className="container mx-auto px-4 relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            
            {/* Hero Copy */}
            <div className="space-y-8">
              <Badge variant="outline" className="bg-white/50 backdrop-blur border-slate-200 px-4 py-1.5 text-sm">
                <Sparkles className="w-3.5 h-3.5 mr-2 text-orange-500 fill-orange-500" />
                Powered by OpenAI & Klaviyo MCP
              </Badge>
              
              <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight text-slate-900 leading-[1.1]">
                Marketing Ops, <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-600 to-amber-500">
                  Autopilot.
                </span>
              </h1>
              
              <p className="text-xl text-slate-600 max-w-lg leading-relaxed">
                Turn natural language into structured Klaviyo actions. Build audiences, draft campaigns, and analyze performance—safely.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href="http://localhost:8000/auth/login" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full h-12 px-8 bg-black hover:bg-slate-800 text-white text-base">
                    Start Authenticated Session
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
                <Button variant="outline" size="lg" className="h-12 px-8 bg-white border-slate-300 hover:bg-slate-50">
                  View Demo Data
                </Button>
              </div>

              <div className="flex items-center gap-4 text-sm text-slate-500 pt-4">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-green-600" />
                  <span>Human-in-the-loop</span>
                </div>
                <div className="w-1 h-1 bg-slate-300 rounded-full"></div>
                <div className="flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-blue-600" />
                  <span>MCP Server</span>
                </div>
              </div>
            </div>

            {/* Hero Visual - Chat Simulation */}
            <div className="relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-orange-500 to-amber-500 rounded-2xl blur opacity-20"></div>
              <Card className="relative border-slate-200 shadow-2xl bg-white/95 backdrop-blur">
                <CardHeader className="border-b bg-slate-50/50 p-4">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <div className="w-3 h-3 rounded-full bg-amber-400" />
                    <div className="w-3 h-3 rounded-full bg-green-400" />
                    <span className="ml-2 text-xs font-mono text-slate-400">nexus_agent — v1.0.0</span>
                  </div>
                </CardHeader>
                <CardContent className="p-6 space-y-6 font-mono text-sm">
                  
                  {/* User Message */}
                  <div className="flex gap-4">
                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                      <span className="font-bold text-xs">YO</span>
                    </div>
                    <div className="space-y-1">
                      <p className="font-semibold text-slate-900">User</p>
                      <div className="bg-slate-100 rounded-lg rounded-tl-none p-3 text-slate-700">
                        Create a Winback segment for customers who haven't purchased in 90 days but spent over $100 lifetime.
                      </div>
                    </div>
                  </div>

                  {/* Nexus Processing */}
                  <div className="flex gap-4">
                    <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center shrink-0">
                      <RocketIcon className="w-4 h-4 text-white" />
                    </div>
                    <div className="space-y-2 w-full">
                      <p className="font-semibold text-slate-900 flex items-center gap-2">
                        Nexus AI
                        <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded uppercase">Thinking</span>
                      </p>
                      
                      {/* Execution Trace Mock */}
                      <div className="bg-slate-900 rounded-lg p-3 text-xs text-green-400 font-mono border border-slate-800">
                        <div className="opacity-50 border-b border-slate-700 pb-2 mb-2">
                          <span className="text-slate-400"># Execution Trace</span>
                        </div>
                        <p>{`> Analyzed intent: "Create Segment"`}</p>
                        <p>{`> Conditions detected: LastOrder > 90d, Revenue > 100`}</p>
                        <p>{`> Calling tool: klaviyo_create_segment(...)`}</p>
                      </div>

                      <div className="bg-white border border-slate-200 rounded-lg rounded-tl-none p-4 shadow-sm">
                        <p className="text-slate-700 mb-3">
                          I've prepared the <strong>"High Value Winback"</strong> segment definition.
                        </p>
                        <div className="flex gap-2">
                          <Button size="sm" className="bg-black hover:bg-slate-800 text-xs h-8">
                            <CheckCircle2 className="w-3 h-3 mr-1.5" />
                            Approve & Create
                          </Button>
                          <Button size="sm" variant="ghost" className="text-xs h-8">
                            Edit Criteria
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight mb-4">Marketing Infrastructure as Code</h2>
            <p className="text-slate-500 text-lg">
              Nexus bridges the gap between marketing intuition and technical execution using the Model Context Protocol.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card className="border-none shadow-none bg-slate-50 hover:bg-slate-100 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center mb-4">
                  <Users className="w-6 h-6 text-orange-600" />
                </div>
                <CardTitle>Smart Audiences</CardTitle>
                <CardDescription>
                  Don't struggle with logic builders. Use preset "Recipes" to build complex VIP, Churn Risk, and Winback segments instantly.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-none shadow-none bg-slate-50 hover:bg-slate-100 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center mb-4">
                  <Code2 className="w-6 h-6 text-indigo-600" />
                </div>
                <CardTitle>Campaign Drafts</CardTitle>
                <CardDescription>
                  Generate campaign copy and HTML structures targeted to your specific segments. Nexus drafts it; you polish and send.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-none shadow-none bg-slate-50 hover:bg-slate-100 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center mb-4">
                  <ShieldCheck className="w-6 h-6 text-green-600" />
                </div>
                <CardTitle>Safe Execution</CardTitle>
                <CardDescription>
                  AI never acts alone. Every API call is presented for approval before execution, ensuring 100% brand safety.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Tech Stack / Footer */}
      <footer className="bg-slate-900 py-12 text-slate-400 text-sm">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <RocketIcon className="h-5 w-5 text-white" />
              <span className="font-bold text-white text-lg">Klaviyo Nexus</span>
            </div>
            
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4" />
                <span>OpenAI GPT-4o</span>
              </div>
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4" />
                <span>MCP Protocol</span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4" />
                <span>Next.js 14</span>
              </div>
            </div>

            <p>Ahmed Khan Klaviyo Winter {new Date().getFullYear()} Hackathon Project. Not affiliated with Klaviyo.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}