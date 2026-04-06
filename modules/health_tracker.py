"""
Health & Fitness Tracker — Track water intake, exercise, sleep, weight,
calories, and generate health insights.
"""

import json
from datetime import datetime, timedelta, date
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("health")

HEALTH_FILE = config.DATA_DIR / "health_data.json"


class HealthTracker:
    """Personal health and fitness tracking system."""

    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if HEALTH_FILE.exists():
            try:
                return json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "water": [],       # {date, glasses}
            "exercise": [],    # {date, type, duration_min, calories}
            "sleep": [],       # {date, hours, quality}
            "weight": [],      # {date, kg}
            "meals": [],       # {date, description, calories, meal_type}
            "mood": [],        # {date, mood, notes}
            "steps": [],       # {date, count}
            "goals": {},       # {water_glasses: 8, sleep_hours: 8, ...}
            "profile": {},     # {height_cm, age, gender, target_weight_kg}
        }

    def _save(self):
        HEALTH_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    # ─── Water Tracking ──────────────────────────────────────
    def log_water(self, glasses: int = 1) -> str:
        """Log water intake (glasses)."""
        today = self._today()
        # Find or create today's entry
        for entry in self.data["water"]:
            if entry["date"] == today:
                entry["glasses"] += glasses
                self._save()
                goal = self.data["goals"].get("water_glasses", 8)
                return f"Water logged: {entry['glasses']}/{goal} glasses today. {'✓ Goal reached!' if entry['glasses'] >= goal else ''}"

        self.data["water"].append({"date": today, "glasses": glasses})
        self._save()
        goal = self.data["goals"].get("water_glasses", 8)
        return f"Water logged: {glasses}/{goal} glasses today."

    def get_water_today(self) -> str:
        today = self._today()
        for entry in self.data["water"]:
            if entry["date"] == today:
                goal = self.data["goals"].get("water_glasses", 8)
                pct = (entry["glasses"] / goal * 100) if goal else 0
                bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                return f"Water today: {entry['glasses']}/{goal} glasses [{bar}] {pct:.0f}%"
        return "No water logged today. Stay hydrated!"

    # ─── Exercise Tracking ────────────────────────────────────
    def log_exercise(self, exercise_type: str, duration_min: int,
                     calories: int = 0, notes: str = "") -> str:
        """Log an exercise session."""
        # Auto-estimate calories if not provided
        if not calories:
            cal_per_min = {
                "running": 10, "jogging": 8, "walking": 4, "cycling": 7,
                "swimming": 9, "yoga": 4, "weights": 5, "hiit": 12,
                "dancing": 6, "hiking": 6, "climbing": 8, "boxing": 10,
                "tennis": 7, "basketball": 8, "football": 9, "stretching": 3,
            }
            calories = cal_per_min.get(exercise_type.lower(), 5) * duration_min

        entry = {
            "date": self._today(),
            "type": exercise_type,
            "duration_min": duration_min,
            "calories": calories,
            "notes": notes,
            "time": datetime.now().strftime("%H:%M"),
        }
        self.data["exercise"].append(entry)
        self._save()

        return (
            f"Exercise logged: {exercise_type}\n"
            f"  Duration: {duration_min} minutes\n"
            f"  Calories burned: ~{calories} kcal\n"
            f"  Keep it up! 💪"
        )

    def get_exercise_today(self) -> str:
        today = self._today()
        todays = [e for e in self.data["exercise"] if e["date"] == today]
        if not todays:
            return "No exercise logged today. Time to move!"

        total_min = sum(e["duration_min"] for e in todays)
        total_cal = sum(e["calories"] for e in todays)
        lines = [f"  • {e['type']}: {e['duration_min']}min (~{e['calories']} kcal)" for e in todays]

        return (
            f"Today's Exercise ({len(todays)} sessions):\n"
            + "\n".join(lines)
            + f"\n  Total: {total_min} min, ~{total_cal} kcal burned"
        )

    # ─── Sleep Tracking ───────────────────────────────────────
    def log_sleep(self, hours: float, quality: str = "good", notes: str = "") -> str:
        """Log sleep. Quality: poor, fair, good, excellent."""
        entry = {
            "date": self._today(),
            "hours": hours,
            "quality": quality,
            "notes": notes,
        }
        self.data["sleep"].append(entry)
        self._save()

        goal = self.data["goals"].get("sleep_hours", 8)
        emoji = {"poor": "😴", "fair": "😐", "good": "😊", "excellent": "🌟"}.get(quality, "😊")

        return (
            f"Sleep logged: {hours} hours ({quality}) {emoji}\n"
            f"  Goal: {goal} hours — {'✓ Met!' if hours >= goal else f'Need {goal - hours:.1f}h more'}"
        )

    def get_sleep_average(self, days: int = 7) -> str:
        recent = [e for e in self.data["sleep"] if self._is_recent(e["date"], days)]
        if not recent:
            return f"No sleep data in the last {days} days."

        avg_hours = sum(e["hours"] for e in recent) / len(recent)
        quality_counts = {}
        for e in recent:
            q = e.get("quality", "good")
            quality_counts[q] = quality_counts.get(q, 0) + 1

        return (
            f"Sleep (last {days} days):\n"
            f"  Average: {avg_hours:.1f} hours/night\n"
            f"  Entries: {len(recent)}\n"
            f"  Quality: {', '.join(f'{q}({c})' for q, c in quality_counts.items())}"
        )

    # ─── Weight Tracking ──────────────────────────────────────
    def log_weight(self, kg: float) -> str:
        """Log weight in kg."""
        entry = {"date": self._today(), "kg": kg}
        self.data["weight"].append(entry)
        self._save()

        target = self.data["goals"].get("target_weight_kg")
        msg = f"Weight logged: {kg} kg"
        if target:
            diff = kg - target
            msg += f" (target: {target} kg, {'↓' if diff > 0 else '↑'}{abs(diff):.1f} kg to go)"

        # Trend
        recent = [e for e in self.data["weight"] if self._is_recent(e["date"], 30)]
        if len(recent) >= 2:
            first = recent[0]["kg"]
            change = kg - first
            msg += f"\n  30-day change: {change:+.1f} kg"

        return msg

    def get_weight_history(self, days: int = 30) -> str:
        recent = [e for e in self.data["weight"] if self._is_recent(e["date"], days)]
        if not recent:
            return "No weight data recorded."

        lines = [f"  {e['date']}: {e['kg']} kg" for e in recent[-10:]]
        return f"Weight history (last {days} days):\n" + "\n".join(lines)

    # ─── Meal/Calorie Tracking ────────────────────────────────
    def log_meal(self, description: str, calories: int = 0,
                 meal_type: str = "meal") -> str:
        """Log a meal. Types: breakfast, lunch, dinner, snack, meal."""
        entry = {
            "date": self._today(),
            "description": description,
            "calories": calories,
            "meal_type": meal_type,
            "time": datetime.now().strftime("%H:%M"),
        }
        self.data["meals"].append(entry)
        self._save()

        # Today's total
        todays = [m for m in self.data["meals"] if m["date"] == self._today()]
        total_cal = sum(m["calories"] for m in todays)
        goal = self.data["goals"].get("daily_calories", 2000)

        return (
            f"Meal logged: {description} ({meal_type})\n"
            f"  Calories: {calories} kcal\n"
            f"  Today's total: {total_cal}/{goal} kcal"
        )

    def get_calories_today(self) -> str:
        today = self._today()
        todays = [m for m in self.data["meals"] if m["date"] == today]
        exercise_cal = sum(e["calories"] for e in self.data["exercise"] if e["date"] == today)

        if not todays:
            return "No meals logged today."

        total_in = sum(m["calories"] for m in todays)
        net = total_in - exercise_cal
        goal = self.data["goals"].get("daily_calories", 2000)

        lines = [f"  {m['time']} [{m['meal_type']}] {m['description']}: {m['calories']} kcal" for m in todays]

        return (
            f"Today's Nutrition:\n"
            + "\n".join(lines)
            + f"\n\n  Calories in: {total_in} kcal"
            + f"\n  Exercise burned: {exercise_cal} kcal"
            + f"\n  Net: {net} kcal (goal: {goal})"
        )

    # ─── Mood Tracking ────────────────────────────────────────
    def log_mood(self, mood: str, notes: str = "") -> str:
        """Log mood. Moods: amazing, happy, good, neutral, tired, stressed, sad, awful."""
        emojis = {
            "amazing": "🌟", "happy": "😊", "good": "🙂", "neutral": "😐",
            "tired": "😴", "stressed": "😰", "sad": "😢", "awful": "😞",
        }
        entry = {
            "date": self._today(),
            "mood": mood.lower(),
            "notes": notes,
            "time": datetime.now().strftime("%H:%M"),
        }
        self.data["mood"].append(entry)
        self._save()

        emoji = emojis.get(mood.lower(), "😐")
        return f"Mood logged: {mood} {emoji}" + (f"\n  Notes: {notes}" if notes else "")

    # ─── Steps ────────────────────────────────────────────────
    def log_steps(self, count: int) -> str:
        """Log daily step count."""
        today = self._today()
        for entry in self.data["steps"]:
            if entry["date"] == today:
                entry["count"] = count
                self._save()
                goal = self.data["goals"].get("daily_steps", 10000)
                pct = (count / goal * 100) if goal else 0
                return f"Steps updated: {count:,}/{goal:,} ({pct:.0f}%)"

        self.data["steps"].append({"date": today, "count": count})
        self._save()
        goal = self.data["goals"].get("daily_steps", 10000)
        return f"Steps logged: {count:,}/{goal:,}"

    # ─── Goals ────────────────────────────────────────────────
    def set_goal(self, goal_type: str, value: float) -> str:
        """Set a health goal."""
        valid_goals = {
            "water_glasses": "daily water (glasses)",
            "sleep_hours": "daily sleep (hours)",
            "daily_calories": "daily calories",
            "daily_steps": "daily steps",
            "target_weight_kg": "target weight (kg)",
            "exercise_minutes": "daily exercise (minutes)",
        }
        if goal_type not in valid_goals:
            return f"Unknown goal. Available: {', '.join(f'{k} ({v})' for k, v in valid_goals.items())}"

        self.data["goals"][goal_type] = value
        self._save()
        return f"Goal set: {valid_goals[goal_type]} = {value}"

    def get_goals(self) -> str:
        goals = self.data.get("goals", {})
        if not goals:
            return "No health goals set. Use set_goal to configure."
        lines = [f"  {k}: {v}" for k, v in goals.items()]
        return "Health Goals:\n" + "\n".join(lines)

    # ─── Profile ──────────────────────────────────────────────
    def set_profile(self, height_cm: int = 0, age: int = 0,
                    gender: str = "", target_weight_kg: float = 0) -> str:
        """Set health profile."""
        profile = self.data.get("profile", {})
        if height_cm:
            profile["height_cm"] = height_cm
        if age:
            profile["age"] = age
        if gender:
            profile["gender"] = gender
        if target_weight_kg:
            profile["target_weight_kg"] = target_weight_kg
            self.data["goals"]["target_weight_kg"] = target_weight_kg
        self.data["profile"] = profile
        self._save()

        lines = [f"  {k}: {v}" for k, v in profile.items()]
        return "Profile updated:\n" + "\n".join(lines)

    def calculate_bmi(self) -> str:
        """Calculate BMI from profile and latest weight."""
        profile = self.data.get("profile", {})
        height = profile.get("height_cm", 0)
        if not height:
            return "Set your height first: set_profile(height_cm=175)"

        weights = self.data.get("weight", [])
        if not weights:
            return "No weight recorded. Log your weight first."

        weight = weights[-1]["kg"]
        height_m = height / 100
        bmi = weight / (height_m ** 2)

        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal weight ✓"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

        return (
            f"BMI Calculation:\n"
            f"  Weight: {weight} kg\n"
            f"  Height: {height} cm\n"
            f"  BMI: {bmi:.1f}\n"
            f"  Category: {category}"
        )

    # ─── Daily Summary ────────────────────────────────────────
    def daily_summary(self, date_str: str = "") -> str:
        """Get health summary for a day."""
        target_date = date_str or self._today()

        water = next((e["glasses"] for e in self.data["water"] if e["date"] == target_date), 0)
        exercises = [e for e in self.data["exercise"] if e["date"] == target_date]
        sleep = next((e for e in self.data["sleep"] if e["date"] == target_date), None)
        meals = [m for m in self.data["meals"] if m["date"] == target_date]
        mood_entries = [m for m in self.data["mood"] if m["date"] == target_date]
        steps = next((e["count"] for e in self.data["steps"] if e["date"] == target_date), 0)

        goals = self.data.get("goals", {})

        lines = [f"Health Summary for {target_date}:", ""]

        # Water
        water_goal = goals.get("water_glasses", 8)
        lines.append(f"  💧 Water: {water}/{water_goal} glasses")

        # Sleep
        if sleep:
            lines.append(f"  🛏️ Sleep: {sleep['hours']}h ({sleep.get('quality', 'good')})")
        else:
            lines.append("  🛏️ Sleep: not logged")

        # Exercise
        if exercises:
            total_min = sum(e["duration_min"] for e in exercises)
            total_cal = sum(e["calories"] for e in exercises)
            lines.append(f"  🏃 Exercise: {total_min}min, ~{total_cal} kcal burned")
        else:
            lines.append("  🏃 Exercise: none logged")

        # Meals
        if meals:
            total_cal = sum(m["calories"] for m in meals)
            cal_goal = goals.get("daily_calories", 2000)
            lines.append(f"  🍽️ Calories: {total_cal}/{cal_goal} kcal ({len(meals)} meals)")
        else:
            lines.append("  🍽️ Meals: none logged")

        # Steps
        step_goal = goals.get("daily_steps", 10000)
        lines.append(f"  👣 Steps: {steps:,}/{step_goal:,}")

        # Mood
        if mood_entries:
            latest = mood_entries[-1]
            lines.append(f"  😊 Mood: {latest['mood']}")

        return "\n".join(lines)

    def weekly_report(self) -> str:
        """Generate a weekly health report."""
        lines = ["Weekly Health Report:", ""]

        # Water average
        recent_water = [e for e in self.data["water"] if self._is_recent(e["date"], 7)]
        if recent_water:
            avg = sum(e["glasses"] for e in recent_water) / len(recent_water)
            lines.append(f"  💧 Avg water: {avg:.1f} glasses/day")

        # Sleep average
        recent_sleep = [e for e in self.data["sleep"] if self._is_recent(e["date"], 7)]
        if recent_sleep:
            avg = sum(e["hours"] for e in recent_sleep) / len(recent_sleep)
            lines.append(f"  🛏️ Avg sleep: {avg:.1f} hours/night")

        # Exercise total
        recent_exercise = [e for e in self.data["exercise"] if self._is_recent(e["date"], 7)]
        if recent_exercise:
            total = sum(e["duration_min"] for e in recent_exercise)
            cal = sum(e["calories"] for e in recent_exercise)
            lines.append(f"  🏃 Exercise: {total}min total, ~{cal} kcal ({len(recent_exercise)} sessions)")

        # Weight trend
        recent_weight = [e for e in self.data["weight"] if self._is_recent(e["date"], 7)]
        if len(recent_weight) >= 2:
            change = recent_weight[-1]["kg"] - recent_weight[0]["kg"]
            lines.append(f"  ⚖️ Weight change: {change:+.1f} kg")

        # Mood distribution
        recent_mood = [e for e in self.data["mood"] if self._is_recent(e["date"], 7)]
        if recent_mood:
            moods = {}
            for m in recent_mood:
                moods[m["mood"]] = moods.get(m["mood"], 0) + 1
            lines.append(f"  😊 Moods: {', '.join(f'{k}({v})' for k, v in moods.items())}")

        if len(lines) <= 2:
            return "Not enough data for a weekly report. Start logging!"

        return "\n".join(lines)

    # ─── Helpers ──────────────────────────────────────────────
    def _is_recent(self, date_str: str, days: int) -> bool:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return (datetime.now() - dt).days <= days
        except (ValueError, TypeError):
            return False

    # ─── Unified Interface ────────────────────────────────────
    def health_operation(self, operation: str, **kwargs) -> str:
        """Unified health tracking interface."""
        ops = {
            "water": lambda: self.log_water(int(kwargs.get("glasses", 1))),
            "water_today": lambda: self.get_water_today(),
            "exercise": lambda: self.log_exercise(kwargs.get("type", "workout"), int(kwargs.get("duration", 30)), int(kwargs.get("calories", 0)), kwargs.get("notes", "")),
            "exercise_today": lambda: self.get_exercise_today(),
            "sleep": lambda: self.log_sleep(float(kwargs.get("hours", 7)), kwargs.get("quality", "good"), kwargs.get("notes", "")),
            "sleep_avg": lambda: self.get_sleep_average(int(kwargs.get("days", 7))),
            "weight": lambda: self.log_weight(float(kwargs.get("kg", 0))),
            "weight_history": lambda: self.get_weight_history(int(kwargs.get("days", 30))),
            "meal": lambda: self.log_meal(kwargs.get("description", ""), int(kwargs.get("calories", 0)), kwargs.get("meal_type", "meal")),
            "calories_today": lambda: self.get_calories_today(),
            "mood": lambda: self.log_mood(kwargs.get("mood", "good"), kwargs.get("notes", "")),
            "steps": lambda: self.log_steps(int(kwargs.get("count", 0))),
            "set_goal": lambda: self.set_goal(kwargs.get("goal_type", ""), float(kwargs.get("value", 0))),
            "goals": lambda: self.get_goals(),
            "profile": lambda: self.set_profile(int(kwargs.get("height_cm", 0)), int(kwargs.get("age", 0)), kwargs.get("gender", ""), float(kwargs.get("target_weight_kg", 0))),
            "bmi": lambda: self.calculate_bmi(),
            "summary": lambda: self.daily_summary(kwargs.get("date", "")),
            "weekly": lambda: self.weekly_report(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown health operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
health_tracker = HealthTracker()
