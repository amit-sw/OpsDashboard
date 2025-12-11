import os
from agentmail import AgentMail

from email.utils import parseaddr

def process_email(client,inbox,msg,params):
    # Python example
    reply = client.inboxes.messages.reply(
        inbox_id=inbox,
        message_id=msg.message_id,
        text="Thanks you - you are allowed to send this, and we are allowed to disregard!")

    print(f"Reply sent successfully with ID: {reply.message_id}")
    
def deny_email(client,inbox,msg,params):
    # Python example
    reply = client.inboxes.messages.reply(
        inbox_id=inbox,
        message_id=msg.message_id,
        text="Thanks you - you are not on the official allowed list, and we are reporting to the authorities!")

    print(f"Reply sent DENY with ID: {reply.message_id}")


    

def process_one_message(client,mailbox,msg, params):
    print(f"About to process message {msg}")
    name,email=parseaddr(msg.from_)
    allowed_sender = email in params.get("allowed_senders")
    if allowed_sender:
        process_email(client,mailbox,msg,params)
    else:
        deny_email(client,mailbox,msg,params)
    

def process_messages(mailbox='finance@aiclubagent.com',search_labels=['unread'], add_labels=['processed'],remove_labels=['unread'], params={}):
    client = AgentMail(api_key=os.getenv('AGENTMAIL_API_KEY'))
    msgs=client.inboxes.messages.list(inbox_id=mailbox, labels=search_labels)
    for msg in msgs.messages:
        process_one_message(client, mailbox, msg, params)
        message_id=msg.message_id
        print(f"AgentMail: Updating. {message_id=}, {add_labels=}, {remove_labels=}, {mailbox=}")
        client.inboxes.messages.update(
            inbox_id=mailbox,
            message_id=message_id,
            add_labels=add_labels,
            remove_labels=remove_labels,
        )
        
