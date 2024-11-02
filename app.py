from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import create_engine, text

app = Flask(__name__)

# Configure the database connection
DATABASE_URL = "postgresql://cv2599:cv2599@w4111.cisxo09blonu.us-east-1.rds.amazonaws.com/w4111"
engine = create_engine(DATABASE_URL)

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("index.html")

@app.route('/guestlogin', methods=['GET', 'POST'])
def guest_login():
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        print("Email:", email)
        print("Password:", password)

        if email and password:
            # Executing raw SQL query
            with engine.connect() as connection:
                result = connection.execute(text("SELECT * FROM users WHERE spec_user='Guest' AND email = :email AND password = :password"), 
                                            {"email": email, "password": password})
                user = result.fetchone()  # Fetch the first matching user

            if user:
                return "Login successful!"
            else:
                return "Invalid credentials."

    return render_template("guestlogin.html")

@app.route('/stafflogin', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        print("Email:", email)
        print("Password:", password)

        if email and password:
            # Executing raw SQL query
            with engine.connect() as connection:
                result = connection.execute(text("SELECT * FROM users WHERE spec_user='Staff' AND email = :email AND password = :password"), 
                                            {"email": email, "password": password})
                user = result.fetchone()  # Fetch the first matching user

            if user:
                return "Login successful!"
            else:
                return "Invalid credentials."

    return render_template('stafflogin.html')

@app.route("/guestregister", methods=["GET", "POST"])
def guest_register():
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone_number = request.form.get('phone_number')
        spec_user = "Guest"  # Default value for all entries
        bank_account = request.form.get('bank_account')  # Only for clients
        user_type = request.form.get('user_type')  # Dropdown selection

        # Insert the new user into the Users table
        with engine.connect() as connection:
            insert_user_query = text("""
                INSERT INTO Users (first_name, last_name, spec_user, password, phonenumber, email) 
                VALUES (:first_name, :last_name, :spec_user, :password, :phone_number, :email) 
                RETURNING user_id
            """)
            result = connection.execute(insert_user_query, {
                "first_name": first_name,
                "last_name": last_name,
                "spec_user": spec_user,
                "password": password,
                "phonenumber": phone_number,
                "email": email
            })

            user_id = result.fetchone()[0]  # Get the generated user_id

            update_guest_query = text("""
                INSERT INTO Guest (user_id) 
                VALUES (:user_id)
                RETURNING guest_id
            """)
            result = connection.execute(update_guest_query, {"user_id": user_id})
            guest_id = result.fetchone()[0]  # Get the generated guest_id

            # Update the appropriate table based on user_type
            if user_type == 'Visitor':
                update_visitor_query = text("""
                    INSERT INTO Visitor (guest_id) 
                    VALUES (:guest_id)
                """)
                connection.execute(update_visitor_query, {"guest_id": guest_id})

            elif user_type == 'Client':
                update_client_query = text("""
                    INSERT INTO Client (guest_id, bank_account) 
                    VALUES (:guest_id, :bank_account)
                """)
                connection.execute(update_client_query, {
                    "guest_id": guest_id,
                    "bank_account": bank_account
                })

        return redirect(url_for('home'))  # Redirect to the main page after successful registration

    return render_template("guestregister.html")

if __name__ == '__main__':
    app.run(debug=True)
