# 🕵️ Mood Investigator

> Tell me what happened. I'll investigate what you might be feeling.

## 💭 What is Mood Investigator?

Mood Investigator is a context-aware AI experiment that analyzes a sentence and tries to understand the **situation behind the words** before interpreting the possible emotions.

It is designed to go beyond simple emotion-word detection.

For example:

> "I have lost my mobile."

The sentence never says *worried*, *sad*, or *anxious*.

But losing something important can naturally suggest:

😟 **Worry / Distress**

Another example:

> "Today is my birthday."

The sentence doesn't explicitly say *happy*, but the context can suggest:

🎉 **Joy / Celebration**

And when a sentence contains conflicting signals:

> "I got the promotion, but I still feel empty."

The investigator should be able to recognize that the situation may contain **mixed emotional signals**.

---

## 🕵️ How It Works

The investigation follows two stages:

```text
Your Sentence
      ↓
Understand the Situation
      ↓
Infer Emotional Signals
      ↓
Primary Emotion
      ↓
Secondary Emotions
      ↓
Confidence + Emotional Signals
      ↓
Investigator's Observation
