"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  User, 
  Mail, 
  Tag, 
  Clock, 
  Gauge,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Observation } from "@/lib/types";
import { formatSentiment, getDifficultyColor } from "@/lib/utils";

interface TicketDisplayProps {
  observation: Observation;
}

export function TicketDisplay({ observation }: TicketDisplayProps) {
  const sentiment = formatSentiment(observation.customer_sentiment);
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              {observation.ticket_subject}
            </CardTitle>
            <CardDescription className="flex items-center gap-4 mt-2">
              <span className="flex items-center gap-1">
                <User className="h-4 w-4" />
                {observation.customer_name}
              </span>
              <span className="flex items-center gap-1">
                <Tag className="h-4 w-4" />
                {observation.ticket_id}
              </span>
            </CardDescription>
          </div>
          
          <div className="flex flex-col items-end gap-2">
            <Badge className={getDifficultyColor(observation.task_difficulty)}>
              {observation.task_difficulty.toUpperCase()}
            </Badge>
            <div className="flex items-center gap-1 text-sm">
              <Clock className="h-4 w-4" />
              {observation.steps_remaining} / {observation.max_steps} steps
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Ticket Body */}
        <div className="bg-muted rounded-lg p-4">
          <p className="whitespace-pre-wrap">{observation.ticket_text}</p>
        </div>
        
        <Separator />
        
        {/* Status Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Sentiment */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Customer Sentiment</p>
            <div className="flex items-center gap-2">
              <span className="text-2xl">{sentiment.emoji}</span>
              <span className={`font-medium ${sentiment.color}`}>
                {sentiment.label}
              </span>
            </div>
          </div>
          
          {/* Classification */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Classification</p>
            <div className="flex items-center gap-2">
              {observation.is_classified ? (
                <>
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                  <span className="font-medium capitalize">
                    {observation.current_classification}
                  </span>
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                  <span className="text-muted-foreground">Not classified</span>
                </>
              )}
            </div>
          </div>
          
          {/* Escalation */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Escalated</p>
            <div className="flex items-center gap-2">
              {observation.is_escalated ? (
                <>
                  <CheckCircle2 className="h-5 w-5 text-orange-500" />
                  <span className="font-medium">Yes</span>
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                  <span className="text-muted-foreground">No</span>
                </>
              )}
            </div>
          </div>
          
          {/* Progress */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Progress</p>
            <div className="flex items-center gap-2">
              <Gauge className="h-5 w-5" />
              <span className="font-medium">
                {Math.round(((observation.max_steps - observation.steps_remaining) / observation.max_steps) * 100)}%
              </span>
            </div>
          </div>
        </div>
        
        {/* Message */}
        {observation.message && (
          <>
            <Separator />
            <div className="bg-blue-50 dark:bg-blue-950 text-blue-800 dark:text-blue-200 rounded-lg p-3 text-sm">
              <strong>System:</strong> {observation.message}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}