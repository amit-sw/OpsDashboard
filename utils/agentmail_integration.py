import os
from agentmail import AgentMail

from utils.finance_graph import FinancebotAgent

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from email.utils import parseaddr
import uuid

from utils.supabase_integration import SupabaseClient, DEFAULT_DAYS

def process_one_email(fr,to,subject,txt):
    client = ChatOpenAI(model="gpt-4o-mini")
    app=FinancebotAgent(os.environ["OPENAI_API_KEY"])
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
    
    records=supabase.get_basic_braintree_info(DEFAULT_DAYS)
    message=f""" 
    {subject}\n
    {txt}
    """
    messages=[{"role": "user", "content": message}]
    
    rsp=app.graph.invoke({'messages': messages, 'revenue_str':records}, {"configurable":{"thread_id":uuid.uuid4()}})
    answer="Here is what I am thinking:\n\n"
    for k,v in rsp.items():
        if k == "response":
            answer = answer + v
    return answer

def process_email(output,client,inbox,msg,params):
    # Python example
    #output(f"Starting process_email with {msg=}")
    #output(msg.model_dump())
    fr=msg.from_
    to=msg.to
    subject=msg.subject
    txt=msg.preview
    resp=process_one_email(fr,to,subject,txt)
    reply = client.inboxes.messages.reply(
        inbox_id=inbox,
        message_id=msg.message_id,
        text=resp)

    output(f"Reply sent successfully with ID: {reply.message_id}")
    
def deny_email(output,client,inbox,msg,params):
    # Python example
    reply = client.inboxes.messages.reply(
        inbox_id=inbox,
        message_id=msg.message_id,
        text="Apologies - you are not on the official allowed list; we cannot help you! Please email your IT Support to get access.")

    output(f"Reply sent DENY with ID: {reply.message_id}")


    

def process_one_message(output,client,mailbox,msg, params):
    output(f"About to process message {msg}")
    name,email=parseaddr(msg.from_)
    allowed_sender = email in params.get("allowed_senders")
    if allowed_sender:
        process_email(output,client,mailbox,msg,params)
    else:
        deny_email(output,client,mailbox,msg,params)
    

def process_messages(output,mailbox,search_labels, add_labels,remove_labels, params):
    client = AgentMail(api_key=os.getenv('AGENTMAIL_API_KEY'))
    msgs=client.inboxes.messages.list(inbox_id=mailbox, labels=search_labels)
    output(f"Saw {len(msgs.messages)} messages")
    for msg in msgs.messages:
        process_one_message(output,client, mailbox, msg, params)
        message_id=msg.message_id
        output(f"AgentMail: Updating. {message_id=}, {add_labels=}, {remove_labels=}, {mailbox=}")
        client.inboxes.messages.update(
            inbox_id=mailbox,
            message_id=message_id,
            add_labels=add_labels,
            remove_labels=remove_labels,
        )
        
