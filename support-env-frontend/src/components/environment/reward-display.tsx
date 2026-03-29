"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, Zap } from "lucide-react";
import { StepHistoryItem } from "@/lib/types";
import { formatReward } from "@/lib/utils";

interface RewardDisplayProps {
  totalReward: number;
  stepHistory: StepHistoryItem[];
  stepsRemaining: number;
  maxSteps: number;
}

export function RewardDisplay({ 
  totalReward, 
  stepHistory, 
  stepsRemaining, 
  maxSteps 
}: RewardDisplayProps) {
  const { display: rewardDisplay, color: rewardColor } = formatReward(totalReward);
  const lastReward = stepHistory.length > 0 ? stepHistory[stepHistory.length - 1].reward : 0;
  const { display: lastDisplay, color: lastColor } = formatReward(lastReward);
  
  const progress = ((maxSteps - stepsRemaining) / maxSteps) * 100;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Zap className="h-5 w-5 text-yellow-500" />
          Rewards
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Total Reward */}
        <div className="text-center p-4 bg-muted rounded-lg">
          <p className="text-sm text-muted-foreground mb-1">Total Reward</p>
          <p className={`text-3xl font-bold ${rewardColor}`}>
            {rewardDisplay}
          </p>
        </div>
        
        {/* Last Step Reward */}
        {stepHistory.length > 0 && (
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div className="flex items-center gap-2">
              {lastReward > 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
              ) : lastReward < 0 ? (
                <TrendingDown className="h-4 w-4 text-red-500" />
              ) : (
                <Minus className="h-4 w-4 text-gray-500" />
              )}
              <span className="text-sm">Last Step</span>
            </div>
            <span className={`font-mono font-medium ${lastColor}`}>
              {lastDisplay}
            </span>
          </div>
        )}
        
        {/* Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Episode Progress</span>
            <span className="font-medium">
              {maxSteps - stepsRemaining} / {maxSteps} steps
            </span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
        
        {/* Recent Rewards */}
        {stepHistory.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Recent Rewards</p>
            <div className="flex flex-wrap gap-1">
              {stepHistory.slice(-5).map((item, idx) => {
                const { color } = formatReward(item.reward);
                return (
                  <Badge 
                    key={idx} 
                    variant="outline"
                    className={`text-xs ${color}`}
                  >
                    Step {item.step}: {item.reward >= 0 ? '+' : ''}{item.reward.toFixed(2)}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}