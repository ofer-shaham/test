
from datetime import datetime, timedelta
from flask import Blueprint
from flask import jsonify, request
from flaskr import db
from flaskr.library.Book import Book

from flask import Flask, request, jsonify
from flaskr.library.Copy import Copy
from flaskr.library.Loan import Loan
from flask import g

from flaskr.library.Member import Member
from flask import session
from flaskr.auth.models import User
from flaskr.auth.views import login_required


app = Flask(__name__)
bpBooks = Blueprint("book", __name__, url_prefix="/api")


@bpBooks.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get("user_id")

    if user_id is not None:
        g.user = db.session.get(User, user_id)
    else:
        g.user = None


@bpBooks.route('/books', methods=['GET', 'POST'])
@login_required
def books():
    if request.method == 'GET':
        # Return a list of all books
        books = db.session.query(Book).all()
        # return jsonify([book.to_dict() for book in books])
        dicted = ([book.to_dict() for book in books])
        return jsonify({'success': True, 'result': dicted}), 200

    elif request.method == 'POST':
        # authorization
        if (g.user.is_admin == False):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        # Add a new book to the library
        data = request.get_json()
        new_book = Book(title=data['title'], author_id=data['author_id'], ISBN=data['ISBN'],
                        publication_date=data['publication_date'], genre=data['genre'])
        db.session.add(new_book)
        db.session.commit()
        return jsonify({'success': True, 'result': new_book.to_dict()}), 201


@bpBooks.route('/books/<int:book_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def book(book_id):
    book = db.session.query(Book).get(book_id)
    if request.method == 'GET':
        # Return a single book
        return jsonify({'success': True, 'result': book.to_dict()})
    elif request.method == 'PUT':
        if (g.user.is_admin == False):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        # Update an existing book
        # update only if property is present in the request
        data = request.get_json()
        if 'title' in data:
            book.title = data['title']
        if 'author_id' in data:
            book.author_id = data['author_id']
        if 'ISBN' in data:
            book.ISBN = data['ISBN']
        if 'publication_date' in data:
            book.publication_date = data['publication_date']
        if 'genre' in data:
            book.genre = data['genre']
        db.session.commit()

        db.session.commit()
        return jsonify({'success': True, 'result': book.to_dict()}), 200

    if request.method == 'DELETE':
        if (g.user.is_admin == False):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        # Delete an existing book
        db.session.delete(book)
        db.session.commit()
        return jsonify({'success': True, 'result': {'id': book_id}}), 200


@bpBooks.route('/books/search', methods=['GET'])
@login_required
def search_books():
    """Search for books by title and/or author and available copies"""
    """available is set to 1 if the user wants to search for available books only"""
    books = []

    title = request.args.get('title')
    authorNickname = request.args.get('author')
    # cast to boolean to match the model type
    available = request.args.get('available') == '1'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    query = None

    # if parameter is not set, or it's empty convert to None or set default value
    if title == '':
        title = None
    if authorNickname == '':
        authorNickname = None
    if available == '':
        available = None
    if page == '':
        page = 1
    if per_page == '':
        per_page = 10

    if (title is None and authorNickname is None and available is None):
        # no filters
        query = db.session.query(Book)
    else:
        query = Book.search(title=title, authorNickname=authorNickname,
                            available=available)

    pagination = query.paginate(page=page, per_page=per_page)
    books = pagination.items
    # if items not found, return empty list

    dicted = ([book.to_dict() for book in books])
    return jsonify({'success': True, 'result': dicted}), 200


# @ bpBooks.route('/books/<int:book_id>/copies', methods=['GET'])
# @login_required
# def query_copies(book_id):
#     if (g.user.is_admin == False):
#         return jsonify({'success': False, 'error': 'Unauthorized'}), 401
#     book = Book.query.get(book_id)
#     if not book:
#         return jsonify({'success': False, 'error': 'Book not found'}), 404
#     copies = Copy.query.filter_by(book_id=book_id).all()
#     output = []
#     for copy in copies:
#         copy_data = {}
#         copy_data['id'] = copy.id
#         copy_data['book_id'] = copy.book_id
#         copy_data['ISBN'] = copy.ISBN
#         copy_data['checkout_date'] = copy.checkout_date
#         copy_data['due_date'] = copy.due_date
#         output.append(copy_data)
#     return jsonify({'success': True, 'result': {'copies': output}})


@ bpBooks.route("/books/copies/<int:copy_id>/checkout", methods=["POST"])
@login_required
def check_out_copy(copy_id):
    copy = Copy.query.get(copy_id)
    if copy is None:
        return jsonify({'success': False, "error": "Copy not found"}), 404
    if not copy.isAvailable():
        return jsonify({'success': False, "error": "Copy not available"}), 400

    member_id = request.json.get("member_id")
    member = Member.query.get(member_id)
    if member is None:
        return jsonify({'success': False, "error": "Member not found"}), 404

    loan = Loan.create_loan(copy, member)
    db.session.add(loan)
    db.session.commit()
    return jsonify({'success': True, 'result': "Copy checked out successfully"}), 200


@bpBooks.route("/books/copies/<int:copy_id>/checkin", methods=["POST"])
@login_required
def check_in_copy(copy_id):
    copy = Copy.query.get(copy_id)

    if copy is None:
        return jsonify({'success': False, "error": "Copy not found"}), 404
    if copy.isAvailable():
        return jsonify({'success': False, "error": "Copy already checked in"}), 400
    # if g.user.is_admin == False and g.user.id != copy.loan.member_id:
    # if copy.loan and copy.loan.member_id == !=is None:
        # return jsonify({'success': False, "error": "Copy not checked out by user"}), 400
    if g.user.id == copy.loan.member_id:
        Loan.return_loan(copy)
        db.session.commit()
        return jsonify({"success": True, 'result': "Copy checked in successfully"}), 200
    else:
        return jsonify({'success': False, "error": "Copy not checked out by user"}), 400
