from flask import Flask,render_template, url_for
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/view')
def view():
    return render_template('view.html')

@app.route('/review')
def review():
    return render_template('review.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/sign')
def sign():
    return render_template('sign.html')

@app.route('/log')
def log():
    return render_template('log.html')

@app.route('/detailed')
def detailed():
    return render_template('detailed.html')

@app.route('/add')
def add():
    return render_template('add_rev.html')

if __name__ == "__main__":
    app.run(debug=True)
