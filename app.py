from flask import Flask, redirect, render_template, request, url_for, session, flash, jsonify
from sqlalchemy import create_engine, text
import os

app = Flask(__name__)

# Configure the database connection
DATABASE_URL = "postgresql://cv2599:cv2599@w4111.cisxo09blonu.us-east-1.rds.amazonaws.com/w4111"
engine = create_engine(DATABASE_URL)

app = Flask(__name__)
app.secret_key = os.urandom(12)

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Debug prints to see values being received
        print("Email:", email)
        print("Password:", password)

        # Check in the database for user credentials
        with engine.connect() as connection:
            query = text("SELECT user_id, spec_user FROM Users WHERE email = :email AND password = :password")
            result = connection.execute(query, {"email": email, "password": password}).fetchone()

            if result:
                user_id, spec_user = result

                # Store user details in session
                session['user_id'] = user_id
                session['spec_user'] = spec_user

                if spec_user == "Guest":
                    # Fetch guest_id from the Guest table
                    guest_query = text("""
                        SELECT guest_id FROM Guest WHERE user_id = :user_id
                    """)
                    guest_result = connection.execute(guest_query, {"user_id": user_id})
                    guest_row = guest_result.fetchone()

                    if guest_row:
                        session['guest_id'] = guest_row[0]  # Store guest_id in session
                    else:
                        flash("Guest not found.", "danger")
                        return redirect(url_for("login"))

                    return redirect(url_for("guest_home"))
                elif spec_user == 'Staff':
                    return redirect(url_for('staff_home'))  # You may have a different staff home page
            else:
                return "Invalid email or password, please try again."

    return render_template("login.html")

@app.route("/guestregister", methods=["GET", "POST"])
def guest_register():
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        phonenumber = request.form.get('phonenumber')
        spec_user = "Guest"  # Default value for all entries

        print("First Name:", first_name)
        print("Last Name:", last_name)
        print("Email:", email)
        print("Password:", password)
        print("Phone Number:", phonenumber)

        # Insert the new user into the Users table
        with engine.connect() as connection:
            insert_user_query = text("""
                INSERT INTO Users (first_name, last_name, spec_user, password, phonenumber, email) 
                VALUES (:first_name, :last_name, :spec_user, :password, :phonenumber, :email) 
                RETURNING user_id
            """)

            result = connection.execute(insert_user_query, {
                "first_name": first_name,
                "last_name": last_name,
                "spec_user": spec_user,
                "password": password,
                "phonenumber": phonenumber,
                "email": email
            })

            user_id = result.fetchone()[0]  # Get the generated user_id

            update_guest_query = text("""
                INSERT INTO Guest (user_id) 
                VALUES (:user_id)
                RETURNING guest_id
            """)
            result = connection.execute(update_guest_query, {"user_id": user_id})
            #guest_id = result.fetchone()[0]  
            # Get the generated guest_id

        return redirect(url_for('home'))  # Redirect to the main page after successful registration

    return render_template("guestregister.html")

@app.route("/guesthome")
def guest_home():
    # Check if user is logged in and is a guest
    if 'user_id' in session and session.get('spec_user') == 'Guest':
        user_id = session['user_id']
        return render_template("guesthome.html", user_id=user_id)
    else:
        return redirect(url_for('login'))

@app.route("/client_page", methods=["GET", "POST"])
def client_page():
    if 'guest_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    guest_id = session['guest_id']

    with engine.connect() as connection:
        # Check if guest_id is in the Client table
        client_query = text("SELECT client_id FROM Client WHERE guest_id = :guest_id")
        result = connection.execute(client_query, {"guest_id": guest_id})
        client_row = result.fetchone()

        if client_row:
            # Get client_id
            client_id = client_row[0]

            # Query for Personal Inventory
            personal_inventory_query = text("""
                SELECT i.name, i.artist, i.photo_url, i.location, i.volume, 
                       i.comment, i.net_worth, io.status
                FROM Item_in i
                JOIN Inventory_owned io ON i.inventory_id = io.inventory_id
                JOIN Client c ON io.client_id = c.client_id
                WHERE c.client_id = :client_id
            """)
            personal_inventory = connection.execute(personal_inventory_query, {"client_id": client_id}).fetchall()

            # Query for Browse Art Pieces
            browse_art_pieces_query = text("""
                SELECT a.name AS art_piece_name, ar.name AS artist_name, a.type, 
                       a.genre, a.price, a.photo_url
                FROM ArtPieces_Produce a
                JOIN Artists_Collaborates ar ON a.artist_id = ar.artist_id
            """)
            browse_art_pieces = connection.execute(browse_art_pieces_query).fetchall()

            return render_template("client.html", client_id=client_id, 
                                   personal_inventory=personal_inventory, 
                                   browse_art_pieces=browse_art_pieces)
        else:
            # If guest_id is not in Client, prompt for bank account number
            if request.method == "POST":
                bank_account = request.form.get("bank_account")
                if bank_account:
                    # Insert new entry into Client table
                    insert_client_query = text("""
                        INSERT INTO Client (guest_id, bank_account) VALUES (:guest_id, :bank_account)
                        RETURNING client_id
                    """)
                    result = connection.execute(insert_client_query, {
                        "guest_id": guest_id,
                        "bank_account": bank_account
                    })
                    client_id = result.fetchone()[0]
                    return render_template("client.html", client_id=client_id)

            # If not a POST request, render the modal to collect bank account
            return render_template("client_modal.html")

@app.route("/visitor", methods=["GET"])
def visitor():
    if 'guest_id' not in session:
        return redirect(url_for("login"))

    # Retrieve exhibitions and tickets for the user
    with engine.connect() as connection:
        # Get the visitor_id from the Visitor table based on the guest_id in the session
        visitor_query = text("""
            SELECT visitor_id FROM Visitor WHERE guest_id = :guest_id
        """)
        visitor_result = connection.execute(visitor_query, {"guest_id": session['guest_id']})
        visitor_row = visitor_result.fetchone()

        if visitor_row:
            visitor_id = visitor_row[0]

            # Get tickets for the user
            my_tickets_query = text("""
                SELECT A.exhibition_id, E.name, E.exhib_date, E.start_time, E.end_time, E.description, 
                       G.name AS gallery_name, D.city
                FROM Attend A
                JOIN Exhibitions_Host E ON A.exhibition_id = E.exhibition_id
                JOIN ArtGallery G ON E.gallery_id = G.gallery_id
                JOIN Address D ON G.location = D.address_id
                WHERE A.visitor_id = :visitor_id
            """)
            my_tickets = connection.execute(my_tickets_query, {"visitor_id": visitor_id}).fetchall()

            # Get available exhibitions
            exhibitions_query = text("""
                SELECT E.exhibition_id, E.name, E.exhib_date, E.start_time, E.end_time, E.description, E.gallery_id,
                       G.name AS gallery_name, D.city
                FROM Exhibitions_Host E
                JOIN ArtGallery G ON E.gallery_id = G.gallery_id
                JOIN Address D ON G.location = D.address_id
                WHERE E.exhibition_id NOT IN (SELECT exhibition_id FROM Attend WHERE visitor_id = :visitor_id)
            """)
            exhibitions = connection.execute(exhibitions_query, {"visitor_id": visitor_id}).fetchall()

            return render_template("visitor.html", my_tickets=my_tickets, exhibitions=exhibitions)

    return render_template("visitor.html", my_tickets=[], exhibitions=[])


@app.route("/delete_ticket", methods=["POST"])
def delete_ticket():
    if 'guest_id' not in session:
        return redirect(url_for("login"))

    exhibition_id = request.form.get("exhibition_id")

    with engine.connect() as connection:
        # Get visitor_id from Visitor table
        visitor_query = text("""
            SELECT visitor_id FROM Visitor WHERE guest_id = :guest_id
        """)
        visitor_result = connection.execute(visitor_query, {"guest_id": session['guest_id']})
        visitor_row = visitor_result.fetchone()

        if visitor_row:
            visitor_id = visitor_row[0]

            # Delete the ticket from the Attend table
            delete_query = text("""
                DELETE FROM Attend WHERE exhibition_id = :exhibition_id AND visitor_id = :visitor_id
            """)
            connection.execute(delete_query, {"exhibition_id": exhibition_id, "visitor_id": visitor_id})

    return redirect(url_for("visitor"))


#@app.route("/visitor", methods=["GET", "POST"])
@app.route("/visitor", methods=["GET"])
def visitor_page():
    # Get search parameters from the form
    name = request.args.get('name')
    exhib_date = request.args.get('exhib_date')
    start_time = request.args.get('start_time')
    city = request.args.get('city')

    # Construct the base query with JOIN
    query = """
        SELECT e.exhibition_id, e.name, e.exhib_date, e.start_time, e.end_time, e.description, e.gallery_id, g.name AS gallery_name, a.city
        FROM Exhibitions_Host e
        JOIN ArtGallery g ON e.gallery_id = g.gallery_id
        JOIN Address a ON g.location = a.address_id
        WHERE (e.name ILIKE :name OR :name IS NULL)
          AND (e.exhib_date = :exhib_date OR :exhib_date IS NULL)
          AND (e.start_time = :start_time OR :start_time IS NULL)
          AND (a.city ILIKE :city OR :city IS NULL)
    """

    # Execute the query and fetch results
    with engine.connect() as connection:
        result = connection.execute(text(query), {
            "name": f"%{name}%" if name else None,
            "exhib_date": exhib_date if exhib_date else None,
            "start_time": start_time if start_time else None,
            "city": f"%{city}%" if city else None
        })
        exhibitions = result.fetchall()

    # Pass the results to the template
    return render_template("visitor.html", exhibitions=exhibitions)

@app.route("/get_ticket", methods=["POST"])
def get_ticket():
    if 'guest_id' not in session:
        return jsonify({"message": "User not logged in."}), 401

    guest_id = session['guest_id']
    data = request.get_json()
    exhibition_id = data.get('exhibition_id')
    gallery_id = data.get('gallery_id')

    try:
        with engine.connect() as connection:
            # Check if guest_id is already in Visitor table
            check_visitor_query = text("SELECT visitor_id FROM Visitor WHERE guest_id = :guest_id")
            result = connection.execute(check_visitor_query, {"guest_id": guest_id})
            visitor_row = result.fetchone()

            # If guest_id is not in Visitor table, insert it
            if visitor_row is None:
                insert_visitor_query = text("INSERT INTO Visitor (guest_id) VALUES (:guest_id) RETURNING visitor_id")
                result = connection.execute(insert_visitor_query, {"guest_id": guest_id})
                visitor_id = result.fetchone()[0]  # Get the new visitor_id
            else:
                visitor_id = visitor_row[0]  # Get the existing visitor_id

            # Insert into Attend table
            insert_attend_query = text("""
                INSERT INTO Attend (exhibition_id, gallery_id, visitor_id)
                VALUES (:exhibition_id, :gallery_id, :visitor_id)
            """)
            connection.execute(insert_attend_query, {
                "exhibition_id": exhibition_id,
                "gallery_id": gallery_id,
                "visitor_id": visitor_id
            })

            # Fetch the details of the booked exhibition to send back to the client
            exhibition_query = text("""
                SELECT E.name, E.exhib_date, E.start_time, E.end_time, E.description, 
                       G.name AS gallery_name, D.city
                FROM Exhibitions_Host E
                JOIN ArtGallery G ON E.gallery_id = G.gallery_id
                JOIN Address D ON G.location = D.address_id
                WHERE E.exhibition_id = :exhibition_id
            """)
            exhibition = connection.execute(exhibition_query, {"exhibition_id": exhibition_id}).fetchone()

            if exhibition:
                return jsonify({
                    "message": "Ticket successfully booked!",
                    "exhibition": {
                        "name": exhibition.name,
                        "exhib_date": exhibition.exhib_date.strftime("%Y-%m-%d"),
                        "start_time": exhibition.start_time.strftime("%H:%M:%S"),
                        "end_time": exhibition.end_time.strftime("%H:%M:%S"),
                        "description": exhibition.description,
                        "gallery_name": exhibition.gallery_name,
                        "city": exhibition.city
                    }
                })
            else:
                return jsonify({"message": "Exhibition not found."}), 404

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route("/logout")
def logout():
    # Clear the session data and redirect to the login page
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)