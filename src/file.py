import json, os

# Serialize an object to json
def to_json(obj):
    return json.dumps(obj, default=lambda obj: obj.__dict__)

# Save the provided data to a json file
def save_file(data, filename):
    try:
        # Get the directory path from the filename
        directory = os.path.dirname(filename)

        # Create the directory if it doesn't exist
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # Open the file and write the data
        with open(filename, 'w') as file:
            file.seek(0)
            json.dump(data, file)
        print(f"File saved successfully: {filename}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Load a json file and return it as an object
def load_file(filename):
  data = None

  try:
    with open(filename, 'r') as file:
      data = json.load(file)

    data = json.loads(data)

  except FileNotFoundError:
    print(f"Error: The file '{filename}' does not exist.")
  except json.JSONDecodeError:
    print("Error: The file could not be decoded. It may not contain valid JSON.")
  except Exception as e:
    print(f"An unexpected error occurred: {e}")

  return data

# Convert an object to dictionary
def to_dict(obj):
    return json.loads(json.dumps(obj, default=lambda o: o.__dict__))
