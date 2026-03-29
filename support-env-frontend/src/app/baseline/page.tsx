"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import {
  BarChart3,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  TrendingUp,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import api from "@/lib/api";
import { BaselineResponse } from "@/lib/types";
import { formatScore, getDifficultyColor } from "@/lib/utils";

export default function BaselinePage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<BaselineResponse | null>(null);

  const runBaseline = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.runBaseline();
      setResults(response);
    } catch (err: any) {
      setError(err.message || "Failed to run baseline");
    } finally {
      setIsLoading(false);
    }
  };

  const chartData = results ? [
    {
      name: "Easy",
      score: results.baseline_results.easy.score,
      color: "#22c55e",
    },
    {
      name: "Medium",
      score: results.baseline_results.medium.score,
      color: "#eab308",
    },
    {
      name: "Hard",
      score: results.baseline_results.hard.score,
      color: "#ef4444",
    },
  ] : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Baseline Results</h1>
          <p className="text-muted-foreground">
            Run the rule-based baseline agent against all difficulty levels
          </p>
        </div>
        
        <Button onClick={runBaseline} disabled={isLoading} className="gap-2">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          Run Baseline
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {isLoading && (
        <Card className="py-12">
          <CardContent className="text-center">
            <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary mb-4" />
            <p className="text-lg font-medium">Running Baseline Agent...</p>
            <p className="text-muted-foreground">
              This may take up to 60 seconds
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {results && !isLoading && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Average Score */}
              <div className="text-center p-6 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">
                  Average Score
                </p>
                <p className="text-5xl font-bold text-primary">
                  {formatScore(results.summary.average_score)}
                </p>
              </div>
              
              {/* Individual Scores */}
              <div className="grid grid-cols-3 gap-4">
                {(["easy", "medium", "hard"] as const).map((difficulty) => {
                  const taskResult = results.baseline_results[difficulty];
                  return (
                    <div key={difficulty} className="text-center p-4 border rounded-lg">
                      <Badge className={getDifficultyColor(difficulty)}>
                        {difficulty.toUpperCase()}
                      </Badge>
                      <p className="text-2xl font-bold mt-2">
                        {formatScore(taskResult.score)}
                      </p>
                      <div className="flex items-center justify-center gap-1 mt-1">
                        {taskResult.passed ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-xs text-muted-foreground">
                          {taskResult.passed ? "Passed" : "Failed"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Chart Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Score Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                    <YAxis type="category" dataKey="name" width={80} />
                    <Tooltip
                      formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`, "Score"]}
                    />
                    <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Detailed Results */}
          {(["easy", "medium", "hard"] as const).map((difficulty) => {
            const taskResult = results.baseline_results[difficulty];
            return (
              <Card key={difficulty}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Badge className={getDifficultyColor(difficulty)}>
                        {difficulty.toUpperCase()}
                      </Badge>
                      Task Results
                    </span>
                    <Badge variant={taskResult.passed ? "default" : "destructive"}>
                      {taskResult.passed ? "PASSED" : "FAILED"}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Metrics */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <p className="text-xs text-muted-foreground">Score</p>
                      <p className="text-xl font-bold">{formatScore(taskResult.score)}</p>
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <p className="text-xs text-muted-foreground">Total Reward</p>
                      <p className="text-xl font-bold">{taskResult.total_reward.toFixed(2)}</p>
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <p className="text-xs text-muted-foreground">Steps</p>
                      <p className="text-xl font-bold">{taskResult.steps}</p>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  {/* Breakdown */}
                  <div className="space-y-3">
                    <p className="text-sm font-medium">Score Breakdown</p>
                    {Object.entries(taskResult.breakdown).map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="capitalize">{key.replace(/_/g, " ")}</span>
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
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* No Results State */}
      {!results && !isLoading && !error && (
        <Card className="py-12">
          <CardContent className="text-center">
            <div className="max-w-md mx-auto space-y-4">
              <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mx-auto">
                <BarChart3 className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-xl font-semibold">No Baseline Results</h3>
              <p className="text-muted-foreground">
                Click "Run Baseline" to execute the rule-based agent against all difficulty levels.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}