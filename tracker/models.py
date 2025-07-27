# tracker/models.py
from django.db import models

class StockAnalysis(models.Model):
    ticker = models.CharField(max_length=10)
    date = models.DateField(auto_now_add=True)
    stock_price = models.FloatField(null=True)
    sentiment = models.CharField(max_length=10)
    polarity_score = models.FloatField(null=True)
    headline = models.TextField()  # store one combined string for now

    def __str__(self):
        return f"{self.ticker} - {self.sentiment} - {self.date}"
