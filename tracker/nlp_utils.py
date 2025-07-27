from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

labels = ['Negative', 'Neutral', 'Positive']

def analyze_financial_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    outputs = model(**inputs)
    probs = F.softmax(outputs.logits, dim=1)
    predicted_class = torch.argmax(probs).item()
    sentiment = labels[predicted_class]
    confidence = probs[0][predicted_class].item()
    return sentiment, confidence
