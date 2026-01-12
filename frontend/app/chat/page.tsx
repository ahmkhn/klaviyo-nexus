'use client';
import React, { useState, useRef, useEffect } from 'react';
import { 
  RocketIcon, 
  Send, 
  Terminal, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  MoreVertical,
  LogOut,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

  // Types for our chat messages
type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  // The "Trace" is the internal monologue/tool calls of the agent
  trace?: string[];
  // If the agent needs user confirmation for an action
  actionRequired?: {
    type: 'approval';
    label: string;
    params?: any;
    onApprove: () => void;
    onDeny: () => void;
  };
  timestamp: Date;
};

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [resolvedActions, setResolvedActions] = useState<Set<string>>(new Set());
  const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

  // Initial State: The welcome message
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Nexus Agent v1.0 initialized. I'm connected to your Klaviyo account via MCP. \n\nI can help you analyze performance, build segments, or draft campaigns. What's the plan?",
      timestamp: new Date(),
    }
  ]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isThinking]);

  // Mock function to simulate AI response 
  const handleSendFake = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    // SIMULATION: Fake delay to show the "Thinking" state
    setTimeout(() => {
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I've analyzed your request. I found 3,420 profiles matching that criteria.",
        // This simulates the "Terminal" view 
        trace: [
            `> Intent Detected: Create_Segment`,
            `> Extraction: "No purchase 90d" -> LastOrderDate < NOW-90d`,
            `> Extraction: "LTV > $100" -> HistoricCLV > 100`,
            `> Tool Call: klaviyo_create_segment(name="High Value Lapsed")`
        ],
        actionRequired: {
          type: 'approval',
          label: 'Create "High Value Lapsed" Segment',
          onApprove: () => alert("Action executed via Klaviyo API!"),
          onDeny: () => alert("Action cancelled.")
        },
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, aiMsg]);
      setIsThinking(false);
    }, 2000);
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    // show user's msg instantly
    const userMsg: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: input,
        timestamp: new Date()
    }

    setMessages(prev=>[...prev, userMsg]);
    setInput('')
    setIsThinking(true);

    // attempt to call the backend agent
    // use cred "include" to send the session cookie
    try{
        const res = await fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include', 
            body: JSON.stringify({ 
              message: userMsg.content,
              history: messages.map(m => ({ role: m.role, content: m.content })) 
            }),
        });
        
        if(!res.ok) {
            throw new Error(`Server error: ${res.status}`)
        }
        
        const data = await res.json();

        const msgId = (Date.now() + 1).toString();

        // if we reach this part, we have the data, so let's
        // display the ai's message.
        const aiMsg: Message = {
            id: (Date.now()+1).toString(),
            role: 'assistant',
            content: data.content, // response from ai model
            trace: data.trace || [], // tool's execution logs
            timestamp: new Date(),
            actionRequired: data.action_required ? {
                type: 'approval',
                label: data.action_required.label,
                params: data.action_required.params,
                // When Approved: Call the EXECUTE tool
                onApprove: () => {
                    setResolvedActions(prev => new Set(prev).add(msgId));
                    handleExecute(data.action_required.approval_id, data.action_required.params);
                }, 
                // When Denied: Just show a message
                onDeny: () => {
                    setResolvedActions(prev => new Set(prev).add(msgId));
                    setMessages(prev => [...prev, {
                        id: Date.now().toString(), 
                        role: 'assistant', 
                        content: "Action cancelled.", 
                        timestamp: new Date()
                    }]);
                }
              } : undefined
            
        }
        setMessages(prev => [...prev, aiMsg])
    } catch(error) {
        console.error(error);
        const errorMsg: Message = {
            id: Date.now().toString(),
            role: 'assistant',
            content: "⚠️ Connection Error: I couldn't reach the Nexus Brain. Is Docker running?",
            timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMsg]);
    } finally {
        setIsThinking(false);
    }
  };
  const handleExecute = async (approvalId : string, params?: any) => {
    setIsThinking(true);
    try {
        // We manually inject the execute call or just ask the AI to do it
        // Ideally, we just hit the chat endpoint again with a specific system prompt or tool output.
        // HACKATHON SHORTCUT: Just tell the AI what to do.
        // Better approach: Since we have the ID, we can just trigger the tool via chat
        // But for simplicity, let's just simulate the user saying "Execute approval ID X"
        // and trust the agent loop to handle it.
        // OR better: Create a new fetch to a dedicated execution endpoint.
        // LET'S STICK TO CHAT for simplicity:
        
        let msg = `User approved action ${approvalId}. Please call execute_action now.`;
        if (params && params.list_name) {
             msg += ` Fallback Params: list_name="${params.list_name}"`;
        }

        const res = await fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ 
                message: msg,
                history: messages.map(m => ({ role: m.role, content: m.content })) 
            }),
        });
        
        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }

        const data = await res.json();
        // ... Handle response same as handleSend ...
        const aiMsg: Message = {
            id: Date.now().toString(),
            role: 'assistant',
            content: data.content,
            trace: data.trace,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMsg]);

    } catch (e) {
        console.error(e);
        const errorMsg: Message = {
            id: Date.now().toString(),
            role: 'assistant',
            content: "⚠️ Execution Failed: The server encountered an error while processing the approval.",
            timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMsg]);
    } finally {
        setIsThinking(false);
    }
  };
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 md:p-8 font-sans">
      
      {/* Main Chat Window - styled like a floating OS window */}
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-200 flex flex-col h-[85vh]">
        
        {/* Window Header */}
        <header className="bg-slate-50/80 backdrop-blur border-b p-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            {/* Mac-style traffic lights */}
            <div className="flex gap-1.5 mr-4">
              <div className="w-3 h-3 rounded-full bg-red-400 hover:bg-red-500 transition-colors" />
              <div className="w-3 h-3 rounded-full bg-amber-400 hover:bg-amber-500 transition-colors" />
              <div className="w-3 h-3 rounded-full bg-green-400 hover:bg-green-500 transition-colors" />
            </div>
            
            <div className="flex items-center gap-2 px-3 py-1 bg-white rounded-md border border-slate-200 shadow-sm">
              <div className="bg-black p-1 rounded-sm">
                <RocketIcon className="w-3 h-3 text-white" />
              </div>
              <span className="text-sm font-semibold text-slate-700">nexus_agent — v1.0.0</span>
            </div>
            
            <Badge variant="outline" className="text-green-600 bg-green-50 border-green-200 gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-600 animate-pulse" />
              Connected
            </Badge>
          </div>

          <Button variant="ghost" size="icon" className="text-slate-400 hover:text-slate-900">
            <LogOut className="w-4 h-4" />
          </Button>
        </header>

        {/* Chat Area */}
        <div className="flex-1 min-h-0 bg-[#FAFAFA]" >
            <ScrollArea className="h-full p-6">
            <div className="space-y-8 max-w-3xl mx-auto pb-4">
                
                {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm
                    ${msg.role === 'assistant' ? 'bg-black text-white' : 'bg-white text-slate-700 border'}`}>
                    {msg.role === 'assistant' ? <RocketIcon className="w-4 h-4" /> : <span className="text-xs font-bold">YO</span>}
                    </div>

                    {/* Message Content */}
                    <div className={`space-y-2 max-w-[85%] ${msg.role === 'user' ? 'items-end flex flex-col' : ''}`}>
                    
                    {/* Name Label */}
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span className="font-medium text-slate-900">{msg.role === 'assistant' ? 'Nexus AI' : 'You'}</span>
                        <span>
                        {mounted
                            ? msg.timestamp.toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                            })
                            : null}
                        </span>
                    </div>

                    {/* Execution Trace (Only for Assistant) */}
                    {msg.trace && (
                        <div className="w-full bg-slate-900 rounded-lg p-4 font-mono text-xs border border-slate-800 shadow-lg my-2">
                        <div className="flex items-center gap-2 text-slate-500 mb-3 border-b border-slate-800 pb-2">
                            <Terminal className="w-3 h-3" />
                            <span>Execution Trace</span>
                        </div>
                        <div className="space-y-1.5">
                            {msg.trace.map((line, i) => (
                            <p key={i} className="text-green-400/90 break-all pl-2 border-l-2 border-slate-700">
                                {line}
                            </p>
                            ))}
                        </div>
                        </div>
                    )}

                    {/* Main Bubble */}
                    <div className={`p-4 rounded-xl shadow-sm text-sm leading-relaxed
                        ${msg.role === 'user' 
                        ? 'bg-white border text-slate-700 rounded-tr-none' 
                        : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                        }`}>
                        {msg.content}
                    </div>

                    {/* Action Card (If Approval Needed) */}
                    {msg.actionRequired && (
                        <Card className="w-full mt-2 border-l-4 border-l-amber-500 bg-amber-50/50">
                        <div className="p-4 flex items-center justify-between gap-4">
                            <div className="space-y-1">
                            <p className="font-semibold text-sm text-amber-900">Approval Required</p>
                            <p className="text-xs text-amber-700/80">{msg.actionRequired.label}</p>
                            </div>
                            {!resolvedActions.has(msg.id) ? (
                            <div className="flex gap-2">
                                <Button 
                                size="sm" 
                                variant="outline"
                                className="text-slate-600 hover:text-red-600 hover:bg-red-50 border-slate-200"
                                onClick={msg.actionRequired.onDeny}
                                >
                                <XCircle className="w-4 h-4" />
                                </Button>
                                <Button 
                                size="sm" 
                                className="bg-black hover:bg-slate-800 text-white"
                                onClick={msg.actionRequired.onApprove}
                                >
                                <CheckCircle2 className="w-3 h-3 mr-2" />
                                Approve
                                </Button>
                            </div>
                            ) : (
                                <Badge variant="secondary" className="bg-slate-100 text-slate-500 border-none">
                                    Completed
                                </Badge>
                            )}
                            
                        </div>
                        </Card>
                    )}
                    </div>
                </div>
                ))}

                {/* Thinking Indicator */}
                {isThinking && (
                <div className="flex gap-4 animate-pulse">
                    <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center shrink-0">
                    <RocketIcon className="w-4 h-4 text-white" />
                    </div>
                    <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span className="font-medium text-slate-900">Nexus AI</span>
                    </div>
                    <div className="flex items-center gap-2 bg-slate-100 px-4 py-3 rounded-xl rounded-tl-none">
                        <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
                        <span className="text-sm text-slate-500 font-medium">Processing logic...</span>
                    </div>
                    </div>
                </div>
                )}
                
                <div ref={scrollRef} />
            </div>
            </ScrollArea>
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-slate-100 shrink-0">
          <div className="max-w-3xl mx-auto relative">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !isThinking && handleSend()}
              placeholder="Describe the audience or campaign you want to build..."
              className="pr-12 py-6 text-base bg-slate-50 border-slate-200 focus-visible:ring-slate-400 rounded-xl shadow-inner"
              disabled={isThinking}
            />
            <Button 
              size="icon"
              className="absolute right-2 top-2 h-8 w-8 bg-black hover:bg-slate-800 transition-all rounded-lg"
              onClick={handleSend}
              disabled={!input.trim() || isThinking}
            >
              <Send className="w-4 h-4 text-white" />
            </Button>
          </div>
          <p className="text-center text-[10px] text-slate-400 mt-3">
            Press Enter to send. Actions require manual approval.
          </p>
        </div>
      </div>
    </div>
  );
}