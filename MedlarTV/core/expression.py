import random
from MedlarTV.core.memory import load_memory
from MedlarTV.core.context import get_contextual_mix

VOCAB = {
    "hype": ["LET'S GOOO!!!", "We're SO back!", "🔥🔥🔥", "WOO!!"],
    "chill": ["just vibin'", "easy breezy", "coolin'", "smooth vibes"],
    "snarky": ["lol", "sure thing", "bruh", "🤨"],
    "supportive": ["you got this", "keep shining", "nice work", "💖"]
}

def blended_phrase():
    """Return a tone phrase mixed by memory and recent context."""
    data = load_memory()
    moods = data["personality_memory"]["mood_weights"]
    total = sum(moods.values()) or 1
    ratios = {m: moods.get(m, 0) / total for m in ["hype", "chill", "snarky", "supportive"]}

    # contextual adjustment
    context = get_contextual_mix()
    for m in ratios:
        ratios[m] = (ratios[m] + context[m]) / 2

    # make sure the pool always exists
    pool = []
    for m, w in ratios.items():
        count = int(w * 10) or 1
        pool.extend([m] * count)

    # just in case
    if not pool:
        pool = ["chill"]

    chosen = random.choice(pool)
    word = random.choice(VOCAB[chosen])
    return word