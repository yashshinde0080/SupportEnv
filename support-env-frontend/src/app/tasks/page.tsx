"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ListChecks,
  AlertCircle,
  Clock,
  Tag,
  MessageSquare,
  AlertTriangle,
  HelpCircle,
  CheckCircle,
  Code,
} from "lucide-react";
import api from "@/lib/api";
import { Task } from "@/lib/types";
import { getDifficultyColor } from "@/lib/utils";

const actionIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  classify: Tag,
  respond: MessageSquare,
  escalate: AlertTriangle,
  request_info: HelpCircle,
  resolve: CheckCircle,
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await api.getTasks();
        setTasks(response.tasks);
      } catch (err: any) {
        setError(err.message || "Failed to fetch tasks");
      } finally {
        setIsLoading(false);
      }
    };

    fetchTasks();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Tasks</h1>
          <p className="text-muted-foreground">Loading available tasks...</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-48 mt-2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Tasks</h1>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <ListChecks className="h-8 w-8" />
          Available Tasks
        </h1>
        <p className="text-muted-foreground">
          {tasks.length} tasks across different difficulty levels
        </p>
      </div>

      {/* Task Cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tasks.map((task) => (
          <Card key={task.task_id} className="flex flex-col">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg">{task.name}</CardTitle>
                  <CardDescription className="font-mono text-xs mt-1">
                    {task.task_id}
                  </CardDescription>
                </div>
                <Badge className={getDifficultyColor(task.difficulty)}>
                  {task.difficulty.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            
            <CardContent className="flex-1 space-y-4">
              {/* Description */}
              <p className="text-sm text-muted-foreground">
                {task.description}
              </p>
              
              <Separator />
              
              {/* Max Steps */}
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>Max Steps: <strong>{task.max_steps}</strong></span>
              </div>
              
              {/* Action Schema */}
              <div className="space-y-2">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Code className="h-4 w-4" />
                  Action Schema
                </p>
                <div className="bg-muted rounded-lg p-3 text-xs font-mono">
                  <ScrollArea className="h-[120px]">
                    <pre>{JSON.stringify(task.action_schema, null, 2)}</pre>
                  </ScrollArea>
                </div>
              </div>
              
              {/* Available Actions */}
              <div className="space-y-2">
                <p className="text-sm font-medium">Available Actions</p>
                <div className="flex flex-wrap gap-2">
                  {task.action_schema.action_type.enum.map((action) => {
                    const Icon = actionIcons[action] || Tag;
                    return (
                      <Badge key={action} variant="outline" className="gap-1">
                        <Icon className="h-3 w-3" />
                        {action}
                      </Badge>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Action Types Reference */}
      <Card>
        <CardHeader>
          <CardTitle>Action Types Reference</CardTitle>
          <CardDescription>
            Detailed description of each action type available in the environment
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              {
                type: "classify",
                icon: Tag,
                description: "Categorize the ticket into billing, technical, account, or general",
                color: "text-blue-500",
              },
              {
                type: "respond",
                icon: MessageSquare,
                description: "Send a response message to the customer",
                color: "text-purple-500",
              },
              {
                type: "escalate",
                icon: AlertTriangle,
                description: "Escalate the ticket to a human agent with a reason",
                color: "text-red-500",
              },
              {
                type: "request_info",
                icon: HelpCircle,
                description: "Ask the customer for additional information",
                color: "text-orange-500",
              },
              {
                type: "resolve",
                icon: CheckCircle,
                description: "Mark the ticket as resolved with a summary",
                color: "text-green-500",
              },
            ].map((action) => {
              const Icon = action.icon;
              return (
                <div key={action.type} className="flex items-start gap-3 p-4 border rounded-lg">
                  <Icon className={`h-5 w-5 ${action.color} flex-shrink-0 mt-0.5`} />
                  <div>
                    <p className="font-mono font-medium">{action.type}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {action.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}