import streamlit as st
import pandas as pd
from supabase.client import Client, create_client
import os
from dotenv import load_dotenv


# --- Page Configuration ---
st.set_page_config(
    page_title="Sparky AI Agent Dashboard",
    page_icon="🤖",
    layout="wide",
)

# --- Load Environment Variables ---
load_dotenv()

# --- Supabase Connection ---
@st.cache_resource
def init_supabase_client():
    """Initializes and returns the Supabase client."""
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        st.error("Supabase URL or Service Key is missing. Please check your .env file.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

supabase = init_supabase_client()

# --- Data Fetching Functions ---
@st.cache_data(ttl=600)  # Cache data for 10 minutes
def fetch_conversation_history():
    """Fetches all conversation histories from Supabase."""
    response = supabase.table("conversation_history").select("conversation_id, history, updated_at").execute()
    return response.data

@st.cache_data(ttl=600)
def fetch_knowledge_base_info():
    """Fetches information about the knowledge base."""
    response = supabase.table("documents").select("id", count="exact").execute()
    return response.count

@st.cache_data(ttl=600)
def fetch_ingestion_log():
    """Fetches the ingestion log to find the last update time."""
    response = supabase.table("ingestion_log").select("updated_at").order("updated_at", desc=True).limit(1).execute()
    if response.data:
        return response.data[0]['updated_at']
    return None

# --- Main Dashboard Logic ---
def main():
    st.title("🤖 Sparky AI Agent Dashboard")
    st.markdown("### A real-time overview of the IPIC WhatsApp Bot's performance.")

    # --- Fetch Data ---
    conversations = fetch_conversation_history()
    knowledge_base_count = fetch_knowledge_base_info()
    last_ingested = fetch_ingestion_log()

    # --- Process Data ---
    leads = []
    escalations = []
    tool_usage = {}

    for conv in conversations:
        for message in conv.get('history', []):
            if message['type'] == 'ai':
                if "I've scheduled your 7-day free trial" in message['data']['content']:
                    leads.append(conv)
                elif "I've sent these details to our party coordinators" in message['data']['content']:
                    leads.append(conv)
                elif "I've passed your request on to our team" in message['data']['content']:
                    escalations.append(conv)

    # --- Key Metrics ---
    st.header("📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Conversations", f"{len(conversations)} 💬")
    with col2:
        st.metric("Leads Generated", f"{len(leads)} 📈")
    with col3:
        st.metric("Escalations to Human", f"{len(escalations)} 🧑‍💻")
    with col4:
        st.metric("KB Documents", f"{knowledge_base_count} 📄")
        if last_ingested:
            st.markdown(f"**Last Update:** {pd.to_datetime(last_ingested).strftime('%Y-%m-%d %H:%M')}")

    st.divider()

    # --- Visualizations ---
    st.header("📈 Visualizations")
    if conversations:
        df = pd.DataFrame(conversations)
        df['updated_at'] = pd.to_datetime(df['updated_at'])
        df['date'] = df['updated_at'].dt.date

        conv_by_date = df.groupby('date').size().reset_index(name='counts')

        st.subheader("Conversations Over Time")
        st.line_chart(conv_by_date.set_index('date'))

    st.divider()

    # --- Data Tables ---
    st.header("📄 Data Tables")

    tab1, tab2, tab3 = st.tabs(["Recent Conversations", "Leads", "Escalations"])

    with tab1:
        st.subheader("Recent Conversations")
        if conversations:
            sorted_convs = sorted(conversations, key=lambda x: x['updated_at'], reverse=True)
            for conv in sorted_convs[:10]:  # Display top 10 recent
                with st.expander(f"Conversation ID: {conv['conversation_id']}"):
                    for message in conv['history']:
                        st.write(f"**{message['type'].capitalize()}:** {message['data']['content']}")
        else:
            st.info("No conversations yet.")

    with tab2:
        st.subheader("Leads")
        if leads:
            st.table(pd.DataFrame([{
                "Conversation ID": lead['conversation_id'],
                "Last Updated": pd.to_datetime(lead['updated_at']).strftime('%Y-%m-%d %H:%M'),
                "Details": [msg['data']['content'] for msg in lead['history'] if msg['type'] == 'ai' and "I've" in msg['data']['content']][0]
            } for lead in leads]))
        else:
            st.info("No leads generated yet.")

    with tab3:
        st.subheader("Escalations")
        if escalations:
            st.table(pd.DataFrame([{
                "Conversation ID": esc['conversation_id'],
                "Last Updated": pd.to_datetime(esc['updated_at']).strftime('%Y-%m-%d %H:%M'),
                "Details": [msg['data']['content'] for msg in esc['history'] if msg['type'] == 'ai' and "I've passed your request" in msg['data']['content']][0]
            } for esc in escalations]))
        else:
            st.info("No escalations yet.")


if __name__ == "__main__":
    main()