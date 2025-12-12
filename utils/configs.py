import os

auth: dict[str, str]
braintree: dict[str, str]
calendar: dict[str, str]
gdrive_secrets: dict[str, str]
gmail_oauth: dict[str, str]
env: dict[str, str]

finance_approved_list={
    'chrissy.hildebrandt@pyxeda.ai',
    'amitamit@gmail.com'
}

def load(secrets: dict):
    global auth, braintree, calendar, gdrive_secrets, gmail_oauth, env
    auth = secrets.get("auth", {})
    braintree = secrets.get("braintree", {})
    calendar = secrets.get("calendar", {})
    gdrive_secrets = secrets.get("gdrive_secrets", {})
    gmail_oauth = secrets.get("gmail_oauth", {})
    env = secrets.get("env", {})

    for k, v in env.items():
        os.environ[k] = str(v)