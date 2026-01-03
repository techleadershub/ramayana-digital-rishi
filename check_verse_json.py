
import json

def check_verse():
    try:
        with open('Valmiki_Ramayan_Shlokas.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Structure of JSON is likely a list of objects or a dict
        # Based on previous tools I've seen, it might be a flat list of verses or hierarchical.
        # Let's inspect the first element to know the structure if needed, but first let's just search.
        
        print(f"Total items in JSON: {len(data)}")
        
        if isinstance(data, list):
            found_sarga_27 = False
            sarga_27_verses = []
            
            for item in data:
                # Normalizing keys just in case
                kanda = item.get('kanda', '').strip()
                sarga = item.get('sarga')
                shloka = item.get('shloka') or item.get('verse_number')
                
                if 'Aranya' in kanda and str(sarga) == '27':
                    found_sarga_27 = True
                    sarga_27_verses.append(int(shloka))
                    if str(shloka) == '39':
                        print("FOUND: Aranya Kanda 27:39 exists in JSON.")
                        return

            if found_sarga_27:
                print(f"Aranya Kanda Sarga 27 exists. Veres found: {sorted(sarga_27_verses)}")
                print("MISSING: Aranya Kanda 27:39 NOT found in JSON.")
            else:
                print("MISSING: Aranya Kanda Sarga 27 NOT found in JSON.")
        else:
            print("JSON structure is not a list?", type(data))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_verse()
