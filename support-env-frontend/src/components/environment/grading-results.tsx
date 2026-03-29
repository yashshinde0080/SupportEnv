"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Trophy, CheckCircle2, XCircle, Info } from "lucide-react";
import { GraderResponse } from "@/lib/types";
import { formatScore } from "@/lib/utils";

interface GradingResultsProps {
  result: GraderResponse;
}

const breakdownLabels: Record<string, string> = {
  classification: "Classification",
  response_quality: "Response Quality",
  escalation_decision: "Escalation Decision",
  resolution: "Resolution",
  efficiency: "Efficiency",
};

export function GradingResults({ result }: GradingResultsProps) {
  const scorePercent = result.score * 100;
  
  return (
    <Card className={result.passed ? "border-green-500" : "border-red-500"}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-yellow-500" />
            Grading Results
          </span>
          <Badge variant={result.passed ? "default" : "destructive"} className="gap-1">
            {result.passed ? (
              <CheckCircle2 className="h-3 w-3" />
            ) : (
              <XCircle className="h-3 w-3" />
            )}
            {result.passed ? "PASSED" : "FAILED"}
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Total Score */}
        <div className="text-center p-4 bg-muted rounded-lg">
          <p className="text-sm text-muted-foreground mb-2">Final Score</p>
          <p className={`text-4xl font-bold ${
            result.score >= 0.8 ? 'text-green-600' :
            result.score >= 0.6 ? 'text-yellow-600' :
            'text-red-600'
          }`}>
            {formatScore(result.score)}
          </p>
          <Progress 
            value={scorePercent} 
            className="h-2 mt-3"
          />
        </div>
        
        <Separator />
        
        {/* Breakdown */}
        <div className="space-y-3">
          <p className="text-sm font-medium">Score Breakdown</p>
          {Object.entries(result.breakdown).map(([key, value]) => (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span>{breakdownLabels[key] || key}</span>
                <span className={`font-medium ${
                  value >= 0.8 ? 'text-green-600' :
                  value >= 0.5 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {formatScore(value)}
                </span>
              </div>
              <Progress value={value * 100} className="h-1.5" />
            </div>
          ))}
        </div>
        
        {/* Feedback */}
        {result.feedback && (
          <>
            <Separator />
            <div className="flex gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
              <Info className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-blue-800 dark:text-blue-200">
                {result.feedback}
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}