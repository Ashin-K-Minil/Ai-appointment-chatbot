import re
import mysql.connector
from datetime import datetime
import google.generativeai as genai

# Add your api_key over here
API_KEY = ''

genai.configure(api_key=API_KEY)

llm = genai.GenerativeModel("gemini-pro")
chat = llm.start_chat()

#Prompting the LLM model to behave as an appointment booking chatbot 
def generate_response(prompt):
    full_prompt = f"""
    You are an AI assistant focused solely on booking appointments and kindly do ask for the age of the user. 
    Maintain a professional and friendly tone. Stick strictly to the appointment booking context.
    To all other questions reply you don't know.
    """
    response = chat.send_message(prompt+full_prompt)
    if hasattr(response, 'parts'):
        result = ''.join([part.text for part in response.parts])
    else:
        result = response.candidates[0].content if response.candidates else "Sorry, no response received."
    return result.strip()

#Connecting the database "appointment-db"
# Add your db details mentioned below
def get_db_connection():
    return mysql.connector.connect(
        host = '',
        user = '',
        password = '',
        database = ''
    )

#Fetching the available time slots for appointment booking
def fetch_available_slots():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        query = "SELECT time_slot FROM time_slots WHERE status = 'Available'"
        cursor.execute(query)
        available_slots = cursor.fetchall()
        return [slot[0] for slot in available_slots]
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def insert_user_details_and_book_slot(name, email, phone, age, time_slot):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Inserting the user details into the `users` table
        user_query = """INSERT INTO users (name, email, phone, age) VALUES (%s, %s, %s, %s)"""
        user_values = (str(name), str(email), str(phone), int(age))
        cursor.execute(user_query, user_values)
        connection.commit()

        # Fetching the user_id of the inserted user
        user_id = cursor.lastrowid

        # Updating the time_slots table with the selected time slot, current date, and user_id
        date_today = datetime.now().strftime('%Y-%m-%d')
        slot_query = """UPDATE time_slots SET status = 'booked', user_id = %s, Date = %s WHERE time_slot = %s"""
        slot_values = (user_id, date_today, str(time_slot))
        cursor.execute(slot_query, slot_values)
        connection.commit()

        print(f"Appointment for {name} at {time_slot} successfully booked!")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
#Using the LLM model to extract name from the user input
def extract_name(prompt):
    full_prompt = f"""Extract the person's name, including any initials, from the following user input. If an initial (a single uppercase letter) precedes a name, retain the initial and capitalize the first letter of each part of the name (e.g., 'S Hafid'). Ensure proper capitalization where the first letter of each word is uppercase and the rest are lowercase. If no name is found, respond with 'No name found.' User input: {prompt}"""
    response = llm.generate_content(full_prompt)
    return response.text.strip()
#Using the LLM model to extract user's email-id from the user input
def extract_email(prompt):
    full_prompt = f"""Extract the email address from the following user input. If no email is found, respond with 'No email found.' User input: {prompt}"""
    response = llm.generate_content(full_prompt)
    return response.text.strip()
#Using the regex to extract mobile number from the user input
def extract_phone(response):
    pattern = r'\b\d{10}\b'
    phone = re.findall(pattern, response)
    return "".join(phone[0]) if phone else None
#Using the regular expression to extract age from the user input
def extract_age(response):
    pattern = r'\b\d{1,3}\b'
    age = re.findall(pattern, response)
    return int(age[0]) if age else None
#Using the LLM model to extract time slot from the user input
def extract_time(prompt):
    full_prompts = f"""Available time slots [9:00AM, 10:00AM, 11:00AM, 12:00PM, 1:00PM, 2:00PM, 3:00PM, 4:00PM, 5:00PM, 6:00PM, 7:00PM, 8:00PM, 9:00PM]. Match the time slots from the list with the user input. User input: {prompt}"""
    response = llm.generate_content(full_prompts)
    return response.text.strip()

#Designing the chatbot to obtain user details and perform appointment booking for the users
class Chatbot:
    def __init__(self):
        self.user_data = {}
        self.current_state = "greeting"
        self.available_slots = fetch_available_slots()
        self.conversation_history = []

    def process_input(self, user_input):
        self.conversation_history.append(f"Human: {user_input}")
        
        slots = ", ".join(self.available_slots)
        
        if self.current_state == "greeting":
            prompt = "Greet the user and only ask for their name to book an appointment. Strictly don't give example of writing the name to the user"
            self.current_state = "ask_name"
        elif self.current_state == "ask_name":
            name = extract_name(user_input)
            if name and name != 'No name found.':
                self.user_data['name'] = name
                prompt = f"Thank {name} and ask for their email address."
                self.current_state = "ask_email"
            else:
                prompt = "The response didn't contain a clear name. Ask for their name again."
        elif self.current_state == "ask_email":
            email = extract_email(user_input)
            if email and email != 'No email found.':
                self.user_data['email'] = email
                prompt = "Ask for the user's phone number, strictly don't give examples for typing the phone number to the user"
                self.current_state = "ask_phone"
            else:
                prompt = "The response didn't contain a valid email. Ask for their email again."
        elif self.current_state == "ask_phone":
            phone = extract_phone(user_input)
            if phone:
                self.user_data['phone'] = phone
                prompt = "Only ask for the user's age and don't tell extra informations."
                self.current_state = "ask_age"
            else:
                prompt = "The response didn't contain a valid phone number. Ask for their phone number again."
        elif self.current_state == "ask_age":
            age = extract_age(user_input)
            if age and 1 <= age <= 120:
                self.user_data['age'] = age
                prompt = f"Thank the user for providing their information. Offer these available appointment slots: {slots}, strictly display the slots as bulletin. Ask which time they prefer."
                self.current_state = "offer_slots"
            else:
                prompt = "The response didn't contain a valid age. Ask for their age again."
        elif self.current_state == "offer_slots":
            extracted_time = extract_time(user_input)
            if extracted_time in self.available_slots:
                self.user_data['appointment_slot'] = extracted_time
                prompt = f"Ask the user to confirm if they want to book the appointment for {extracted_time}."
                self.current_state = "confirm_slot"
            else:
                prompt = f"The selected time is not available. Offer these slots again: {slots}. Ask which time they prefer."
        elif self.current_state == "confirm_slot":
            if "yes" in user_input.lower() or "confirm" in user_input.lower():
                insert_user_details_and_book_slot(
                    self.user_data['name'],
                    self.user_data['email'],
                    self.user_data['phone'],
                    self.user_data['age'],
                    self.user_data['appointment_slot']
                )
                prompt = f"Appointment confirmed for {self.user_data['appointment_slot']}. Thank the user and ask if there's anything else regarding the appointment."
                self.current_state = "appointment_booked"
            else:
                prompt = f"The user didn't confirm. Offer these available slots again: {slots}. Ask which time they prefer."
                self.current_state = "offer_slots"
        else:
            prompt = "Inform the user that you can only assist with appointment booking. Ask if there's anything else they need help with regarding their appointment."

        response = generate_response(prompt)
        self.conversation_history.append(f"Assistant: {response}")
        return response

if __name__ == "__main__":
    bot = Chatbot()
    print("Chatbot: Welcome. Please let me know if you have any questions or require assistance.")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit', 'bye', 'thank', 'no thank you', "that's all"]:
            print("Chatbot: Thank you for using our service. Goodbye!")
            break
        response = bot.process_input(user_input)
        print(f"Chatbot: {response}")