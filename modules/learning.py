"""
Learning & Flashcard Module — Spaced repetition flashcards, quiz system,
learning progress tracking, and study session management.
"""

import json
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("learning")

LEARNING_FILE = config.DATA_DIR / "learning.json"


class Flashcard:
    """A single flashcard with spaced repetition data."""
    def __init__(self, question: str, answer: str, category: str = "",
                 tags: str = "", difficulty: str = "medium"):
        self.id = 0
        self.question = question
        self.answer = answer
        self.category = category
        self.tags = tags
        self.difficulty = difficulty  # easy, medium, hard
        self.created_at = datetime.now().isoformat()
        # Spaced repetition fields
        self.interval_days = 1  # Days until next review
        self.ease_factor = 2.5  # SM-2 algorithm ease factor
        self.repetitions = 0
        self.next_review = datetime.now().isoformat()[:10]
        self.last_reviewed = ""
        self.correct_count = 0
        self.incorrect_count = 0
        self.streak = 0

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'Flashcard':
        f = Flashcard(d.get("question", ""), d.get("answer", ""))
        for k, v in d.items():
            if hasattr(f, k):
                setattr(f, k, v)
        return f

    def update_review(self, quality: int):
        """
        Update card based on review quality (SM-2 algorithm).
        quality: 0=complete_fail, 1=hard, 2=medium, 3=easy, 4=perfect
        """
        self.last_reviewed = datetime.now().isoformat()

        if quality >= 2:  # Correct
            self.correct_count += 1
            self.streak += 1
            if self.repetitions == 0:
                self.interval_days = 1
            elif self.repetitions == 1:
                self.interval_days = 3
            else:
                self.interval_days = round(self.interval_days * self.ease_factor)
            self.repetitions += 1
        else:  # Incorrect
            self.incorrect_count += 1
            self.streak = 0
            self.repetitions = 0
            self.interval_days = 1

        # Update ease factor (SM-2)
        self.ease_factor = max(1.3, self.ease_factor + 0.1 - (4 - quality) * (0.08 + (4 - quality) * 0.02))

        # Set next review date
        self.next_review = (datetime.now() + timedelta(days=self.interval_days)).strftime("%Y-%m-%d")

    @property
    def is_due(self) -> bool:
        return self.next_review <= datetime.now().strftime("%Y-%m-%d")

    @property
    def accuracy(self) -> float:
        total = self.correct_count + self.incorrect_count
        return (self.correct_count / total * 100) if total else 0


class StudyDeck:
    """A collection of flashcards organized as a deck."""
    def __init__(self, name: str, description: str = "", cards: list = None):
        self.name = name
        self.description = description
        self.cards: list[Flashcard] = cards or []
        self.created_at = datetime.now().isoformat()
        self.study_sessions = 0
        self.total_study_time_min = 0

    def to_dict(self):
        return {
            "name": self.name, "description": self.description,
            "cards": [c.to_dict() for c in self.cards],
            "created_at": self.created_at,
            "study_sessions": self.study_sessions,
            "total_study_time_min": self.total_study_time_min,
        }

    @staticmethod
    def from_dict(d) -> 'StudyDeck':
        deck = StudyDeck(d.get("name", ""), d.get("description", ""))
        deck.cards = [Flashcard.from_dict(c) for c in d.get("cards", [])]
        deck.created_at = d.get("created_at", "")
        deck.study_sessions = d.get("study_sessions", 0)
        deck.total_study_time_min = d.get("total_study_time_min", 0)
        return deck

    @property
    def due_count(self) -> int:
        return sum(1 for c in self.cards if c.is_due)

    @property
    def mastery(self) -> float:
        if not self.cards:
            return 0
        mastered = sum(1 for c in self.cards if c.repetitions >= 3 and c.streak >= 2)
        return mastered / len(self.cards) * 100


class LearningManager:
    """Manages flashcard decks and study sessions."""

    def __init__(self):
        self.decks: dict[str, StudyDeck] = {}
        self._next_card_id = 1
        self._load()

    def _load(self):
        if LEARNING_FILE.exists():
            try:
                data = json.loads(LEARNING_FILE.read_text(encoding="utf-8"))
                for name, ddata in data.get("decks", {}).items():
                    self.decks[name] = StudyDeck.from_dict(ddata)
                self._next_card_id = data.get("next_card_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {
            "decks": {n: d.to_dict() for n, d in self.decks.items()},
            "next_card_id": self._next_card_id,
        }
        LEARNING_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_deck(self, name: str, description: str = "") -> str:
        if name in self.decks:
            return f"Deck '{name}' already exists."
        self.decks[name] = StudyDeck(name, description)
        self._save()
        return f"Deck '{name}' created."

    def add_card(self, deck_name: str, question: str, answer: str,
                 category: str = "", tags: str = "",
                 difficulty: str = "medium") -> str:
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."
        card = Flashcard(question, answer, category, tags, difficulty)
        card.id = self._next_card_id
        self._next_card_id += 1
        deck.cards.append(card)
        self._save()
        return f"Card #{card.id} added to '{deck_name}': {question[:50]}..."

    def add_cards_bulk(self, deck_name: str, cards_text: str) -> str:
        """Add multiple cards from text format: Q: question\\nA: answer (separated by blank lines)."""
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."

        blocks = cards_text.strip().split("\n\n")
        added = 0
        for block in blocks:
            lines = block.strip().split("\n")
            question = ""
            answer = ""
            for line in lines:
                if line.upper().startswith("Q:"):
                    question = line[2:].strip()
                elif line.upper().startswith("A:"):
                    answer = line[2:].strip()
            if question and answer:
                card = Flashcard(question, answer)
                card.id = self._next_card_id
                self._next_card_id += 1
                deck.cards.append(card)
                added += 1

        self._save()
        return f"Added {added} cards to '{deck_name}'."

    def study(self, deck_name: str, count: int = 10) -> str:
        """Get due cards for study session."""
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."

        due = [c for c in deck.cards if c.is_due]
        if not due:
            return f"No cards due for review in '{deck_name}'! You're all caught up. 🎉"

        random.shuffle(due)
        session = due[:count]

        lines = [f"Study Session: {deck_name} ({len(session)}/{len(due)} due cards)\n"]
        for i, card in enumerate(session, 1):
            streak_str = f"🔥{card.streak}" if card.streak > 0 else ""
            lines.append(f"  Card {i}/{len(session)} (#{card.id}) {streak_str}")
            lines.append(f"  Q: {card.question}")
            lines.append(f"  A: [hidden — use 'reveal' command]")
            lines.append(f"  Difficulty: {card.difficulty} | Accuracy: {card.accuracy:.0f}%")
            lines.append("")

        deck.study_sessions += 1
        self._save()
        return "\n".join(lines)

    def review_card(self, deck_name: str, card_id: int, quality: int) -> str:
        """Review a card. quality: 0=fail, 1=hard, 2=ok, 3=easy, 4=perfect."""
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."

        for card in deck.cards:
            if card.id == card_id:
                card.update_review(quality)
                self._save()

                quality_labels = {0: "Failed", 1: "Hard", 2: "OK", 3: "Easy", 4: "Perfect"}
                label = quality_labels.get(quality, "?")

                return (
                    f"Card #{card_id} reviewed: {label}\n"
                    f"  Next review: {card.next_review}\n"
                    f"  Interval: {card.interval_days} days\n"
                    f"  Streak: {card.streak} | Ease: {card.ease_factor:.2f}"
                )
        return f"Card #{card_id} not found in '{deck_name}'."

    def reveal_card(self, deck_name: str, card_id: int) -> str:
        """Reveal the answer for a card."""
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."
        for card in deck.cards:
            if card.id == card_id:
                return f"Card #{card.id}:\n  Q: {card.question}\n  A: {card.answer}"
        return f"Card #{card_id} not found."

    def get_card(self, deck_name: str, card_id: int) -> str:
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."
        for card in deck.cards:
            if card.id == card_id:
                return (
                    f"Card #{card.id}:\n"
                    f"  Question: {card.question}\n"
                    f"  Answer: {card.answer}\n"
                    f"  Category: {card.category or '(none)'}\n"
                    f"  Difficulty: {card.difficulty}\n"
                    f"  Accuracy: {card.accuracy:.0f}%\n"
                    f"  Streak: {card.streak}\n"
                    f"  Reviews: {card.correct_count + card.incorrect_count}\n"
                    f"  Next review: {card.next_review}\n"
                    f"  Interval: {card.interval_days} days\n"
                    f"  Ease factor: {card.ease_factor:.2f}"
                )
        return f"Card #{card_id} not found."

    def delete_card(self, deck_name: str, card_id: int) -> str:
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."
        for i, card in enumerate(deck.cards):
            if card.id == card_id:
                deck.cards.pop(i)
                self._save()
                return f"Card #{card_id} deleted from '{deck_name}'."
        return f"Card #{card_id} not found."

    def delete_deck(self, name: str) -> str:
        if name not in self.decks:
            return f"Deck '{name}' not found."
        del self.decks[name]
        self._save()
        return f"Deck '{name}' deleted."

    def list_decks(self) -> str:
        if not self.decks:
            return "No study decks. Create one with create_deck."
        lines = []
        for name, deck in self.decks.items():
            due = deck.due_count
            due_label = f"📚 {due} due" if due else "✓ all caught up"
            lines.append(
                f"  {name}: {len(deck.cards)} cards | {due_label} | "
                f"Mastery: {deck.mastery:.0f}% | Sessions: {deck.study_sessions}"
            )
        return f"Study Decks ({len(self.decks)}):\n" + "\n".join(lines)

    def deck_stats(self, deck_name: str) -> str:
        deck = self.decks.get(deck_name)
        if not deck:
            return f"Deck '{deck_name}' not found."

        total = len(deck.cards)
        due = deck.due_count
        mastered = sum(1 for c in deck.cards if c.repetitions >= 3)
        learning = sum(1 for c in deck.cards if 0 < c.repetitions < 3)
        new = sum(1 for c in deck.cards if c.repetitions == 0)
        avg_accuracy = sum(c.accuracy for c in deck.cards) / max(total, 1)
        avg_ease = sum(c.ease_factor for c in deck.cards) / max(total, 1)

        return (
            f"Deck Statistics: {deck_name}\n"
            f"  Total cards: {total}\n"
            f"  Due for review: {due}\n"
            f"  Mastered (3+ reps): {mastered}\n"
            f"  Learning (1-2 reps): {learning}\n"
            f"  New (0 reps): {new}\n"
            f"  Mastery: {deck.mastery:.0f}%\n"
            f"  Average accuracy: {avg_accuracy:.0f}%\n"
            f"  Average ease: {avg_ease:.2f}\n"
            f"  Study sessions: {deck.study_sessions}\n"
            f"  Created: {deck.created_at[:10]}"
        )

    def quiz(self, deck_name: str, count: int = 5) -> str:
        """Generate a quiz with multiple cards."""
        deck = self.decks.get(deck_name)
        if not deck or not deck.cards:
            return f"Deck '{deck_name}' not found or empty."

        cards = random.sample(deck.cards, min(count, len(deck.cards)))
        lines = [f"Quiz: {deck_name} ({len(cards)} questions)\n"]
        for i, card in enumerate(cards, 1):
            lines.append(f"  {i}. {card.question}")
            lines.append(f"     (Card #{card.id} — answer hidden)")
            lines.append("")

        lines.append("Use 'reveal_card' with the card ID to check your answers.")
        return "\n".join(lines)

    def search_cards(self, query: str, deck_name: str = "") -> str:
        q = query.lower()
        results = []
        decks_to_search = [self.decks[deck_name]] if deck_name and deck_name in self.decks else self.decks.values()

        for deck in decks_to_search:
            for card in deck.cards:
                if q in card.question.lower() or q in card.answer.lower() or q in card.tags.lower():
                    results.append((deck.name, card))

        if not results:
            return f"No cards matching '{query}'."
        lines = [f"  [{dname}] #{card.id}: {card.question[:60]}..." for dname, card in results[:20]]
        return f"Card search ({len(results)} matches):\n" + "\n".join(lines)

    # ─── Unified Interface ────────────────────────────────
    def learning_operation(self, operation: str, **kwargs) -> str:
        deck = kwargs.get("deck", kwargs.get("deck_name", ""))
        ops = {
            "create_deck": lambda: self.create_deck(deck, kwargs.get("description", "")),
            "add_card": lambda: self.add_card(deck, kwargs.get("question", ""), kwargs.get("answer", ""), kwargs.get("category", ""), kwargs.get("tags", ""), kwargs.get("difficulty", "medium")),
            "add_bulk": lambda: self.add_cards_bulk(deck, kwargs.get("cards_text", "")),
            "study": lambda: self.study(deck, int(kwargs.get("count", 10))),
            "review": lambda: self.review_card(deck, int(kwargs.get("card_id", 0)), int(kwargs.get("quality", 2))),
            "reveal": lambda: self.reveal_card(deck, int(kwargs.get("card_id", 0))),
            "get_card": lambda: self.get_card(deck, int(kwargs.get("card_id", 0))),
            "delete_card": lambda: self.delete_card(deck, int(kwargs.get("card_id", 0))),
            "delete_deck": lambda: self.delete_deck(deck),
            "list": lambda: self.list_decks(),
            "stats": lambda: self.deck_stats(deck),
            "quiz": lambda: self.quiz(deck, int(kwargs.get("count", 5))),
            "search": lambda: self.search_cards(kwargs.get("query", ""), deck),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown learning operation: {operation}. Available: {', '.join(ops.keys())}"


learning_manager = LearningManager()
