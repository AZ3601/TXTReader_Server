import os

from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# 定义书籍模型
class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    coverUrl = db.Column(db.String(200), nullable=True)  # 允许封面URL为空
    filePath = db.Column(db.String(200), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'coverUrl': self.coverUrl,
            'filePath': self.filePath
        }


# 定义用户模型
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(80), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username
        }


# 定义用户书架模型
class UserBookshelf(db.Model):
    __tablename__ = 'user_bookshelf'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id
        }


# 初始化数据库
with app.app_context():
    db.create_all()

    # 添加初始化数据
    if not Book.query.first():
        books = [
            Book(title="The Great Gatsby", author="F. Scott Fitzgerald", coverUrl="https://example.com/gatsby.jpg",
                 filePath="contents/1.txt"),
            Book(title="To Kill a Mockingbird", author="Harper Lee", coverUrl="https://example.com/mockingbird.jpg",
                 filePath="mockingbird.txt"),
            Book(title="1984", author="George Orwell", coverUrl="https://example.com/1984.jpg", filePath="3.txt")
        ]
        db.session.add_all(books)
        db.session.commit()

    if not User.query.first():
        users = [
            User(username="user1", password="password1"),
            User(username="user2", password="password2"),
            User(username="user3", password="password3")
        ]
        db.session.add_all(users)
        db.session.commit()


# 上传书籍
@app.route('/upload_book', methods=['POST'])
def upload_book():
    title = request.form.get('title')
    author = request.form.get('author')
    cover_file = request.files.get('coverImage')
    content_file = request.files.get('contentFile')

    if not title or not author or not content_file:
        return jsonify({'message': 'Missing required fields'}), 400

    # 保存封面图片（如果存在）
    cover_path = None
    if cover_file:
        cover_filename = cover_file.filename
        cover_path = os.path.join('covers', cover_filename)
        cover_file.save(cover_path)

    # 保存内容文件
    content_filename = content_file.filename
    content_path = os.path.join('contents', content_filename)
    content_file.save(content_path)

    # 创建书籍记录
    new_book = Book(
        title=title,
        author=author,
        coverUrl=cover_path,
        filePath=content_path
    )
    db.session.add(new_book)
    db.session.commit()

    return jsonify({'message': 'Book uploaded successfully'}), 201


# 获取书籍列表
@app.route('/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    print("1\n")
    return jsonify([book.to_dict() for book in books])


# 获取单个书籍
@app.route('/get_book/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get(book_id)
    if book:
        return jsonify(book.to_dict())
    return jsonify({'message': 'Book not found'}), 404


# 获取书籍内容
@app.route('/get_book_content/<int:book_id>', methods=['GET'])
def get_book_content(book_id):
    book = db.session.get(Book, book_id)
    print(book)
    if book:
        print(2)
        return send_from_directory('contents', os.path.basename(book.filePath))
    return jsonify({'message': 'Book not found'}), 404


# 添加用户
@app.route('/register', methods=['POST'])
def register():
    data = request.form
    username = data['username']
    password = data['password']

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201


# 登录
@app.route('/login', methods=['POST'])
def login():
    data = request.form
    username = data['username']
    password = data['password']

    user = User.query.filter_by(username=username, password=password).first()
    if user:
        return jsonify({'message': 'Login successful', 'user_id': user.id}), 200
    return jsonify({'message': 'Invalid username or password'}), 401


# 获取用户书架上的书籍
@app.route('/get_user_bookshelf/<int:user_id>', methods=['GET'])
def get_user_bookshelf(user_id):
    user = User.query.get(user_id)
    if user:
        bookshelf = UserBookshelf.query.filter_by(user_id=user_id).all()
        book_ids = [item.book_id for item in bookshelf]
        books = Book.query.filter(Book.id.in_(book_ids)).all()
        return jsonify([book.to_dict() for book in books])
    return jsonify({'message': 'User not found'}), 404


# 添加书籍到用户书架
@app.route('/add_to_bookshelf', methods=['POST'])
def add_to_bookshelf():
    data = request.form
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    print(user_id)
    print(book_id)

    if not user_id or not book_id:
        return jsonify({'message': 'Missing required fields'}), 400

    user = User.query.get(user_id)
    book = Book.query.get(book_id)

    if not user or not book:
        return jsonify({'message': 'User or book not found'}), 404

    # Check if the book is already in the user's bookshelf
    existing_entry = UserBookshelf.query.filter_by(user_id=user_id, book_id=book_id).first()
    if existing_entry:
        return jsonify({'message': 'Book already in bookshelf'}), 409

    # Add the book to the user's bookshelf
    new_entry = UserBookshelf(user_id=user_id, book_id=book_id)
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({'message': 'Book added to bookshelf successfully'}), 201


# 移除书籍从用户书架
@app.route('/remove_from_bookshelf', methods=['POST'])
def remove_from_bookshelf():
    data = request.form
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    print(user_id)
    print(book_id)

    if not user_id or not book_id:
        return jsonify({'message': 'Missing required fields'}), 400

    user = User.query.get(user_id)
    book = Book.query.get(book_id)

    if not user or not book:
        return jsonify({'message': 'User or book not found'}), 404

    # Check if the book is in the user's bookshelf
    existing_entry = UserBookshelf.query.filter_by(user_id=user_id, book_id=book_id).first()
    if not existing_entry:
        return jsonify({'message': 'Book not found in bookshelf'}), 404

    # Remove the book from the user's bookshelf
    db.session.delete(existing_entry)
    db.session.commit()

    return jsonify({'message': 'Book removed from bookshelf successfully'}), 200


if __name__ == '__main__':
    if not os.path.exists('covers'):
        os.makedirs('covers')
    if not os.path.exists('contents'):
        os.makedirs('contents')
    app.run(host='127.0.0.1', port=5000)

# from flask import Flask, jsonify, request, send_from_directory
# from flask_sqlalchemy import SQLAlchemy
#
# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
#
#
# # 定义书籍模型
# class Book(db.Model):
#     __tablename__ = 'books'
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(100), nullable=False)
#     author = db.Column(db.String(100), nullable=False)
#     coverUrl = db.Column(db.String(200), nullable=False)
#     filePath = db.Column(db.String(200), nullable=False)
#
#     def to_dict(self):
#         return {
#             'id': self.id,
#             'title': self.title,
#             'author': self.author,
#             'coverUrl': self.coverUrl,
#             'filePath': self.filePath
#         }
#
#
# # 定义用户模型
# class User(db.Model):
#     __tablename__ = 'users'
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False, index=True)
#     password = db.Column(db.String(80), nullable=False)
#
#     def to_dict(self):
#         return {
#             'id': self.id,
#             'username': self.username
#         }
#
#
# # 定义用户书架模型
# class UserBookshelf(db.Model):
#     __tablename__ = 'user_bookshelf'
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
#     book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
#
#     def to_dict(self):
#         return {
#             'id': self.id,
#             'user_id': self.user_id,
#             'book_id': self.book_id
#         }
#
#
# # 初始化数据库
# with app.app_context():
#     db.create_all()
#
#     # 添加初始化数据
#     if not Book.query.first():
#         books = [
#             Book(title="The Great Gatsby", author="F. Scott Fitzgerald", coverUrl="https://example.com/gatsby.jpg",
#                  filePath="gatsby.txt"),
#             Book(title="To Kill a Mockingbird", author="Harper Lee", coverUrl="https://example.com/mockingbird.jpg",
#                  filePath="mockingbird.txt"),
#             Book(title="1984", author="George Orwell", coverUrl="https://example.com/1984.jpg", filePath="1984.txt")
#         ]
#         db.session.add_all(books)
#         db.session.commit()
#
#     if not User.query.first():
#         users = [
#             User(username="user1", password="password1"),
#             User(username="user2", password="password2"),
#             User(username="user3", password="password3")
#         ]
#         db.session.add_all(users)
#         db.session.commit()
#
#
# # 添加书籍
# @app.route('/add_book', methods=['POST'])
# def add_book():
#     data = request.json
#     new_book = Book(title=data['title'], author=data['author'], coverUrl=data['coverUrl'], filePath=data['filePath'])
#     db.session.add(new_book)
#     db.session.commit()
#     return jsonify({'message': 'Book added successfully'}), 201
#
#
# # 获取书籍列表
# @app.route('/get_books', methods=['GET'])
# def get_books():
#     books = Book.query.all()
#     return jsonify([book.to_dict() for book in books])
#
#
# # 获取单个书籍
# @app.route('/get_book/<int:book_id>', methods=['GET'])
# def get_book(book_id):
#     book = Book.query.get(book_id)
#     if book:
#         return jsonify(book.to_dict())
#     return jsonify({'message': 'Book not found'}), 404
#
#
# # 获取书籍内容
# @app.route('/get_book_content/<int:book_id>', methods=['GET'])
# def get_book_content(book_id):
#     book = Book.query.get(book_id)
#     if book:
#         return send_from_directory('/path/to/your/book/files', book.filePath)
#     return jsonify({'message': 'Book not found'}), 404
#
#
# # 添加用户
# @app.route('/register', methods=['POST'])
# def register():
#     data = request.form
#     username = data['username']
#     password = data['password']
#
#     if User.query.filter_by(username=username).first():
#         return jsonify({'message': 'Username already exists'}), 400
#
#     new_user = User(username=username, password=password)
#     db.session.add(new_user)
#     db.session.commit()
#     return jsonify({'message': 'User registered successfully'}), 201
#
#
# # 登录
# @app.route('/login', methods=['POST'])
# def login():
#     data = request.form
#     username = data['username']
#     password = data['password']
#
#     user = User.query.filter_by(username=username, password=password).first()
#     if user:
#         return jsonify({'message': 'Login successful', 'user_id': user.id}), 200
#     return jsonify({'message': 'Invalid username or password'}), 401
#
#
# # 获取用户书架上的书籍
# @app.route('/get_user_bookshelf/<int:user_id>', methods=['GET'])
# def get_user_bookshelf(user_id):
#     user = User.query.get(user_id)
#     if user:
#         bookshelf = UserBookshelf.query.filter_by(user_id=user_id).all()
#         book_ids = [item.book_id for item in bookshelf]
#         books = Book.query.filter(Book.id.in_(book_ids)).all()
#         return jsonify([book.to_dict() for book in books])
#     return jsonify({'message': 'User not found'}), 404
#
#
# if __name__ == '__main__':
#     app.run(host='127.0.0.1', port=5000)
