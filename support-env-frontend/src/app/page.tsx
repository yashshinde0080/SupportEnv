import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Headphones,
  PlayCircle,
  BarChart3,
  ListChecks,
  Zap,
  Target,
  Brain,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

const features = [
  {
    icon: Target,
    title: "3 Difficulty Levels",
    description: "Easy, Medium, and Hard tasks with progressive complexity",
  },
  {
    icon: Zap,
    title: "Dense Rewards",
    description: "Step-by-step feedback for effective learning",
  },
  {
    icon: Brain,
    title: "Real-World Tasks",
    description: "Actual customer support scenarios, not toys",
  },
  {
    icon: BarChart3,
    title: "Deterministic Grading",
    description: "Reproducible scores from 0.0 to 1.0",
  },
];

const actions = [
  {
    type: "classify",
    description: "Categorize ticket (billing, technical, account, general)",
    color: "bg-blue-500",
  },
  {
    type: "respond",
    description: "Send response to customer",
    color: "bg-purple-500",
  },
  {
    type: "escalate",
    description: "Escalate to human agent",
    color: "bg-red-500",
  },
  {
    type: "request_info",
    description: "Ask for more information",
    color: "bg-orange-500",
  },
  {
    type: "resolve",
    description: "Mark ticket as resolved",
    color: "bg-green-500",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center space-y-6 py-12">
        <Badge variant="secondary" className="text-sm">
          OpenEnv Compatible
        </Badge>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
          Customer Support
          <br />
          <span className="text-primary">RL Environment</span>
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Train AI agents to handle real customer support workflows.
          Classification, response generation, and escalation decisions.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link href="/playground">
            <Button size="lg" className="gap-2">
              <PlayCircle className="h-5 w-5" />
              Try Playground
            </Button>
          </Link>
          <Link href="/baseline">
            <Button size="lg" variant="outline" className="gap-2">
              <BarChart3 className="h-5 w-5" />
              View Baseline
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <Card key={feature.title}>
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                  <Icon className="h-6 w-6 text-primary" />
                </div>
                <CardTitle className="text-lg">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{feature.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      {/* Action Space */}
      <section>
        <Card>
          <CardHeader>
            <CardTitle>Action Space</CardTitle>
            <CardDescription>
              Available actions an agent can take in the environment
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {actions.map((action) => (
                <div
                  key={action.type}
                  className="flex items-start gap-3 p-4 rounded-lg border"
                >
                  <div className={`h-3 w-3 rounded-full mt-1.5 ${action.color}`} />
                  <div>
                    <p className="font-mono font-medium">{action.type}</p>
                    <p className="text-sm text-muted-foreground">
                      {action.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Quick Start */}
      <section>
        <Card>
          <CardHeader>
            <CardTitle>Quick Start</CardTitle>
            <CardDescription>
              Get started with SupportEnv in minutes
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted rounded-lg p-4 font-mono text-sm overflow-x-auto">
              <pre>{`# Install client
pip install git+https://huggingface.co/spaces/username/support-env

# Connect to environment
from support_env.client import SupportEnv
from support_env.models import SupportAction

env = SupportEnv(base_url="https://username-support-env.hf.space")

with env.sync() as client:
    result = client.reset(difficulty="medium")
    print(f"Ticket: {result.observation.ticket_text}")
    
    action = SupportAction(action_type="classify", content="billing")
    result = client.step(action)
    print(f"Reward: {result.reward}")`}</pre>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* CTA */}
      <section className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Ready to train your agent?</h2>
        <Link href="/playground">
          <Button size="lg" className="gap-2">
            Open Playground
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </section>
    </div>
  );
}