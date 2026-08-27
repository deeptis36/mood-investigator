from pathlib import Path
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

MODEL_NAME = "MoritzLaurer/deberta-v3-base-zeroshot-v1.1-all-33"
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Mood Investigator — Context AI", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class MoodRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


EMOTIONS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]
EMOTION_NAMES = {"anger":"Anger","disgust":"Disgust","fear":"Fear","joy":"Joy","neutral":"Neutral","sadness":"Sadness","surprise":"Surprise"}
EMOTION_EMOJI = {"anger":"😡","disgust":"🤢","fear":"😨","joy":"😀","neutral":"😐","sadness":"😔","surprise":"😲"}

# Situation candidates deliberately include context that can imply an emotion
# without using an explicit emotion word.
SITUATIONS = [
    "something important has been lost or cannot be found",
    "something important has gone wrong unexpectedly",
    "the person is facing an uncertain or worrying situation",
    "the person is celebrating a birthday or a personal milestone",
    "the person received good news or achieved something",
    "the person received bad news or experienced a setback",
    "the person is dealing with conflict or unfair treatment",
    "the person is waiting for an important outcome",
    "the person is missing someone or experiencing separation",
    "the person is expressing gratitude or affection",
    "the person is describing an ordinary situation without a clear emotional event",
]

SITUATION_TO_SECONDARY = {
    "something important has been lost or cannot be found": ["Worry", "Distress"],
    "something important has gone wrong unexpectedly": ["Frustration", "Distress"],
    "the person is facing an uncertain or worrying situation": ["Worry", "Unease"],
    "the person is celebrating a birthday or a personal milestone": ["Happiness", "Celebration"],
    "the person received good news or achieved something": ["Happiness", "Excitement"],
    "the person received bad news or experienced a setback": ["Disappointment", "Sadness"],
    "the person is dealing with conflict or unfair treatment": ["Frustration", "Resentment"],
    "the person is waiting for an important outcome": ["Anticipation", "Uncertainty"],
    "the person is missing someone or experiencing separation": ["Longing", "Sadness"],
    "the person is expressing gratitude or affection": ["Warmth", "Happiness"],
    "the person is describing an ordinary situation without a clear emotional event": ["Reflection"],
}


@lru_cache(maxsize=1)
def get_classifier():
    from transformers import pipeline
    return pipeline("zero-shot-classification", model=MODEL_NAME)


def classify(classifier, text, labels):
    result = classifier(
        text,
        candidate_labels=labels,
        multi_label=True,
        hypothesis_template="This text is about {}."
    )
    return list(zip(result["labels"], result["scores"]))


def infer_emotions(classifier, text, situation):
    # Give the model the inferred context as part of the hypothesis.
    labels = [f"the person is experiencing {e}" for e in EMOTIONS]
    result = classifier(
        f"The situation described is: {situation}. Original text: {text}",
        candidate_labels=labels,
        multi_label=True,
        hypothesis_template="This suggests that {}."
    )
    scores = []
    for label, score in zip(result["labels"], result["scores"]):
        emotion = next((e for e in EMOTIONS if f"experiencing {e}" in label), label)
        scores.append({"label": emotion, "score": float(score)})
    return sorted(scores, key=lambda x: x["score"], reverse=True)


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/app.js")
def javascript():
    return FileResponse(BASE_DIR / "app.js")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/analyze")
def analyze(req: MoodRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please enter some text.")

    try:
        classifier = get_classifier()

        # Stage 1: understand the situation.
        situation_scores = classify(classifier, text, SITUATIONS)
        situation = situation_scores[0][0]
        situation_confidence = float(situation_scores[0][1])

        # Stage 2: infer emotions from the understood situation + original text.
        emotions = infer_emotions(classifier, text, situation)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"AI model could not analyze the text: {exc}"
        )

    primary = emotions[0]
    secondary = list(SITUATION_TO_SECONDARY.get(situation, []))

    # Add strong secondary model emotions without pretending every feeling is certain.
    for item in emotions[1:3]:
        if item["score"] >= 0.15:
            label = EMOTION_NAMES[item["label"]]
            if label not in secondary:
                secondary.append(label)

    # Confidence is intentionally conservative: both context understanding
    # and emotional inference need to agree.
    confidence = min(0.97, max(0.05, 0.55 * primary["score"] + 0.45 * situation_confidence))

    observation = {
        "anger": "The situation appears to be creating irritation, frustration, or a sense of unfairness.",
        "disgust": "The situation appears to be creating a strong sense of aversion or dislike.",
        "fear": "The situation appears to involve uncertainty, threat, or worry.",
        "joy": "The situation appears connected to something positive, rewarding, or worth celebrating.",
        "neutral": "The text describes a situation without a strong emotional signal being detected.",
        "sadness": "The situation appears connected to loss, disappointment, separation, or a heavier emotional state.",
        "surprise": "The situation appears unexpected and carries a noticeable surprise response.",
    }.get(primary["label"], "Several emotional signals appear to be present.")

    return {
        "primary_emotion": EMOTION_NAMES.get(primary["label"], primary["label"].title()),
        "emoji": EMOTION_EMOJI.get(primary["label"], "💭"),
        "confidence": confidence,
        "secondary_emotions": secondary[:5],
        "emotions": emotions[:4],
        "situation": situation[0].upper() + situation[1:] + ".",
        "observation": observation,
        "model": MODEL_NAME,
    }
