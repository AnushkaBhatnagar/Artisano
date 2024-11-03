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

@app.route("/client")
def client_page():
    # Only allow access if user is logged in and is a guest
    if 'user_id' in session and session.get('spec_user') == 'Guest':
        return render_template("client.html")
    else:
        return redirect(url_for('login'))

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

    print("Guest ID:", guest_id)
    print("Exhibition ID:", exhibition_id)
    print("Gallery ID:", gallery_id)

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

        return jsonify({"message": "Ticket successfully booked!"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route("/logout")
def logout():
    # Clear the session data and redirect to the login page
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)