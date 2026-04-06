"""
AI Conversation Analyzer — Analyze conversation patterns, sentiment, 
topic extraction, and usage analytics for the Jarvis system.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict
from core.logger import get_logger
import config

log = get_logger("analyzer")


class ConversationAnalyzer:
    """Analyze conversation history for patterns and insights."""

    def __init__(self):
        self.history_file = config.MEMORY_DIR / "conversation_history.jsonl"
        self.activity_file = config.LOGS_DIR / "activity.jsonl"

    def _load_history(self, days: int = 30) -> list[dict]:
        """Load conversation history for analysis."""
        if not self.history_file.exists():
            return []

        entries = []
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        for line in self.history_file.read_text(encoding="utf-8").strip().split("\n"):
            try:
                entry = json.loads(line)
                if entry.get("timestamp", "") >= cutoff:
                    entries.append(entry)
            except json.JSONDecodeError:
                pass
        return entries

    def _load_activity(self, days: int = 30) -> list[dict]:
        """Load activity log for analysis."""
        if not self.activity_file.exists():
            return []

        entries = []
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        for line in self.activity_file.read_text(encoding="utf-8").strip().split("\n"):
            try:
                entry = json.loads(line)
                if entry.get("timestamp", "") >= cutoff:
                    entries.append(entry)
            except json.JSONDecodeError:
                pass
        return entries

    def usage_summary(self, days: int = 7) -> str:
        """Get overall usage summary."""
        history = self._load_history(days)
        activity = self._load_activity(days)

        if not history and not activity:
            return f"No data available for the last {days} days."

        # Conversation stats
        total_conversations = len(history)
        avg_user_length = 0
        avg_assistant_length = 0
        if history:
            user_lengths = [len(h.get("user", "")) for h in history]
            assistant_lengths = [len(h.get("assistant", "")) for h in history]
            avg_user_length = sum(user_lengths) / len(user_lengths)
            avg_assistant_length = sum(assistant_lengths) / len(assistant_lengths)

        # Tool usage
        tool_calls = [a for a in activity if a.get("type") == "tool_call"]
        tool_counts = Counter(a.get("tool", "") for a in tool_calls)
        top_tools = tool_counts.most_common(10)

        # Time distribution
        hour_counts = Counter()
        for h in history:
            try:
                ts = datetime.fromisoformat(h.get("timestamp", ""))
                hour_counts[ts.hour] += 1
            except (ValueError, TypeError):
                pass

        # Day distribution
        day_counts = Counter()
        for h in history:
            try:
                ts = datetime.fromisoformat(h.get("timestamp", ""))
                day_counts[ts.strftime("%a")] += 1
            except (ValueError, TypeError):
                pass

        result = (
            f"Usage Summary (last {days} days):\n"
            f"\n  ── Conversations ──\n"
            f"  Total exchanges: {total_conversations}\n"
            f"  Avg user message length: {avg_user_length:.0f} chars\n"
            f"  Avg response length: {avg_assistant_length:.0f} chars\n"
        )

        if top_tools:
            result += f"\n  ── Top Tools ──\n"
            for tool, count in top_tools:
                result += f"  {tool}: {count} calls\n"

        if hour_counts:
            peak_hour = hour_counts.most_common(1)[0]
            result += f"\n  ── Usage Patterns ──\n"
            result += f"  Peak hour: {peak_hour[0]}:00 ({peak_hour[1]} interactions)\n"

        if day_counts:
            peak_day = day_counts.most_common(1)[0]
            result += f"  Most active day: {peak_day[0]} ({peak_day[1]} interactions)\n"

        # Tool success rate
        success_count = sum(1 for a in tool_calls if a.get("success", True))
        fail_count = len(tool_calls) - success_count
        if tool_calls:
            result += f"\n  ── Tool Reliability ──\n"
            result += f"  Total tool calls: {len(tool_calls)}\n"
            result += f"  Successful: {success_count} ({success_count / len(tool_calls) * 100:.1f}%)\n"
            result += f"  Failed: {fail_count}\n"

        return result

    def topic_analysis(self, days: int = 7) -> str:
        """Analyze conversation topics."""
        history = self._load_history(days)
        if not history:
            return "No conversation data to analyze."

        # Extract common words (simple topic extraction)
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "dare", "ought",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "into", "about", "like", "through", "after", "over", "between",
            "out", "against", "during", "without", "before", "under", "around",
            "among", "i", "me", "my", "we", "our", "you", "your", "he", "she",
            "it", "they", "them", "this", "that", "these", "those", "what",
            "which", "who", "whom", "and", "but", "or", "not", "no", "so",
            "if", "when", "how", "all", "each", "every", "both", "few", "more",
            "some", "any", "most", "other", "than", "just", "also", "very",
            "often", "here", "there", "where", "why", "up", "get", "make",
            "go", "see", "come", "take", "know", "think", "say", "tell",
            "give", "work", "call", "try", "ask", "use", "find", "want",
            "please", "can", "could", "hi", "hey", "hello", "thanks", "thank",
            "okay", "ok", "yes", "no", "right", "well", "just", "now", "then",
        }

        all_words = []
        for h in history:
            words = re.findall(r'[a-zA-Z]{3,}', h.get("user", "").lower())
            all_words.extend(w for w in words if w not in stop_words)

        word_freq = Counter(all_words)
        top_words = word_freq.most_common(25)

        if not top_words:
            return "Not enough conversation data for topic analysis."

        lines = [f"  {word}: {count} mentions" for word, count in top_words]

        # Topic clusters (simple grouping)
        tech_words = {"code", "python", "javascript", "api", "server", "database", "git", "docker", "deploy", "debug", "error", "bug", "test"}
        system_words = {"system", "cpu", "memory", "disk", "process", "file", "folder", "directory", "install", "update"}
        comm_words = {"email", "message", "send", "whatsapp", "notify", "slack", "call"}
        iot_words = {"esp32", "sensor", "temperature", "humidity", "led", "relay", "arduino", "mqtt"}

        clusters = {}
        for word, count in top_words:
            if word in tech_words:
                clusters.setdefault("Technology", []).append(f"{word}({count})")
            elif word in system_words:
                clusters.setdefault("System Management", []).append(f"{word}({count})")
            elif word in comm_words:
                clusters.setdefault("Communication", []).append(f"{word}({count})")
            elif word in iot_words:
                clusters.setdefault("IoT/Hardware", []).append(f"{word}({count})")

        result = f"Topic Analysis (last {days} days):\n\n  ── Most Discussed ──\n" + "\n".join(lines)

        if clusters:
            result += "\n\n  ── Topic Clusters ──\n"
            for cluster, words in clusters.items():
                result += f"  {cluster}: {', '.join(words)}\n"

        return result

    def sentiment_overview(self, days: int = 7) -> str:
        """Simple sentiment analysis of conversations."""
        history = self._load_history(days)
        if not history:
            return "No conversation data."

        positive_words = {"great", "awesome", "perfect", "excellent", "amazing", "wonderful", "love", "thanks", "thank", "good", "nice", "helpful", "brilliant", "fantastic", "cool", "happy", "pleased"}
        negative_words = {"bad", "wrong", "error", "fail", "broken", "annoying", "terrible", "horrible", "awful", "frustrated", "angry", "worst", "sucks", "hate", "useless", "stupid"}
        question_words = {"what", "how", "why", "when", "where", "which", "who", "can", "could", "would", "should", "is", "are", "do", "does"}

        positive_count = 0
        negative_count = 0
        question_count = 0
        command_count = 0

        for h in history:
            text = h.get("user", "").lower()
            words = set(re.findall(r'[a-zA-Z]+', text))

            if words & positive_words:
                positive_count += 1
            if words & negative_words:
                negative_count += 1
            if text.endswith("?") or (words & question_words and len(text) < 100):
                question_count += 1
            else:
                command_count += 1

        total = len(history)
        return (
            f"Sentiment Overview (last {days} days, {total} exchanges):\n"
            f"  😊 Positive interactions: {positive_count} ({positive_count / max(total, 1) * 100:.0f}%)\n"
            f"  😟 Negative interactions: {negative_count} ({negative_count / max(total, 1) * 100:.0f}%)\n"
            f"  ❓ Questions asked: {question_count} ({question_count / max(total, 1) * 100:.0f}%)\n"
            f"  ⚡ Commands given: {command_count} ({command_count / max(total, 1) * 100:.0f}%)\n"
            f"\n  Overall vibe: {'Positive 🌟' if positive_count > negative_count else 'Neutral' if positive_count == negative_count else 'Could be better'}"
        )

    def response_time_analysis(self, days: int = 7) -> str:
        """Analyze when responses are fastest/slowest."""
        activity = self._load_activity(days)
        tool_calls = [a for a in activity if a.get("type") == "tool_call" and a.get("duration_ms")]

        if not tool_calls:
            return "No response time data available."

        durations = [a["duration_ms"] for a in tool_calls]
        avg = sum(durations) / len(durations)
        max_d = max(durations)
        min_d = min(durations)

        # Slowest tools
        tool_times = defaultdict(list)
        for a in tool_calls:
            tool_times[a.get("tool", "unknown")].append(a["duration_ms"])

        slow_tools = []
        for tool, times in tool_times.items():
            avg_time = sum(times) / len(times)
            slow_tools.append((tool, avg_time, len(times)))
        slow_tools.sort(key=lambda x: -x[1])

        result = (
            f"Response Time Analysis (last {days} days):\n"
            f"  Total tool calls: {len(tool_calls)}\n"
            f"  Average: {avg:.0f}ms\n"
            f"  Fastest: {min_d:.0f}ms\n"
            f"  Slowest: {max_d:.0f}ms\n"
            f"\n  ── Tool Performance ──\n"
        )

        for tool, avg_time, count in slow_tools[:10]:
            result += f"  {tool}: avg {avg_time:.0f}ms ({count} calls)\n"

        return result

    def daily_activity_chart(self, days: int = 14) -> str:
        """Generate a text-based daily activity chart."""
        history = self._load_history(days)
        if not history:
            return "No data for activity chart."

        # Count by day
        day_counts = defaultdict(int)
        for h in history:
            try:
                ts = datetime.fromisoformat(h.get("timestamp", ""))
                day_str = ts.strftime("%m/%d")
                day_counts[day_str] += 1
            except (ValueError, TypeError):
                pass

        if not day_counts:
            return "No dated entries."

        max_count = max(day_counts.values())
        bar_width = 30

        result = f"Daily Activity (last {days} days):\n\n"
        # Generate dates in order
        for i in range(days - 1, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%m/%d")
            count = day_counts.get(d, 0)
            bar_len = int((count / max(max_count, 1)) * bar_width)
            bar = "█" * bar_len + "░" * (bar_width - bar_len)
            result += f"  {d} [{bar}] {count}\n"

        return result

    def hourly_heatmap(self, days: int = 7) -> str:
        """Generate a text-based hourly activity heatmap."""
        history = self._load_history(days)
        if not history:
            return "No data for heatmap."

        hour_day = defaultdict(lambda: defaultdict(int))
        for h in history:
            try:
                ts = datetime.fromisoformat(h.get("timestamp", ""))
                hour_day[ts.strftime("%a")][ts.hour] += 1
            except (ValueError, TypeError):
                pass

        days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        max_val = max(
            (hour_day[d][h] for d in days_order for h in range(24) if hour_day[d][h]),
            default=1,
        )

        result = "Activity Heatmap (by hour and day):\n\n"
        result += "       " + " ".join(f"{h:>2}" for h in range(0, 24, 2)) + "\n"

        for day in days_order:
            row = f"  {day}  "
            for h in range(0, 24, 2):
                val = hour_day[day][h] + hour_day[day].get(h + 1, 0)
                if val == 0:
                    row += " · "
                elif val <= max_val * 0.25:
                    row += " ░ "
                elif val <= max_val * 0.5:
                    row += " ▒ "
                elif val <= max_val * 0.75:
                    row += " ▓ "
                else:
                    row += " █ "
            result += row + "\n"

        result += "\n  Legend: · none  ░ low  ▒ medium  ▓ high  █ peak\n"
        return result

    def conversation_insights(self, days: int = 7) -> str:
        """Generate AI-ready conversation insights."""
        history = self._load_history(days)
        if len(history) < 5:
            return "Need at least 5 conversations for insights."

        # Find repeated queries
        user_msgs = [h.get("user", "").lower().strip() for h in history]
        repeated = Counter(msg for msg in user_msgs if len(msg) > 10)
        most_repeated = repeated.most_common(5)

        # Find longest conversations
        lengths = [(len(h.get("user", "")), len(h.get("assistant", "")), h.get("timestamp", "")) for h in history]
        lengths.sort(key=lambda x: x[1], reverse=True)

        # Find error patterns
        errors = [h for h in history if any(w in h.get("assistant", "").lower() for w in ["error", "failed", "cannot", "unable", "sorry"])]

        result = f"Conversation Insights (last {days} days):\n"

        if most_repeated:
            result += "\n  ── Frequently Asked ──\n"
            for msg, count in most_repeated:
                if count > 1:
                    result += f"  ({count}x) \"{msg[:60]}...\"\n"

        result += f"\n  ── Statistics ──\n"
        result += f"  Total conversations: {len(history)}\n"
        result += f"  Avg per day: {len(history) / max(days, 1):.1f}\n"

        if errors:
            result += f"\n  ── Error Rate ──\n"
            result += f"  Responses with potential errors: {len(errors)} ({len(errors) / len(history) * 100:.1f}%)\n"

        return result

    # ─── Unified Interface ────────────────────────────────────
    def analyze_operation(self, operation: str, **kwargs) -> str:
        """Unified conversation analysis."""
        days = int(kwargs.get("days", 7))
        ops = {
            "usage": lambda: self.usage_summary(days),
            "topics": lambda: self.topic_analysis(days),
            "sentiment": lambda: self.sentiment_overview(days),
            "response_times": lambda: self.response_time_analysis(days),
            "daily_chart": lambda: self.daily_activity_chart(days),
            "heatmap": lambda: self.hourly_heatmap(days),
            "insights": lambda: self.conversation_insights(days),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown analysis: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
conversation_analyzer = ConversationAnalyzer()
