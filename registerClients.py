import json

import requests


def register_account(email, password, module):
    url = "http://127.0.0.1:8080/account/register"
    data = {
        "guid": email,
        "newGUID": email,
        "newPassword": password,
        "name": email.split('@')[0]  # Assuming the name is the part before the '@' in the email
    }

    response = requests.post(url, data=data)

    if response.status_code == 200:
        print(f"Account {email} registered successfully.")
        with open("account.json", "r") as f:
            accounts_data = json.load(f)
        # Check if the account already exists
        if any(account['email'] == email for account in accounts_data["accounts"]):
            print(f"Account {email} already exists in account.json.")
            return
        accounts_data["accounts"].append({
            "email": email,
            "password": password,
            "module": module
        })

        with open("account.json", "w") as f:
            json.dump(accounts_data, f, indent=4)
    else:
        print(f"Failed to register account {email}. Status code: {response.status_code}")
def number_to_chars(number):
    chars = ""
    while number >= 0:
        chars = chr(97 + (number % 26)) + chars
        number = number // 26 - 1
    return chars

def register_accounts(name, amount):
    accId = 0
    for i in range(amount):
        curName = f"{name}{number_to_chars(accId)}"
        email = f"{curName}@gmail.com"
        password = "password"
        register_account(email, password, "afk")
        accId += 1
        print(f"Registered {email} with password {password}")

if __name__ == "__main__":
    register_accounts("player", 100)
    #register_account("newuserp@example.com", "newpassword123", "afk")
