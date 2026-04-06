"""
Lorem Ipsum & Dummy Data Generator — Generate placeholder text, fake data,
random names, addresses, and test datasets for development.
"""

import random
import string
import json
from datetime import datetime, timedelta
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("datagen")


# ─── Lorem Ipsum Text ────────────────────────────────────────
LOREM_WORDS = [
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit",
    "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore",
    "magna", "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud",
    "exercitation", "ullamco", "laboris", "nisi", "aliquip", "ex", "ea", "commodo",
    "consequat", "duis", "aute", "irure", "in", "reprehenderit", "voluptate",
    "velit", "esse", "cillum", "fugiat", "nulla", "pariatur", "excepteur", "sint",
    "occaecat", "cupidatat", "non", "proident", "sunt", "culpa", "qui", "officia",
    "deserunt", "mollit", "anim", "id", "est", "laborum", "pellentesque",
    "habitant", "morbi", "tristique", "senectus", "netus", "malesuada", "fames",
    "turpis", "egestas", "integer", "feugiat", "scelerisque", "varius", "morbi",
    "enim", "nunc", "faucibus", "vitae", "aliquet", "sagittis", "orci",
    "diam", "vulputate", "mattis", "ante", "porta", "nibh", "dictum",
    "viverra", "mauris", "augue", "neque", "gravida", "risus", "pretium",
    "elementum", "facilisis", "leo", "vel", "fringilla", "est", "ullamcorper",
    "massa", "tincidunt", "proin", "suscipit", "lectus", "urna", "posuere",
    "pharetra", "lacus", "placerat", "cursus", "interdum", "imperdiet",
]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Emily", "Alex",
    "Oliver", "Sophie", "Liam", "Emma", "Noah", "Ava", "Ethan", "Mia",
    "Raj", "Priya", "Wei", "Yuki", "Ahmed", "Fatima", "Pablo", "Maria",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore",
    "Martin", "Jackson", "Thompson", "White", "Harris", "Clark", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Hill", "Green",
    "Adams", "Nelson", "Carter", "Mitchell", "Roberts", "Turner", "Phillips",
    "Campbell", "Parker", "Evans", "Edwards", "Collins", "Chen", "Singh", "Park",
]

STREETS = [
    "Main St", "Oak Ave", "Elm St", "Maple Dr", "Pine Rd", "Cedar Ln",
    "Birch Way", "Willow Ct", "Park Ave", "Lake Dr", "River Rd", "Hill St",
    "Valley Dr", "Mountain Rd", "Forest Ave", "Spring St", "Ocean Blvd",
    "Sunset Dr", "Broadway", "Washington Ave", "Lincoln St", "Madison Ave",
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "San Antonio",
    "San Diego", "Dallas", "San Jose", "Austin", "Seattle", "Denver",
    "Boston", "Nashville", "Portland", "Las Vegas", "Atlanta", "Miami",
    "Toronto", "London", "Paris", "Berlin", "Tokyo", "Sydney",
]

COUNTRIES = [
    "US", "UK", "CA", "AU", "DE", "FR", "JP", "IN", "BR", "MX",
]

DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "protonmail.com",
    "company.com", "example.org", "test.net", "mail.com",
]

COMPANIES = [
    "TechCorp", "DataFlow Inc", "CloudNine Solutions", "PixelForge",
    "Quantum Labs", "NexGen Systems", "ByteWave", "CodeCraft",
    "InnovateTech", "DigitalPulse", "CyberDyne", "FutureStack",
    "AlphaWorks", "BetaLabs", "GammaCore", "DeltaSoft",
]

JOB_TITLES = [
    "Software Engineer", "Product Manager", "Data Scientist", "Designer",
    "DevOps Engineer", "Marketing Manager", "Sales Director", "CEO",
    "CTO", "Analyst", "Consultant", "Architect", "Lead Developer",
    "QA Engineer", "Project Manager", "Research Scientist",
]


def generate_lorem(paragraphs: int = 3, words_per_para: int = 50) -> str:
    """Generate Lorem Ipsum placeholder text."""
    result = []
    for _ in range(paragraphs):
        words = [random.choice(LOREM_WORDS) for _ in range(words_per_para)]
        words[0] = words[0].capitalize()
        # Add periods at random intervals
        for i in range(len(words)):
            if random.random() < 0.08 and i > 3 and i < len(words) - 2:
                words[i] += "."
                if i + 1 < len(words):
                    words[i + 1] = words[i + 1].capitalize()
        para = " ".join(words)
        if not para.endswith("."):
            para += "."
        result.append(para)
    return "\n\n".join(result)


def generate_name(count: int = 1) -> str:
    """Generate random names."""
    names = [f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}" for _ in range(count)]
    if count == 1:
        return names[0]
    return "\n".join(f"  {i+1}. {n}" for i, n in enumerate(names))


def generate_email(name: str = "") -> str:
    """Generate a random email address."""
    if name:
        parts = name.lower().split()
        local = f"{parts[0]}.{parts[-1]}" if len(parts) > 1 else parts[0]
    else:
        fn = random.choice(FIRST_NAMES).lower()
        ln = random.choice(LAST_NAMES).lower()
        local = random.choice([f"{fn}.{ln}", f"{fn}{ln}", f"{fn[0]}{ln}", f"{fn}_{ln}"])
    domain = random.choice(DOMAINS)
    return f"{local}@{domain}"


def generate_phone() -> str:
    """Generate a random phone number."""
    area = random.randint(200, 999)
    prefix = random.randint(200, 999)
    line = random.randint(1000, 9999)
    return f"+1-{area}-{prefix}-{line}"


def generate_address() -> str:
    """Generate a random address."""
    number = random.randint(1, 9999)
    street = random.choice(STREETS)
    city = random.choice(CITIES)
    state = random.choice(["CA", "NY", "TX", "FL", "WA", "IL", "PA", "OH", "GA", "NC"])
    zip_code = random.randint(10000, 99999)
    return f"{number} {street}, {city}, {state} {zip_code}"


def generate_person() -> dict:
    """Generate a complete fake person profile."""
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    return {
        "name": f"{fn} {ln}",
        "email": generate_email(f"{fn} {ln}"),
        "phone": generate_phone(),
        "address": generate_address(),
        "company": random.choice(COMPANIES),
        "job_title": random.choice(JOB_TITLES),
        "age": random.randint(22, 65),
        "birthday": (datetime.now() - timedelta(days=random.randint(8000, 24000))).strftime("%Y-%m-%d"),
    }


def generate_dataset(count: int = 10, dataset_type: str = "people") -> str:
    """Generate a test dataset."""
    count = min(count, 100)

    if dataset_type == "people":
        data = [generate_person() for _ in range(count)]
    elif dataset_type == "products":
        categories = ["Electronics", "Books", "Clothing", "Food", "Sports", "Home"]
        data = [{
            "id": i + 1,
            "name": f"Product {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Pro', 'Ultra', 'Lite', 'Max'])} {random.randint(100, 999)}",
            "price": round(random.uniform(9.99, 999.99), 2),
            "category": random.choice(categories),
            "in_stock": random.choice([True, True, True, False]),
            "rating": round(random.uniform(1, 5), 1),
        } for i in range(count)]
    elif dataset_type == "transactions":
        data = [{
            "id": i + 1,
            "date": (datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
            "amount": round(random.uniform(1, 5000), 2),
            "type": random.choice(["purchase", "refund", "subscription", "transfer"]),
            "status": random.choice(["completed", "pending", "failed"]),
            "customer": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        } for i in range(count)]
    elif dataset_type == "tasks":
        priorities = ["low", "medium", "high", "critical"]
        statuses = ["todo", "in_progress", "done", "blocked"]
        data = [{
            "id": i + 1,
            "title": f"Task {i + 1}: {random.choice(['Fix', 'Build', 'Update', 'Review', 'Test', 'Deploy', 'Design'])} {random.choice(['feature', 'bug', 'module', 'API', 'UI', 'docs'])}",
            "priority": random.choice(priorities),
            "status": random.choice(statuses),
            "assignee": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES[0])}.",
            "due_date": (datetime.now() + timedelta(days=random.randint(-7, 30))).strftime("%Y-%m-%d"),
        } for i in range(count)]
    else:
        return f"Unknown dataset type: {dataset_type}. Available: people, products, transactions, tasks"

    # Format output
    formatted = json.dumps(data, indent=2, ensure_ascii=False)
    return f"Generated {count} {dataset_type} records:\n\n{formatted[:3000]}" + ("\n..." if len(formatted) > 3000 else "")


def generate_uuid_batch(count: int = 5) -> str:
    """Generate multiple UUIDs."""
    import uuid
    ids = [str(uuid.uuid4()) for _ in range(min(count, 50))]
    return f"UUIDs ({len(ids)}):\n" + "\n".join(f"  {u}" for u in ids)


def generate_password_batch(count: int = 5, length: int = 16) -> str:
    """Generate multiple passwords."""
    import secrets
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    passwords = ["".join(secrets.choice(chars) for _ in range(length)) for _ in range(min(count, 20))]
    return f"Passwords ({len(passwords)}):\n" + "\n".join(f"  {p}" for p in passwords)


def generate_csv_data(rows: int = 20, columns: list = None) -> str:
    """Generate CSV-formatted dummy data."""
    if not columns:
        columns = ["id", "name", "email", "age", "city"]

    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)

    for i in range(min(rows, 100)):
        row = []
        for col in columns:
            if col == "id":
                row.append(str(i + 1))
            elif "name" in col.lower():
                row.append(f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}")
            elif "email" in col.lower():
                row.append(generate_email())
            elif "age" in col.lower():
                row.append(str(random.randint(18, 80)))
            elif "city" in col.lower():
                row.append(random.choice(CITIES))
            elif "phone" in col.lower():
                row.append(generate_phone())
            elif "price" in col.lower() or "amount" in col.lower():
                row.append(f"{random.uniform(1, 1000):.2f}")
            elif "date" in col.lower():
                row.append((datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"))
            elif "bool" in col.lower() or "active" in col.lower():
                row.append(random.choice(["true", "false"]))
            else:
                row.append(f"value_{random.randint(1, 999)}")
        writer.writerow(row)

    return output.getvalue()


# ─── Unified Interface ───────────────────────────────────────
def datagen_operation(operation: str, **kwargs) -> str:
    """Unified data generation interface."""
    ops = {
        "lorem": lambda: generate_lorem(int(kwargs.get("paragraphs", 3)), int(kwargs.get("words", 50))),
        "name": lambda: generate_name(int(kwargs.get("count", 1))),
        "email": lambda: generate_email(kwargs.get("name", "")),
        "phone": lambda: generate_phone(),
        "address": lambda: generate_address(),
        "person": lambda: json.dumps(generate_person(), indent=2),
        "dataset": lambda: generate_dataset(int(kwargs.get("count", 10)), kwargs.get("type", "people")),
        "uuid": lambda: generate_uuid_batch(int(kwargs.get("count", 5))),
        "passwords": lambda: generate_password_batch(int(kwargs.get("count", 5)), int(kwargs.get("length", 16))),
        "csv": lambda: generate_csv_data(int(kwargs.get("rows", 20)), kwargs.get("columns")),
    }
    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown datagen operation: {operation}. Available: {', '.join(ops.keys())}"
