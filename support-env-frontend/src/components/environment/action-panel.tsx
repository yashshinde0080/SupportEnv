"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Send, 
  Loader2,
  Tag,
  MessageSquare,
  AlertTriangle,
  HelpCircle,
  CheckCircle,
} from "lucide-react";
import { Observation, ActionType, CATEGORY_OPTIONS } from "@/lib/types";
import { getActionColor } from "@/lib/utils";

interface ActionPanelProps {
  observation: Observation;
  onAction: (actionType: ActionType, content: string) => Promise<void>;
  isLoading: boolean;
  isDone: boolean;
}

const actionConfigs = {
  classify: {
    icon: Tag,
    label: "Classify",
    description: "Categorize the ticket type",
    placeholder: "Select category...",
    isSelect: true,
  },
  respond: {
    icon: MessageSquare,
    label: "Respond",
    description: "Send a response to the customer",
    placeholder: "Type your response to the customer...",
    isSelect: false,
  },
  escalate: {
    icon: AlertTriangle,
    label: "Escalate",
    description: "Escalate to a human agent",
    placeholder: "Provide reason for escalation...",
    isSelect: false,
  },
  request_info: {
    icon: HelpCircle,
    label: "Request Info",
    description: "Ask customer for more details",
    placeholder: "What information do you need?",
    isSelect: false,
  },
  resolve: {
    icon: CheckCircle,
    label: "Resolve",
    description: "Mark the ticket as resolved",
    placeholder: "Provide resolution summary...",
    isSelect: false,
  },
};

export function ActionPanel({ observation, onAction, isLoading, isDone }: ActionPanelProps) {
  const [selectedAction, setSelectedAction] = useState<ActionType>("classify");
  const [content, setContent] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");

  const handleSubmit = async () => {
    const actionContent = selectedAction === "classify" ? selectedCategory : content;
    
    if (!actionContent.trim()) return;
    
    await onAction(selectedAction, actionContent);
    setContent("");
    setSelectedCategory("");
  };

  const currentConfig = actionConfigs[selectedAction];
  const Icon = currentConfig.icon;

  const availableActions = observation.available_actions as ActionType[];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          Take Action
        </CardTitle>
        <CardDescription>
          Choose an action and provide the required content
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Action Type Tabs */}
        <Tabs value={selectedAction} onValueChange={(v) => setSelectedAction(v as ActionType)}>
          <TabsList className="grid grid-cols-5">
            {(Object.keys(actionConfigs) as ActionType[]).map((action) => {
              const config = actionConfigs[action];
              const ActionIcon = config.icon;
              const isAvailable = availableActions.includes(action);
              
              return (
                <TabsTrigger
                  key={action}
                  value={action}
                  disabled={!isAvailable || isDone}
                  className="gap-1.5 text-xs"
                >
                  <ActionIcon className="h-3.5 w-3.5" />
                  <span className="hidden md:inline">{config.label}</span>
                </TabsTrigger>
              );
            })}
          </TabsList>

          {(Object.keys(actionConfigs) as ActionType[]).map((action) => {
            const config = actionConfigs[action];
            
            return (
              <TabsContent key={action} value={action} className="mt-4 space-y-4">
                <div className="flex items-center gap-2">
                  <Badge className={getActionColor(action)}>
                    {config.label}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {config.description}
                  </span>
                </div>

                {config.isSelect ? (
                  <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                    <SelectTrigger>
                      <SelectValue placeholder={config.placeholder} />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORY_OPTIONS.map((category) => (
                        <SelectItem key={category} value={category}>
                          {category.charAt(0).toUpperCase() + category.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder={config.placeholder}
                    rows={4}
                    disabled={isDone}
                  />
                )}
              </TabsContent>
            );
          })}
        </Tabs>

        {/* Submit Button */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Available: {availableActions.join(", ")}
          </p>
          
          <Button
            onClick={handleSubmit}
            disabled={
              isLoading || 
              isDone || 
              (!content.trim() && !selectedCategory)
            }
            className="gap-2"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Execute Action
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}