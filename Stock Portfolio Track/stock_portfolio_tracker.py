import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import simpledialog, messagebox
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import json
import os

# ----------- CONFIG -----------
NEWS_API_KEY = "a585d881b76c4ea4b6d467366cc6a80a"  # <-- Replace with your NewsAPI key
FILENAME = "portfolio.json"

# ----------- GLOBALS -----------
portfolio = {}

# ----------- FUNCTIONS -----------

def save_portfolio():
    try:
        with open(FILENAME, "w") as f:
            json.dump(portfolio, f)
        messagebox.showinfo("Save", "Portfolio saved successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save portfolio:\n{e}")

def load_portfolio():
    global portfolio
    if os.path.exists(FILENAME):
        try:
            with open(FILENAME, "r") as f:
                portfolio = json.load(f)
            update_display()
            messagebox.showinfo("Load", "Portfolio loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load portfolio:\n{e}")
    else:
        messagebox.showinfo("Load", "No saved portfolio found.")

def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'].iloc[-1]
        return round(price, 2)
    except Exception as e:
        messagebox.showerror("Error", f"Could not fetch data for {ticker}:\n{e}")
        return None

def get_day_high_low(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if data.empty:
            return None, None
        high = data['High'].iloc[-1]
        low = data['Low'].iloc[-1]
        return round(high, 2), round(low, 2)
    except Exception:
        return None, None

def get_usd_to_inr():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url)
        data = response.json()
        return data['rates'].get('INR', None)
    except Exception:
        return None

def fetch_news(ticker):
    if NEWS_API_KEY == "YOUR_NEWSAPI_KEY_HERE":
        return ["Please set your NewsAPI key in the code to get news."]
    try:
        url = ("https://newsapi.org/v2/everything?"
               f"q={ticker}&"
               "sortBy=publishedAt&"
               "language=en&"
               "pageSize=5&"
               f"apiKey={NEWS_API_KEY}")
        response = requests.get(url)
        news_data = response.json()
        if news_data.get("status") != "ok":
            return ["Failed to fetch news."]
        articles = news_data.get("articles", [])
        headlines = [f"- {a['title']}" for a in articles]
        if not headlines:
            return ["No recent news found."]
        return headlines
    except Exception:
        return ["Error fetching news."]

def update_display():
    for row in tree.get_children():
        tree.delete(row)

    total_investment = total_value = 0
    values_for_pie = []

    for symbol, data in portfolio.items():
        price = get_stock_price(symbol)
        if price is None:
            continue
        shares = data['shares']
        cost = data['buy_price']
        current_value = shares * price
        investment = shares * cost
        profit_loss = current_value - investment

        total_investment += investment
        total_value += current_value
        values_for_pie.append((symbol, current_value))

        tree.insert("", "end", values=(
            symbol.upper(), shares, cost, price, round(current_value, 2), round(profit_loss, 2)
        ))

    summary_label.config(text=f"Total Investment: ${total_investment:.2f} | "
                              f"Current Value: ${total_value:.2f} | "
                              f"Net Gain/Loss: ${total_value - total_investment:.2f}")

    draw_pie_chart(values_for_pie)
    update_exchange_rate()

def add_stock():
    symbol = simpledialog.askstring("Stock Symbol", "Enter stock symbol (e.g. AAPL):")
    if not symbol:
        return
    try:
        shares = float(simpledialog.askstring("Shares", "Enter number of shares:"))
        buy_price = float(simpledialog.askstring("Buy Price", "Enter buy price:"))
    except (TypeError, ValueError):
        messagebox.showerror("Error", "Invalid input")
        return

    portfolio[symbol.upper()] = {'shares': shares, 'buy_price': buy_price}
    update_display()
    save_portfolio()  # auto-save on change

def remove_stock():
    selected = tree.selection()
    if not selected:
        messagebox.showinfo("Remove", "No stock selected.")
        return
    for item in selected:
        symbol = tree.item(item, 'values')[0]
        if symbol in portfolio:
            del portfolio[symbol]
    update_display()
    clear_chart()
    news_list.delete(0, tk.END)
    save_portfolio()  # auto-save on change

def toggle_theme():
    current = root.style.theme.name
    new_theme = "darkly" if current != "darkly" else "flatly"
    root.style.theme_use(new_theme)

def draw_pie_chart(values):
    pie_ax.clear()
    if not values:
        pie_ax.text(0.5, 0.5, "No data", horizontalalignment='center', verticalalignment='center')
        pie_canvas.draw()
        return

    labels, sizes = zip(*values)
    pie_ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    pie_ax.set_title("Portfolio Distribution")
    pie_canvas.draw()

def plot_historical_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="6mo")  # last 6 months
        if hist.empty:
            messagebox.showinfo("Info", f"No historical data for {symbol}")
            return
        dates = hist.index
        prices = hist['Close']

        chart_ax.clear()
        chart_ax.plot(dates, prices, label=symbol.upper())
        chart_ax.set_title(f"Historical Close Prices: {symbol.upper()} (6 months)")
        chart_ax.set_xlabel("Date")
        chart_ax.set_ylabel("Price ($)")
        chart_ax.legend()
        chart_ax.grid(True)
        chart_canvas.draw()

        # Also update day high/low labels
        high, low = get_day_high_low(symbol)
        if high is not None and low is not None:
            day_high_label.config(text=f"Day High: ${high}")
            day_low_label.config(text=f"Day Low: ${low}")
        else:
            day_high_label.config(text="Day High: N/A")
            day_low_label.config(text="Day Low: N/A")

        # Update news list
        news_list.delete(0, tk.END)
        news = fetch_news(symbol)
        for headline in news:
            news_list.insert(tk.END, headline)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to get historical data:\n{e}")

def on_stock_select(event):
    selected = tree.selection()
    if selected:
        symbol = tree.item(selected[0], 'values')[0]
        plot_historical_price(symbol)

def clear_chart():
    chart_ax.clear()
    chart_ax.text(0.5, 0.5, "Select a stock to view chart", horizontalalignment='center', verticalalignment='center')
    chart_canvas.draw()
    day_high_label.config(text="Day High: N/A")
    day_low_label.config(text="Day Low: N/A")
    news_list.delete(0, tk.END)

def update_exchange_rate():
    rate = get_usd_to_inr()
    if rate:
        exchange_rate_label.config(text=f"USD to INR: {rate:.2f}")
    else:
        exchange_rate_label.config(text="USD to INR: N/A")

# ----------- GUI SETUP -----------
root = tb.Window(themename="flatly")
root.title("Stock Portfolio Tracker with News, Exchange Rate, and High/Low")
root.geometry("1150x720")

btn_frame = tb.Frame(root)
btn_frame.pack(pady=10)

tb.Button(btn_frame, text="Add Stock", command=add_stock, bootstyle="success").grid(row=0, column=0, padx=5)
tb.Button(btn_frame, text="Remove Selected", command=remove_stock, bootstyle="danger").grid(row=0, column=1, padx=5)
tb.Button(btn_frame, text="Toggle Theme", command=toggle_theme, bootstyle="info").grid(row=0, column=2, padx=5)
tb.Button(btn_frame, text="Save Portfolio", command=save_portfolio, bootstyle="primary").grid(row=0, column=3, padx=5)
tb.Button(btn_frame, text="Load Portfolio", command=load_portfolio, bootstyle="secondary").grid(row=0, column=4, padx=5)

columns = ("Symbol", "Shares", "Buy Price", "Current Price", "Current Value", "Profit/Loss")
tree = tb.Treeview(root, columns=columns, show="headings", height=10, bootstyle="primary")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, anchor="center", width=140)
tree.pack(padx=10, fill='x')
tree.bind("<<TreeviewSelect>>", on_stock_select)

summary_label = tb.Label(root, text="", font=("Arial", 12))
summary_label.pack(pady=5)

# Exchange rate label
exchange_rate_label = tb.Label(root, text="USD to INR: Loading...", font=("Arial", 11))
exchange_rate_label.pack(pady=2)

# Chart and Pie chart area
fig, (chart_ax, pie_ax) = plt.subplots(1, 2, figsize=(10,4))
fig.tight_layout(pad=4)

chart_canvas = FigureCanvasTkAgg(fig, master=root)
chart_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)

# Day High/Low labels below chart
hl_frame = tb.Frame(root)
hl_frame.pack(pady=5)
day_high_label = tb.Label(hl_frame, text="Day High: N/A", font=("Arial", 11))
day_high_label.grid(row=0, column=0, padx=20)
day_low_label = tb.Label(hl_frame, text="Day Low: N/A", font=("Arial", 11))
day_low_label.grid(row=0, column=1, padx=20)

pie_canvas = FigureCanvasTkAgg(fig, master=root)  # pie chart shares fig with chart_ax (handled in draw_pie_chart)

# News listbox (using tkinter Listbox)
news_frame = tb.LabelFrame(root, text="Latest News", padding=10)
news_frame.pack(padx=10, pady=10, fill='both', expand=False)

news_list = tk.Listbox(news_frame, height=6, font=("Arial", 10))
news_list.pack(fill='both', expand=True)

clear_chart()
load_portfolio()
update_display()

root.mainloop()
