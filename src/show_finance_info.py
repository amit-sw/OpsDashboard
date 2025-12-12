import streamlit as st
import os
import pandas as pd
import time

import uuid

from utils.supabase_integration import SupabaseClient
from utils import configs

from utils.braintree_integration import sync_transactions_last_n_days
from utils.agentmail_integration import process_messages
from utils.finance_graph import FinancebotAgent

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

DEFAULT_DAYS=91
DEFAULT_FULL_INFO=365*10

def format_revenue(title: str, sdf: pd.DataFrame, scol: str, n: int) -> str:
    df = sdf.sort_values(scol, ascending=False).copy()
    df = df.head(n)
    df[scol] = df[scol].astype(str)
    lines = [f"{getattr(row, scol)} {row.amount}" for row in df.itertuples(index=False)]
    lines_str="\n".join(lines)

    # Wrap with separators
    result = f"\n*********\n{title}\n\n\n{lines_str} \n*********"
    return result

@st.cache_data(ttl=3600)
def get_cached_braintree_info(_supabase, num_days):
    records=_supabase.get_basic_braintree_info(DEFAULT_DAYS)
    return records

@st.cache_data(ttl=3600)
def get_braintree_info(_supabase,days):
    supabase=_supabase
    records=supabase.get_braintree_last_n_days(DEFAULT_DAYS)
    df6=pd.DataFrame(records)
    st.caption("Braintree info")
    #st.dataframe(df6)
    #combined="Background information:\n"+"\n".join(records)
    return df6
    

def email_check():
    if st.sidebar.button("Trigger email check"):
        finance_allowed_list=configs.finance_approved_list
        params={'allowed_senders':finance_allowed_list}
        st.write(f"Params are: {params=}")
        process_messages(st.write,'finance@aiclubagent.com',['unread'], ['processed'],['unread'], params)
    
def finance_chat_old():
    st.title("Finance Chat")
    client = ChatOpenAI(model="gpt-4o-mini")
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])

    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    revenue_str=get_cached_braintree_info(supabase,DEFAULT_DAYS)
    xx=get_braintree_info(supabase,DEFAULT_DAYS)
    core_msg=revenue_str
    msgs=[HumanMessage(core_msg)]

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
        
def finance_chat():
    st.title("Finance Chat")
    client = ChatOpenAI(model="gpt-4o-mini")
    app=FinancebotAgent(os.environ["OPENAI_API_KEY"])
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])

    msgs=[]
    
    if "revenue_str" not in st.session_state:
        revenue_str=get_cached_braintree_info(supabase,DEFAULT_DAYS)
        st.session_state.revenue_str = revenue_str
    
    if "messages" not in st.session_state:
        st.session_state.messages=[]
        
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
            #response = client.invoke(msgs)
            rsp=app.graph.invoke({'messages': st.session_state.messages, 'revenue_str':st.session_state.revenue_str}, {"configurable":{"thread_id":uuid.uuid4()}})
            #st.sidebar.json(rsp)
            for k,v in rsp.items():
                if k == "response":
                    st.markdown(v)
                    st.session_state.messages.append({"role": "assistant", "content": v})

def show_finance_agent():
    #st.title("Finance Agent")
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
    start_ts = time.perf_counter()
    with st.spinner("Pre-loading...", show_time=True):
        revenue_str=get_cached_braintree_info(supabase,DEFAULT_DAYS)
    with st.sidebar:
        st.caption(f"Pre-load finished in {time.perf_counter() - start_ts:.2f} seconds")
        #st.download_button(label="Download CSV",data=cmb,file_name="data.txt",icon=":material/download:",)
    email_check()
    st.divider()
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
