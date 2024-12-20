import json
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor

import requests
from client import Client

def run_client(account):
    with open("NameDictionary.pkl", "rb") as f:
        nameDictionary = pickle.load(f)

    c = Client(nameDictionary)
    if not c.initializeAccountDetails(account['email'], account['password'], account['module']):
        print(f"Encountered exception in initializing account details for {account['email']}. Quitting.")
        return
    if not c.loadModules():
        print(f"No module was loaded for {account['email']}. Quitting.")
        return
    c.mainLoop()

if __name__ == "__main__":
    with open("account.json", "r") as f:
        accounts = json.load(f)["accounts"]
    client_count = 1#accounts.__len__()
    cores_to_use = 4  # Number of cores you want to use
    clients_per_core = client_count // cores_to_use
    with ThreadPoolExecutor(max_workers=client_count) as executor:
        for i in range(cores_to_use):
            start_index = i * clients_per_core
            end_index = start_index + clients_per_core
            if i == cores_to_use - 1:  # Ensure the last core gets any remaining clients
                end_index = client_count
            executor.map(run_client, accounts[start_index:end_index])