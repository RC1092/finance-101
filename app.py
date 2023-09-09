import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")
os.environ["API_KEY"] = "pk_043c576957ed48bfb1910da092155434"
# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    portfolio = db.execute("SELECT * FROM ? WHERE shares != '0';",session["user_name"])
    stocks = []
    shares = []
    prices = []
    total = 0
    row = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])
    cash = row[0]["cash"]
    for i in range(len(portfolio)):
        stocks.append(portfolio[i]["stock_symbol"])
        shares.append(portfolio[i]["shares"])
        current_price = lookup(portfolio[i]["stock_symbol"])
        prices.append(current_price["price"])
        total = total +(current_price["price"]*portfolio[i]["shares"])

    return render_template("index.html", stocks = stocks, shares = shares, prices = prices, length = len(portfolio), total = total, cash = cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please Enter a symbol")
        if not lookup(request.form.get("symbol")):
            return apology("please Enter a valid stock symbol")
        rows = db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])
        cash = rows[0]['cash']
        current_user = db.execute("SELECT username FROM users WHERE id = '1'")
        current_dict = lookup(request.form.get("symbol"))
        current_price = current_dict["price"]
        number_of_shares = float(request.form.get("shares"))

        if "." in request.form.get("shares") or "/" in request.form.get("shares") or "," in request.form.get("shares") or number_of_shares < 0:
            return apology("Number of shares must be a positive integer!")

        if (current_price * number_of_shares) > cash:
            return apology("Not enough cash")
        cash = cash - (current_price * number_of_shares)
        now = datetime.now()

        user_stock = db.execute("SELECT * FROM ? WHERE stock_symbol = ? ",rows[0]['username'],request.form.get("symbol"))
        if not user_stock:
            db.execute("INSERT INTO ? (stock_symbol,shares) VALUES(?,?);",rows[0]['username'],request.form.get("symbol"),int(number_of_shares))
        else:
            db.execute("UPDATE ? SET shares = ? WHERE stock_symbol = ?",rows[0]['username'],user_stock[0]['shares']+int(number_of_shares),request.form.get("symbol"))
        db.execute("UPDATE users SET cash=? WHERE id=?",cash,session["user_id"])
        db.execute("INSERT INTO transactions (user_id,stock_symbol,buying_price,shares,time,balance,type) VALUES(?,?,?,?,?,?,?)",session["user_id"],request.form.get("symbol"),current_price,int(number_of_shares),now,cash,"buy")
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT * FROM TRANSACTIONS WHERE user_id = ?",session["user_id"])

    return render_template("history.html",history=history,length=len(history))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["user_name"] = request.form.get("username")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please Enter a symbol")
        if not lookup(request.form.get("symbol")):
            return apology("please Enter a valid stock symbol")
        quote_val = lookup(request.form.get("symbol"))
        return render_template("quoted.html",price=usd(quote_val["price"]),symbol=request.form.get("symbol"))
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Please enter your Username.")

        ids = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if request.form.get("username") in ids:
            return apology("Username already taken!")

        if not request.form.get("password"):
            return apology("Please enter your Password.")

        if not request.form.get("confirmation"):
            return apology("Please confirm your Password.")

        if request.form.get("password") != request.form.get("confirmation"):
         return apology("Passwords dont match!")

        Pass_hash = generate_password_hash(request.form.get("password"))

        db.execute("INSERT INTO users (username,hash) VALUES(?,?);",request.form.get("username"),Pass_hash)
        db.execute("CREATE TABLE ? (id INTEGER,stock_symbol TEXT,shares INT,PRIMARY KEY(id))",request.form.get("username"))
        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        rows = db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])
        stock_info = db.execute("SELECT stock_symbol,shares FROM ? WHERE stock_symbol = ?",rows[0]["username"],request.form.get("symbol"))
        if not stock_info:
            return apology("The user does not own any shares of this stock")
        if int(request.form.get("shares")) > int(stock_info[0]["shares"]) or stock_info[0]["shares"] < 0 :
            return apology("The user does not own enough shares")

        current_dict = lookup(request.form.get("symbol"))
        current_price = float(current_dict["price"])
        cash = rows[0]["cash"] + (current_price*float(request.form.get("shares")))
        now = datetime.now()

        if stock_info[0]['shares'] - int(request.form.get("shares")) > 0:
            db.execute("UPDATE ? SET shares = ? WHERE stock_symbol = ?",rows[0]['username'],stock_info[0]['shares']-int(request.form.get("shares")),request.form.get("symbol"))
        else:
            db.execute("DELETE FROM ? WHERE stock_symbol = ?",rows[0]['username'],request.form.get("symbol"))

        db.execute("UPDATE users SET cash=? WHERE id=?",cash,session["user_id"])
        db.execute("INSERT INTO transactions (user_id,stock_symbol,buying_price,shares,time,balance,type) VALUES(?,?,?,?,?,?,?)",session["user_id"],request.form.get("symbol"),current_price,request.form.get("shares"),now,cash,"sell")

        return redirect("/")
    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
