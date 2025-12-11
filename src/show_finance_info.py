import streamlit as st
import os


from utils.supabase_integration import SupabaseClient
from utils import configs

from utils.braintree_integration import sync_transactions_last_n_days
from utils.agentmail_integration import process_messages

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


def email_check():
    if st.button("Trigger email check"):
        finance_allowed_list=configs.finance_approved_list
        params={'allowed_senders':finance_allowed_list}
        st.write(f"Params are: {params=}")
        process_messages(st.write,'finance@aiclubagent.com',['unread'], ['processed'],['unread'], params)
    
def finance_chat():
    st.title("Finance Chat")
    client = ChatOpenAI(model="gpt-4o-mini")

    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    msgs=[]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        if message['role']=='user':
            msgs.append(HumanMessage(message['content']))
        if message['role']=='assistant':
            msgs.append(AIMessage(message['content']))

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        msgs.append(HumanMessage(prompt))

        with st.chat_message("assistant"):
            response = client.invoke(msgs)
            st.markdown(response.content)
        st.session_state.messages.append({"role": "assistant", "content": response.content})

def show_finance_agent():
    #st.title("Finance Agent")
    tab1,tab2=st.tabs(["Email check","Chat"])
    with tab1:
        email_check()
    with tab2:
        finance_chat()

            
def show_braintree():
    st.title("BrainTree")
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])

    days=st.sidebar.number_input("Sync Days", value=3)
    if st.sidebar.button("Sync"):
        with st.spinner("Syncing...", show_time=True):
            #st.warning("Sorry - Sync not implemented yet.")
            cb = configs.braintree
            #print(f"Debug: {cb=}")
            mid,pubk,prik=cb['BRAINTREE_MERCHANT_ID'],cb['BRAINTREE_PUBLIC_KEY'],cb['BRAINTREE_PRIVATE_KEY']
            print(f"Debug2:{mid=}, {pubk=}, {prik=}")
            transactions=sync_transactions_last_n_days(supabase,days,mid,pubk,prik)
            #st.write(transactions) 
    ndays=st.number_input("Number of days", value=3000)
    trs=supabase.get_braintree_last_n_days(ndays)
    df = pd.DataFrame(trs)
    df.drop(columns=["order_id", "customer_id", "merchant_account_id", "payment_instrument_type"], inplace=True)
    st.write(f"Displaying {len(df)} records for lookback of {ndays} days")
    st.dataframe(df, hide_index=True )   