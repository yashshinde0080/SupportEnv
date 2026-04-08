# File Tree: SupportEnv

**Generated:** 4/7/2026, 9:43:14 PM
**Root Path:** `d:\SupportEnv`

```
├── 📁 .agents
│   ├── 📁 _shared
│   │   ├── 📝 clarification-protocol.md
│   │   ├── 📝 context-budget.md
│   │   ├── 📝 context-loading.md
│   │   ├── 📝 reasoning-templates.md
│   │   ├── 📝 serena-memory-protocol.md
│   │   ├── 📝 skill-routing.md
│   │   └── 📄 verify.sh
│   ├── 📁 backend-agent
│   │   ├── 📁 resources
│   │   │   ├── 📝 checklist.md
│   │   │   ├── 📝 error-playbook.md
│   │   │   ├── 📝 execution-protocol.md
│   │   │   └── 📝 tech-stack.md
│   │   └── 📝 SKILL.md
│   ├── 📁 code_review_enforcer
│   │   └── 📝 SKILL.md
│   ├── 📁 debug-agent
│   │   ├── 📁 resources
│   │   │   ├── 📝 checklist.md
│   │   │   ├── 📝 error-playbook.md
│   │   │   └── 📝 execution-protocol.md
│   │   └── 📝 SKILL.md
│   ├── 📁 dependency_manager
│   │   └── 📝 SKILL.md
│   ├── 📁 docs_updater
│   │   └── 📝 SKILL.md
│   ├── 📁 frontend-agent
│   │   └── 📁 resources
│   │       ├── 📝 SKILL.md
│   │       ├── 📝 checklist.md
│   │       ├── 📝 error-playbook.md
│   │       ├── 📝 execution-protocol.md
│   │       └── 📝 tech-stack.md
│   ├── 📁 git_manager
│   │   └── 📝 SKILL.md
│   ├── 📁 mobile-agent
│   │   ├── 📁 resources
│   │   │   ├── 📝 checklist.md
│   │   │   ├── 📝 error-playbook.md
│   │   │   ├── 📝 execution-protocol.md
│   │   │   └── 📝 tech-stack.md
│   │   └── 📝 SKILL.md
│   ├── 📁 observability_configurator
│   │   └── 📝 SKILL.md
│   ├── 📁 orchestrator
│   │   └── 📝 SKILL.md
│   ├── 📁 pm-agent
│   │   ├── 📁 resources
│   │   │   ├── 📝 error-playbook.md
│   │   │   └── 📝 execution-protocol.md
│   │   └── 📝 SKILL.md
│   ├── 📁 qa-agent
│   │   ├── 📁 resources
│   │   │   ├── 📝 checklist.md
│   │   │   ├── 📝 error-playbook.md
│   │   │   └── 📝 execution-protocol.md
│   │   └── 📝 SKILL.md
│   ├── 📁 security_hardening
│   │   └── 📝 SKILL.md
│   ├── 📁 skill_creator
│   │   └── 📝 SKILL.md
│   └── 📁 workflow-guide
│       └── 📝 SKILL.md
├── 📁 .claude
│   ├── 📁 skills
│   │   ├── 📝 debug-issue.md
│   │   ├── 📝 explore-codebase.md
│   │   ├── 📝 refactor-safely.md
│   │   └── 📝 review-changes.md
│   ├── ⚙️ settings.json
│   └── ⚙️ settings.local.json
├── 📁 .code-review-graph
│   ├── ⚙️ .gitignore
│   ├── 📄 graph.db
│   ├── 📄 graph.db-shm
│   └── 📄 graph.db-wal
├── 📁 .github
│   ├── 📁 instructions
│   │   └── 📝 kluster-code-verify.instructions.md
│   └── 📁 workflows
│       └── ⚙️ test.yml
├── 📁 baseline
│   ├── 🐍 __init__.py
│   ├── 🐍 policy.py
│   ├── ⚙️ results.json
│   ├── 🐍 run_baseline.py
│   └── ⚙️ test_results.json
├── 📁 documentation
│   ├── 📄 prd.txt
│   └── 📄 trd.txt
├── 📁 frontend
├── 📁 scripts
│   ├── 📁 linux
│   │   ├── 📄 deploy.sh
│   │   ├── 📄 start_local.sh
│   │   └── 📄 validate.sh
│   └── 📁 windows
│       ├── 📄 deploy.bat
│       ├── 📄 start_local.bat
│       └── 📄 validate.bat
├── 📁 server
│   ├── 🐍 __init__.py
│   ├── 🐍 app.py
│   ├── 🐍 environment.py
│   ├── 🐍 graders.py
│   ├── 🐍 reward.py
│   ├── 🐍 semantic_scorer.py
│   └── 🐍 ticket_generator.py
├── 📁 support-env-frontend
│   ├── 📁 public
│   │   ├── 🖼️ file.svg
│   │   ├── 🖼️ globe.svg
│   │   ├── 🖼️ next.svg
│   │   ├── 🖼️ vercel.svg
│   │   └── 🖼️ window.svg
│   ├── 📁 src
│   │   ├── 📁 app
│   │   │   ├── 📁 api
│   │   │   │   └── 📁 proxy
│   │   │   │       └── 📄 route.ts
│   │   │   ├── 📁 baseline
│   │   │   │   └── 📄 page.tsx
│   │   │   ├── 📁 playground
│   │   │   │   └── 📄 page.tsx
│   │   │   ├── 📁 tasks
│   │   │   │   └── 📄 page.tsx
│   │   │   ├── 📄 favicon.ico
│   │   │   ├── 🎨 globals.css
│   │   │   ├── 📄 layout.tsx
│   │   │   └── 📄 page.tsx
│   │   └── 📁 components
│   │       ├── 📁 environment
│   │       │   ├── 📄 action-panel.tsx
│   │       │   ├── 📄 grading-results.tsx
│   │       │   ├── 📄 history-panel.tsx
│   │       │   ├── 📄 reward-display.tsx
│   │       │   └── 📄 ticket-display.tsx
│   │       ├── 📁 layout
│   │       │   └── 📄 header.tsx
│   │       ├── 📁 shared
│   │       │   └── 📄 loading-spinner.tsx
│   │       └── 📁 ui
│   │           ├── 📄 alert.tsx
│   │           ├── 📄 avatar.tsx
│   │           ├── 📄 badge.tsx
│   │           ├── 📄 button.tsx
│   │           ├── 📄 card.tsx
│   │           ├── 📄 dialog.tsx
│   │           ├── 📄 dropdown-menu.tsx
│   │           ├── 📄 input.tsx
│   │           ├── 📄 progress.tsx
│   │           ├── 📄 scroll-area.tsx
│   │           ├── 📄 select.tsx
│   │           ├── 📄 separator.tsx
│   │           ├── 📄 sheet.tsx
│   │           ├── 📄 skeleton.tsx
│   │           ├── 📄 sonner.tsx
│   │           ├── 📄 tabs.tsx
│   │           ├── 📄 textarea.tsx
│   │           └── 📄 tooltip.tsx
│   ├── ⚙️ .gitignore
│   ├── 📝 README.md
│   ├── ⚙️ components.json
│   ├── 📄 eslint.config.mjs
│   ├── 📄 next-env.d.ts
│   ├── 📄 next.config.ts
│   ├── ⚙️ package-lock.json
│   ├── ⚙️ package.json
│   ├── 📄 postcss.config.mjs
│   ├── 📄 tailwind.config.ts
│   └── ⚙️ tsconfig.json
├── 📁 tests
│   ├── 🐍 __init__.py
│   ├── 🐍 test_api.py
│   ├── 🐍 test_baseline.py
│   ├── 🐍 test_concurrency.py
│   ├── 🐍 test_environment.py
│   ├── 🐍 test_graders.py
│   └── 🐍 test_reward.py
├── ⚙️ .cursorrules
├── ⚙️ .dockerignore
├── ⚙️ .env.example
├── ⚙️ .gitignore
├── ⚙️ .mcp.json
├── ⚙️ .opencode.json
├── ⚙️ .windsurfrules
├── 📝 AGENTS.md
├── 📝 CLAUDE.md
├── 🐳 Dockerfile
├── 📝 GEMINI.md
├── 📄 LICENSE
├── 📝 PRD.md
├── 📝 README.md
├── 🐍 check.py
├── 🐍 client.py
├── 🐍 config.py
├── 📄 docs.txt
├── 🐍 fix_ui.py
├── 🐍 gradio_ui.py
├── 📝 improve.md
├── 🐍 inference.py
├── 📄 inference_output.txt
├── 📄 install.cmd
├── 🐍 interface.py
├── 🐍 main.py
├── 🐍 models.py
├── 📝 new_review.md
├── ⚙️ openenv.yaml
├── ⚙️ package-lock.json
├── 📄 pre-submission.ps1
├── 📄 pre-submission.sh
├── ⚙️ pyproject.toml
├── 📄 pytest_out.txt
├── 📄 requirements.txt
├── 📝 review_new_updated.md
├── 🐍 rewrite_gradio.py
├── 📄 routes.txt
├── 📝 setup.md
├── ⚙️ space.yaml
├── 🐍 test_gradio.py
├── 📄 uv.lock
└── 📄 validate-submission.sh
```

---
*Generated by FileTree Pro Extension*