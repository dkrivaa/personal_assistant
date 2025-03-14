import base64


def encode_string(string):
    encoded_string = base64.b64encode(string.encode("utf-8")).decode("utf-8")
    print(encoded_string)


def encode_json(json_file):
    # Read and encode the JSON file
    with open(json_file, "rb") as f:
        encoded_data = base64.b64encode(f.read()).decode("utf-8")

    print(encoded_data)  # This is your encoded Base64 string


encode_json('credentials.json')