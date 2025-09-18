import os

def setup_env_from_dict(dict_env):
    for k in dict_env.keys():
        v=dict_env.get(k)
        #print(f"DEBUG: setup-env-from-dict: {k=},{v=}")
        os.environ[k]=v
        