import os
import random
from google.cloud import firestore
from datetime import datetime, timedelta

# Initialize Firestore
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "assignment2-362c8-firebase-adminsdk-3ajwf-42b1cba715.json"
db = firestore.Client()

# Password for Mr. Johnson
mr_johnson_password = "password123"


def get_cars_from_firestore():
    cars_ref = db.collection('Cars')
    cars = []
    for doc in cars_ref.stream():
        car_data = doc.to_dict()
        car_data['id'] = doc.id
        cars.append(car_data)
    return cars


def view_reservations(reservations):
    print("\nCurrent Reservations:")
    if not reservations:
        print("No current reservations.")
    else:
        for reservation in reservations:
            print(
                f"Reservation ID: {reservation['id']}, "
                f"Car ID: {reservation['car_id']}, "
                f"Start: {reservation['start_time']}, "
                f"End: {reservation['end_time']}")


def list_available_cars(cars):
    print("\nAvailable Cars:")
    if not cars:
        print("No cars available.")
    else:
        for car in cars:
            print(f"{car['Type']}: {car['Year']} {car['Color']} {car['Model']} "
                  f"\n ID: {car['id']} "
                  f"\n Price: {car.get('Price')} per day")


def show_blocked_dates(car):
    blocked_dates = []
    reservations_table = car.get('Reservation', [])

    for i in range(0, len(reservations_table), 3):
        reservation_id = reservations_table[i]  # Get reservation ID
        start_date = datetime.strptime(reservations_table[i + 1], "%m/%d/%Y").date()
        end_date = datetime.strptime(reservations_table[i + 2], "%m/%d/%Y").date()
        blocked_dates.append((reservation_id, start_date, end_date))

    if blocked_dates:
        print("Blocked dates for this car:")
        for reservation_id, start, end in blocked_dates:
            print(f"Reservation ID: {reservation_id}, From {start} to {end}")
    else:
        print("No blocked dates for this car.")


def generate_unique_reservation_id(reservations):
    existing_ids = {reservations[i] for i in range(0, len(reservations), 3)}
    while True:
        reservation_id = random.randint(10000, 99999)
        if reservation_id not in existing_ids:
            return reservation_id


def calculate_price(start_time, end_time, daily_rate):
    num_days = (end_time - start_time).days + 1
    total_price = num_days * daily_rate
    if num_days >= 7:
        total_price -= 10
    return total_price, num_days


def make_reservation(car, start_time, end_time):
    if start_time <= (datetime.now().date() + timedelta(days=1)):
        print("Reservation must be made at least 1 day in advance.")
        return

    reservations_table = car.get('Reservation', [])
    for i in range(0, len(reservations_table), 3):
        reserved_start = datetime.strptime(reservations_table[i + 1], "%m/%d/%Y").date()
        reserved_end = datetime.strptime(reservations_table[i + 2], "%m/%d/%Y").date()

        if not (end_time < reserved_start or start_time > reserved_end):
            print("Car is not available for the requested time.")
            show_blocked_dates(car)
            return

    reservation_id = generate_unique_reservation_id(reservations_table)
    daily_rate = car.get('Price')
    total_due, num_days = calculate_price(start_time, end_time, daily_rate)

    new_reservation = [reservation_id, start_time.strftime("%m/%d/%Y"), end_time.strftime("%m/%d/%Y")]
    car['Reservation'] = reservations_table + new_reservation

    # Save back to Firestore
    db.collection('Cars').document(car['id']).set(car, merge=True)
    print(f"Reservation made successfully. Your Reservation ID is: {reservation_id} "
          f"\nTotal due at pickup for {num_days} day(s): ${total_due} "
          f"\nSave your ID.")

    if num_days >= 7:
        print('You saved: ' + str(10 * num_days))


def request_extension(cars):
    while True:
        try:
            reservation_id = int(input("Enter reservation ID: "))
            break
        except ValueError:
            print("Invalid input. Please enter a ID.")
    car_id = input("Enter the car ID associated with the reservation: ")

    # Find the specified car
    car = next((car for car in cars if car['id'] == car_id), None)
    if not car:
        print("Car ID not found.")
        return

    # Get current reservations
    reservations_table = car.get('Reservation', [])
    reservation_index = -1

    # Check if the reservation ID exists
    for i in range(0, len(reservations_table), 3):
        if reservations_table[i] == reservation_id:
            reservation_index = i
            break

    if reservation_index == -1:
        print("Reservation ID not found.")
        return

    # Get the current return date
    current_end_date = datetime.strptime(reservations_table[reservation_index + 2], "%m/%d/%Y").date()

    # Request new return date
    new_end_date_str = input("Enter the new return date (MM/DD/YYYY): ")
    try:
        new_end_date = datetime.strptime(new_end_date_str, "%m/%d/%Y").date()
    except ValueError:
        print("Invalid date format. Please use MM/DD/YYYY.")
        return

    if new_end_date <= current_end_date:
        print("New return date must be after the current return date.")
        return

    # Check for conflicting reservations
    for i in range(0, len(reservations_table), 3):
        if i != reservation_index:
            reserved_start = datetime.strptime(reservations_table[i + 1], "%m/%d/%Y").date()
            reserved_end = datetime.strptime(reservations_table[i + 2], "%m/%d/%Y").date()

            if not (new_end_date < reserved_start or current_end_date > reserved_end):
                print("Cannot extend reservation due to a conflict with another reservation.")
                return

    # Calculate the new price using the calculate_price function
    daily_rate = car.get('Price')
    total_price_extension, num_days_extended = calculate_price(datetime.strptime(reservations_table[reservation_index + 1], "%m/%d/%Y").date(), new_end_date, daily_rate)

    # Update the reservation with the new return date
    reservations_table[reservation_index + 2] = new_end_date.strftime("%m/%d/%Y")
    car['Reservation'] = reservations_table

    # Save back to Firestore
    db.collection('Cars').document(car['id']).set(car, merge=True)

    print(f"Reservation extended successfully. New return date is: {new_end_date.strftime('%m/%d/%Y')}.")
    print(f"New total price for the extension: ${total_price_extension:.2f}")


def reservation_form(cars):
    car_id = input("Enter the ID of the car you want to reserve: ")
    car = next((car for car in cars if car['id'] == car_id), None)

    if car:
        show_blocked_dates(car)

        while True:
            start_date_str = input("Enter the start date (MM/DD/YYYY): ")
            end_date_str = input("Enter the end date (MM/DD/YYYY): ")

            try:
                start_time = datetime.strptime(start_date_str, "%m/%d/%Y").date()
                end_time = datetime.strptime(end_date_str, "%m/%d/%Y").date()
                if start_time > end_time or start_time < (datetime.now().date()):
                    print("Valid and current dates must be entered.")
                    continue
                break
            except ValueError:
                print("Invalid date format. Please use MM/DD/YYYY.")

        make_reservation(car, start_time, end_time)
    else:
        print("Car ID not found.")


def delete_reservation(car, reservation_id):
    reservations = car.get('Reservation', [])
    for i in range(0, len(reservations), 3):
        if reservations[i] == reservation_id:
            del reservations[i:i + 3]
            car['Reservation'] = reservations
            db.collection('Cars').document(car['id']).set(car, merge=True)
            print(f"Reservation ID {reservation_id} has been deleted.")
            return
    print("Reservation ID not found.")


def manage_reservations(cars):
    while True:
        print("\nManage Reservations Menu:")
        print("1. View Cars")
        print("2. Select Car to View Reservations")
        print("3. Delete Reservation")
        print("4. Exit")
        choice = input("Select an option: ")

        if choice == '1':
            list_available_cars(cars)
        elif choice == '2':
            car_id = input("Enter the car ID to view reservations: ")
            car = next((car for car in cars if car['id'] == car_id), None)
            if car:
                show_blocked_dates(car)
            else:
                print("Car ID not found.")
        elif choice == '3':
            car_id = input("Enter the car ID to delete a reservation: ")
            car = next((car for car in cars if car['id'] == car_id), None)
            if car:
                reservation_id = int(input("Enter the Reservation ID to delete: "))
                delete_reservation(car, reservation_id)
            else:
                print("Car ID not found.")
        elif choice == '4':
            print("Exiting the menu.")
            break
        else:
            print("Invalid choice, please try again.")


def add_car():
    print("Add a New Car")
    car_type = input("Enter car type (Sedan, SUV, Pick-up, Van, etc.): ")

    while True:
        try:
            year = int(input("Enter car year: "))
            break
        except ValueError:
            print("Invalid input. Please enter a valid year.")

    color = input("Enter car color: ")
    model = input("Enter car make (BMW, Honda, Toyota, etc.): ")

    # Create car ID in the format year_make
    car_id = f"{year}_{model}"

    # Set a default price for the car
    while True:
        try:
            price = float(input("Enter price per day (minimum $15): "))
            # Check if the price has more than 2 decimal places
            if round(price, 2) != price:
                print("Price cannot exceed two decimal places. Please enter a valid price.")
                continue
            if price < 15:
                print("Price needs to be greater than $15.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid price.")

    new_car = {
        "Type": car_type,
        "Year": year,
        "Color": color,
        "Model": model,
        "Price": price,
        "Reservation": [],
        "id": car_id
    }

    # Add the new car to Firestore using the car_id as the document name
    db.collection('Cars').document(car_id).set(new_car)
    print(f"Car added successfully with ID: {car_id}")


def edit_car_price(cars):
    car_id = input("Enter the ID of the car you want to edit the price for: ")
    car = next((car for car in cars if car['id'] == car_id), None)

    if car:
        while True:
            try:
                new_price = float(input("Enter the new price per day: "))
                if round(new_price, 2) != new_price:
                    print("Price cannot exceed two decimal places. Please enter a valid price.")
                    continue
                if new_price < 15:
                    print("Price needs to be greater than $15.")
                    continue
                car['Price'] = new_price
                # Update Firestore with the new price
                db.collection('Cars').document(car['id']).set(car, merge=True)
                print(f"The price for {car['Year']} {car['Model']} has been updated to ${new_price} per day.")
                break
            except ValueError:
                print("Invalid input. Please enter a valid price.")
    else:
        print("Car ID not found.")


def access_mr_johnson_menu():
    password = input("Enter Admin password (password123): ")
    if password == mr_johnson_password:
        mr_johnson_menu()
    else:
        print("Incorrect password. Access denied.")


def mr_johnson_menu():
    while True:
        print("\n Admin Menu:")
        print("1. Manage Reservations")
        print("2. Add a Car (Do not enter duplicate year and model)")
        print("3. Edit Car Price (minimum $15)")
        print("4. See Cars")
        print("5. Exit")
        choice = input("Select an option: ")

        if choice == '1':
            manage_reservations(get_cars_from_firestore())
        elif choice == '2':
            add_car()
        elif choice == '3':
            edit_car_price(get_cars_from_firestore())
        elif choice == '4':
            list_available_cars(get_cars_from_firestore())
        elif choice == '5':
            print("Exiting the menu.")
            break
        else:
            print("Invalid choice, please try again.")


def client_interface():
    while True:
        print("\nClient Interface Menu:")
        print("1. Make Reservation")
        print("2. Request Reservation Extension")
        print("3. See Cars")
        print("4. Exit")
        choice = input("Select an option: ")

        if choice == '1':
            list_available_cars(get_cars_from_firestore())
            reservation_form(get_cars_from_firestore())
        elif choice == '2':
            request_extension(get_cars_from_firestore())
        elif choice == '3':
            list_available_cars(get_cars_from_firestore())
        elif choice == '4':
            print("Exiting the client interface.")
            break
        else:
            print("Invalid choice, please try again.")


def main_menu():
    while True:
        print("\nMain Menu:")
        print("1. Client Interface")
        print("2. Admin Interface")
        print("3. Exit")
        choice = input("Select an option: ")

        if choice == '1':
            client_interface()
        elif choice == '2':
            access_mr_johnson_menu()
        elif choice == '3':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice, please try again.")


# Start the program
main_menu()
