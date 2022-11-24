from flask import Flask,render_template,flash,redirect,url_for,session,request,logging,send_from_directory
from wtforms import Form,StringField,TextAreaField,PasswordField,validators,SelectField,FileField,SubmitField
from passlib.hash import sha256_crypt
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask_uploads import IMAGES, UploadSet, configure_uploads
from werkzeug.utils import secure_filename
from sqlalchemy.orm import relationship
from sqlalchemy import desc

db=SQLAlchemy()

app = Flask(__name__)
app.secret_key="venus"
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:////Workspaces/Python/Project/venus.db'
db.init_app(app)

UPLOAD_FOLDER = '/Workspaces/Python/Project/static/images/ProductImages'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = "VENUS123"
app.config['UPLOADED_PHOTOS_DEST'] = os.getcwd()
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(func):
    @wraps(func)
    def decorator_function(*args,**kwargs):
        if "logged_in" in session:
            return func(*args,**kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","warning")
            return redirect(url_for("login"))
    return decorator_function

def admin_required(func):
    @wraps(func)
    def decorator_function(*args,**kwargs):
        if "role_id" in session:
            if(session["role_id"]==1):
                return func(*args,**kwargs)
            else:
                flash("Bu sayfayı görüntülemek için yetkiniz yok.","warning")
                return redirect(url_for("index"))
    return decorator_function

class RegisterForm(Form):
    name=StringField("Ad",validators=[validators.Length(min=2, max=30)])
    surname=StringField("Soyad",validators=[validators.Length(min=2, max=30)])
    email = StringField("E posta",validators=[validators.email(message="Geçerli bir email adresi giriniz!")])
    password = PasswordField("Parola",validators=[
        validators.DataRequired("Lütfen bir parola belileyin."),
        validators.EqualTo(fieldname="confirm",message="Parolanız Uyuşmuyor"),
        validators.length(min=4)
    ])
    confirm=PasswordField("Parola Doğrula")

class LoginForm(Form):
    email=StringField("Eposta Adresi")
    password=PasswordField("Parola")
    
class CategoryForm(Form):
    name=StringField("Kategori Adı",validators=[validators.Length(min=2, max=30)])

class AdminForm(Form):
    name=StringField("Kullanıcı Adı",validators=[validators.Length(min=2, max=60)])

class AccountUpdateForm(Form):
    name=StringField("Ad",validators=[validators.Length(min=2, max=30)])
    surname=StringField("Soyad",validators=[validators.Length(min=2, max=30)])
    email = StringField("E posta",validators=[validators.email(message="Geçerli bir email adresi giriniz!")])
    password = PasswordField("Parola",validators=[validators.EqualTo(fieldname="confirm",message="Parolanız Uyuşmuyor")])
    confirm=PasswordField("Parola Doğrula")
        
class AddProductForm(Form):
    name=StringField("Ürün Adı",validators=[validators.Length(min=2, max=100)])
    code=StringField("Ürün Kodu")
    color=StringField("Renk")
    category = SelectField("Kategori", choices=[])
    description=TextAreaField("Ürün Açıklaması",validators=[validators.Length(max=500)])
    photoPath= StringField("Ürün Fotoğrafı")

def getCategories(pageName, Form = None, Name = ""):
    categories=Categories.query.all()
    if(Form !=None):
        return render_template(pageName + ".html", categories=categories, form=Form, name = Name)
    else:
        return render_template(pageName + ".html", categories=categories, name = Name)

@app.route("/")
def index():
    categories=Categories.query.all()
    productList = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).order_by(Products.UpdateDate.desc()).all()
    if (productList == None):
        flash("Buralar ıssız. Ürünler en yakın zamanda yüklenecektir.","danger")
    else:
        return render_template("index.html", categories=categories, productList=productList)

@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if(request.method=="POST" and form.validate()):
        newUser = Users(Name=form.name.data, Surname=form.surname.data, Email=form.email.data, Password=sha256_crypt.encrypt(form.password.data), BirthdayDate=None, StartedDate=datetime.now(), RoleID=2)
        db.session.add(newUser)
        db.session.commit()
        flash("Başarıyla kayıt oldunuz...","success")
        return redirect(url_for("login"))
    else:
        return getCategories("register",form)

@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    if(request.method=="POST"):
        email=form.email.data
        password = form.password.data
        query=Users.query.filter_by(Email=email).first()

        if query != None:
            if sha256_crypt.verify(password,query.Password):
                flash("Başarılı giriş yaptınız..","success")
                session["logged_in"] = True
                session["user_id"] = query.ID
                session["email"] = query.Email
                session["name"] = query.Name
                session["surname"] = query.Surname
                session["role_id"] = query.RoleID
                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor!","danger")
            return redirect(url_for("login"))

    return getCategories("login",form)

@app.route("/userroles",methods=["GET","POST"])
@login_required
@admin_required
def userroles():
    form = AdminForm(request.form)
    categories=Categories.query.all()
    admins=Users.query.filter_by(RoleID = 1).all()
    if(request.method == "POST" and form.validate()):
        fullname = form.name.data.rsplit(' ', 1)
        name = fullname[0]
        if (len(fullname) > 1): surname = fullname[1]
        user1 = Users.query.filter_by(Name=name)
        if(user1 != None and len(fullname) > 1):
            user = user1.filter_by(Surname = surname).first()
            if user != None:
                user.RoleID = 1
                db.session.commit()
                flash("Admin ekleme işlemi başarılı.","success")
                return redirect(url_for("userroles"))            
    else:
        return render_template("editUserRoles.html", admins=admins, form=form, categories=categories)
    flash("Böyle bir kullanıcı bulunamadı.","danger")
    return render_template("editUserRoles.html", admins=admins, form=form, categories=categories)

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/addcategory",methods=["GET","POST"])
@login_required
@admin_required
def addcategory():
    form = CategoryForm(request.form)
    if(request.method == "POST" and form.validate()):
        newCat = Categories(Name=form.name.data)
        db.session.add(newCat)
        db.session.commit()
        flash("Kategori ekleme işlemi başarılı.","success")
        return redirect(url_for("addcategory"))
    else:
        return getCategories("addOrEditCategory",form)

@app.route("/addproduct",methods=["GET","POST"])
@login_required
@admin_required
def addproduct():
    form = AddProductForm(request.form)
    categories=Categories.query.all()
    form.category.choices = [(cats.ID,cats.Name) for cats in Categories.query.all()]
    if(request.method == "POST" and form.validate()):
        newProd = Products(Name=form.name.data, Color=form.color.data, Code=form.code.data, CategoryID=form.category.data, Description=form.description.data, UpdateDate=datetime.now(), CreatorID=session["user_id"])
        db.session.add(newProd)
        db.session.commit()
        if(form.photoPath.data != None and form.photoPath.data != ""):
            filename = secure_filename(form.photoPath.data)
            form.photoPath.data = "static/images/ProductImages/" + filename
        else:
            form.photoPath.data = "static/images/venus.png"
        newPhoto = ProductPhotos(ImagePath = form.photoPath.data, ProductID = newProd.ID, UpdateDate=datetime.now(), CreatorID=session["user_id"])
        db.session.add(newPhoto)
        db.session.commit()
        flash("Ürün ekleme işlemi başarılı.","success")
        return redirect(url_for("addproduct"))
    else:
        return render_template("addProduct.html", categories=categories, form=form, product="")


@app.route("/editproduct/<string:id>",methods=["GET","POST"])
@login_required
@admin_required
def editproduct(id):
    form = AddProductForm(request.form)
    form.category.choices = [(cats.ID,cats.Name) for cats in Categories.query.all()]
    categories=Categories.query.all()
    product=Products.query.filter_by(ID=id).first()
    productPhotos=ProductPhotos.query.filter_by(ProductID=id).first()
    if(request.method == "POST" and form.validate()):
        product.Name = form.name.data
        product.Color=form.color.data
        product.Code=form.code.data
        product.CategoryID=form.category.data
        product.Description=form.description.data
        product.UpdateDate=datetime.now()
        if(form.photoPath.data != None and form.photoPath.data != ""):
            filename = secure_filename(form.photoPath.data)
            productPhotos.ImagePath = "static/images/ProductImages/" + filename
        db.session.commit()
        flash("Ürün düzenleme işlemi başarılı.","success")
        return redirect(url_for("index"))
    else:
        return render_template("addProduct.html", form=form, product=product, categories=categories)

@app.route("/favorites")
@login_required
def favorites():
    categories=Categories.query.all()
    favorites=UserFavorites.query.filter_by(UserID = session["user_id"])
    productList = []
    for fav in favorites:
        prod = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter(Products.ID == fav.ProductID).all()
        productList.extend(prod)
    if not productList:
        flash("Buralar ıssız. Hemen favorilerine ürün eklemeye başla!","danger")
    return render_template("myfavorites.html", categories=categories, productList=productList, userFavorites=True)

@app.route("/myaccount",methods=["GET","POST"])
@login_required
def myaccount():
    form = AccountUpdateForm(request.form)
    if(request.method=="POST" and form.validate()):
        email=form.email.data
        query=Users.query.filter_by(Email=email).first()   
        if query != None:
            query.Name = session["name"] = form.name.data
            query.Surname  = session["surname"] = form.surname.data
            query.Email  = session["email"] = form.email.data
            if(form.password.data != None and form.password.data != ""):
                query.Password = sha256_crypt.encrypt(form.password.data)
            db.session.commit()
        flash("Bilgileriniz başarılı bir şekilde güncellendi.","success")
        return getCategories("editProfile",form)
    else:
        return getCategories("editProfile",form)

@app.route("/categories/<string:id>")
def categoryDetails(id):
    category=Categories.query.filter_by(ID=id).first()
    categories=Categories.query.all()
    productList = []
    if(category != None):
        pList = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter(Products.CategoryID == category.ID).order_by(Products.UpdateDate.desc()).all()
        productList.extend(pList)
        if not productList:
            flash("Buralar ıssız. Ürünler en yakın zamanda yüklenecektir.","danger")
        return render_template("productsList.html", productList=productList, categories=categories, name=category.Name)
    else:
        flash("Bu kategoriye erişilemiyor veya böyle bir kategori yok!","danger")
        return redirect(url_for("index")) 

@app.route("/removefavorites/<string:id>")
@login_required
def removefavorites(id):
    product = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter_by(ID=id).first()
    if(product == None):
        flash("Bu ürün artık sitemizde bulunmuyor.","danger")
        return redirect(url_for("favorites"))
    else:        
        favorites = UserFavorites.query.filter_by(UserID = session["user_id"], ProductID = product.Products.ID).first()
        if(favorites != None):   
            db.session.delete(favorites)
            db.session.commit()        
        categories=Categories.query.all()
        favList = UserFavorites.query.filter_by(UserID = session["user_id"])
        productList = []
        for fav in favList:
            prod = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter_by(ID = fav.ProductID).all()
            productList.extend(prod)
        if not productList:
            flash("Buralar ıssız. Hemen favorilerine ürün eklemeye başla!","danger")
        return render_template("myfavorites.html", categories=categories, productList=productList, userFavorites=True)

@app.route("/addfavorites/<string:id>")
@login_required
def addfavorites(id):
    product = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter_by(ID=id).first()
    if(product == None):
        flash("Bu ürün artık sitemizde bulunmuyor.","danger")
        return redirect(url_for("favorites"))
    else:        
        favorites = UserFavorites.query.filter_by(UserID = session["user_id"], ProductID = product.Products.ID).first()
        if(favorites == None):   
            newFav = UserFavorites(UserID=session["user_id"], ProductID=product.Products.ID)
            db.session.add(newFav)
            db.session.commit()        
        categories=Categories.query.all()
        favList = UserFavorites.query.filter_by(UserID = session["user_id"])
        productList = []
        for fav in favList:
            prod = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter_by(ID = fav.ProductID).all()
            productList.extend(prod)

        return render_template("myfavorites.html", categories=categories, productList=productList, userFavorites=True)


@app.route("/deleteCat/<string:id>")
@login_required
@admin_required
def deletecat(id):
    products = Products.query.filter_by(CategoryID=id)
    if(products != None and products.count() > 0):
        flash("Silmek istediğiniz kategoriye tanımlı ürünler bulunuyor. Bu kategoriyi silemezsiniz.","danger")
        return redirect(url_for("addcategory"))        
    else:
        category=Categories.query.filter_by(ID=id).first()    
        if category != None:
            db.session.delete(category)
            db.session.commit()
            return redirect(url_for("addcategory"))
        else:
            flash("Böyle bir kategori yok veya bu işlem için yetkiniz yok","danger")
            return getCategories("index")

@app.route("/deleteAdmin/<string:id>")
@login_required
@admin_required
def deleteadmin(id):
    user = Users.query.filter_by(ID=id).first() 
    if user != None:
        user.RoleID = 2
        db.session.commit()
        return redirect(url_for("userroles"))
    else:
        flash("Böyle bir kullanıcı yok veya bu işlem için yetkiniz yok","danger")
        return getCategories("index")

"""@app.route("/deleteproduct/<string:id>")
@login_required
@admin_required
def deleteadmin(id):
    product = Products.query.filter_by(ID=id).first() 
    if product != None:
        db.session.delete(product)
        db.session.commit()
        return redirect(url_for("userroles"))
    else:
        flash("Böyle bir kullanıcı yok veya bu işlem için yetkiniz yok","danger")
        return getCategories("index")"""

@app.route("/search",methods=["GET","POST"])
def search():
    if request == "GET":
        return redirect(url_for("index"))
    else:
        keyword = str(request.form.get("keyword"))
        categories=Categories.query.all()
        productList=[]
        products = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter(Products.Name.like("%" +keyword+ "%")).all()
        productList.extend(products)
        products1 = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter(Products.Description.like("%" +keyword+ "%")).all()
        productList.extend(products1)
        products2 = db.session.query(Products, ProductPhotos).join(Products, ProductPhotos.ProductID == Products.ID).filter(Products.Code.like("%" +keyword+ "%")).all()
        productList.extend(products2)
        productList = list(set(productList))

        return render_template("productsList.html", categories=categories, productList=productList) 

class Users(db.Model):
    ID = db.Column(db.Integer,primary_key=True)
    Name = db.Column(db.String(100))
    Surname = db.Column(db.String(100))
    Email = db.Column(db.String(200),unique=True,nullable=False)
    Password = db.Column(db.String(200),nullable=False)
    BirthdayDate = db.Column(db.Date)
    StartedDate = db.Column(db.Date)
    RoleID = db.Column(db.Integer)

class Categories(db.Model):
    ID = db.Column(db.Integer,primary_key=True)
    Name = db.Column(db.String(100))

class Products(db.Model):
    ID = db.Column(db.Integer,primary_key=True)
    Name = db.Column(db.String(100))
    Color = db.Column(db.String)
    Code = db.Column(db.String(100))
    CategoryID = db.Column(db.Integer)
    Description = db.Column(db.String)
    UpdateDate = db.Column(db.Date)
    CreatorID = db.Column(db.Integer)

class ProductPhotos(db.Model):
    ID = db.Column(db.Integer,primary_key=True)
    ImagePath = db.Column(db.String)
    ProductID = db.Column(db.Integer)
    UpdateDate = db.Column(db.Date)
    CreatorID = db.Column(db.Integer)

class UserFavorites(db.Model):
    ID = db.Column(db.Integer,primary_key=True)
    UserID = db.Column(db.Integer)
    ProductID = db.Column(db.Integer)

class AccountRoles(db.Model):
    ID = db.Column(db.Integer,primary_key=True)
    Name = db.Column(db.String(100))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)