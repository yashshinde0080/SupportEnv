"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { MessageSquare, User, Bot } from "lucide-react";
import { InteractionMessage, StepHistoryItem } from "@/lib/types";
import { getActionColor, timeAgo } from "@/lib/utils";

interface HistoryPanelProps {
  history: InteractionMessage[];
  stepHistory: StepHistoryItem[];
}

export function HistoryPanel({ history, stepHistory }: HistoryPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          History
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          {stepHistory.length === 0 && history.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              No actions taken yet
            </p>
          ) : (
            <div className="space-y-4">
              {/* Step History */}
              {stepHistory.map((step, idx) => (
                <div key={idx} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        Step {step.step}
                      </Badge>
                      <Badge className={getActionColor(step.action_type)}>
                        {step.action_type}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {timeAgo(step.timestamp)}
                    </span>
                  </div>
                  
                  <div className="pl-4 border-l-2 border-muted">
                    <p className="text-sm">{step.content}</p>
                    <p className={`text-xs mt-1 ${
                      step.reward > 0 ? 'text-green-600' : 
                      step.reward < 0 ? 'text-red-600' : 
                      'text-muted-foreground'
                    }`}>
                      Reward: {step.reward >= 0 ? '+' : ''}{step.reward.toFixed(4)}
                    </p>
                  </div>
                </div>
              ))}
              
              {stepHistory.length > 0 && history.length > 0 && (
                <Separator />
              )}
              
              {/* Interaction History */}
              {history.map((msg, idx) => (
                <div key={idx} className="flex gap-3">
                  <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                    msg.role === 'agent' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted'
                  }`}>
                    {msg.role === 'agent' ? (
                      <Bot className="h-4 w-4" />
                    ) : (
                      <User className="h-4 w-4" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium capitalize mb-1">
                      {msg.role}
                    </p>
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}