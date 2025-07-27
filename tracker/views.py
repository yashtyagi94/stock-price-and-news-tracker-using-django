import requests
from django.shortcuts import render
from .nlp_utils import analyze_financial_sentiment
import yfinance as yf
import plotly.graph_objs as go
from plotly.offline import plot
import pandas as pd
from django.http import HttpResponse
from .models import StockAnalysis
from decouple import config

# Map tickers to possible company name mentions
TICKER_COMPANY_MAP = {
    'AAPL': ['Apple'],
    'GOOGL': ['Google', 'Alphabet'],
    'MSFT': ['Microsoft'],
    'AMZN': ['Amazon'],
    'TSLA': ['Tesla'],
    'META': ['Facebook', 'Meta'],
}

# Common finance-related keywords
FINANCE_KEYWORDS = [
    'stock', 'shares', 'market', 'price', 'exchange', 'trading',
    'investor', 'investment', 'financial', 'earnings', 'profit', 'loss',
    'ipo', 'dividend', 'forecast', 'revenue', 'NASDAQ', 'NYSE', 'index',
    'quarter', 'buy', 'sell', 'portfolio'
]

# def analyze_sentiment(text):
#     blob = TextBlob(text)
#     polarity = blob.sentiment.polarity
#     if polarity > 0.1:
#         return "Positive", polarity
#     elif polarity < -0.1:
#         return "Negative", polarity
#     else:
#         return "Neutral", polarity


def home(request):
    ticker = ''
    sentiment = ''
    polarity_score = None
    headlines = []
    chart_html = None
    stock_price = None
    sentiment_chart = None

    if request.method == 'POST':
        ticker = request.POST.get('ticker', '').upper()
        company_aliases = TICKER_COMPANY_MAP.get(ticker, [ticker])

        if ticker:
            try:
                stock = yf.Ticker(ticker)
                stock_price = stock.history(period="1d")['Close'].iloc[-1]
                stock_price = round(stock_price, 2)
            except Exception as e:
                stock_price = "N/A"

            api_key = config('NEWS_API_KEY')
            url = f'https://newsdata.io/api/1/news?apikey={api_key}&q={ticker}&language=en'

            response = requests.get(url)
            data = response.json()

            if data.get('results'):
                all_headlines = [article['title'] for article in data['results']]

                def is_relevant(title):
                    title_lower = title.lower()
                    mentions_company = any(name.lower() in title_lower for name in company_aliases)
                    mentions_finance = any(word in title_lower for word in FINANCE_KEYWORDS)
                    return mentions_company and mentions_finance

                filtered_headlines = [t for t in all_headlines if is_relevant(t)]
                seen = set()
                unique_headlines = []
                for h in filtered_headlines:
                    h_norm = h.strip().lower()
                    if h_norm not in seen:
                        seen.add(h_norm)
                        unique_headlines.append(h)
                headlines = unique_headlines

                if headlines:
                    combined_text = " ".join(headlines)
                    sentiment, score = analyze_financial_sentiment(combined_text)
                    polarity_score = score 
                else:
                    sentiment = "No finance-related news found."
            else:
                sentiment = "No news found for this ticker."
            
            try:
                hist = stock.history(period="1mo") 
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Close Price'))
                fig.update_layout(title=f"{ticker} - 1 Month Price", xaxis_title='Date', yaxis_title='Price (USD)')
                chart_html = plot(fig, output_type='div')
            except Exception as e:
                chart_html = None
                
            try:
                dates = pd.date_range(end=pd.Timestamp.today(), periods=10)
                scores = [0.2, 0.1, -0.1, 0.3, 0.0, -0.2, 0.15, 0.4, 0.1, 0.05]

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=dates, y=scores, mode='lines+markers', name='Sentiment'))
                fig.update_layout(title='Historical Sentiment', xaxis_title='Date', yaxis_title='Sentiment Score')
                sentiment_chart = plot(fig, output_type='div')

            except Exception as e:
                sentiment_chart = None
    if headlines:
        # Save a single record with all relevant data
        StockAnalysis.objects.create(
            ticker=ticker,
            stock_price=stock_price if isinstance(stock_price, (float, int)) else None,
            sentiment=sentiment,
            polarity_score=polarity_score,
            headline="\n".join(headlines)
        )

        
    return render(request, 'tracker/home.html', {
        'ticker': ticker,
        'sentiment': sentiment,
        'polarity_score': polarity_score,
        'headlines': headlines,
        'stock_price': stock_price,
        'chart_html': chart_html,
        'sentiment_chart': sentiment_chart,
    })

import csv
from io import BytesIO, StringIO
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def download_csv(request):
    headlines = request.GET.getlist('headlines', [])
    sentiment = request.GET.get('sentiment', 'N/A')
    polarity = request.GET.get('polarity', 'N/A')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sentiment_data.csv"'

    writer = csv.writer(response)
    writer.writerow(['Headline', 'Sentiment', 'Polarity Score'])
    for h in headlines:
        writer.writerow([h, sentiment, polarity])

    return response

def download_pdf(request):
    headlines = request.GET.getlist('headlines', [])
    sentiment = request.GET.get('sentiment', 'N/A')
    polarity = request.GET.get('polarity', 'N/A')

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Sentiment Report")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Sentiment: {sentiment}")
    y -= 20
    p.drawString(50, y, f"Polarity Score: {polarity}")
    y -= 30

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Headlines:")
    y -= 20

    p.setFont("Helvetica", 10)
    for headline in headlines:
        if y < 40:
            p.showPage()
            y = height - 40
        p.drawString(60, y, f"- {headline}")
        y -= 15

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="sentiment_report.pdf")
