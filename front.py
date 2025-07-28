import streamlit as st
from AIbot import Chatbot  # Importing the Chatbot class

EXIT_PHRASES = ['exit', 'quit', 'bye', 'thank', 'no thank you', "that's all"]

def main():
    st.title("📅 Appointment Booking Chatbot")

    # Initializing the session state
    if 'chatbot' not in st.session_state: 
        st.session_state.chatbot = Chatbot()
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'conversation_ended' not in st.session_state:
        st.session_state.conversation_ended = False

    # Displaying the chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if not st.session_state.conversation_ended:
        if prompt := st.chat_input("Type your message here..."):
            # Adding user's message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Checking for exit phrases
            if any(phrase in prompt.lower() for phrase in EXIT_PHRASES):
                response = "Thank you for using our service. Goodbye!"
                st.session_state.conversation_ended = True
            else:
                # Geting chatbot response
                response = st.session_state.chatbot.process_input(prompt)

            # Adding the assistant's response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)

            st.rerun() #Refreshing the Webpage for new conversation
    else:
        st.write("The conversation has ended. Refresh the page to start a new conversation.")

if __name__ == "__main__":
    main()