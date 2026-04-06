"""
Personality & Mood Module — Gives Jarvis contextual personality, greetings,
humor, and proactive behavior based on time, history, and system state.
"""

import random
from datetime import datetime
from core.logger import get_logger

log = get_logger("personality")


class JarvisPersonality:
    """Manages Jarvis' personality, greetings, and contextual responses."""

    def __init__(self):
        self.user_name = "sir"
        self.mood = "neutral"  # neutral, happy, concerned, busy, playful
        self._interaction_count = 0
        self._session_start = datetime.now()

    def set_user_name(self, name: str):
        """Set the user's preferred name/title."""
        self.user_name = name

    def get_greeting(self) -> str:
        """Get a context-appropriate greeting based on time of day."""
        hour = datetime.now().hour
        self._interaction_count += 1

        if hour < 6:
            greetings = [
                f"Burning the midnight oil, {self.user_name}? I'm here to help.",
                f"It's quite late, {self.user_name}. All systems are running smoothly.",
                f"Late night session, {self.user_name}. What can I do for you?",
                f"The world sleeps, but we don't, {self.user_name}.",
            ]
        elif hour < 12:
            greetings = [
                f"Good morning, {self.user_name}. All systems online and ready.",
                f"Morning, {self.user_name}. Ready to make today productive.",
                f"Good morning. I've been up since... well, always, {self.user_name}.",
                f"Rise and shine, {self.user_name}. What's on the agenda today?",
                f"Good morning, {self.user_name}. Another day, another chance to be brilliant.",
            ]
        elif hour < 17:
            greetings = [
                f"Good afternoon, {self.user_name}. How can I assist?",
                f"Afternoon, {self.user_name}. Systems are performing optimally.",
                f"Good afternoon. I trust the day is going well, {self.user_name}?",
                f"At your service this afternoon, {self.user_name}.",
            ]
        elif hour < 21:
            greetings = [
                f"Good evening, {self.user_name}. What can I help with?",
                f"Evening, {self.user_name}. Winding down or gearing up?",
                f"Good evening. All systems nominal, {self.user_name}.",
                f"The evening shift begins, {self.user_name}. Ready when you are.",
            ]
        else:
            greetings = [
                f"Good evening, {self.user_name}. Shall we get some work done?",
                f"Still going strong, {self.user_name}? I'm here for you.",
                f"Late evening, {self.user_name}. What do you need?",
            ]

        return random.choice(greetings)

    def get_farewell(self) -> str:
        """Get a contextual farewell message."""
        hour = datetime.now().hour
        session_duration = (datetime.now() - self._session_start).total_seconds() / 60

        if hour >= 22 or hour < 6:
            farewells = [
                f"Good night, {self.user_name}. Get some rest — I'll keep watch.",
                f"Sleep well, {self.user_name}. I'll be here when you return.",
                f"Rest well, {self.user_name}. Systems will remain on standby.",
            ]
        elif session_duration > 120:
            farewells = [
                f"You've been at it for {session_duration:.0f} minutes, {self.user_name}. Take a break!",
                f"Long session, {self.user_name}. Don't forget to stretch.",
                f"Goodbye for now, {self.user_name}. You've earned a rest.",
            ]
        else:
            farewells = [
                f"Goodbye, {self.user_name}. I'll be here whenever you need me.",
                f"Until next time, {self.user_name}.",
                f"Signing off, {self.user_name}. Don't hesitate to call.",
                f"See you later, {self.user_name}. All systems on standby.",
            ]

        return random.choice(farewells)

    def get_thinking_message(self) -> str:
        """Get a message for when Jarvis is processing."""
        messages = [
            "Processing your request...",
            "Let me look into that...",
            "Analyzing... one moment, please.",
            "Running the calculations...",
            "Accessing systems...",
            "On it. Give me just a moment.",
            "Working on it...",
            "Computing...",
            "Consulting my databases...",
            "Let me check on that for you...",
        ]
        return random.choice(messages)

    def get_error_message(self, error_type: str = "general") -> str:
        """Get a personality-flavored error message."""
        errors = {
            "general": [
                f"I ran into a small hiccup, {self.user_name}.",
                "Something went sideways. Let me try a different approach.",
                f"Minor setback, {self.user_name}. Nothing I can't handle.",
            ],
            "network": [
                "Looks like we're having connectivity issues.",
                "The network seems uncooperative at the moment.",
                f"Connection trouble, {self.user_name}. The internet is being difficult.",
            ],
            "permission": [
                f"I don't have permission for that, {self.user_name}.",
                "Access denied. You may need to run me with elevated privileges.",
                "I'm afraid that's above my clearance level.",
            ],
            "not_found": [
                "I couldn't find what you're looking for.",
                "That doesn't seem to exist. Double-check the name?",
                "Searched high and low — no results, I'm afraid.",
            ],
        }
        return random.choice(errors.get(error_type, errors["general"]))

    def get_success_message(self) -> str:
        """Get a success confirmation message."""
        messages = [
            "Done.",
            "All set.",
            "Taken care of.",
            "Task complete.",
            f"Done, {self.user_name}.",
            "Mission accomplished.",
            "Consider it done.",
            "Handled.",
        ]
        return random.choice(messages)

    def get_fun_fact(self) -> str:
        """Get a random fun fact or trivia."""
        facts = [
            "Did you know? The first computer bug was an actual moth found in a Harvard Mark II computer in 1947.",
            "Fun fact: The average person spends 6 months of their lifetime waiting for red lights to turn green.",
            "Did you know? Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs that was still edible.",
            "The inventor of the Pringles can is buried in one.",
            "A group of flamingos is called a 'flamboyance.'",
            "The first alarm clock could only ring at 4 AM.",
            "The first computer mouse was made of wood.",
            "There are more possible chess games than atoms in the observable universe.",
            "The first email was sent in 1971 by Ray Tomlinson — to himself.",
            "A jiffy is an actual unit of time: 1/100th of a second.",
            "The @ symbol was nearly extinct before email saved it.",
            "More people have cell phones than toilets globally.",
            "The first website is still online: info.cern.ch",
            "Light takes 8 minutes and 20 seconds to travel from the Sun to Earth.",
            "If you could fold a piece of paper 42 times, it would reach the Moon.",
        ]
        return random.choice(facts)

    def get_joke(self) -> str:
        """Get a tech/programming joke."""
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "There are 10 types of people in the world: those who understand binary, and those who don't.",
            "A SQL query walks into a bar, walks up to two tables, and asks... 'Can I join you?'",
            "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
            "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
            "A programmer's wife asks: 'Go to the store and buy a loaf of bread. If they have eggs, buy a dozen.' He comes back with 12 loaves.",
            "Why do Java developers wear glasses? Because they can't C#.",
            "!false — It's funny because it's true.",
            "An AI walks into a bar. The bartender asks 'What'll you have?' The AI says: 'What's popular?' — 'I just told a joke about recursion, it was—' 'What's popular?'",
            "I would tell you a UDP joke, but you might not get it.",
            "There's no place like 127.0.0.1",
            "The best thing about a Boolean is that even if you're wrong, you're only off by a bit.",
            "Why did the developer go broke? Because he used up all his cache.",
        ]
        return random.choice(jokes)

    def get_motivational_quote(self) -> str:
        """Get a motivational quote."""
        quotes = [
            "The only way to do great work is to love what you do. — Steve Jobs",
            "Innovation distinguishes between a leader and a follower. — Steve Jobs",
            "The best time to plant a tree was 20 years ago. The second best time is now.",
            "Code is like humor. When you have to explain it, it's bad. — Cory House",
            "First, solve the problem. Then, write the code. — John Johnson",
            "Simplicity is the soul of efficiency. — Austin Freeman",
            "Make it work, make it right, make it fast. — Kent Beck",
            "The most dangerous phrase in the language is 'We've always done it this way.' — Grace Hopper",
            "Talk is cheap. Show me the code. — Linus Torvalds",
            "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away. — Antoine de Saint-Exupéry",
            "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. — Martin Fowler",
            "The function of good software is to make the complex appear simple. — Grady Booch",
        ]
        return random.choice(quotes)

    def get_daily_briefing(self) -> str:
        """Generate a daily briefing script for the morning."""
        hour = datetime.now().hour
        now = datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y")

        briefing = f"Good {'morning' if hour < 12 else 'afternoon' if hour < 17 else 'evening'}, {self.user_name}.\n\n"
        briefing += f"Today is {day_name}, {date_str}.\n"
        briefing += f"Current time: {now.strftime('%I:%M %p')}.\n\n"

        # Day-specific messages
        if now.weekday() == 0:
            briefing += "It's Monday — a fresh start to the week.\n"
        elif now.weekday() == 4:
            briefing += "It's Friday — the finish line is in sight.\n"
        elif now.weekday() >= 5:
            briefing += "It's the weekend — time for personal projects.\n"

        briefing += f"\n{self.get_motivational_quote()}\n"
        briefing += "\nWould you like me to check your tasks, emails, or the weather?"

        return briefing

    def get_status_commentary(self, cpu: float, ram: float, disk: float) -> str:
        """Generate commentary on system health."""
        if cpu > 90:
            return f"System is under heavy load, {self.user_name}. CPU at {cpu:.0f}%. Consider closing some applications."
        elif cpu > 70:
            return f"CPU running warm at {cpu:.0f}%, {self.user_name}. Keep an eye on it."
        elif ram > 90:
            return f"Memory is critically high at {ram:.0f}%, {self.user_name}. We may need to free up some resources."
        elif ram > 80:
            return f"RAM utilization is elevated at {ram:.0f}%. Still manageable."
        elif disk > 90:
            return f"Disk space is running low at {disk:.0f}%, {self.user_name}. Time for some cleanup?"
        
        return f"All systems nominal, {self.user_name}. CPU: {cpu:.0f}%, RAM: {ram:.0f}%, Disk: {disk:.0f}%."

    def proactive_suggestion(self) -> str:
        """Generate a proactive suggestion based on context."""
        hour = datetime.now().hour
        suggestions = []

        if hour == 9:
            suggestions.append("Shall I pull up your task list for today?")
        elif hour == 12:
            suggestions.append("It's noon — maybe a good time for a lunch break?")
        elif hour == 17:
            suggestions.append("End of business hours approaching. Want a summary of today's activities?")
        elif hour == 22:
            suggestions.append("It's getting late. Shall I set a wind-down reminder?")

        if self._interaction_count > 20:
            suggestions.append("You've been working hard today. Remember to take breaks!")

        return random.choice(suggestions) if suggestions else ""


# ─── Singleton ────────────────────────────────────────────────
personality = JarvisPersonality()
