"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  PlayCircle,
  RotateCcw,
  Trophy,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useEnvironment } from "@/lib/hooks/use-environment";
import { DIFFICULTY_LEVELS, DifficultyLevel } from "@/lib/types";
import { getDifficultyColor } from "@/lib/utils";
import { TicketDisplay } from "@/components/environment/ticket-display";
import { ActionPanel } from "@/components/environment/action-panel";
import { HistoryPanel } from "@/components/environment/history-panel";
import { RewardDisplay } from "@/components/environment/reward-display";
import { GradingResults } from "@/components/environment/grading-results";

export default function PlaygroundPage() {
  const [selectedDifficulty, setSelectedDifficulty] = useState<DifficultyLevel>("easy");
  const {
    sessionId,
    observation,
    isLoading,
    error,
    totalReward,
    stepHistory,
    gradeResult,
    isDone,
    reset,
    step,
    grade,
    clearError,
  } = useEnvironment();

  const handleReset = () => {
    clearError();
    reset(selectedDifficulty);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <PlayCircle className="h-8 w-8" />
            Playground
          </h1>
          <p className="text-muted-foreground">
            Interact with the SupportEnv environment in real-time
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Difficulty Selector */}
          <Select
            value={selectedDifficulty}
            onValueChange={(v) => setSelectedDifficulty(v as DifficultyLevel)}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Difficulty" />
            </SelectTrigger>
            <SelectContent>
              {DIFFICULTY_LEVELS.map((level) => (
                <SelectItem key={level} value={level}>
                  <Badge className={getDifficultyColor(level)}>
                    {level.toUpperCase()}
                  </Badge>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Reset Button */}
          <Button onClick={handleReset} disabled={isLoading} className="gap-2">
            {isLoading && !observation ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4" />
            )}
            {observation ? "Reset" : "Start"}
          </Button>

          {/* Grade Button */}
          {isDone && !gradeResult && (
            <Button onClick={grade} variant="secondary" disabled={isLoading} className="gap-2">
              <Trophy className="h-4 w-4" />
              Grade
            </Button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Session Info */}
      {sessionId && (
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>
            Session: <code className="bg-muted px-2 py-0.5 rounded">{sessionId.slice(0, 8)}...</code>
          </span>
          {isDone && (
            <Badge variant="outline" className="text-amber-600 border-amber-600">
              Episode Complete
            </Badge>
          )}
        </div>
      )}

      {/* Main Content */}
      {observation ? (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Ticket & Action */}
          <div className="lg:col-span-2 space-y-6">
            <TicketDisplay observation={observation} />
            <ActionPanel
              observation={observation}
              onAction={step}
              isLoading={isLoading}
              isDone={isDone}
            />
          </div>

          {/* Right Column - Rewards & History */}
          <div className="space-y-6">
            <RewardDisplay
              totalReward={totalReward}
              stepHistory={stepHistory}
              stepsRemaining={observation.steps_remaining}
              maxSteps={observation.max_steps}
            />
            <HistoryPanel
              history={observation.interaction_history}
              stepHistory={stepHistory}
            />
          </div>
        </div>
      ) : (
        /* No Session State */
        <Card className="py-12">
          <CardContent className="text-center">
            <div className="max-w-md mx-auto space-y-4">
              <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mx-auto">
                <PlayCircle className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-xl font-semibold">Ready to Play</h3>
              <p className="text-muted-foreground">
                Select a difficulty level and click &quot;Start&quot; to begin interacting with a 
                customer support ticket. Take actions like classifying, responding, and resolving.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Grading Results */}
      {gradeResult && <GradingResults result={gradeResult} />}
    </div>
  );
}
