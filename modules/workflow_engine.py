"""
Workflow Engine — Define and execute multi-step automated workflows with
conditions, loops, error handling, and inter-step data passing.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field
from core.logger import get_logger
import config

log = get_logger("workflow")

WORKFLOWS_DIR = config.DATA_DIR / "workflows"
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    action: str  # Tool name to call
    params: dict = field(default_factory=dict)
    condition: str = ""  # Python expression evaluated against context
    on_error: str = "stop"  # stop, skip, retry
    max_retries: int = 1
    delay_seconds: float = 0
    store_result_as: str = ""  # Variable name to store result
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "action": self.action,
            "params": self.params, "condition": self.condition,
            "on_error": self.on_error, "max_retries": self.max_retries,
            "delay_seconds": self.delay_seconds,
            "store_result_as": self.store_result_as,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: dict) -> 'WorkflowStep':
        return WorkflowStep(
            name=data.get("name", ""),
            action=data.get("action", ""),
            params=data.get("params", {}),
            condition=data.get("condition", ""),
            on_error=data.get("on_error", "stop"),
            max_retries=data.get("max_retries", 1),
            delay_seconds=data.get("delay_seconds", 0),
            store_result_as=data.get("store_result_as", ""),
            description=data.get("description", ""),
        )


@dataclass
class Workflow:
    """A complete workflow definition."""
    name: str
    description: str = ""
    steps: list = field(default_factory=list)
    created_at: str = ""
    last_run: str = ""
    run_count: int = 0
    enabled: bool = True
    tags: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at, "last_run": self.last_run,
            "run_count": self.run_count, "enabled": self.enabled,
            "tags": self.tags,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Workflow':
        wf = Workflow(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=[WorkflowStep.from_dict(s) for s in data.get("steps", [])],
            created_at=data.get("created_at", ""),
            last_run=data.get("last_run", ""),
            run_count=data.get("run_count", 0),
            enabled=data.get("enabled", True),
            tags=data.get("tags", ""),
        )
        return wf


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    workflow_name: str
    success: bool
    steps_completed: int
    steps_total: int
    duration_seconds: float
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def to_str(self) -> str:
        status = "✓ SUCCESS" if self.success else "✗ FAILED"
        lines = [
            f"Workflow '{self.workflow_name}': {status}",
            f"  Steps: {self.steps_completed}/{self.steps_total}",
            f"  Duration: {self.duration_seconds:.2f}s",
        ]
        if self.errors:
            lines.append("  Errors:")
            for err in self.errors:
                lines.append(f"    • {err}")
        if self.results:
            lines.append("  Step Results:")
            for r in self.results:
                status_icon = "✓" if r.get("success") else "✗"
                lines.append(f"    {status_icon} {r.get('step', '?')}: {str(r.get('result', ''))[:100]}")
        return "\n".join(lines)


class WorkflowEngine:
    """Execute and manage automated workflows."""

    def __init__(self):
        self.workflows: dict[str, Workflow] = {}
        self.tool_handlers: dict[str, Callable] = {}
        self._running_workflows: dict[str, bool] = {}
        self._load_all()

    def set_tool_handlers(self, handlers: dict[str, Callable]):
        """Set the available tool handlers (from brain)."""
        self.tool_handlers = handlers

    def _load_all(self):
        """Load all saved workflows."""
        for f in WORKFLOWS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                wf = Workflow.from_dict(data)
                self.workflows[wf.name] = wf
            except (json.JSONDecodeError, OSError):
                pass

    def _save_workflow(self, workflow: Workflow):
        """Save a workflow to disk."""
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in workflow.name)
        path = WORKFLOWS_DIR / f"{safe_name}.json"
        path.write_text(json.dumps(workflow.to_dict(), indent=2), encoding="utf-8")

    # ─── Workflow CRUD ────────────────────────────────────────
    def create_workflow(self, name: str, description: str = "",
                        steps: list = None, tags: str = "") -> str:
        """Create a new workflow."""
        if name in self.workflows:
            return f"Workflow '{name}' already exists. Use a different name."

        workflow = Workflow(
            name=name,
            description=description,
            steps=[WorkflowStep.from_dict(s) if isinstance(s, dict) else s for s in (steps or [])],
            created_at=datetime.now().isoformat(),
            tags=tags,
        )
        self.workflows[name] = workflow
        self._save_workflow(workflow)
        return f"Workflow '{name}' created with {len(workflow.steps)} steps."

    def add_step(self, workflow_name: str, step_name: str, action: str,
                 params: dict = None, condition: str = "",
                 on_error: str = "stop", store_as: str = "",
                 delay: float = 0) -> str:
        """Add a step to an existing workflow."""
        wf = self.workflows.get(workflow_name)
        if not wf:
            return f"Workflow '{workflow_name}' not found."

        step = WorkflowStep(
            name=step_name,
            action=action,
            params=params or {},
            condition=condition,
            on_error=on_error,
            store_result_as=store_as,
            delay_seconds=delay,
        )
        wf.steps.append(step)
        self._save_workflow(wf)
        return f"Step '{step_name}' added to workflow '{workflow_name}' (total: {len(wf.steps)} steps)."

    def remove_step(self, workflow_name: str, step_index: int) -> str:
        """Remove a step from a workflow by index."""
        wf = self.workflows.get(workflow_name)
        if not wf:
            return f"Workflow '{workflow_name}' not found."
        if step_index < 0 or step_index >= len(wf.steps):
            return f"Invalid step index. Workflow has {len(wf.steps)} steps (0-{len(wf.steps) - 1})."

        removed = wf.steps.pop(step_index)
        self._save_workflow(wf)
        return f"Removed step '{removed.name}' from workflow '{workflow_name}'."

    def delete_workflow(self, name: str) -> str:
        """Delete a workflow."""
        if name not in self.workflows:
            return f"Workflow '{name}' not found."
        del self.workflows[name]
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        path = WORKFLOWS_DIR / f"{safe_name}.json"
        if path.exists():
            path.unlink()
        return f"Workflow '{name}' deleted."

    def get_workflow(self, name: str) -> str:
        """Get workflow details."""
        wf = self.workflows.get(name)
        if not wf:
            return f"Workflow '{name}' not found."

        lines = [
            f"Workflow: {wf.name}",
            f"  Description: {wf.description or '(none)'}",
            f"  Steps: {len(wf.steps)}",
            f"  Created: {wf.created_at[:19]}",
            f"  Last run: {wf.last_run[:19] if wf.last_run else 'never'}",
            f"  Run count: {wf.run_count}",
            f"  Enabled: {wf.enabled}",
            f"  Tags: {wf.tags or '(none)'}",
            "",
            "  Steps:"
        ]
        for i, step in enumerate(wf.steps):
            cond = f" [if: {step.condition}]" if step.condition else ""
            lines.append(f"    {i}. {step.name}: {step.action}({json.dumps(step.params)[:60]}){cond}")

        return "\n".join(lines)

    def list_workflows(self) -> str:
        """List all workflows."""
        if not self.workflows:
            return "No workflows defined."

        lines = []
        for name, wf in self.workflows.items():
            status = "✓" if wf.enabled else "✗"
            last = wf.last_run[:10] if wf.last_run else "never"
            lines.append(f"  {status} {name}: {len(wf.steps)} steps — ran {wf.run_count}x (last: {last})")

        return f"Workflows ({len(self.workflows)}):\n" + "\n".join(lines)

    # ─── Execution ────────────────────────────────────────────
    async def run_workflow(self, name: str, initial_context: dict = None) -> str:
        """Execute a workflow."""
        wf = self.workflows.get(name)
        if not wf:
            return f"Workflow '{name}' not found."
        if not wf.enabled:
            return f"Workflow '{name}' is disabled."
        if name in self._running_workflows:
            return f"Workflow '{name}' is already running."

        self._running_workflows[name] = True
        context = dict(initial_context or {})
        result = WorkflowResult(
            workflow_name=name,
            success=True,
            steps_completed=0,
            steps_total=len(wf.steps),
            results=[],
            context=context,
        )

        start_time = time.time()
        log.info(f"Starting workflow: {name}")

        try:
            for i, step in enumerate(wf.steps):
                # Check condition
                if step.condition:
                    try:
                        if not eval(step.condition, {"__builtins__": {}}, context):
                            result.results.append({
                                "step": step.name,
                                "success": True,
                                "result": "Skipped (condition not met)",
                            })
                            result.steps_completed += 1
                            continue
                    except Exception as e:
                        result.results.append({
                            "step": step.name,
                            "success": False,
                            "result": f"Condition error: {e}",
                        })
                        if step.on_error == "stop":
                            result.success = False
                            result.errors.append(f"Step '{step.name}': condition error — {e}")
                            break
                        continue

                # Apply delay
                if step.delay_seconds > 0:
                    await asyncio.sleep(step.delay_seconds)

                # Execute step
                step_result = await self._execute_step(step, context)

                result.results.append({
                    "step": step.name,
                    "success": step_result.get("success", False),
                    "result": str(step_result.get("result", ""))[:200],
                })

                if step_result.get("success"):
                    result.steps_completed += 1
                    # Store result in context
                    if step.store_result_as:
                        context[step.store_result_as] = step_result.get("result", "")
                else:
                    if step.on_error == "stop":
                        result.success = False
                        result.errors.append(f"Step '{step.name}' failed: {step_result.get('result', '')}")
                        break
                    elif step.on_error == "retry":
                        # Retry logic
                        retried = False
                        for retry in range(step.max_retries):
                            await asyncio.sleep(1)
                            retry_result = await self._execute_step(step, context)
                            if retry_result.get("success"):
                                result.steps_completed += 1
                                if step.store_result_as:
                                    context[step.store_result_as] = retry_result.get("result", "")
                                retried = True
                                break
                        if not retried:
                            result.errors.append(f"Step '{step.name}' failed after {step.max_retries} retries")
                            result.success = False
                            break
                    # skip: just continue

        finally:
            self._running_workflows.pop(name, None)

        result.duration_seconds = time.time() - start_time
        result.context = {k: str(v)[:100] for k, v in context.items()}

        # Update workflow stats
        wf.last_run = datetime.now().isoformat()
        wf.run_count += 1
        self._save_workflow(wf)

        log.info(f"Workflow '{name}' completed: {'success' if result.success else 'failed'}")
        return result.to_str()

    async def _execute_step(self, step: WorkflowStep, context: dict) -> dict:
        """Execute a single workflow step."""
        handler = self.tool_handlers.get(step.action)
        if not handler:
            return {"success": False, "result": f"Tool '{step.action}' not found"}

        # Substitute context variables in params
        params = {}
        for key, value in step.params.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                params[key] = context.get(var_name, value)
            else:
                params[key] = value

        try:
            result = handler(**params)
            if asyncio.iscoroutine(result):
                result = await result
            return {"success": True, "result": str(result)}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}

    def stop_workflow(self, name: str) -> str:
        """Stop a running workflow."""
        if name in self._running_workflows:
            self._running_workflows.pop(name)
            return f"Workflow '{name}' stop signal sent."
        return f"Workflow '{name}' is not running."

    # ─── Predefined Workflow Templates ────────────────────────
    def create_from_template(self, template_name: str, workflow_name: str = "") -> str:
        """Create a workflow from a predefined template."""
        templates = {
            "morning_routine": {
                "description": "Morning routine: weather, tasks, briefing",
                "steps": [
                    {"name": "briefing", "action": "get_daily_briefing", "params": {}, "store_result_as": "briefing"},
                    {"name": "weather", "action": "get_weather", "params": {"location": "auto"}, "store_result_as": "weather"},
                    {"name": "tasks", "action": "task_operation", "params": {"operation": "today"}, "store_result_as": "today_tasks"},
                    {"name": "emails", "action": "count_unread_emails", "params": {}, "store_result_as": "email_count", "on_error": "skip"},
                ],
            },
            "system_health": {
                "description": "System health check: status, processes, network",
                "steps": [
                    {"name": "system_info", "action": "system_info", "params": {}, "store_result_as": "sys_info"},
                    {"name": "processes", "action": "process_operation", "params": {"operation": "hogs", "top": "10"}, "store_result_as": "top_procs"},
                    {"name": "network", "action": "network_tool", "params": {"operation": "usage"}, "store_result_as": "net_usage"},
                    {"name": "security", "action": "security_tool", "params": {"operation": "suspicious"}, "store_result_as": "security", "on_error": "skip"},
                ],
            },
            "backup_project": {
                "description": "Backup a project: git status, zip, verify",
                "steps": [
                    {"name": "git_status", "action": "git_operation", "params": {"operation": "status"}, "store_result_as": "git", "on_error": "skip"},
                    {"name": "backup", "action": "backup_operation", "params": {"operation": "create", "source": "."}, "store_result_as": "backup_result"},
                ],
            },
            "end_of_day": {
                "description": "End of day: task summary, time tracking, reminder",
                "steps": [
                    {"name": "task_summary", "action": "task_operation", "params": {"operation": "summary"}, "store_result_as": "tasks"},
                    {"name": "time_summary", "action": "task_operation", "params": {"operation": "time_summary", "days": "1"}, "store_result_as": "time"},
                    {"name": "habits", "action": "task_operation", "params": {"operation": "habits"}, "store_result_as": "habits", "on_error": "skip"},
                ],
            },
        }

        template = templates.get(template_name)
        if not template:
            available = ", ".join(templates.keys())
            return f"Unknown template: {template_name}. Available: {available}"

        name = workflow_name or template_name
        return self.create_workflow(
            name=name,
            description=template.get("description", ""),
            steps=template.get("steps", []),
        )

    # ─── Unified Interface ────────────────────────────────────
    async def workflow_operation(self, operation: str, **kwargs) -> str:
        """Unified workflow management."""
        name = kwargs.get("name", kwargs.get("workflow_name", ""))

        ops = {
            "create": lambda: self.create_workflow(name, kwargs.get("description", ""), kwargs.get("steps"), kwargs.get("tags", "")),
            "add_step": lambda: self.add_step(name, kwargs.get("step_name", ""), kwargs.get("action", ""), kwargs.get("params"), kwargs.get("condition", ""), kwargs.get("on_error", "stop"), kwargs.get("store_as", ""), float(kwargs.get("delay", 0))),
            "remove_step": lambda: self.remove_step(name, int(kwargs.get("step_index", 0))),
            "delete": lambda: self.delete_workflow(name),
            "get": lambda: self.get_workflow(name),
            "list": lambda: self.list_workflows(),
            "stop": lambda: self.stop_workflow(name),
            "template": lambda: self.create_from_template(kwargs.get("template", ""), name),
        }

        # Async ops
        if operation == "run":
            return await self.run_workflow(name, kwargs.get("context"))

        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown workflow operation: {operation}. Available: create, add_step, remove_step, delete, get, list, run, stop, template"


# ─── Singleton ────────────────────────────────────────────────
workflow_engine = WorkflowEngine()
