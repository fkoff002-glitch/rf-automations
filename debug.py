import csv

try:
    # Try opening with utf-8-sig to handle hidden BOM characters
    with open("inventory.csv", "r", encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        print(f"Found {len(headers)} headers:")
        for i, h in enumerate(headers):
            print(f"{i}: '{h}'")
            
        # Check if specific keys exist
        print("\nValidation Check:")
        print(f"Is 'Client_IP' in headers? {'Client_IP' in headers}")
        print(f"Is 'Base_IP' in headers? {'Base_IP' in headers}")
        
        # Try reading one row
        row = next(reader, None)
        if row:
            print("\nFirst Row Data:")
            print(f"Client: {row.get('Client_Name')}")
            print(f"Base IP: {row.get('Base_IP')}")

except Exception as e:
    print(f"Error: {e}")
