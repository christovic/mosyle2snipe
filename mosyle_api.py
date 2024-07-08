import json
import requests
import logging
from datetime import datetime, timedelta

class MosyleConnection:
    def __init__(self, url, api_key, username, password):
        self.s = requests.Session()
        self.url = url
        self.access_token_expiry = datetime.now() + timedelta(hours=24)
        access_token, self.access_token_expiry = self.get_token(api_key, username, password)
        self.access_token_expiry = datetime.strptime(self.access_token_expiry, "%a, %d %b %Y %H:%M:%S %Z")
        logging.info(self.access_token_expiry > datetime.now())
        logging.info(f"""api_key: {api_key}
        username: {username}
        password: {password}""")

        self.headers = {
            "Authorization": f"{access_token}",
            "accessToken": f"{api_key}",
            'Content-Type': 'application/json'
        }
        payload = {
            "operation": "list",
            "options": {
                "os": "mac"
            }
        }
        response = requests.post(f"{self.url}/devices", headers=self.headers, json=payload)
        if response.status_code != 200:
            logging.error(f"Failed to get authenticate with Mosyle:\nHTTP Status Code: {response.status_code}\nResponse: {response.text}")

            raise ConnectionError("Failed to connect to Mosyle")

    def get_token(self, api_key, username, password):
        headers = {
            "accessToken": api_key
        }
        json = {
            "email": username,
            "password": password
        }
        request = requests.Request(
            "POST",
            f"{self.url}/login",
            headers=headers,
            json=json
        )
        response, validated = self.validate_request(request)
        if validated:
            r_headers = response.headers
            return r_headers['Authorization'], r_headers['Expires']


    def validate_request(self, request):
        if self.access_token_expiry <= datetime.now():
            self.get_token()
            return
        prepped = request.prepare()
        response = self.s.send(prepped)
        if response.status_code != 200:
            logging.info(f"Failed to get devices from Mosyle:\nHTTP Status Code: {response.status_code}\nResponse: {response.text}")
            return response, False
        if 'status' in json.loads(response.text) and \
            json.loads(response.text)['status'] != "OK":
            logging.info(f"Failed to get devices from Mosyle:\nHTTP Status Code: {response.status_code}\nResponse: {response.text}")
            return response, False
        return response, True

    def get_devices(self, device_type, specific_columns=None):
        fail = 1
        page = 1
        payload = {
            "operation": "list",
            "options": {
                "os": device_type,
                "page": page
            }
        }
        if specific_columns is not None:
            payload['options']['specific_columns'] = specific_columns
        all_devices = []
        while fail > 0 and fail <= 3:
            request = requests.Request("POST", f"{self.url}/devices", headers=self.headers, json=payload)
            response, validated = self.validate_request(request)
            if not validated:
                fail = fail + 1
                continue
            mosyle_response = json.loads(response.text)['response'][0]
            if 'status' in mosyle_response and mosyle_response['status'] == "DEVICES_NOTFOUND":
                fail = 0
                break
            for device in mosyle_response['devices']:
                all_devices.append(device)
            payload['options']['page'] = payload['options']['page'] + 1
        return all_devices
    
    def update_devices(self, serial_number, provided_payload):
        fail = 1
        payload = {
            "operation": "update_device",
            "serialnumber": serial_number,
        }
        payload = payload | provided_payload
        while fail > 0 and fail <= 3:
            request = requests.Request("POST", f"{self.url}/devices", headers=self.headers, json=payload)
            response, validated = self.validate_request(request)
            if validated:
                break
            else:
                fail = fail + 1
                continue
        return fail < 4
            
