from flask import Flask,render_template, url_for,request, redirect
from flask_sqlalchemy import SQLAlchemy
import requests
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from tqdm.notebook import tqdm
sia = SentimentIntensityAnalyzer()
from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer("english")
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os

amzon_df = pickle.load(open("artifacts/table.pkl","rb"))

def tokenize_stem(text):
    tokens = nltk.word_tokenize(text.lower())
    stem = [stemmer.stem(w) for w in tokens]
    return " ".join(stem)


tfidvectorizer = TfidfVectorizer(tokenizer=tokenize_stem)

def cosine_sim(txt1,txt2):
    tfid_matrix = tfidvectorizer.fit_transform([txt1,txt2])
    return cosine_similarity(tfid_matrix)[0][1]

def search_product(query):
    stemmed_query = tokenize_stem(query)
    #calcualting cosine similarity between query and stemmed tokens columns
    amzon_df['similarity'] = amzon_df['stemmed_tokens'].apply(lambda x:cosine_sim(stemmed_query,x))
    res = amzon_df.sort_values(by=['similarity'],ascending=False).head(10)[['Title','Description','Category']]
    return res

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///revanalysis.db'
db = SQLAlchemy(app)
app.app_context().push()
with app.app_context():
    db.create_all()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asin = db.Column(db.String(20), nullable=False)
    uid = db.Column(db.Integer,nullable=False)
    title = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    price= db.Column(db.Integer, nullable=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    perc5 = db.Column(db.Integer, nullable=True)
    perc4 = db.Column(db.Integer, nullable=True)
    perc3 = db.Column(db.Integer, nullable=True)
    perc2 = db.Column(db.Integer, nullable=True)
    perc1 = db.Column(db.Integer, nullable=True)
    reviews_count = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return '<Product %r>' % self.id

class Reviews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asin = db.Column(db.String(20), nullable=False)
    author = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.String(500), nullable=False)
    sentiment = db.Column(db.Integer)

    def __repr__(self):
        return '<Reviews %r>' % self.id
    
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(30),nullable=False)
    password = db.Column(db.String(20), nullable=False)
    def __repr__(self):
        return '<Users %r>' % self.id


def get_rev(asin):
    payload = {
    'source': 'amazon_reviews',
    'domain': 'in',
    'pages' : "3",
    'query': asin,
    'parse': True,
    }
    response = requests.request(
    'POST',
    'https://realtime.oxylabs.io/v1/queries',
    auth=('iwpproject', 'CyrVasAnu1234'), #Your credentials go here
    json=payload,
    )
    abc = response.json()['results'][0]['content']['reviews']
    return (abc)

def get_prod(asin):
    payload = {
    'source': 'amazon_product',
    'domain': 'in',
    'query': asin,
    'parse': True,
    }
    response = requests.request(
    'POST',
    'https://realtime.oxylabs.io/v1/queries',
    auth=('iwpproject', 'CyrVasAnu1234'), #Your credentials go here
    json=payload,
    )
    abc = response.json()['results'][0]['content']
    return (abc)

IMG_FOLDER = os.path.join("static", "IMG")
app.config["UPLOAD_FOLDER"] = IMG_FOLDER

@app.route('/')
def index():
    bg_vid = os.path.join(app.config["UPLOAD_FOLDER"], "bg_video.mp4")
    return render_template('index.html',vid = bg_vid)


@app.route('/sign',  methods = ['POST','GET'])
def sign():
    bg_vid = os.path.join(app.config["UPLOAD_FOLDER"], "bg1_vid.mp4")
    if request.method == "POST":
        uname = request.form.get("username")
        email = request.form.get("email")
        passw = request.form.get("password")
        rpassw = request.form.get("rpassword")
        try:
            user = Users.query.filter_by(email=email).one()
            if(user):
                return render_template("sign.html",vid = bg_vid,alert1 = "User with same email already exists")
        except:
            if passw==rpassw:
                new_row = Users(username=uname,email=email,password=passw)
                db.session.add(new_row)
                db.session.commit()
                print("user added")
                return redirect("/log")
            else:
                return render_template("sign.html",vid = bg_vid,alert1 = "passwords do not match")
    return render_template('sign.html',vid = bg_vid,alert1="")

@app.route('/log', methods = ['POST','GET'])
def log():
    bg_vid = os.path.join(app.config["UPLOAD_FOLDER"], "bg1_vid.mp4")
    if request.method == "POST":
        mail = request.form.get("email")
        passw = request.form.get("password")
        try:
            user = Users.query.filter_by(email=mail).one()
            if(user.password==passw):
                return redirect("/home/"+str(user.id))
            else:
                return render_template("log.html",vid = bg_vid,alert1 = "wrong password",alert2="")
        except:
            return render_template("log.html",vid = bg_vid,alert1="",alert2 = "no such email found")
    return render_template("log.html",vid = bg_vid,alert1="",alert2 = "")

@app.route('/home/<int:user>', methods=["POST","GET"])
def home(user):
    products = Product.query.filter_by(uid=user).all()
    return render_template('home.html',user=user, products=products)


@app.route('/view/<int:user>/<string:asin>', methods = ['POST','GET'])
def view(user,asin):
    product = Product.query.filter_by(uid = user, asin=asin).one()
    print(product)
    recc = search_product(product.title)
    return render_template('view.html',user=user, product=product,recommended = recc[:5]['Title'])

# @app.route('/review/<int:user>/<string:asin>', methods = ['POST','GET'])
# def review(user, asin):
#     product = Product.query.filter_by(asin=asin).one()
#     reviews = Reviews.query.order_by(Reviews.sentiment).filter_by(asin=asin).all()
#     return render_template('review.html',user=user, product=product, reviews=reviews)

@app.route('/delete/<int:user>/<int:id>', methods = ['POST','GET'])
def delete(user,id):
    prod_to_delete = Product.query.get_or_404(id)
    # print(prod_to_delete.asin)
    sin = prod_to_delete.asin
    revs_to_delete = Reviews.query.filter_by(asin=sin).all()
    print(revs_to_delete)
    try:
        
        db.session.delete(prod_to_delete)
        for a in revs_to_delete:
            # print(a)
            db.session.delete(a)   
        db.session.commit()
        return redirect('/home/'+str(user))
    except:
        return 'There was a problem deleting that task'

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/detailed/<int:user>/<string:asin>')
def detailed(user,asin):
    product = Product.query.filter_by(uid = user, asin=asin).one()
    reviews = Reviews.query.order_by(Reviews.sentiment.desc()).filter_by(asin=asin).all()
    return render_template('detailed.html',user=user,product=product, reviews=reviews)

@app.route('/add/<int:user>', methods = ['POST','GET'])
def add(user):
    if request.method == "POST":
        asin = request.form.get("productASIN")
        prod = get_prod(asin)
        title = prod['title']
        desc = prod['description']
        image = prod['images'][0]
        rating = prod['rating']
        price= prod['price_upper']
        manufacturer = prod['manufacturer']
        perc5 = prod['rating_stars_distribution'][0]['percentage']
        perc4 = prod['rating_stars_distribution'][1]['percentage']
        perc3 = prod['rating_stars_distribution'][2]['percentage']
        perc2 = prod['rating_stars_distribution'][3]['percentage']
        perc1 = prod['rating_stars_distribution'][4]['percentage']
        reviews_count = prod['reviews_count']
        new_row1 = Product(asin = asin,uid=user,title=title,desc=desc,image=image,rating=rating,price=price,manufacturer=manufacturer,perc5=perc5,perc4=perc4,perc3=perc3,perc2=perc2,perc1=perc1,reviews_count=reviews_count)
        db.session.add(new_row1)
        revs = get_rev(asin)
        for a in revs:
            author = a['author']
            rating = a['rating']
            review = a['content']
            sentiment = sia.polarity_scores(review)['compound']
            new_row2 = Reviews(asin = asin,author=author, rating = rating, review = review,sentiment=sentiment)
            db.session.add(new_row2)
            db.session.commit()
        return redirect('/home/'+str(user))
        
    return render_template('add_rev.html')

if __name__ == "__main__":
    app.run(debug=True)