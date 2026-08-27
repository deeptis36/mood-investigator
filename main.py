import os
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
MODEL = "facebook/bart-large-mnli"
HF_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL}"

app = FastAPI(title="Mood Investigator API", version="4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class MoodRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


SITUATIONS = [
    "the person lost or cannot find something important",
    "the person is celebrating a birthday or personal milestone",
    "the person received good news or achieved something",
    "the person experienced a disappointing setback",
    "the person is worried about an uncertain future event",
    "the person is dealing with conflict, unfairness, or someone upsetting them",
    "the person is missing someone or experiencing separation",
    "the person is spending enjoyable time with friends or celebrating socially",
    "the person is expressing affection, gratitude, or love",
    "the person is exhausted or overwhelmed by responsibilities",
    "the person is describing an ordinary situation without a clear emotional event",
]

EMOTIONS = [
    "worry or anxiety", "sadness or disappointment", "happiness or joy",
    "excitement", "anger or frustration", "fear or insecurity", "surprise",
    "relief", "loneliness or longing", "calmness or contentment",
    "mixed or conflicting emotions", "neutral or unclear emotion",
]

EMOTION_META = {
    "worry or anxiety": ("Anxiety / Worry", "😟"),
    "sadness or disappointment": ("Sadness / Disappointment", "😔"),
    "happiness or joy": ("Happiness / Joy", "😊"),
    "excitement": ("Excitement", "🤩"),
    "anger or frustration": ("Anger / Frustration", "😤"),
    "fear or insecurity": ("Fear / Insecurity", "😨"),
    "surprise": ("Surprise", "😲"),
    "relief": ("Relief", "😌"),
    "loneliness or longing": ("Loneliness / Longing", "🥺"),
    "calmness or contentment": ("Calm / Contentment", "😌"),
    "mixed or conflicting emotions": ("Mixed Emotions", "💭"),
    "neutral or unclear emotion": ("Neutral / Unclear", "😐"),
}


def hf_headers():
    token = os.getenv("HF_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="HF_TOKEN is not configured on the server.")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def hf_zero_shot(text, labels, multi_label=False):
    payload = {"inputs": text, "parameters": {"candidate_labels": labels, "multi_label": multi_label}}
    try:
        response = requests.post(HF_URL, headers=hf_headers(), json=payload, timeout=60)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Hugging Face: {exc}")

    if response.status_code != 200:
        try:
            body = response.json()
            message = body.get("error") or body.get("message") or str(body)
        except ValueError:
            message = response.text[:500]
        raise HTTPException(status_code=502, detail=f"Hugging Face returned {response.status_code}: {message}")

    try:
        return response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Hugging Face returned an invalid response.")


def classify_situation(text):
    result = hf_zero_shot(text, SITUATIONS, multi_label=False)
    return result["labels"][0], float(result["scores"][0])


def classify_emotions(text, situation):
    contextual_text = f"Situation understood: {situation}. Original sentence: {text}"
    result = hf_zero_shot(contextual_text, EMOTIONS, multi_label=True)
    return [{"label": label, "score": float(score)}
            for label, score in zip(result["labels"], result["scores"])]


def observation_for(emotion):
    return {
        "worry or anxiety": "The situation itself can create uncertainty or concern, even though the sentence does not explicitly say that you are worried.",
        "sadness or disappointment": "The situation suggests a heavier emotional response, such as loss, disappointment, or feeling low.",
        "happiness or joy": "The situation appears connected with something positive, rewarding, affectionate, or worth celebrating.",
        "excitement": "The situation suggests positive anticipation or high emotional energy.",
        "anger or frustration": "The situation suggests irritation, frustration, conflict, or a sense that something is unfair.",
        "fear or insecurity": "The situation suggests that something feels threatening, uncertain, or unsafe.",
        "surprise": "The situation appears unexpected and carries a noticeable element of surprise.",
        "relief": "The situation suggests that tension may have eased or that something difficult has turned out better than expected.",
        "loneliness or longing": "The situation suggests missing someone, separation, or a desire for connection.",
        "calmness or contentment": "The wording suggests a relatively settled, comfortable, or peaceful emotional state.",
        "mixed or conflicting emotions": "The sentence contains signals that can point in different emotional directions, so one simple feeling may not tell the whole story.",
        "neutral or unclear emotion": "The situation is understandable, but the sentence does not provide enough emotional evidence to confidently identify a strong feeling.",
    }.get(emotion, "The situation contains emotional signals that can be interpreted in more than one way.")


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/app.js")
def javascript():
    return FileResponse(BASE_DIR / "app.js")


@app.get("/health")
def health():
    return {"status": "ok", "ai": "Hugging Face Inference API", "model": MODEL,
            "hf_token_configured": bool(os.getenv("HF_TOKEN"))}


@app.post("/analyze")
def analyze(req: MoodRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please enter some text.")

    situation, situation_confidence = classify_situation(text)
    emotions = classify_emotions(text, situation)
    primary = emotions[0]
    secondary = [x["label"].title() for x in emotions[1:5] if x["score"] >= 0.15]
    if not secondary:
        secondary = ["Context considered"]

    display_name, emoji = EMOTION_META.get(primary["label"], (primary["label"].title(), "💭"))
    confidence = round(min(0.97, max(0.05, 0.55 * primary["score"] + 0.45 * situation_confidence)), 3)

    return {
        "primary_emotion": display_name,
        "emoji": emoji,
        "confidence": confidence,
        "secondary_emotions": secondary,
        "emotions": emotions[:4],
        "situation": situation[0].upper() + situation[1:] + ".",
        "observation": observation_for(primary["label"]),
    }
