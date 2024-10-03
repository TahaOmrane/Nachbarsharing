from flask import Blueprint, request, jsonify, render_template, flash, url_for
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from werkzeug.utils import redirect
from models import db, User, Tool, BorrowingHistory,Favorite
from datetime import datetime

main = Blueprint('main', __name__)


@main.route('/submit-tool', methods=['GET', 'POST'])
@login_required
def submit_tool():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        available_from = datetime.strptime(request.form['available_from'], '%Y-%m-%d')
        available_until = datetime.strptime(request.form['available_until'], '%Y-%m-%d')
        condition = request.form['condition']
        deposit = float(request.form.get('deposit')) 
        if available_from > available_until:
            flash('Das Anfangsdatum darf nicht nach dem Enddatum liegen.', 'error')
            return redirect(url_for('main.submit_tool'))

       
        new_tool = Tool(
            name=name,
            description=description,
            available_from=available_from,
            available_until=available_until,
            availability='available',  
            condition=condition,  
            deposit_required=deposit,  
            owner_id=current_user.id
        )
        print("added tool")
        db.session.add(new_tool)
        db.session.commit()
        tools=Tool.query.all()
        for tool in tools:
            print(tool.name, tool.description, tool.available_from, tool.available_until, tool.condition, tool.deposit_required, tool.owner_id, tool.borrowed_by_id)
        flash('Werkzeug erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('dashboard'))  

    return render_template('submit_tool.html')

@main.route('/explore', methods=['GET'])
@login_required
def explore():
    tools = Tool.query.filter(Tool.owner_id != current_user.id).all()

    for tool in tools:
        print(tool.name, tool.description, tool.available_from, tool.available_until, tool.condition, tool.deposit_required, tool.owner_id, tool.borrowed_by_id)

    return render_template('explore.html', tools=tools)

@main.route('/tool/<int:tool_id>', methods=['GET', 'POST'])
@login_required
def tool_detail(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    if request.method == 'POST':
        if not tool.borrowed_by_id:
            borrowing = BorrowingHistory(
                tool_id=tool.id,
                borrower_id=current_user.id,
                lender_id=tool.owner_id
            )
            tool.borrowed_by_id = current_user.id

            db.session.add(borrowing)
            db.session.commit()

            flash('Werkzeug erfolgreich ausgeliehen!', 'success')
            return redirect(url_for('main.borrowing_history'))
        else:
            flash('Werkzeug ist derzeit nicht verfügbar.', 'error')

    return render_template('tool_detail.html', tool=tool)

def check_tool_availability(tool_id, start_date, end_date):
    conflicts = BorrowingHistory.query.filter(
        BorrowingHistory.tool_id == tool_id,
        BorrowingHistory.return_date >= start_date,  
        BorrowingHistory.borrow_date <= end_date    
    ).all()
    for conflict in conflicts:
        print(conflict.lender_id)

    return len(conflicts) == 0  

def borrow_tool(user_id, tool_id, start_date, end_date):
    tool = Tool.query.get(tool_id)

    if not tool:
        return "Tool not found."

    if not check_tool_availability(tool_id, start_date, end_date):
        return "Tool is not available during this period."

    borrowing_entry = BorrowingHistory(
        tool_id=tool.id,
        borrower_id=user_id,
        lender_id=tool.owner_id,
        borrow_date=start_date,
        return_date=end_date
    )

    db.session.add(borrowing_entry)

    tool.borrowed_by_id = user_id
    db.session.commit()

    return "Tool successfully borrowed."

@main.route('/borrow/<int:tool_id>', methods=['POST'])
def borrow_tool_route(tool_id):
    user_id = current_user.id  # Assuming Flask-Login for current user
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

    message = borrow_tool(user_id, tool_id, start_date, end_date)

    flash(message)
    return redirect(url_for('main.tool_detail', tool_id=tool_id))


@main.route('/borrowing-history')
@login_required
def borrowing_history():
    borrowed_tools = BorrowingHistory.query.filter_by(borrower_id=current_user.id).all()

    lent_tools = BorrowingHistory.query.filter_by(lender_id=current_user.id).all()
    for history in borrowed_tools:
        print(history.borrower_id,history.lender_id)

    return render_template('borrowing_history.html', borrowed_tools=borrowed_tools, lent_tools=lent_tools)


@main.route('/friends')
@login_required
def friends():
    friends = current_user.friends
   
    return render_template('friends.html', friends=friends)


@main.route('/add_friend/<string:username>', methods=['POST'])
@login_required
def add_friend(username):
    friend = User.query.filter_by(username=username).first()

    if friend and friend != current_user:
        if friend not in current_user.friends:
            current_user.friends.append(friend)
            db.session.commit()
            flash(f'{friend.username} wurde als Freund hinzugefügt!', 'success')
        else:
            flash(f'{friend.username} ist bereits dein Freund!', 'info')
    else:
        flash(f'Benutzer {username} wurde nicht gefunden!', 'danger')

    return redirect(url_for('main.add_friend_page'))



@main.route('/remove_friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    friend = User.query.get(friend_id)

    if friend and friend in current_user.friends:
        current_user.friends.remove(friend)
        db.session.commit()
        flash(f'{friend.username} wurde aus deiner Freundesliste entfernt.', 'success')
    else:
        flash('Freund wurde nicht gefunden.', 'danger')

    return redirect(url_for('main.friends'))


@main.route('/add_friend_page', methods=['GET'])
@login_required
def add_friend_page():
    search = request.args.get('search', '')
    if search:
        users = User.query.filter(User.username.like(f"%{search}%")).filter(User.id != current_user.id).all()
    else:
        users = User.query.filter(User.id != current_user.id).all()

    return render_template('add_friend.html', users=users)


@main.route('/favorite-tool/<int:tool_id>', methods=['POST'])
@login_required
def favorite_tool(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    
    # Check if the tool is already favorited
    existing_favorite = Favorite.query.filter_by(user_id=current_user.id, tool_id=tool.id).first()
    
    if not existing_favorite:
        favorite = Favorite(user_id=current_user.id, tool_id=tool.id, neighbor_id=tool.owner_id)
        db.session.add(favorite)
        db.session.commit()
        flash('Tool added to favorites!', 'success')
    else:
        flash('Tool is already in favorites.', 'info')

    return redirect(url_for('main.tool_detail', tool_id=tool.id))

@main.route('/favorites')
@login_required
def favorites():
    favorite_items = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', favorite_items=favorite_items)


from flask import render_template
from models import User

@main.route('/ranks')
def ranks():
    top_lenders = User.query.all()
    top_borrowers = User.query.all()
    
    top_lenders = [user for user in top_lenders if  len(user.tools) >= 5]
    top_borrowers = [user for user in top_borrowers if len(user.borrowing_history) >= 5]
    
    return render_template('ranks.html', top_lenders=top_lenders, top_borrowers=top_borrowers)
